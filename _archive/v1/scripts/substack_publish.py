"""Create a Substack draft from data/ai_article.json.

Current behavior is intentionally non-publishing:
- draft=True
- should_send_email=False

To switch to fully automatic publishing later:
- set draft=False
- set should_send_email=True
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_ARTICLE_PATH = ROOT / "data" / "ai_article.json"
SUBSTACK_URL = "https://fxregimelab.substack.com"
LOGIN_URL = "https://substack.com/api/v1/login"
DRAFTS_URL = f"{SUBSTACK_URL}/api/v1/drafts"

load_dotenv(ROOT / ".env", override=True)

EMAIL = os.environ.get("SUBSTACK_EMAIL")
PASSWORD = os.environ.get("SUBSTACK_PASSWORD")


def _safe_int_pct(value: object) -> int:
    try:
        return int(float(value) * 100)
    except (TypeError, ValueError):
        return 0


def get_substack_session(email: str, password: str) -> requests.Session:
    """Log in to Substack and return authenticated session."""
    session = requests.Session()
    response = session.post(
        LOGIN_URL,
        json={"email": email, "password": password},
        timeout=10,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Login failed: HTTP {response.status_code}")
    return session


def format_brief_as_substack_post(article: dict) -> dict:
    """Convert ai_article.json payload into a Substack draft payload."""
    default_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_str = article.get("date", default_date)
    headline = article.get("headline", f"G10 FX Regime Brief — {date_str}")

    sections = article.get("sections", {}) or {}
    body_parts: list[str] = []

    macro = sections.get("macro_context", "")
    if macro:
        body_parts.append(f"<p>{macro}</p>")

    eurusd = sections.get("eurusd", {}) or {}
    if eurusd:
        regime = str(eurusd.get("regime", "")).replace("_", " ")
        confidence = _safe_int_pct(eurusd.get("confidence", 0))
        narrative = eurusd.get("narrative", "")
        driver = eurusd.get("key_driver", "")
        watch = eurusd.get("watch_for", "")
        body_parts.append(
            f"""
<h2>EUR/USD — {regime} ({confidence}%)</h2>
<p>{narrative}</p>
<p><strong>Primary driver:</strong> {driver}</p>
<p><em>Watch: {watch}</em></p>
""".strip()
        )

    usdjpy = sections.get("usdjpy", {}) or {}
    if usdjpy:
        regime = str(usdjpy.get("regime", "")).replace("_", " ")
        confidence = _safe_int_pct(usdjpy.get("confidence", 0))
        narrative = usdjpy.get("narrative", "")
        driver = usdjpy.get("key_driver", "")
        watch = usdjpy.get("watch_for", "")
        body_parts.append(
            f"""
<h2>USD/JPY — {regime} ({confidence}%)</h2>
<p>{narrative}</p>
<p><strong>Primary driver:</strong> {driver}</p>
<p><em>Watch: {watch}</em></p>
""".strip()
        )

    usdinr = sections.get("usdinr", {}) or {}
    if usdinr:
        regime = str(usdinr.get("regime", "")).replace("_", " ")
        confidence = _safe_int_pct(usdinr.get("confidence", 0))
        narrative = usdinr.get("narrative", "")
        driver = usdinr.get("key_driver", "")
        body_parts.append(
            f"""
<h2>USD/INR — {regime} ({confidence}%)</h2>
<p>{narrative}</p>
<p><em>Directional only — RBI intervention distorts precision entries.</em></p>
<p><strong>Primary driver:</strong> {driver}</p>
""".strip()
        )

    changes = sections.get("signal_changes", []) or []
    if changes:
        changes_html = "".join(f"<li>{change}</li>" for change in changes)
        body_parts.append(
            f"""
<h2>Signal Changes Today</h2>
<ul>{changes_html}</ul>
""".strip()
        )

    body_parts.append(
        """
<hr>
<p><em>FX Regime Lab — Live quantamental macro research.
<a href="https://fxregimelab.com">fxregimelab.com</a></em></p>
""".strip()
    )

    body_html = "\n\n".join(body_parts)
    return {
        "draft": True,
        "type": "newsletter",
        "title": headline,
        "body": body_html,
        "subtitle": f"G10 FX regime intelligence — {date_str}",
        # This controls subscriber emails. Keep False while in draft workflow.
        "should_send_email": False,
    }


def publish_to_substack(article: dict) -> bool:
    """Post article as draft on Substack."""
    if not EMAIL or not PASSWORD:
        print("[Substack] Credentials not set — skipping")
        return True

    try:
        session = get_substack_session(EMAIL, PASSWORD)
        payload = format_brief_as_substack_post(article)
        response = session.post(DRAFTS_URL, json=payload, timeout=15)

        if response.status_code in (200, 201):
            post_id = response.json().get("id")
            print(f"[Substack] Draft created: post ID {post_id}")
            print(f"[Substack] Review at: {SUBSTACK_URL}/publish/post/{post_id}")
            return True

        print(f"[Substack] Draft failed: HTTP {response.status_code}")
        print(f"[Substack] Response: {response.text[:300]}")
        return False
    except Exception as exc:
        print(f"[Substack] Error: {exc}")
        return False


def main() -> int:
    """Entry point."""
    if not DATA_ARTICLE_PATH.exists():
        print("[Substack] No ai_article.json found — run ai_brief.py first")
        return 1

    try:
        with DATA_ARTICLE_PATH.open("r", encoding="utf-8") as handle:
            article = json.load(handle)
    except Exception as exc:
        print(f"[Substack] Failed to read ai_article.json: {exc}")
        return 1

    success = publish_to_substack(article)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
