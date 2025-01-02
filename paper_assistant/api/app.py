from flask import Flask, render_template, jsonify, request
import json
from datetime import datetime
from paper_assistant.core.arxiv_scraper import Paper
import os
from paper_assistant.core.qa_processor import QaProcessor
from paper_assistant.utils.markdown_processor import MarkdownProcessor
import glob
from paper_assistant.utils.helpers import get_api_key


def create_app():
    app = Flask(__name__, static_folder="static")

    # Get API key and initialize processors
    try:
        # Get and validate API key
        GEMINI_API_KEY = get_api_key()
        qa_processor = QaProcessor(api_key=GEMINI_API_KEY)
        md_processor = MarkdownProcessor()
    except Exception as e:
        print(f"Error initializing API key: {str(e)}")
        GEMINI_API_KEY = None
        qa_processor = None
        md_processor = MarkdownProcessor()

    def get_cached_dates():
        """Get list of available cached dates"""
        cache_files = glob.glob("out/cache/*_output.json")
        dates = []
        for file in cache_files:
            # Extract date from filename (format: YYYY-MM-DD_output.json)
            date_str = os.path.basename(file).replace("_output.json", "").split("_")[0]
            try:
                # Verify it's a valid date
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                dates.append(
                    {"date": date_str, "display_date": date_obj.strftime("%B %d, %Y")}
                )
            except ValueError:
                continue

        # Sort dates in reverse chronological order
        dates.sort(key=lambda x: x["date"], reverse=True)
        return dates

    def cache_daily_output():
        """Cache current day's output"""
        global main_progress
        today = datetime.now().strftime("%Y-%m-%d")

        # Only reset progress if main.py is actually running
        if not os.path.exists("out/output.json"):
            main_progress = {
                "running": True,
                "current": 0,
                "total": 0,
                "message": "Starting paper collection...",
            }
        else:
            main_progress = {"running": False, "current": 0, "total": 0, "message": ""}

        # Cache JSON output
        if os.path.exists("out/output.json"):
            os.makedirs("out/cache", exist_ok=True)
            cache_path = f"out/cache/{today}_output.json"
            if not os.path.exists(cache_path):
                # Cache papers
                with open("out/output.json", "r") as src, open(cache_path, "w") as dst:
                    dst.write(src.read())

                # Cache authors if the file exists
                if os.path.exists("out/all_authors.debug.json"):
                    authors_cache_path = f"out/cache/{today}_authors.json"
                    with (
                        open("out/all_authors.debug.json", "r") as src,
                        open(authors_cache_path, "w") as dst,
                    ):
                        dst.write(src.read())

    # Global variable to track main.py status
    main_progress = {"running": False, "current": 0, "total": 0, "message": ""}

    @app.route("/")
    def index():
        """Main route to display papers"""
        if not GEMINI_API_KEY or not qa_processor:
            return render_template(
                "error.html",
                message="API key validation failed. Please check your configuration.",
            ), 503

        try:
            # Cache daily output
            cache_daily_output()

            # Get requested date or use latest
            date_param = request.args.get("date")

            # Get list of available dates
            available_dates = get_cached_dates()

            # Check if output files exist
            if not os.path.exists("out/output.json") and not available_dates:
                return render_template(
                    "error.html",
                    message="No paper data available yet. Please wait for the next scheduled update at 9:00 AM EST.",
                ), 503

            # Determine which file to load
            if date_param and os.path.exists(f"out/cache/{date_param}_output.json"):
                json_file = f"out/cache/{date_param}_output.json"
                display_date = datetime.strptime(date_param, "%Y-%m-%d").strftime(
                    "%B %d, %Y"
                )
            else:
                json_file = "out/output.json"
                display_date = datetime.now().strftime("%B %d, %Y")

            # Load papers from JSON
            with open(json_file, "r") as f:
                papers_dict = json.load(f)

            # Load header content
            with open("configs/header.md", "r") as f:
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
            print(f"Error in index route: {e}")
            return render_template(
                "error.html", message=f"Error loading papers: {str(e)}"
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
            print(f"Looking for paper with arxiv_id: {arxiv_id}")

            # Determine which file to load based on date
            if date_param and os.path.exists(f"out/cache/{date_param}_output.json"):
                json_file = f"out/cache/{date_param}_output.json"
            else:
                json_file = "out/output.json"

            print(f"Loading papers from: {json_file}")

            # Load the paper data
            with open(json_file, "r") as f:
                papers = json.load(f)

            # Find the paper with matching arxiv_id
            paper = None
            for p in papers.values():
                paper_arxiv_id = p.get("ARXIVID") or p.get("arxiv_id")
                print(f"Comparing with paper ID: {paper_arxiv_id}")

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
                print(f"No paper found matching arxiv_id: {arxiv_id}")
                return jsonify({"error": "Paper not found"})

            # Process Q&A
            qa_results = qa_processor.process_qa(paper)

            if "error" in qa_results:
                return jsonify({"error": qa_results["error"]})

            return jsonify(qa_results)
        except Exception as e:
            print(f"Error in get_qa: {e}")
            return jsonify({"error": str(e)})

    @app.route("/main_progress")
    def get_main_progress():
        """Get the current progress of main.py"""
        return jsonify(main_progress)

    @app.route("/get_authors/<date>")
    def get_authors(date):
        """Get author data for a specific date"""
        try:
            authors_file = f"out/cache/{date}_authors.json"
            if os.path.exists(authors_file):
                with open(authors_file, "r") as f:
                    return jsonify(json.load(f))
            return jsonify({"error": "No author data found for this date"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/history")
    def history():
        """Show historical data"""
        try:
            dates = get_cached_dates()
            return render_template("history.html", dates=dates)
        except Exception as e:
            return render_template(
                "error.html", message=f"Error loading history: {str(e)}"
            ), 500

    return app
