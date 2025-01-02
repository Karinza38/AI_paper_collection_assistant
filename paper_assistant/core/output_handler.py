from typing import Dict, List, Set
import json
import os
from datetime import datetime
from configparser import ConfigParser

from paper_assistant.core.arxiv_scraper import Paper, EnhancedJSONEncoder
from paper_assistant.utils.parse_json_to_md import render_md_string
from paper_assistant.utils.push_to_slack import push_to_slack


class OutputHandler:
    def __init__(self, config: ConfigParser):
        self.config = config
        self.output_path = config["OUTPUT"]["output_path"]

    def dump_debug_files(self, papers: List[Paper], all_authors: Dict, author_id_set: Set[str]):
        """Dump debug files if configured"""
        if self.config["OUTPUT"].getboolean("dump_debug_file"):
            with open(self.output_path + "papers.debug.json", "w") as outfile:
                json.dump(papers, outfile, cls=EnhancedJSONEncoder, indent=4)
            with open(self.output_path + "all_authors.debug.json", "w") as outfile:
                json.dump(all_authors, outfile, cls=EnhancedJSONEncoder, indent=4)
            with open(self.output_path + "author_id_set.debug.json", "w") as outfile:
                json.dump(list(author_id_set), outfile, cls=EnhancedJSONEncoder, indent=4)

    def output_json(self, selected_papers: Dict):
        """Output papers as JSON if configured"""
        if self.config["OUTPUT"].getboolean("dump_json"):
            with open(self.output_path + "output.json", "w") as outfile:
                json.dump(selected_papers, outfile, indent=4)

    def output_markdown(self, selected_papers: Dict):
        """Output papers as Markdown if configured"""
        if self.config["OUTPUT"].getboolean("dump_md"):
            today = datetime.now().strftime("%Y-%m-%d")
            formatted_papers = self._format_papers(selected_papers)
            with open(self.output_path + f"{today}_output.md", "w") as f:
                f.write(render_md_string(formatted_papers))

    def output_slack(self, selected_papers: Dict):
        """Push papers to Slack if configured"""
        if self.config["OUTPUT"].getboolean("push_to_slack"):
            SLACK_KEY = os.environ.get("SLACK_KEY")
            if SLACK_KEY is None:
                print("Warning: push_to_slack is true, but SLACK_KEY is not set - not pushing to slack")
            else:
                push_to_slack(selected_papers)

    def _format_papers(self, selected_papers: Dict) -> Dict:
        """Convert dictionary values to Paper objects if they aren't already"""
        formatted_papers = {}
        for key, paper_dict in selected_papers.items():
            if isinstance(paper_dict, dict):
                paper = Paper(
                    title=paper_dict['title'],
                    authors=paper_dict['authors'],
                    abstract=paper_dict['abstract'],
                    arxiv_id=paper_dict['arxiv_id']
                )
                if 'comment' in paper_dict:
                    paper.comment = paper_dict['comment']
                if 'relevance' in paper_dict:
                    paper.relevance = paper_dict['relevance']
                if 'novelty' in paper_dict:
                    paper.novelty = paper_dict['novelty']
                formatted_papers[key] = paper
            else:
                formatted_papers[key] = paper_dict
        return formatted_papers
