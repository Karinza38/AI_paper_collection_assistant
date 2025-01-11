import os
import json
from typing import Dict, Optional
from loguru import logger

class CacheHandler:
    def __init__(self, cache_dir: str):
        """Initialize cache handler with a directory"""
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cache_path(self, cache_key: str) -> str:
        """Get the cache file path for a key"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def get_cached_data(self, cache_key: str) -> Optional[Dict]:
        """Get cached data if it exists"""
        cache_path = self.get_cache_path(cache_key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading cache for {cache_key}: {e}")
        return None

    def save_cache_data(self, cache_key: str, data: Dict):
        """Save data to cache"""
        cache_path = self.get_cache_path(cache_key)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache for {cache_key}: {e}")
