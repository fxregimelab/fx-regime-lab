"""Substack RSS + post HTML scrape for weekly research memos."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SUBSTACK_FEED_URL = "https://fxregimelab.substack.com/feed"
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def _rss_headers() -> dict[str, str]:
    return {
        "User-Agent": BROWSER_UA,
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }


def _html_headers() -> dict[str, str]:
    return {
        "User-Agent": BROWSER_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def _first_item_from_rss(xml: str) -> dict[str, Any] | None:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        logger.warning("RSS parse error: %s", exc)
        return None
    channel = root.find("channel")
    if channel is None:
        return None
    item = channel.find("item")
    if item is None:
        return None
    title_el = item.find("title")
    link_el = item.find("link")
    pub_el = item.find("pubDate")
    title = (title_el.text or "").strip() if title_el is not None and title_el.text else ""
    link = (link_el.text or "").strip() if link_el is not None and link_el.text else ""
    pub_raw = (pub_el.text or "").strip() if pub_el is not None and pub_el.text else ""
    return {"title": title, "link": link, "pubDate": pub_raw}


def _parse_pub_date(pub_raw: str) -> date:
    """Best-effort RFC822-ish pubDate → UTC date."""
    if not pub_raw:
        return date.today()
    try:
        dt = datetime.strptime(pub_raw[:25], "%a, %d %b %Y %H:%M:%S")
        return dt.date()
    except ValueError:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", pub_raw)
        if m:
            return date.fromisoformat(m.group(1))
    return date.today()


def _extract_available_content(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    div = soup.find("div", class_="available-content")
    if div is not None:
        text = div.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    body = soup.find("body")
    if body is not None:
        return body.get_text(separator="\n", strip=True)[:500_000]
    return soup.get_text(separator="\n", strip=True)[:500_000]


def fetch_latest_substack_memo() -> dict[str, Any]:
    """Fetch latest post from RSS, download HTML, extract ``available-content`` body text."""
    r = requests.get(SUBSTACK_FEED_URL, headers=_rss_headers(), timeout=45)
    r.raise_for_status()
    meta = _first_item_from_rss(r.text)
    if not meta or not meta.get("link"):
        raise RuntimeError("Substack RSS: no item or missing link")

    post_url = str(meta["link"])
    title = str(meta.get("title") or "Weekly Macro Memo")
    pub_d = _parse_pub_date(str(meta.get("pubDate") or ""))

    hr = requests.get(post_url, headers=_html_headers(), timeout=45)
    hr.raise_for_status()
    raw_content = _extract_available_content(hr.text)
    if not raw_content:
        raise RuntimeError("Substack post: empty body after extraction")

    return {
        "title": title,
        "link_url": post_url,
        "raw_content": raw_content,
        "date": pub_d.isoformat(),
    }
