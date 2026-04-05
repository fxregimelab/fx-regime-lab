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
import json
from datetime import datetime, timezone

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
AI_ARTICLE_SRC = os.path.join(DATA_SRC, "ai_article.json")

# Terminal + static mirrors: ship merged master + COT/INR slices for /data/*.csv on Cloudflare.
_DATA_FILES = (
    "latest_with_cot.csv",
    "cot_latest.csv",
    "inr_latest.csv",
    "macro_cal.json",
)

_AI_ARCHIVE_PREFIX = "ai_article_"
_AI_ARCHIVE_SUFFIX = ".json"
_AI_ARCHIVE_KEEP = 30
_AI_ARCHIVES_MANIFEST = "ai_article_archives.json"

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
        if name.lower() == "global_workspace.html":
            continue
        sp = os.path.join(src, name)
        if os.path.isfile(sp):
            shutil.copy2(sp, os.path.join(dst, name))


def _sync_ai_article_archive() -> None:
    os.makedirs(OUT_DATA, exist_ok=True)
    if not os.path.isfile(AI_ARTICLE_SRC):
        print("WARN: skip data/ai_article.json (not found — run ai_brief.py first)")
        return

    try:
        with open(AI_ARTICLE_SRC, encoding="utf-8") as fh:
            article = json.load(fh)
    except Exception as exc:
        print(f"WARN: failed to read data/ai_article.json: {exc}")
        return

    article_date = article.get("date", "")
    try:
        date_slug = datetime.strptime(article_date, "%Y-%m-%d").strftime("%Y%m%d")
    except ValueError:
        date_slug = datetime.now(timezone.utc).strftime("%Y%m%d")

    latest_dst = os.path.join(OUT_DATA, "ai_article.json")
    dated_dst = os.path.join(OUT_DATA, f"{_AI_ARCHIVE_PREFIX}{date_slug}{_AI_ARCHIVE_SUFFIX}")
    shutil.copy2(AI_ARTICLE_SRC, latest_dst)
    shutil.copy2(AI_ARTICLE_SRC, dated_dst)
    print(f"Copied data/ai_article.json -> {latest_dst}")
    print(f"Archived data/ai_article.json -> {dated_dst}")

    archive_candidates = []
    for name in os.listdir(OUT_DATA):
        if not name.startswith(_AI_ARCHIVE_PREFIX) or not name.endswith(_AI_ARCHIVE_SUFFIX):
            continue
        date_token = name[len(_AI_ARCHIVE_PREFIX):-len(_AI_ARCHIVE_SUFFIX)]
        if len(date_token) == 8 and date_token.isdigit():
            archive_candidates.append((date_token, os.path.join(OUT_DATA, name)))

    archive_candidates.sort(reverse=True)
    for _, path in archive_candidates[_AI_ARCHIVE_KEEP:]:
        os.remove(path)
        print(f"Pruned old archive file: {path}")


def _write_ai_article_archives_manifest() -> None:
    """List dated ai_article_YYYYMMDD.json files for the brief page (no blind 404 probes)."""
    os.makedirs(OUT_DATA, exist_ok=True)
    slugs: list[str] = []
    for name in os.listdir(OUT_DATA):
        if not name.startswith(_AI_ARCHIVE_PREFIX) or not name.endswith(_AI_ARCHIVE_SUFFIX):
            continue
        token = name[len(_AI_ARCHIVE_PREFIX):-len(_AI_ARCHIVE_SUFFIX)]
        if len(token) == 8 and token.isdigit():
            slugs.append(token)
    slugs.sort(reverse=True)
    slugs = slugs[:_AI_ARCHIVE_KEEP]
    manifest_path = os.path.join(OUT_DATA, _AI_ARCHIVES_MANIFEST)
    payload = {"slugs": slugs}
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    print(f"Wrote {manifest_path} ({len(slugs)} archive slug(s))")


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

    _pipe_status_site_data = os.path.join(SITE, "data", "pipeline_status.json")
    _pipe_status_static = os.path.join(STATIC_SRC, "pipeline_status.json")
    os.makedirs(OUT_STATIC, exist_ok=True)
    # Precedence: site/data/pipeline_status.json (run.py merge output) wins over static/.
    if os.path.isfile(_pipe_status_site_data):
        shutil.copy2(_pipe_status_site_data, os.path.join(OUT_STATIC, "pipeline_status.json"))
        print("Copied site/data/pipeline_status.json -> site/static/ (terminal HOME fetch)")
    elif os.path.isfile(_pipe_status_static):
        shutil.copy2(_pipe_status_static, os.path.join(OUT_STATIC, "pipeline_status.json"))
        print("Copied static/pipeline_status.json -> site/static/ (terminal HOME fetch)")

    os.makedirs(OUT_DATA, exist_ok=True)
    for name in _DATA_FILES:
        src = os.path.join(DATA_SRC, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(OUT_DATA, name))
            print(f"Copied data/{name} -> {OUT_DATA}/")
        else:
            print(f"WARN: skip data/{name} (not found — run pipeline first)")
    _sync_ai_article_archive()
    _write_ai_article_archives_manifest()
    return 0


if __name__ == "__main__":
    sys.exit(main())
