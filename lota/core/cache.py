"""File-based caching for HTTP responses."""

from __future__ import annotations

import dataclasses
import hashlib
import os
from typing import Optional


@dataclasses.dataclass(frozen=True)
class Cache:
    """Simple file-based cache; disabled when cache_dir is None."""

    cache_dir: Optional[str]

    def _path_for_url(self, url: str) -> str:
        assert self.cache_dir is not None
        h = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{h}.json")

    def get(self, url: str) -> Optional[bytes]:
        if not self.cache_dir:
            return None
        path = self._path_for_url(url)
        try:
            with open(path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def set(self, url: str, data: bytes) -> None:
        if not self.cache_dir:
            return
        os.makedirs(self.cache_dir, exist_ok=True)
        path = self._path_for_url(url)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
