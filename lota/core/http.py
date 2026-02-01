"""HTTP utilities for fetching data."""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from typing import Any, Dict, Tuple

from lota.core.cache import Cache
from lota.core.errors import LotaError


def download_bytes(
    url: str, *, timeout: int, user_agent: str, debug: bool = False
) -> Tuple[bytes, Dict[str, str], int]:
    """Download raw bytes with minimal HTTP metadata for debugging."""
    if debug:
        sys.stderr.write(
            f"[DEBUG][HTTP] GET {url} timeout={timeout}s user_agent={user_agent!r}\n"
        )
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        dt_ms = int((time.time() - t0) * 1000)
        status = int(getattr(r, "status", 200) or 200)
        headers = {k.lower(): v for k, v in dict(r.headers).items()}
        if debug:
            sys.stderr.write(
                f"[DEBUG][HTTP] <- status={status} bytes={len(data)} elapsed_ms={dt_ms}\n"
            )
        return data, headers, status


def fetch_json(
    url: str,
    *,
    cache: Cache,
    timeout: int,
    user_agent: str,
    debug: bool = False,
) -> Any:
    """Fetch JSON from URL with optional caching."""
    cached = cache.get(url)
    if cached is not None:
        if debug:
            sys.stderr.write(f"[DEBUG][CACHE HIT] {url} bytes={len(cached)}\n")
        return json.loads(cached)

    try:
        data, _headers, _status = download_bytes(
            url, timeout=timeout, user_agent=user_agent, debug=debug
        )
    except Exception as e:
        raise LotaError(f"Network request failed: {url} ({e})") from e
    if not data:
        raise LotaError(f"Empty response: {url}")
    cache.set(url, data)
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        raise LotaError(f"JSON parse failed: {url} ({e})") from e
