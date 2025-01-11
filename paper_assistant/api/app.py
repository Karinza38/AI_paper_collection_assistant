from flask import Flask, render_template, jsonify, request
import json
from datetime import datetime
import threading
from pathlib import Path
import os
from paper_assistant.core.arxiv_scraper import Paper
from paper_assistant.core.qa_processor import QaProcessor
from paper_assistant.utils.markdown_processor import MarkdownProcessor
from paper_assistant.utils.helpers import get_api_key
from paper_assistant.utils.cache_handler import CacheHandler
from loguru import logger

# Thread-safe progress tracking
progress_lock = threading.Lock()
main_progress = {"running": False, "current": 0, "total": 0, "message": ""}


def update_progress(progress_data):
    """Thread-safe progress update"""
    global main_progress
    with progress_lock:
        main_progress.update(progress_data)


def create_app(template_dir=None, static_dir=None):
    """Create Flask app with configurable paths"""
    # Get package root directory
    package_root = Path(__file__).parent.parent.parent

    # Set default template and static directories relative to package root
    default_template_dir = package_root / "paper_assistant" / "templates"
    default_static_dir = package_root / "paper_assistant" / "api" / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir or default_template_dir),
        static_folder=str(static_dir or default_static_dir),
    )

    # Enable debug mode based on environment variable
    app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    # Initialize cache handler with configurable base directory
    cache_dir = os.getenv("CACHE_DIR", "out/cache")
    cache_handler = CacheHandler(cache_dir)

    # Get API key and initialize processors with proper error handling
    try:
        GEMINI_API_KEY = get_api_key()
        if not GEMINI_API_KEY:
            raise ValueError("API key is empty or invalid")
        qa_processor = QaProcessor(api_key=GEMINI_API_KEY)
        md_processor = MarkdownProcessor()
    except Exception as e:
        app.logger.error(f"Error initializing API key: {str(e)}")
        GEMINI_API_KEY = None
        qa_processor = None
        md_processor = MarkdownProcessor()

    def get_cached_dates():
        """Get list of available cached dates with error handling"""
        try:
            return cache_handler.get_cached_dates()
        except Exception as e:
            app.logger.error(f"Error getting cached dates: {str(e)}")
            return []

    def cache_daily_output():
        """Cache current day's output with proper error handling and thread safety"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")

            # Update progress safely
            update_progress({"running": False, "current": 0, "total": 0, "message": ""})

            # Check if today's cache already exists
            if cache_handler.get_cached_data(f"{today}_output"):
                app.logger.info(f"Cache for {today} already exists")
                return

            # Cache papers if output.json exists
            if os.path.exists("out/output.json"):
                try:
                    with open("out/output.json", "r") as f:
                        papers_data = json.load(f)
                    cache_handler.save_cache_data(f"{today}_output", papers_data)
                except Exception as e:
                    app.logger.error(f"Error caching papers: {str(e)}")

                # Cache authors if available
                try:
                    if os.path.exists("out/all_authors.debug.json"):
                        with open("out/all_authors.debug.json", "r") as f:
                            authors_data = json.load(f)
                        cache_handler.save_cache_data(f"{today}_authors", authors_data)
                except Exception as e:
                    app.logger.error(f"Error caching authors: {str(e)}")

        except Exception as e:
            app.logger.error(f"Error in cache_daily_output: {str(e)}")

    @app.route("/")
    def index():
        """Main route to display papers"""
        if not GEMINI_API_KEY or not qa_processor:
            reason = (
                "No API key" if not GEMINI_API_KEY else "QA processor not initialized"
            )
            return render_template(
                "error.html",
                message=f"API key validation failed. Please check your configuration. Reason: {reason}",
            ), 503

        try:
            # Cache daily output
            cache_daily_output()

            # Get requested date or use latest
            date_param = request.args.get("date")

            # Get list of available dates
            available_dates = get_cached_dates()

            # Check if output files exist
            # TODO: link this with a generate function.
            if not os.path.exists("out/output.json") and not available_dates:
                return render_template(
                    "error.html",
                    message="No paper data available yet. Please wait for the next scheduled update at 9:00 AM EST.",
                ), 503

            # Load papers using cache handler
            if date_param:
                papers_dict = cache_handler.get_cached_data(f"{date_param}_output")
                if papers_dict:
                    display_date = datetime.strptime(date_param, "%Y-%m-%d").strftime(
                        "%B %d, %Y"
                    )
                else:
                    # Fallback to output.json if cache not found
                    with open("out/output.json", "r") as f:
                        papers_dict = json.load(f)
                    display_date = datetime.now().strftime("%B %d, %Y")
            else:
                with open("out/output.json", "r") as f:
                    papers_dict = json.load(f)
                display_date = datetime.now().strftime("%B %d, %Y")

            # Load header content
            with open("paper_assistant/config/header.md", "r") as f:
                header_content = f.read()

            # Load paper topics/criteria
            with open("paper_assistant/config/paper_topics.txt", "r") as f:
                topics_content = f.read()

            # Convert markdown to HTML
            header_html = md_processor.process_content(header_content)
            topics_html = md_processor.process_content(topics_content)

            # Convert the data structure to match Paper class
            papers = []
            for p in papers_dict.values():
                paper_data = {
                    "arxiv_id": p.get("ARXIVID") or p.get("arxiv_id"),
                    "title": p["title"],
                    "abstract": p["abstract"],
                    "authors": p["authors"],
                    "url": f"https://arxiv.org/abs/{p.get('ARXIVID') or p.get('arxiv_id')}",
                    "comment": p.get("COMMENT") or p.get("comment"),
                    "relevance": p.get("RELEVANCE") or p.get("relevance"),
                    "novelty": p.get("NOVELTY") or p.get("novelty"),
                    "criterion": p.get("CRITERION") or p.get("criterion"),
                }
                papers.append(Paper(**paper_data))

            # Sort papers by criterion priority if sort parameter is present
            if request.args.get("sort") == "criterion":
                # Get unique criteria in priority order
                criteria_order = []
                with open("paper_assistant/config/paper_topics.txt", "r") as f:
                    for line in f:
                        if line.strip() and not line.startswith("#"):
                            criteria_order.append(line.strip())

                # Sort papers by criterion priority
                papers.sort(
                    key=lambda x: (
                        criteria_order.index(x.criterion)
                        if x.criterion in criteria_order
                        else len(criteria_order),
                        -(x.relevance or 0),
                        -(x.novelty or 0),
                    )
                )

            # Get the CSS for markdown styling
            markdown_css = md_processor.get_css()

            # Render template with all content
            return render_template(
                "paper_template.html",
                papers=papers,
                date=display_date,
                header_content=header_html,
                topics_content=topics_html,
                available_dates=available_dates,
                current_date=date_param or datetime.now().strftime("%Y-%m-%d"),
                markdown_css=markdown_css,
            )
        except Exception as e:
            app.logger.error(f"Error in index route: {str(e)}")
            return render_template(
                "error.html",
                message="An error occurred while processing the papers. Please try again later.",
            ), 500

    @app.route("/qa_progress/<arxiv_id>")
    def get_qa_progress(arxiv_id):
        """Get the current progress of Q&A generation for a paper"""
        return jsonify(qa_processor.get_progress(arxiv_id))

    @app.route("/get_qa/<arxiv_id>")
    def get_qa(arxiv_id):
        try:
            # Get the date parameter or use current date
            date_param = request.args.get("date") or datetime.now().strftime("%Y-%m-%d")

            # Add debug logging
            logger.info(f"Looking for paper with arxiv_id: {arxiv_id}")

            # Determine which file to load based on date
            if date_param and os.path.exists(f"out/cache/{date_param}_output.json"):
                json_file = f"out/cache/{date_param}_output.json"
            else:
                json_file = "out/output.json"

            logger.info(f"Loading papers from: {json_file}")

            # Load the paper data
            with open(json_file, "r") as f:
                papers = json.load(f)

            # Find the paper with matching arxiv_id
            paper = None
            for p in papers.values():
                paper_arxiv_id = p.get("ARXIVID") or p.get("arxiv_id")
                logger.info(f"Comparing with paper ID: {paper_arxiv_id}")

                # Strip version numbers from arxiv IDs for comparison
                clean_paper_id = (
                    paper_arxiv_id.split("v")[0] if paper_arxiv_id else None
                )
                clean_input_id = arxiv_id.split("v")[0] if arxiv_id else None

                if clean_paper_id == clean_input_id:
                    paper_data = {
                        "arxiv_id": paper_arxiv_id,
                        "title": p["title"],
                        "abstract": p["abstract"],
                        "authors": p["authors"],
                        "url": f"https://arxiv.org/abs/{paper_arxiv_id}",
                        "comment": p.get("COMMENT") or p.get("comment"),
                        "relevance": p.get("RELEVANCE") or p.get("relevance"),
                        "novelty": p.get("NOVELTY") or p.get("novelty"),
                    }
                    paper = Paper(**paper_data)
                    break

            if not paper:
                logger.warning(f"No paper found matching arxiv_id: {arxiv_id}")
                return jsonify({"error": "Paper not found"})

            # Process Q&A
            qa_results = qa_processor.process_qa(paper)

            if "error" in qa_results:
                return jsonify({"error": qa_results["error"]})

            return jsonify(qa_results)
        except Exception as e:
            logger.error(f"Error in get_qa: {e}")
            return jsonify({"error": str(e)})

    @app.route("/main_progress")
    def get_main_progress():
        """Get the current progress of main.py"""
        return jsonify(main_progress)

    @app.route("/get_authors/<date>")
    def get_authors(date):
        """Get author data for a specific date using cache handler"""
        try:
            authors_data = cache_handler.get_cached_data(f"{date}_authors")
            if authors_data:
                return jsonify(authors_data)
            return jsonify({"error": "No author data found for this date"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/history")
    def history():
        """Show historical data organized by month"""
        try:
            dates = get_cached_dates()

            # Organize dates by month
            papers_by_month = {}
            for date in dates:
                # Convert date string to datetime for month extraction
                date_obj = datetime.strptime(date["date"], "%Y-%m-%d")
                month_key = date_obj.strftime("%B %Y")  # e.g., "March 2024"

                # Add paper count from cache
                cache_data = cache_handler.get_cached_data(f"{date['date']}_output")
                paper_count = len(cache_data) if cache_data else 0
                date["paper_count"] = paper_count

                # Add to month group
                if month_key not in papers_by_month:
                    papers_by_month[month_key] = []
                papers_by_month[month_key].append(date)

            # Sort months in reverse chronological order
            papers_by_month = dict(
                sorted(
                    papers_by_month.items(),
                    key=lambda x: datetime.strptime(x[0], "%B %Y"),
                    reverse=True,
                )
            )

            return render_template("history.html", papers_by_month=papers_by_month)
        except Exception as e:
            app.logger.error(f"Error in history route: {str(e)}")
            return render_template(
                "error.html", message=f"Error loading history: {str(e)}"
            ), 500

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("error.html", message="Page not found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {str(error)}")
        return render_template("error.html", message="Internal server error"), 500

    return app
