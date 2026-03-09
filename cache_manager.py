import contextlib
import hashlib
import os
import pickle
import time
from typing import Any


class CacheManager:
    def __init__(self, cache_dir: str = "./cache", ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_hours * 3600
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def _get_cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.pkl")

    def get_cache_key(self, **kwargs) -> str:
        key_str = "_".join(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, key: str) -> Any | None:
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            mtime = os.path.getmtime(cache_path)
            if (time.time() - mtime) < self.ttl_seconds:
                try:
                    with open(cache_path, "rb") as f:
                        return pickle.load(f)
                except (OSError, pickle.PickleError, EOFError):
                    return None
        return None

    def set(self, key: str, data: Any):
        cache_path = self._get_cache_path(key)
        with contextlib.suppress(OSError, pickle.PickleError), open(cache_path, "wb") as f:
            pickle.dump(data, f)

    def clear_expired(self):
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".pkl"):
                path = os.path.join(self.cache_dir, filename)
                if (time.time() - os.path.getmtime(path)) > self.ttl_seconds:
                    with contextlib.suppress(OSError):
                        os.remove(path)
