"""Japanese current-source semantics and saved review version boundaries."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from src.ai import client as ai
from src.private_desk import boj_current, data
from src.private_desk.current_review import capture_review_output, verify_current_review
from src.private_desk.report import apply_current_review
from tests.test_private_desk_current_review import CLOCK, headline, parent_report

NOW = datetime(2026, 10, 1, 18, 0, tzinfo=UTC)
POLICY = '''<html><h2>The Bank's Market Operations</h2>
<p>Uncollateralized Overnight Call Rate(average) 1.227 percent</p>
<p>Interest Rate Applied to the Complementary Deposit Facility 1.25% since September 24, 2026</p>
<section class="policy"><h3>Guideline</h3>
<a href="/en/mopo/mpmdeci/state_2026/index.htm">The Bank will encourage
the uncollateralized overnight call rate to remain at around 1.25 percent.</a></section></html>'''
ITEM = '''<item><title>Summary of Opinions</title><description>Not article evidence</description>
<pubDate>Thu, 01 Oct 2026 08:50:00 +0900</pubDate>
<link>http://www.boj.or.jp/en/mopo/opinion.pdf</link>
<guid>http://www.boj.or.jp/en/mopo/opinion.pdf</guid></item>'''
FEED = '''<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>
<atom:link href="http://www.boj.or.jp/en/rss/whatsnew.xml?id=1002"
 rel="self" type="application/rss+xml"/>
''' + ITEM + '</channel></rss>'


def test_current_guideline_is_separate_from_market_rate_and_facility_date() -> None:
    parsed = data._boj_policy(POLICY, NOW)
    assert parsed["value"] == 1.25 and parsed["policy_target_qualifier"] == "around"
    assert parsed["observation_date"] == "2026-10-01"
    assert parsed["current_page_observed_at"] == NOW.isoformat()
    assert parsed["date_role"] == "current_page_observed_on"
    assert parsed["effective_from"] is None and parsed["decision_date"] is None


@pytest.mark.parametrize("raw", [
    POLICY.replace('<h3>Guideline</h3>', ''),
    POLICY.replace('<h3>Guideline</h3>', '<h3>Guideline</h3><h3>Guideline</h3>'),
    POLICY.replace('</section>', '<a href="/en/mopo/mpmdeci/state_2026/index.htm">'
                   'The Bank will encourage the uncollateralized overnight call rate '
                   'to remain at around 2.00 percent.</a></section>'),
    POLICY.replace('<section class="policy">', '<section class="other">'),
    POLICY.replace('</html>', '<a href="/en/mopo/mpmdeci/state_2026/index.htm">'
                   'The Bank will encourage the uncollateralized overnight call rate '
                   'to remain at around 2.00 percent.</a></html>'),
    POLICY.replace('around 1.25 percent', 'around 0 to 0.1 percent'),
    POLICY.replace('around 1.25 percent', 'around 1.25 basis points'),
    POLICY.replace('around 1.25 percent', 'around NaN percent'),
    POLICY.replace('/en/mopo/mpmdeci/state_2026/index.htm', 'https://evil.example/en/mopo/mpmdeci/state_2026/index.htm'),
    POLICY.replace(
        'uncollateralized overnight call rate to remain',
        'interest paid on reserve balances to remain',
    ),
])
def test_invalid_guideline_never_borrows_neighbouring_rate(raw: str) -> None:
    with pytest.raises(ValueError):
        data._boj_policy(raw, NOW)


def test_boj_feed_preserves_original_link_and_explicit_source_clock() -> None:
    parsed = data._parse_feed(FEED, 'Bank of Japan', NOW)
    assert len(parsed) == 1
    item = parsed[0]
    assert item['published_at'] == '2026-09-30T23:50:00+00:00'
    assert item['original_url'] == 'http://www.boj.or.jp/en/mopo/opinion.pdf'
    assert item['url'] == 'https://www.boj.or.jp/en/mopo/opinion.pdf'
    assert 'ARTICLE_NOT_FETCHED' in item['link_transport']
    assert 'POLICY_DECISION_COMPLETENESS_UNKNOWN' in item['coverage_scope']
    assert 'Not article evidence' not in json.dumps(item)


@pytest.mark.parametrize('raw', [
    FEED.replace(' +0900', ''),
    FEED.replace('Thu, 01 Oct 2026', 'Fri, 02 Oct 2026'),
    FEED.replace('http://www.boj.or.jp/en/mopo/opinion.pdf', 'http://www.boj.or.jp.evil.example/en/mopo/opinion.pdf'),
    FEED.replace('<guid>http://www.boj.or.jp/en/mopo/opinion.pdf</guid>', ''),
])
def test_boj_feed_rejects_undated_future_or_false_attribution(raw: str) -> None:
    assert data._parse_feed(raw, 'Bank of Japan', NOW) == []


def test_feed_duplicate_and_identity_controls() -> None:
    equal = FEED.replace(ITEM, ITEM + ITEM)
    assert len(data._parse_feed(equal, 'Bank of Japan', NOW)) == 1
    conflict = FEED.replace(ITEM, ITEM + ITEM.replace('Summary of Opinions', 'Different title'))
    with pytest.raises(ValueError, match='Conflicting'):
        data._parse_feed(conflict, 'Bank of Japan', NOW)
    with pytest.raises(ValueError, match='identity'):
        data._parse_feed(FEED.replace('whatsnew.xml?id=1002', 'other.xml'), 'Bank of Japan', NOW)
    with pytest.raises(ValueError, match='entity'):
        data._parse_feed('<!DOCTYPE rss>' + FEED, 'Bank of Japan', NOW)
    with pytest.raises(ValueError, match='item bound'):
        data._parse_feed(FEED.replace(ITEM, ITEM * 101), 'Bank of Japan', NOW)


class SourceResponse:
    def __init__(
        self, raw: bytes, *, status: int = 200, media: str = 'text/html',
        url: str = boj_current.POLICY_URL,
    ):
        self.raw, self.status_code, self.url = raw, status, url
        self.headers = {'Content-Type': media}

    def __enter__(self) -> SourceResponse:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def iter_content(self, size: int) -> Any:
        for offset in range(0, len(self.raw), size):
            yield self.raw[offset:offset + size]


def test_original_bytes_and_receipt_are_bound_before_parsing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []
    raw = b'\xef\xbb\xbf' + POLICY.encode('utf-8')
    def get(url: str, **kwargs: Any) -> SourceResponse:
        calls.append(kwargs)
        return SourceResponse(raw)
    monkeypatch.setattr('src.private_desk.boj_current.requests.get', get)
    text, receipt = boj_current.capture_source(tmp_path, boj_current.POLICY_URL, clock=lambda: NOW)
    assert text == POLICY
    assert calls[0]['allow_redirects'] is False and calls[0]['stream'] is True
    body = receipt['source_body']
    assert Path(body['capture_path']).read_bytes() == raw
    assert hashlib.sha256(raw).hexdigest() == body['sha256']
    saved = receipt['source_receipt']
    assert hashlib.sha256(Path(saved['capture_path']).read_bytes()).hexdigest() == saved['sha256']
    assert receipt['received_at'] == NOW.isoformat() and receipt['point_in_time'] is False
    assert data._boj_policy(text, NOW)['value'] == 1.25


@pytest.mark.parametrize('response', [
    SourceResponse(b'redirect', status=302),
    SourceResponse(b'wrong media', media='application/json'),
    SourceResponse(b'wrong origin', url='https://evil.example/'),
    SourceResponse(b'x' * (128 * 1024 + 1)),
])
def test_bad_boj_transport_creates_no_accepted_capture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, response: SourceResponse,
) -> None:
    monkeypatch.setattr('src.private_desk.boj_current.requests.get', lambda *a, **k: response)
    with pytest.raises(ValueError):
        boj_current.capture_source(tmp_path, boj_current.POLICY_URL, clock=lambda: NOW)
    assert not list(tmp_path.rglob('*.bin'))


def jpy_headline(**changes: Any) -> dict[str, Any]:
    return headline(
        source="Bank of Japan",
        url="https://www.boj.or.jp/en/mopo/mpmsche_minu/opinion_2026/fixture.pdf",
        **changes,
    )


def test_v4_counts_japan_without_changing_legacy_seven_currency_admission() -> None:
    news = [jpy_headline(), headline()]
    current = ai.private_brief_input([{"pair": "USDJPY"}], news, {}, as_of=CLOCK)
    legacy = ai.private_brief_input(
        [{"pair": "USDJPY"}], news, {}, as_of=CLOCK,
        method_version="private-current-headline-v3",
    )
    assert current["input_admission"]["news_currencies"] == ["JPY", "USD"]
    assert "JPY" not in current["input_admission"]["missing_news_currencies"]
    assert len(current["headlines"]) == 2
    assert legacy["headlines"][0]["source"] == "Federal Reserve"
    assert len(legacy["headlines"]) == 1
    assert legacy["input_admission"]["news_currencies"] == ["USD"]
    assert "JPY" not in legacy["input_admission"]["missing_news_currencies"]
    assert legacy["input_admission"]["rejected_news"] == [
        {"url": news[0]["url"], "reason": "INVALID_NEWS_METADATA"}
    ]


@pytest.mark.parametrize("url", [
    "https://www.boj.or.jp.evil.example/news",
    "https://unreviewed.boj.or.jp/en/news",
    "https://unreviewed.www.boj.or.jp/en/news",
    "https://www.boj.or.jp:8443/en/news",
    "https://www.federalreserve.gov/newsevents/fixture",
    "https://user@www.boj.or.jp/en/news",
    "http://www.boj.or.jp/en/news",
])
def test_bo_j_attribution_cannot_borrow_another_host(url: str) -> None:
    item = jpy_headline()
    item["url"] = url
    payload = ai.private_brief_input([{"pair": "USDJPY"}], [item], {}, as_of=CLOCK)
    assert payload["headlines"] == []
    assert "JPY" in payload["input_admission"]["missing_news_currencies"]


def test_unknown_review_method_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        ai.private_brief_input([], [], {}, as_of=CLOCK, method_version="unreviewed-v99")


def test_saved_v3_receipt_replays_after_jpy_admission_is_added(tmp_path: Path) -> None:
    report = parent_report()
    apply_current_review(report, tmp_path, use_ai=False)
    receipt = report["current_review"]
    legacy = ai.private_brief_input(
        report["pair_reports"], report["news"], {}, as_of=receipt["reviewed_at"],
        method_version="private-current-headline-v3",
    )
    raw = ai.private_packet_text(legacy).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    path = tmp_path / "current-review" / (digest + ".json")
    path.write_bytes(raw)
    receipt.update(
        method_version="private-current-headline-v3",
        input_admission=legacy["input_admission"],
        input_packet={"capture_path": str(path), "sha256": digest},
    )
    report["ai_summary"].update(method_version="private-current-headline-v3", payload_sha256=digest)
    for item in report["pair_reports"]:
        item["ai_analysis"].update(
            method_version="private-current-headline-v3", payload_sha256=digest
        )
    receipt["output_packet"] = capture_review_output(
        report["ai_summary"], tmp_path / "current-review"
    )
    verify_current_review(report, tmp_path / "current-review")
    receipt["method_version"] = "private-current-headline-v4"
    with pytest.raises(ValueError, match="inputs no longer match"):
        verify_current_review(report, tmp_path / "current-review")
