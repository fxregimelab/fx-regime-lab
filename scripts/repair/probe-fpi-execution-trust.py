"""Offline execution-trust experiment; synthetic approval is NOT production trust.

Reads pinned private originals and an earlier retained independent row inspection.
No source/receipt data is printed, persisted, downloaded, or sent to a database.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import json
import platform
import sys
import tempfile
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = Path("C:/Users/sakha/.agent-reach/fxregimelab-fpi-evidence")
CLAIM_HASH = "519bfb9420c76f83cf329d58375377c2fe9314564e8aa2349d0321770c03bb87"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "pipeline/scripts"))

from src.research.fpi_observation import build_fpi_observation  # noqa: E402
from src.research.fpi_selection import FpiParsedDay  # noqa: E402
from verify_fpi_source_capture import _CAPTURES, _verify_capture  # noqa: E402


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def require_equal(expected: Any, observed: Any) -> None:
    if expected != observed:
        raise ValueError("TRUST_COMPARISON_REJECTED")


def fingerprint_files(files: dict[str, Path]) -> dict[str, str]:
    return {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in files.items()}


def trust_manifest() -> dict[str, Any]:
    """Measure a local experiment inventory, never infer owner approval from it."""
    runtime_platform = platform.platform()
    names = (
        "pipeline/src/__init__.py",
        "pipeline/src/research/__init__.py",
        "pipeline/src/research/fpi_parser.py",
        "pipeline/src/research/fpi_observation.py",
        "pipeline/src/research/fpi_capture.py",
        "pipeline/src/research/fpi_selection.py",
        "pipeline/src/research/fpi_parse_record.py",
        "pipeline/src/signals/__init__.py",
        "pipeline/src/signals/fpi.py",
        "pipeline/src/signals/special.py",
        "pipeline/src/types.py",
        "pipeline/scripts/verify_fpi_source_capture.py",
        "pipeline/pyproject.toml",
        "scripts/repair/probe-fpi-execution-trust.py",
    )
    files = {name: ROOT / name for name in names}
    versions = {}
    # Include optional Beautiful Soup backends/encoding detectors when installed.
    for package in (
        "beautifulsoup4",
        "soupsieve",
        "typing_extensions",
        "charset-normalizer",
        "chardet",
        "lxml",
        "html5lib",
        "numpy",
    ):
        try:
            distribution = importlib.metadata.distribution(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "ABSENT"
            continue
        versions[package] = distribution.version
        for member in distribution.files or ():
            if member.suffix in {".pyc", ".pyo"} or "__pycache__" in member.parts:
                continue
            path = Path(str(distribution.locate_file(member)))
            if path.is_file():
                files[f"distribution/{package}/{member.as_posix()}"] = path
    # This bounded probe is not a full OS/interpreter release-image audit.
    files["runtime/executable"] = Path(sys.executable)
    for name, module in tuple(sys.modules.items()):
        origin = getattr(module, "__file__", None)
        if origin and Path(origin).is_file() and name not in {"__main__"}:
            files[f"loaded/{name}"] = Path(origin)
    return {
        "authority": "SYNTHETIC_OFFLINE_FIXTURE_ONLY",
        "python": sys.version,
        "platform": runtime_platform,
        "packages": versions,
        "files": fingerprint_files(files),
        "parser_backend": "html.parser",
        "source_encoding": "BeautifulSoup byte detection",
    }


def retained_claims() -> dict[str, tuple[tuple[str, str], ...]]:
    """Convert pre-existing expanded rows; do not call the HTML parser here."""
    body = (PRIVATE / "source-analysis.json").read_bytes()
    require_equal(CLAIM_HASH, hashlib.sha256(body).hexdigest())
    analysis = json.loads(body)
    claims: dict[str, tuple[tuple[str, str], ...]] = {}
    for name in ("latest", "monthly"):
        evidence = analysis[name]
        require_equal(_CAPTURES[name]["html_sha256"], evidence["sha256"])
        rows = evidence["expanded_rows"]
        require_equal(25 if name == "latest" else 450, len(rows))
        documents = []
        for offset in range(0, len(rows), 25):
            block = rows[offset : offset + 25]
            categories: dict[str, Any] = {}
            usd_categories: dict[str, Any] = {}
            total = None
            total_usd = None
            rates = set()
            dates = set()
            for row in block:
                require_equal(8, len(row))
                dates.add(row[0])
                rates.add(row[7])
                amounts = []
                for value in row[3:7]:
                    normalized = "-" + value[1:-1] if value.startswith("(") else value
                    amounts.append(format(Decimal(normalized), ".2f"))
                inr = dict(zip(("purchases_cr", "sales_cr", "net_cr"), amounts[:3], strict=True))
                category, route = row[1:3]
                if route == "Total":
                    total, total_usd = inr, amounts[3]
                    continue
                categories.setdefault(category, {"routes": {}})
                usd_categories.setdefault(category, {"routes_net_usd_million": {}})
                if route == "Sub-total":
                    categories[category]["subtotal"] = inr
                    usd_categories[category]["subtotal_net_usd_million"] = amounts[3]
                else:
                    categories[category]["routes"][route] = inr
                    usd_categories[category]["routes_net_usd_million"][route] = amounts[3]
            require_equal(1, len(rates))
            require_equal(1, len(dates))
            day_text, month_text, year_text = next(iter(dates)).split("-")
            months = (
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            )
            day = date(int(year_text), months.index(month_text) + 1, int(day_text)).isoformat()
            rate = next(iter(rates)).removeprefix("Rs.").strip()
            documents.append(
                (
                    canonical(
                        {
                            "version": "fpi-inr-observation-v1",
                            "series_id": "NSDL_FPI_CONFIRMED_REPORTED_ALL7_INR_CRORE_DAILY_V1",
                            "units": "INR_CRORE",
                            "date_basis": "reporting_date",
                            "reporting_date": day,
                            "categories": categories,
                            "total": total,
                        }
                    ),
                    canonical(
                        {
                            "version": "nsdl-fpi-source-evidence-v1",
                            "reporting_date": day,
                            "usd_units": "USD_MILLION",
                            "conversion_rate_units": "INR_PER_USD",
                            "conversion_rate_inr_per_usd": rate,
                            "categories": usd_categories,
                            "total_net_usd_million": total_usd,
                        }
                    ),
                )
            )
        claims[name] = tuple(documents)
    return claims


def reject_control(operation: Callable[[], None]) -> None:
    try:
        operation()
    except ValueError as error:
        require_equal("TRUST_COMPARISON_REJECTED", str(error))
    else:
        raise RuntimeError("NEGATIVE_CONTROL_DID_NOT_REJECT")


def execution_trust_probe() -> None:
    claims = retained_claims()
    approved_fixture = trust_manifest()
    require_equal(approved_fixture, trust_manifest())
    parsed = {}
    for name in ("latest", "monthly"):
        days, retrieved = _verify_capture(PRIVATE, name)
        parsed[name] = days
        observed = tuple(
            (day.observation.document_json, day.source_evidence.document_json) for day in days
        )
        require_equal(claims[name], observed)
        for day in days:
            observation = day.observation
            source = day.source_evidence
            require_equal(
                hashlib.sha256(observation.document_json.encode("ascii")).hexdigest(),
                observation.observation_sha256,
            )
            require_equal(
                hashlib.sha256(source.document_json.encode("ascii")).hexdigest(),
                source.evidence_sha256,
            )
            require_equal(_CAPTURES[name]["source_url"], observation.source_url)
            require_equal(_CAPTURES[name]["html_sha256"], observation.raw_sha256)
            require_equal("nsdl-fpi-html-v1", observation.parser_version)
            require_equal(retrieved, observation.retrieved_at)
            require_equal(retrieved, observation.first_seen_at)
            inr_document = json.loads(observation.document_json)
            usd_document = json.loads(source.document_json)
            require_equal(inr_document["reporting_date"], observation.reporting_date.isoformat())
            require_equal(
                int(inr_document["total"]["net_cr"].replace(".", "")), observation.net_hundredths_cr
            )
            require_equal(usd_document["total_net_usd_million"], source.total_net_usd_million)
            require_equal(
                usd_document["conversion_rate_inr_per_usd"], source.conversion_rate_inr_per_usd
            )
    require_equal(claims["latest"][0], claims["monthly"][-1])

    # A fresh, internally reconciled claim retains the same capture/code identities.
    # Its recomputed hashes cannot make it the parser's actual output.
    original = parsed["latest"][0].observation
    wrong = json.loads(original.document_json)
    category = wrong["categories"]["Equity"]
    for amounts in (category["routes"]["Stock Exchange"], category["subtotal"], wrong["total"]):
        for key in ("purchases_cr", "sales_cr"):
            amounts[key] = format(Decimal(amounts[key]) + Decimal("0.01"), ".2f")
    rebuilt = build_fpi_observation(
        reporting_date=original.reporting_date,
        categories=wrong["categories"],
        total=wrong["total"],
        source_url=original.source_url,
        raw_sha256=original.raw_sha256,
        parser_version=original.parser_version,
        retrieved_at=original.retrieved_at,
        first_seen_at=original.first_seen_at,
    )
    forged = FpiParsedDay(
        rebuilt.document_json, parsed["latest"][0].source_evidence.evidence_sha256
    )
    require_equal(original.net_hundredths_cr, forged.net_hundredths_cr)
    reject_control(lambda: require_equal(original.document_json, forged.document_json))
    wrong_claims = copy.deepcopy(claims)
    wrong_claims["latest"] = ((forged.document_json, claims["latest"][0][1]),)
    reject_control(lambda: require_equal(claims, wrong_claims))

    # Tamper with actual copied bytes, not just a supplied hash. Each control starts
    # and ends with matching bytes. Temporary files contain public code only.
    import bs4

    with tempfile.TemporaryDirectory(prefix="fpi-trust-probe-") as temporary:
        files = {
            "parser": Path(temporary) / "parser.py",
            "dependency": Path(temporary) / "dependency.py",
        }
        originals = {
            "parser": (ROOT / "pipeline/src/research/fpi_parser.py").read_bytes(),
            "dependency": Path(bs4.__file__).read_bytes(),
        }
        for key, path in files.items():
            path.write_bytes(originals[key])
        protected_fixture = fingerprint_files(files)
        for key, path in files.items():
            require_equal(protected_fixture, fingerprint_files(files))
            path.write_bytes(originals[key] + b"\n# synthetic tamper control\n")
            reject_control(lambda: require_equal(protected_fixture, fingerprint_files(files)))
            path.write_bytes(originals[key])
            require_equal(protected_fixture, fingerprint_files(files))

    # Compare the already inventoried files again. Newly loaded modules are reported
    # as a probe limitation rather than silently included in an approval assertion.
    after = trust_manifest()
    require_equal(approved_fixture["packages"], after["packages"])
    require_equal(approved_fixture["python"], after["python"])
    for name, digest in approved_fixture["files"].items():
        require_equal(digest, after["files"].get(name))
    print("19 complete INR/USD date outputs match pinned retained inspection")
    print("Wrong reconciled output, parser bytes, and dependency bytes rejected")
    print("Synthetic authority only; production execution trust remains unimplemented")
    print("FPI_EXECUTION_TRUST_PROBE_VERIFIED")


if __name__ == "__main__":
    try:
        execution_trust_probe()
    except Exception:
        # Raw source and supplied documents must never appear in diagnostic output.
        print("FPI_EXECUTION_TRUST_PROBE_FAILED", file=sys.stderr)
        raise SystemExit(1) from None
