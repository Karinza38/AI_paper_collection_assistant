import os
import configparser
import io

from litellm import completion
import instructor

from helpers import get_api_key
from api_handler import APIHandler
from paper_processor import PaperProcessor
from output_handler import OutputHandler

if __name__ == "__main__":
    try:
        # Initialize API key and client
        api_key = get_api_key()
        os.environ["GEMINI_API_KEY"] = api_key
        client = instructor.from_litellm(completion)

        # Load configuration
        config = configparser.ConfigParser()
        config.read("configs/config.ini")

        # Initialize modules
        api_handler = APIHandler()
        paper_processor = PaperProcessor(config)
        output_handler = OutputHandler(config)

        # Load author list
        with io.open("configs/authors.txt", "r") as fopen:
            author_names, author_ids = paper_processor.parse_authors(fopen.readlines())
        author_id_set = set(author_ids)

        # Get papers from arXiv
        papers = list(paper_processor.get_papers_from_arxiv(config))

        # Get author metadata
        all_authors = set()
        for paper in papers:
            all_authors.update(set(paper.authors))
        
        if config["OUTPUT"].getboolean("debug_messages"):
            print(f"Getting author info for {len(all_authors)} authors")
        
        all_authors = api_handler.get_authors(list(all_authors))

        # Dump debug files if configured
        output_handler.dump_debug_files(papers, all_authors, author_id_set)

        # Process papers through filtering pipeline
        selected_papers, all_papers, sort_dict = paper_processor.process_papers(
            papers, all_authors, author_id_set, client, config
        )

        # Sort papers by relevance and novelty
        selected_papers = paper_processor.sort_papers(selected_papers, sort_dict)

        if config["OUTPUT"].getboolean("debug_messages"):
            print(sort_dict)
            print(selected_papers)

        # Generate outputs
        if len(papers) > 0:
            output_handler.output_json(selected_papers)
            output_handler.output_markdown(selected_papers)
            output_handler.output_slack(selected_papers)

    except Exception as e:
        print(f"Error initializing application: {str(e)}")
        exit(1)
