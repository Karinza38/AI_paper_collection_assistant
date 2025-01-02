from typing import Dict, List, Set, Tuple
from arxiv_scraper import Paper
from configparser import ConfigParser
from instructor import Instructor
from arxiv_scraper import get_papers_from_arxiv_rss_api
from filter_papers import filter_by_author, filter_by_gpt
from helpers import argsort

class PaperProcessor:
    def __init__(self, config: ConfigParser):
        self.config = config

    def parse_authors(self, lines: List[str]) -> Tuple[List[str], List[str]]:
        """Parse the comma-separated author list, ignoring comments and empty lines"""
        author_ids = []
        authors = []
        for line in lines:
            if line.startswith("#") or not line.strip():
                continue
            author_split = line.split(",")
            author_ids.append(author_split[1].strip())
            authors.append(author_split[0].strip())
        return authors, author_ids

    def get_papers_from_arxiv(self, config: ConfigParser) -> Set[Paper]:
        """Get papers from arXiv based on configured categories"""
        area_list = config["FILTERING"]["arxiv_category"].split(",")
        paper_set = set()
        for area in area_list:
            papers = get_papers_from_arxiv_rss_api(area.strip(), config)
            paper_set.update(set(papers))
        return paper_set

    def process_papers(self, papers: List[Paper], all_authors: Dict, author_id_set: Set[str], 
                      client: Instructor, config: ConfigParser) -> Tuple[Dict, Dict, Dict]:
        """Process papers through filtering pipeline"""
        # First filter by author
        selected_papers, all_papers, sort_dict = filter_by_author(
            all_authors, papers, author_id_set, config
        )
        
        # Then filter by GPT
        filter_by_gpt(
            all_authors,
            papers,
            config,
            client,
            all_papers,
            selected_papers,
            sort_dict,
        )
        
        return selected_papers, all_papers, sort_dict

    def sort_papers(self, selected_papers: Dict, sort_dict: Dict) -> Dict:
        """Sort papers by relevance and novelty"""
        keys = list(sort_dict.keys())
        values = list(sort_dict.values())
        sorted_keys = [keys[idx] for idx in argsort(values)[::-1]]
        return {key: selected_papers[key] for key in sorted_keys}
