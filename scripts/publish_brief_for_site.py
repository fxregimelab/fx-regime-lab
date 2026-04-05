#!/usr/bin/env python3
"""
Copy latest generated HTML brief + charts + static assets into site/ for Cloudflare.
Run from repo root after create_html_brief.py (e.g. CI before deploy.py).

Rewrites paths: ../charts/ -> /charts/, ../static/ -> /static/
"""
from __future__ import annotations

import os
import re
import shutil
import sys

# Repo root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIEFS = os.path.join(ROOT, "briefs")
SITE = os.path.join(ROOT, "site")
DATA_SRC = os.path.join(ROOT, "data")
CHARTS_SRC = os.path.join(ROOT, "charts")
STATIC_SRC = os.path.join(ROOT, "static")
OUT_BRIEF = os.path.join(SITE, "brief", "latest.html")
OUT_CHARTS = os.path.join(SITE, "charts")
OUT_STATIC = os.path.join(SITE, "static")
OUT_DATA = os.path.join(SITE, "data")

# Terminal + static mirrors: ship merged master + COT/INR slices for /data/*.csv on Cloudflare.
_DATA_FILES = (
    "latest_with_cot.csv",
    "cot_latest.csv",
    "inr_latest.csv",
)


def _latest_brief_path() -> str | None:
    if not os.path.isdir(BRIEFS):
        return None
    candidates = []
    for name in os.listdir(BRIEFS):
        if not name.startswith("brief_") or not name.endswith(".html"):
            continue
        path = os.path.join(BRIEFS, name)
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            candidates.append(path)
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0]


def _rewrite_html(html: str) -> str:
    html = re.sub(
        r'(<iframe\b[^>]*\bsrc=")\.\./charts/',
        r"\1/charts/",
        html,
    )
    html = re.sub(
        r"(<iframe\b[^>]*\bsrc=')\.\./charts/",
        r"\1/charts/",
        html,
    )
    html = html.replace('href="../static/', 'href="/static/')
    html = html.replace("href='../static/", "href='/static/")
    html = html.replace('src="../static/', 'src="/static/')
    # Any remaining ../static in inline URLs
    html = html.replace("../static/", "/static/")
    return html


def _sync_dir(src: str, dst: str) -> None:
    if not os.path.isdir(src):
        print(f"WARN: missing source dir {src}, skipping sync")
        return
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        sp = os.path.join(src, name)
        if os.path.isfile(sp):
            shutil.copy2(sp, os.path.join(dst, name))


def _sync_charts_html_only(src: str, dst: str) -> None:
    """Copy only *.html from charts/ (exclude registry.py, etc.)."""
    if not os.path.isdir(src):
        print(f"WARN: missing source dir {src}, skipping chart sync")
        return
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        if not name.lower().endswith(".html"):
            continue
        sp = os.path.join(src, name)
        if os.path.isfile(sp):
            shutil.copy2(sp, os.path.join(dst, name))


def main() -> int:
    os.chdir(ROOT)
    brief_path = _latest_brief_path()
    if not brief_path:
        print("ERROR: no briefs/brief_*.html found — run create_html_brief first")
        return 1
    with open(brief_path, encoding="utf-8") as f:
        html = f.read()
    html = _rewrite_html(html)
    os.makedirs(os.path.dirname(OUT_BRIEF), exist_ok=True)
    with open(OUT_BRIEF, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {OUT_BRIEF} from {brief_path}")

    _sync_charts_html_only(CHARTS_SRC, OUT_CHARTS)
    print(f"Synced charts (*.html) -> {OUT_CHARTS}")

    _sync_dir(STATIC_SRC, OUT_STATIC)
    print(f"Synced static -> {OUT_STATIC}")

    _pipe_status = os.path.join(SITE, "data", "pipeline_status.json")
    if os.path.isfile(_pipe_status):
        os.makedirs(OUT_STATIC, exist_ok=True)
        shutil.copy2(_pipe_status, os.path.join(OUT_STATIC, "pipeline_status.json"))
        print("Copied site/data/pipeline_status.json -> site/static/ (terminal HOME fetch)")

    os.makedirs(OUT_DATA, exist_ok=True)
    for name in _DATA_FILES:
        src = os.path.join(DATA_SRC, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(OUT_DATA, name))
            print(f"Copied data/{name} -> {OUT_DATA}/")
        else:
            print(f"WARN: skip data/{name} (not found — run pipeline first)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
