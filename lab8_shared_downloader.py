#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse


def safe_filename_from_url(url: str, max_len: int = 80) -> str:
    parsed = urlparse(url)
    raw = f"{parsed.netloc}_{parsed.path}_{parsed.query}".strip("_")
    raw = re.sub(r"[^A-Za-z0-9._-]+", "_", raw)
    raw = raw[:max_len].strip("_.-") or "page"
    digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    return f"{raw}_{digest}.html"


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_url_list(path: str | Path) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines()]
    return [line for line in lines if line and not line.startswith("#")]


def build_urls_from_range(base_url: str, start_id: int, end_id: int) -> list[str]:
    return [base_url.format(id=i) for i in range(start_id, end_id + 1)]
