import argparse
import os
import configparser
import io
from litellm import completion
import instructor

from paper_assistant.utils.helpers import get_api_key
from paper_assistant.api.api_handler import APIHandler
from paper_assistant.core.paper_processor import PaperProcessor
from paper_assistant.core.output_handler import OutputHandler
from paper_assistant.api.app import create_app


def generate_command(args):
    """Generate paper summaries and output in specified format."""
    try:
        # Initialize API key and client
        api_key = get_api_key()
        os.environ["GEMINI_API_KEY"] = api_key
        client = instructor.from_litellm(completion)

        # Load configuration
        config = configparser.ConfigParser()
        config.read(args.config or "paper_assistant/config/config.ini")

        # Initialize modules
        api_handler = APIHandler()
        paper_processor = PaperProcessor(config)
        output_handler = OutputHandler(config)

        # Load author list
        authors_path = args.authors or "paper_assistant/config/authors.txt"
        with io.open(authors_path, "r") as fopen:
            author_names, author_ids = paper_processor.parse_authors(fopen.readlines())
        author_id_set = set(author_ids)

        # Get papers from arXiv
        papers = list(paper_processor.get_papers_from_arxiv(config))

        # Get author metadata
        all_authors = set()
        for paper in papers:
            all_authors.update(set(paper.authors))

        if args.debug or config["OUTPUT"].getboolean("debug_messages"):
            print(f"Getting author info for {len(all_authors)} authors")

        all_authors = api_handler.get_authors(list(all_authors))

        # Process papers through filtering pipeline
        selected_papers, all_papers, sort_dict = paper_processor.process_papers(
            papers, all_authors, author_id_set, client, config
        )

        # Sort papers by relevance and novelty
        selected_papers = paper_processor.sort_papers(selected_papers, sort_dict)

        if args.debug or config["OUTPUT"].getboolean("debug_messages"):
            print(sort_dict)
            print(selected_papers)

        # Generate outputs based on specified format
        if len(papers) > 0:
            formats = (
                args.output_format.split(",") if args.output_format else ["markdown"]
            )
            if "json" in formats:
                output_handler.output_json(selected_papers)
            if "markdown" in formats:
                output_handler.output_markdown(selected_papers)
            if "slack" in formats:
                output_handler.output_slack(selected_papers)

    except Exception as e:
        print(f"Error in generate command: {str(e)}")
        exit(1)


def serve_command(args):
    """Start the web server."""
    try:
        app = create_app()
        port = args.port or 5000
        app.run(host="0.0.0.0", port=port, debug=args.debug)
    except Exception as e:
        print(f"Error starting server: {str(e)}")
        exit(1)


def create_parser():
    """Create argument parser with subcommands."""
    parser = argparse.ArgumentParser(description="Paper Assistant CLI")
    parser.add_argument("--debug", action="store_true", help="Enable debug messages")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate paper summaries")
    generate_parser.add_argument("--config", help="Path to config file")
    generate_parser.add_argument("--authors", help="Path to authors file")
    generate_parser.add_argument(
        "--output-format", help="Output formats (comma-separated: markdown,json,slack)"
    )
    generate_parser.add_argument("--query", help="ArXiv search query")

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start web server")
    serve_parser.add_argument("--port", type=int, help="Server port (default: 5000)")

    return parser


def main():
    """Main CLI entrypoint."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "generate":
        generate_command(args)
    elif args.command == "serve":
        serve_command(args)
    else:
        parser.print_help()
        exit(1)


if __name__ == "__main__":
    main()
