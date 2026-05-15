"""Bulk backfill all Substack posts into research_memos.

Uses Substack's public archive API, scrapes full post bodies,
and upserts via pg8000 direct SQL for speed.
"""

from __future__ import annotations
import os

import logging
import ssl
import uuid
from datetime import datetime
from typing import Any

import pg8000.native
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

ARCHIVE_API_URL = "https://fxregimelab.substack.com/api/v1/archive"
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def _pg_conn() -> pg8000.native.Connection:
    ctx = ssl._create_unverified_context()
    return pg8000.native.Connection(
        host=os.environ.get("SUPABASE_DB_HOST", ""),
        database="postgres",
        user="postgres",
        password=os.environ.get("SUPABASE_DB_PASSWORD", ""),
        ssl_context=ctx,
    )


def _html_headers() -> dict[str, str]:
    return {
        "User-Agent": BROWSER_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def _extract_available_content(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    div = soup.find("div", class_="available-content")
    if div is not None:
        text = div.get_text(separator="\n", strip=True)
        # collapse excessive newlines
        import re

        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    body = soup.find("body")
    if body is not None:
        return body.get_text(separator="\n", strip=True)[:500_000]
    return soup.get_text(separator="\n", strip=True)[:500_000]


def _fetch_archive_posts(offset: int, limit: int = 20) -> list[dict[str, Any]]:
    url = f"{ARCHIVE_API_URL}?sort=new&search=&offset={offset}&limit={limit}"
    r = requests.get(url, headers={"User-Agent": BROWSER_UA}, timeout=45)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        return []
    return data


def _scrape_post_body(post_url: str) -> str:
    r = requests.get(post_url, headers=_html_headers(), timeout=45)
    r.raise_for_status()
    return _extract_available_content(r.text)


def _parse_post_date(post_date_raw: str) -> str:
    """ISO 8601 post_date → YYYY-MM-DD."""
    if not post_date_raw:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        dt = datetime.fromisoformat(post_date_raw.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return post_date_raw[:10]


def _build_memo_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    limit = 20

    while True:
        posts = _fetch_archive_posts(offset, limit)
        if not posts:
            break
        logger.info("Fetched %d posts at offset %d", len(posts), offset)
        for post in posts:
            canonical_url = str(post.get("canonical_url") or "")
            if not canonical_url:
                logger.warning("Skipping post without canonical_url")
                continue
            title = str(post.get("title") or "")
            post_date = _parse_post_date(str(post.get("post_date") or ""))
            post_id = str(uuid.uuid5(uuid.NAMESPACE_URL, canonical_url))
            try:
                raw_content = _scrape_post_body(canonical_url)
            except Exception as exc:
                logger.warning("Failed to scrape %s: %s", canonical_url, exc)
                continue
            rows.append({
                "id": post_id,
                "date": post_date,
                "title": title,
                "raw_content": raw_content,
                "ai_thesis_summary": [],
                "link_url": canonical_url,
            })
        if len(posts) < limit:
            break
        offset += len(posts)

    return rows


def _upsert_memos(rows: list[dict[str, Any]], batch_size: int = 20) -> tuple[int, int]:
    if not rows:
        return 0, 0

    conn = _pg_conn()
    inserted = 0
    updated = 0

    columns = ["id", "date", "title", "raw_content", "ai_thesis_summary", "link_url"]
    col_str = ", ".join(columns)

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        placeholders: list[str] = []
        params: dict[str, Any] = {}

        for bidx, row in enumerate(batch):
            prefix = f"p{i}_{bidx}_"
            row_placeholders: list[str] = []
            for cidx, col in enumerate(columns):
                param_key = f"{prefix}c{cidx}"
                row_placeholders.append(f":{param_key}")
                val = row.get(col)
                if col == "ai_thesis_summary":
                    params[param_key] = "[]"
                else:
                    params[param_key] = val
            placeholders.append(f"({', '.join(row_placeholders)})")

        sql = (
            f"INSERT INTO research_memos ({col_str}) VALUES {', '.join(placeholders)} "
            "ON CONFLICT (link_url) DO UPDATE SET "
            "id = EXCLUDED.id, "
            "date = EXCLUDED.date, "
            "title = EXCLUDED.title, "
            "raw_content = EXCLUDED.raw_content, "
            "ai_thesis_summary = EXCLUDED.ai_thesis_summary "
            "RETURNING xmax"
        )

        result = conn.run(sql, **params)
        for row in result:
            # xmax = 0 means insert, >0 means update
            if row[0] == 0:
                inserted += 1
            else:
                updated += 1

    conn.close()
    return inserted, updated


def run_backfill() -> tuple[int, int, int]:
    """Fetch all posts, scrape bodies, upsert to DB.

    Returns (total_rows, inserted, updated).
    """
    rows = _build_memo_rows()
    logger.info("Built %d memo rows", len(rows))
    inserted, updated = _upsert_memos(rows)
    return len(rows), inserted, updated


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    total, inserted, updated = run_backfill()
    logger.info("Backfill complete: %d total, %d inserted, %d updated", total, inserted, updated)


if __name__ == "__main__":
    main()
