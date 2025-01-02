import json
import time
from typing import TypeVar, Generator, List, Dict, Optional
from requests import Session
from tqdm import tqdm
from retry import retry

T = TypeVar("T")


class APIHandler:
    def __init__(self, s2_api_key: Optional[str] = None):
        self.s2_api_key = s2_api_key

    def batched(self, items: list[T], batch_size: int) -> list[T]:
        """Batch items into smaller chunks"""
        return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

    @retry(tries=3, delay=2.0)
    def get_paper_batch(
        self, session: Session, ids: List[str], fields: str = "paperId,title", **kwargs
    ) -> List[Dict]:
        """Get batch of papers from Semantic Scholar API"""
        params = {"fields": fields, **kwargs}
        headers = {"X-API-KEY": self.s2_api_key} if self.s2_api_key else {}

        with session.post(
            "https://api.semanticscholar.org/graph/v1/paper/batch",
            params=params,
            headers=headers,
            json={"ids": ids},
        ) as response:
            response.raise_for_status()
            return response.json()

    @retry(tries=3, delay=2.0)
    def get_author_batch(
        self,
        session: Session,
        ids: List[str],
        fields: str = "name,hIndex,citationCount",
        **kwargs,
    ) -> List[Dict]:
        """Get batch of authors from Semantic Scholar API"""
        params = {"fields": fields, **kwargs}
        headers = {"X-API-KEY": self.s2_api_key} if self.s2_api_key else {}

        with session.post(
            "https://api.semanticscholar.org/graph/v1/author/batch",
            params=params,
            headers=headers,
            json={"ids": ids},
        ) as response:
            response.raise_for_status()
            return response.json()

    @retry(tries=3, delay=2.0)
    def get_one_author(self, session: Session, author: str) -> Optional[List[Dict]]:
        """Get single author info from Semantic Scholar API"""
        params = {"query": author, "fields": "authorId,name,hIndex", "limit": "10"}
        headers = {"X-API-KEY": self.s2_api_key} if self.s2_api_key else {}

        with session.get(
            "https://api.semanticscholar.org/graph/v1/author/search",
            params=params,
            headers=headers,
        ) as response:
            response.raise_for_status()
            response_json = response.json()
            return response_json["data"] if response_json["data"] else None

    def get_papers(
        self, ids: List[str], batch_size: int = 100, **kwargs
    ) -> Generator[Dict, None, None]:
        """Get papers in batches from Semantic Scholar API"""
        with Session() as session:
            for ids_batch in self.batched(ids, batch_size=batch_size):
                yield from self.get_paper_batch(session, ids_batch, **kwargs)

    def get_authors(
        self,
        all_authors: List[str],
        batch_size: int = 100,
        debug_file: Optional[str] = None,
    ) -> Dict:
        """Get author metadata from Semantic Scholar API"""
        if debug_file:
            try:
                with open(debug_file, "r") as f:
                    return json.load(f)
            except FileNotFoundError:
                pass

        author_metadata_dict = {}
        with Session() as session:
            for author in tqdm(all_authors):
                auth_map = self.get_one_author(session, author)
                if auth_map is not None:
                    author_metadata_dict[author] = auth_map
                time.sleep(0.02 if self.s2_api_key else 1.0)
        return author_metadata_dict
