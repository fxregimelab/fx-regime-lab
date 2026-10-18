"""AD-T05 immutable snapshots: strict layout, digest chains, isolated restore.

The suite pins the on-disk snapshot contract: content files are written first,
the module-owned ``archive.index.json`` sealed listing second,
``manifest.json`` (canonical bytes of the frozen ``SnapshotManifest`` record)
third and ``manifest.sha256`` (its digest) last. The frozen record's single
content slot must name the sealed listing and carry the SHA-256 of its exact
canonical bytes, so ``manifest.sha256`` transitively anchors every archived
file: flipping or consistently rewriting any payload and/or the index without
also rewriting the manifest record is always detected. Every verify/read/
restore path recomputes SHA-256; any byte flip, unlisted file, missing file,
manifest edit, digest disagreement or unsafe relpath fails typed; restore is
allowlist-gated before the first byte and round-trips byte-for-byte.

Boundary: a full consistent local rewrite (payloads + index + manifest.json +
manifest.sha256) is deliberately not claimed to be detectable locally — spec 01
section 7 requires the externally witnessed head hash for that. All files live
under ``tmp_path``; no network, broker, DB or terminal is touched.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from functools import partial
from pathlib import Path
from typing import Any

import pytest

from src.paper.contracts import (
    ContractError,
    Coverage,
    Pair,
    SnapshotKind,
    SnapshotManifest,
    canonical_bytes,
    digest_record,
    parse_record,
)
from src.paper.snapshots import (
    INDEX_NAME,
    MANIFEST_DIGEST_NAME,
    MANIFEST_NAME,
    archive_file,
    create_snapshot_workspace,
    finalize_snapshot,
    read_snapshot_file,
    restore_snapshot,
    sealed_index_digest,
    snapshot_dir,
    verify_snapshot,
)

SID = "7c2e5d1a-9b3f-4e6a-8d0c-5f1a2b3c4d5e"
OTHER_SID = str(uuid.UUID("11111111-2222-3333-4444-555555555555"))
T0 = datetime(2026, 10, 18, 12, 0, 0, tzinfo=UTC)
BARS = b'{"pair":"EURUSD","bars":[[1760791200,1.1,1.2,1.0,1.15]]}'
CLOCK = b'{"broker_epoch":1760791200,"utc_epoch":1760791200,"uncertainty_s":1}'
NEWS = b'{"headlines":[{"id":"h1","publisher_family":"central-bank"}]}'
DIGEST_C = "c" * 64


def _manifest(
    snapshot_id: str = SID,
    *,
    content_path: str = INDEX_NAME,
    content_digest: str,
    available_at: datetime = T0,
) -> SnapshotManifest:
    return SnapshotManifest(
        snapshot_id=snapshot_id,
        kind=SnapshotKind.bars,
        source_id="mt5-bars",
        fetched_at=available_at,
        available_at=available_at,
        valid_from=available_at,
        expires_at=available_at + timedelta(hours=1),
        coverage=Coverage.verified,
        content_digest=content_digest,
        content_relative_path=content_path,
        clock_profile_digest=DIGEST_C,
        collector_version="ad-t05-test-v1",
        licensing_class="private-local",
        pair=Pair.EURUSD,
    )


def _build(
    tmp_path: Path,
    files: tuple[tuple[str, bytes], ...] = (("bars.json", BARS), ("clock.json", CLOCK)),
    *,
    row_file: str = "bars.json",
    row_timestamps: tuple[datetime, ...] | None = None,
) -> tuple[Path, SnapshotManifest]:
    workspace = create_snapshot_workspace(tmp_path / "archive", SID)
    for relpath, payload in files:
        rows = row_timestamps if relpath == row_file else None
        archive_file(workspace, relpath, payload, as_of=T0, row_timestamps=rows)
    manifest = _manifest(content_digest=sealed_index_digest(workspace))
    finalize_snapshot(workspace, manifest)
    return workspace, manifest


def _error(call: Callable[[], object]) -> ContractError:
    with pytest.raises(ContractError) as excinfo:
        call()
    return excinfo.value


def _index_entry(document: Any, path: str) -> Any:
    matches = [entry for entry in document["files"] if entry["path"] == path]
    assert len(matches) == 1, f"{path!r} not uniquely listed"
    return matches[0]


def _rewrite_index(workspace: Path, mutate: Callable[[Any], None]) -> None:
    """Rewrite ``archive.index.json`` canonically after ``mutate`` tampers it."""
    document = json.loads((workspace / INDEX_NAME).read_text(encoding="utf-8"))
    mutate(document)
    payload = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    (workspace / INDEX_NAME).write_bytes(payload)


def _snapshot_state(workspace: Path) -> tuple[tuple[str, ...], dict[str, bytes]]:
    children = sorted(workspace.rglob("*"))
    entries = tuple(child.relative_to(workspace).as_posix() for child in children)
    files = {
        child.relative_to(workspace).as_posix(): child.read_bytes()
        for child in children
        if child.is_file()
    }
    return entries, files


def test_unlisted_data_file_read_rejected(tmp_path: Path) -> None:
    workspace, _ = _build(tmp_path)
    assert read_snapshot_file(workspace, "bars.json") == BARS
    assert _error(lambda: read_snapshot_file(workspace, "missing.json")).code == "INVALID_SCHEMA"
    (workspace / "stray.json").write_bytes(b"{}")
    assert _error(lambda: read_snapshot_file(workspace, "stray.json")).code == "INVALID_SCHEMA"


def test_row_timestamp_after_as_of_rejected(tmp_path: Path) -> None:
    workspace = create_snapshot_workspace(tmp_path / "archive", SID)
    future = _error(
        lambda: archive_file(
            workspace,
            "bars.json",
            BARS,
            as_of=T0,
            row_timestamps=(T0 - timedelta(minutes=1), T0 + timedelta(seconds=1)),
        )
    )
    assert future.code == "SOURCE_STALE"
    assert not (workspace / "bars.json").exists()
    equal = archive_file(workspace, "bars.json", BARS, as_of=T0, row_timestamps=(T0,))
    assert len(equal) == 64
    naive = _error(
        lambda: archive_file(
            workspace,
            "clock.json",
            CLOCK,
            as_of=T0,
            row_timestamps=(datetime(2026, 10, 18, 11, 0, 0),),
        )
    )
    assert naive.code == "INVALID_SCHEMA"
    assert not (workspace / "clock.json").exists()


def test_naive_or_non_utc_as_of_rejected(tmp_path: Path) -> None:
    workspace = create_snapshot_workspace(tmp_path / "archive", SID)
    naive = _error(
        lambda: archive_file(workspace, "bars.json", BARS, as_of=datetime(2026, 10, 18, 12))
    )
    assert naive.code == "INVALID_SCHEMA"
    offset = _error(
        lambda: archive_file(
            workspace,
            "bars.json",
            BARS,
            as_of=T0.astimezone(timezone(timedelta(hours=2))),
        )
    )
    assert offset.code == "INVALID_SCHEMA"
    assert not (workspace / "bars.json").exists()


def test_dependency_digest_mismatch_rejected(tmp_path: Path) -> None:
    workspace, manifest = _build(tmp_path)
    changed = _error(
        lambda: verify_snapshot(workspace, dependency_lookup={"clock.json": CLOCK + b" "})
    )
    assert changed.code == "HASH_MISMATCH"
    refreshed = verify_snapshot(workspace, dependency_lookup={"clock.json": CLOCK})
    assert refreshed == manifest
    unknown = _error(
        lambda: verify_snapshot(workspace, dependency_lookup={"unknown.json": CLOCK})
    )
    assert unknown.code == "INVALID_SCHEMA"


def test_restore_outside_allowlist_rejected(tmp_path: Path) -> None:
    workspace, _ = _build(tmp_path)
    target = tmp_path / "restore"
    error = _error(lambda: restore_snapshot(workspace, target, allowlist=("bars.json",)))
    assert error.code == "INVALID_SCHEMA"
    assert not target.exists() or not any(target.iterdir())


def test_byte_for_byte_replay(tmp_path: Path) -> None:
    workspace, manifest = _build(tmp_path, row_timestamps=(T0 - timedelta(hours=1), T0))
    verify_snapshot(workspace)
    target = tmp_path / "restore"
    restore_snapshot(workspace, target, allowlist=("*.json",))
    assert (target / "bars.json").read_bytes() == BARS
    assert (target / "clock.json").read_bytes() == CLOCK
    assert read_snapshot_file(workspace, "bars.json") == BARS
    assert manifest.snapshot_id == SID


def test_verify_detects_payload_byte_flip(tmp_path: Path) -> None:
    workspace, _ = _build(tmp_path)
    payload = bytearray((workspace / "clock.json").read_bytes())
    payload[-1] ^= 0x01
    (workspace / "clock.json").write_bytes(bytes(payload))
    assert _error(lambda: verify_snapshot(workspace)).code == "HASH_MISMATCH"


def test_verify_detects_manifest_edit(tmp_path: Path) -> None:
    workspace, _ = _build(tmp_path)
    manifest_path = workspace / "manifest.json"
    original = manifest_path.read_bytes()
    manifest_path.write_bytes(original + b"\n")
    assert _error(lambda: verify_snapshot(workspace)).code == "HASH_MISMATCH"
    document = json.loads(original.decode("utf-8"))
    document["source_id"] = "forged-source"
    manifest_path.write_bytes(json.dumps(document, sort_keys=True).encode("utf-8"))
    assert _error(lambda: verify_snapshot(workspace)).code == "HASH_MISMATCH"
    manifest_path.write_bytes(original)
    verify_snapshot(workspace)


def test_verify_detects_unlisted_extra_file(tmp_path: Path) -> None:
    workspace, _ = _build(tmp_path)
    (workspace / "extra.bin").write_bytes(b"unexpected")
    assert _error(lambda: verify_snapshot(workspace)).code == "HASH_MISMATCH"


def test_verify_detects_missing_listed_file(tmp_path: Path) -> None:
    workspace, _ = _build(tmp_path)
    (workspace / "clock.json").unlink()
    assert _error(lambda: verify_snapshot(workspace)).code == "HASH_MISMATCH"


def test_verify_detects_consistent_manifest_digest_rewrite(tmp_path: Path) -> None:
    workspace, manifest = _build(tmp_path)
    forged = _manifest(content_path=INDEX_NAME, content_digest="a" * 64, available_at=T0)
    (workspace / MANIFEST_NAME).write_bytes(canonical_bytes(forged))
    (workspace / MANIFEST_DIGEST_NAME).write_bytes(digest_record(forged).encode("ascii"))
    error = _error(lambda: verify_snapshot(workspace))
    assert error.code == "HASH_MISMATCH"
    assert manifest.content_digest != forged.content_digest


def test_path_escape_rejected_on_archive_and_read(tmp_path: Path) -> None:
    workspace, _ = _build(tmp_path)
    unsafe = (
        "../evil",
        "..",
        "a/../../b",
        "",
        "a//b",
        "a/./b",
        "abs/path/",
        "/abs/path",
        "\\abs\\path",
        "C:\\evil",
        "sub\\file.json",
        "manifest.json",
        "manifest.sha256",
        "archive.index.json",
    )
    for bad in unsafe:
        assert _error(
            partial(archive_file, workspace, bad, BARS, as_of=T0)
        ).code == "INVALID_SCHEMA", bad
        assert _error(partial(read_snapshot_file, workspace, bad)).code == "INVALID_SCHEMA", bad
    assert not (tmp_path / "evil").exists()
    verify_snapshot(workspace)


def test_snapshot_id_validation(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    created = create_snapshot_workspace(root, SID)
    assert created == root / SID
    assert created.is_dir()
    assert snapshot_dir(root, SID) == created
    assert _error(lambda: snapshot_dir(root, SID.upper())).code == "INVALID_SCHEMA"
    assert _error(lambda: snapshot_dir(root, "not-a-uuid")).code == "INVALID_SCHEMA"
    assert _error(lambda: snapshot_dir(root, "")).code == "INVALID_SCHEMA"
    assert _error(lambda: create_snapshot_workspace(root, "not-a-uuid")).code == "INVALID_SCHEMA"


def test_manifest_roundtrip_parse_and_digest_stable(tmp_path: Path) -> None:
    workspace, manifest = _build(tmp_path)
    stored = (workspace / "manifest.json").read_bytes()
    assert stored == canonical_bytes(manifest)
    parsed = parse_record(json.loads(stored.decode("utf-8")), "SnapshotManifest")
    assert parsed == manifest
    assert canonical_bytes(parsed) == stored
    stored_digest = (workspace / "manifest.sha256").read_bytes().decode("ascii")
    assert stored_digest == digest_record(parsed)


def test_finalize_binds_content_slot_to_sealed_index(tmp_path: Path) -> None:
    workspace = create_snapshot_workspace(tmp_path / "archive", SID)
    archive_file(workspace, "bars.json", BARS, as_of=T0)
    index_digest = sealed_index_digest(workspace)
    # A payload path in the single content slot is refused: the slot is the seal.
    wrong_path = _manifest(content_path="bars.json", content_digest=index_digest)
    assert _error(lambda: finalize_snapshot(workspace, wrong_path)).code == "INVALID_SCHEMA"
    assert not (workspace / MANIFEST_NAME).exists()
    # A digest that does not match the exact canonical index bytes is refused.
    wrong_digest = _manifest(content_path=INDEX_NAME, content_digest="a" * 64)
    assert _error(lambda: finalize_snapshot(workspace, wrong_digest)).code == "HASH_MISMATCH"
    assert not (workspace / MANIFEST_NAME).exists()
    good = _manifest(content_path=INDEX_NAME, content_digest=index_digest)
    committed = finalize_snapshot(workspace, good)
    assert committed == digest_record(good)
    assert _error(lambda: finalize_snapshot(workspace, good)).code == "CONFLICT"
    verify_snapshot(workspace)


def test_duplicate_archive_idempotent_and_conflict(tmp_path: Path) -> None:
    workspace = create_snapshot_workspace(tmp_path / "archive", SID)
    first = archive_file(workspace, "bars.json", BARS, as_of=T0)
    assert archive_file(workspace, "bars.json", BARS, as_of=T0) == first
    assert _error(
        lambda: archive_file(workspace, "bars.json", BARS + b" ", as_of=T0)
    ).code == "CONFLICT"
    assert _error(
        lambda: archive_file(workspace, "bars.json", BARS, as_of=T0 + timedelta(seconds=1))
    ).code == "CONFLICT"
    assert (workspace / "bars.json").read_bytes() == BARS


def test_restore_target_inside_snapshot_dir_rejected(tmp_path: Path) -> None:
    workspace, _ = _build(tmp_path)
    inside = _error(
        lambda: restore_snapshot(workspace, workspace / "nested", allowlist=("*.json",))
    )
    assert inside.code == "INVALID_SCHEMA"
    equal = _error(lambda: restore_snapshot(workspace, workspace, allowlist=("*.json",)))
    assert equal.code == "INVALID_SCHEMA"
    assert not (workspace / "nested").exists()


def test_restore_reuses_verification_and_requires_full_allowlist(tmp_path: Path) -> None:
    workspace, _ = _build(
        tmp_path,
        files=(("bars.json", BARS), ("news.json", NEWS), ("clock.json", CLOCK)),
    )
    partial = tmp_path / "partial"
    error = _error(
        lambda: restore_snapshot(workspace, partial, allowlist=("bars.json", "news.json"))
    )
    assert error.code == "INVALID_SCHEMA"
    assert not partial.exists() or not any(partial.iterdir())
    target = tmp_path / "restore"
    restore_snapshot(workspace, target, allowlist=("*.json",))
    assert (target / "bars.json").read_bytes() == BARS
    assert (target / "news.json").read_bytes() == NEWS
    assert (target / "clock.json").read_bytes() == CLOCK
    payload = bytearray((workspace / "news.json").read_bytes())
    payload[0] ^= 0x02
    (workspace / "news.json").write_bytes(bytes(payload))
    broken = tmp_path / "restore2"
    assert _error(
        lambda: restore_snapshot(workspace, broken, allowlist=("*.json",))
    ).code == "HASH_MISMATCH"
    assert not broken.exists() or not any(broken.iterdir())


def test_snapshot_root_is_gitignored() -> None:
    gitignore = Path(__file__).resolve().parents[2] / ".gitignore"
    rules = {
        line.strip().rstrip("/")
        for line in gitignore.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    assert "data/desk" in rules


# --- Reviewer anchor probes (M2/M5/M9/M11) ---------------------------------------
#
# These probe the transitive anchor manifest.sha256 -> archive.index.json ->
# per-file digests. A full consistent local rewrite that also recomputes
# manifest.json and manifest.sha256 is out of scope by design: spec 01 section 7
# requires the externally witnessed head hash for that boundary.


def test_anchor_probe_m2_payload_byte_flip_detected(tmp_path: Path) -> None:
    """M2: flip a byte in an archived file; index and manifest untouched."""
    workspace, _ = _build(
        tmp_path,
        files=(("bars.json", BARS), ("clock.json", CLOCK), ("news.json", NEWS)),
    )
    payload = bytearray((workspace / "news.json").read_bytes())
    payload[0] ^= 0x04
    (workspace / "news.json").write_bytes(bytes(payload))
    assert _error(lambda: verify_snapshot(workspace)).code == "HASH_MISMATCH"


def test_anchor_probe_m5_payload_and_index_digest_rewrite_detected(tmp_path: Path) -> None:
    """M5: rewrite a payload byte AND its digest in the index; manifest untouched."""
    workspace, _ = _build(
        tmp_path,
        files=(("bars.json", BARS), ("clock.json", CLOCK), ("news.json", NEWS)),
    )
    payload = bytearray((workspace / "news.json").read_bytes())
    payload[0] ^= 0x08
    rewritten = bytes(payload)
    (workspace / "news.json").write_bytes(rewritten)
    new_digest = hashlib.sha256(rewritten).hexdigest()

    def rewrite_digest(document: Any) -> None:
        _index_entry(document, "news.json")["sha256"] = new_digest

    _rewrite_index(workspace, rewrite_digest)
    assert _error(lambda: verify_snapshot(workspace)).code == "HASH_MISMATCH"


def test_anchor_probe_m9_index_listing_tamper_detected(tmp_path: Path) -> None:
    """M9: tamper only the index listing; manifest and payloads untouched."""
    files = (("bars.json", BARS), ("clock.json", CLOCK), ("news.json", NEWS))

    def swap_digests(document: Any) -> None:
        clock = _index_entry(document, "clock.json")
        news = _index_entry(document, "news.json")
        clock["sha256"], news["sha256"] = news["sha256"], clock["sha256"]

    def drop_entry(document: Any) -> None:
        document["files"] = [
            entry for entry in document["files"] if entry["path"] != "news.json"
        ]

    def add_entry(document: Any) -> None:
        document["files"].append(
            {"path": "ghost.json", "sha256": "d" * 64, "as_of": None, "row_count": None}
        )

    def listing_only_edit(document: Any) -> None:
        # ``row_count`` is not re-derived from the payload, so this canonical
        # edit is only caught by the manifest -> index digest binding.
        _index_entry(document, "bars.json")["row_count"] = 0

    for label, mutate in (
        ("swap", swap_digests),
        ("drop", drop_entry),
        ("add", add_entry),
        ("listing-only", listing_only_edit),
    ):
        workspace, _ = _build(tmp_path / label, files=files)
        _rewrite_index(workspace, mutate)
        assert _error(lambda: verify_snapshot(workspace)).code == "HASH_MISMATCH", label


def test_anchor_probe_m11_consistent_payload_index_rewrite_detected(tmp_path: Path) -> None:
    """M11: consistently rewrite every payload and the whole index; manifest untouched.

    The local payload/index pair stays coherent, so only the manifest -> index
    digest binding can detect it without the external witness.
    """
    workspace, _ = _build(
        tmp_path,
        files=(("bars.json", BARS), ("clock.json", CLOCK), ("news.json", NEWS)),
    )
    document = json.loads((workspace / INDEX_NAME).read_text(encoding="utf-8"))
    for entry in document["files"]:
        payload = (workspace / entry["path"]).read_bytes() + b"!"
        (workspace / entry["path"]).write_bytes(payload)
        entry["sha256"] = hashlib.sha256(payload).hexdigest()
    (workspace / INDEX_NAME).write_bytes(
        json.dumps(
            document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    )
    assert _error(lambda: verify_snapshot(workspace)).code == "HASH_MISMATCH"


def test_verify_rejects_non_canonical_sealed_index(tmp_path: Path) -> None:
    workspace, _ = _build(tmp_path)
    document = json.loads((workspace / INDEX_NAME).read_text(encoding="utf-8"))
    (workspace / INDEX_NAME).write_bytes(json.dumps(document).encode("utf-8"))
    assert _error(lambda: verify_snapshot(workspace)).code == "HASH_MISMATCH"


def test_finalize_rejects_non_canonical_sealed_index(tmp_path: Path) -> None:
    workspace = create_snapshot_workspace(tmp_path / "archive", SID)
    archive_file(workspace, "bars.json", BARS, as_of=T0)
    canonical = (workspace / INDEX_NAME).read_bytes()
    document = json.loads(canonical)
    non_canonical = json.dumps(document, separators=(", ", ": ")).encode("utf-8")
    assert non_canonical != canonical
    (workspace / INDEX_NAME).write_bytes(non_canonical)
    manifest = _manifest(
        content_path=INDEX_NAME,
        content_digest=hashlib.sha256(canonical).hexdigest(),
    )
    error = _error(lambda: finalize_snapshot(workspace, manifest))
    assert error.code == "HASH_MISMATCH"
    assert not (workspace / MANIFEST_NAME).exists()


def test_verify_rejects_manifest_content_slot_not_the_sealed_index(tmp_path: Path) -> None:
    workspace, _ = _build(tmp_path)
    index_digest = sealed_index_digest(workspace)
    forged = _manifest(content_path="bars.json", content_digest=index_digest)
    (workspace / MANIFEST_NAME).write_bytes(canonical_bytes(forged))
    (workspace / MANIFEST_DIGEST_NAME).write_bytes(digest_record(forged).encode("ascii"))
    assert _error(lambda: verify_snapshot(workspace)).code == "INVALID_SCHEMA"


def test_archive_after_finalize_rejected_without_writes(tmp_path: Path) -> None:
    """Once manifest.json exists the snapshot is one immutable commit."""
    workspace, _ = _build(tmp_path)
    state = _snapshot_state(workspace)
    error = _error(lambda: archive_file(workspace, "late.json", NEWS, as_of=T0))
    assert error.code == "CONFLICT"
    assert _snapshot_state(workspace) == state


def test_finalize_binds_snapshot_id_to_directory(tmp_path: Path) -> None:
    workspace = create_snapshot_workspace(tmp_path / "archive", SID)
    archive_file(workspace, "bars.json", BARS, as_of=T0)
    index_digest = sealed_index_digest(workspace)
    mismatched = _manifest(snapshot_id=OTHER_SID, content_digest=index_digest)
    error = _error(lambda: finalize_snapshot(workspace, mismatched))
    assert error.code == "INVALID_SCHEMA"
    assert not (workspace / MANIFEST_NAME).exists()
    matching = _manifest(snapshot_id=SID, content_digest=index_digest)
    assert finalize_snapshot(workspace, matching) == digest_record(matching)
    verify_snapshot(workspace)
    assert _error(lambda: finalize_snapshot(workspace, matching)).code == "CONFLICT"


def test_windows_reserved_and_trailing_segment_relpaths_rejected(tmp_path: Path) -> None:
    workspace = create_snapshot_workspace(tmp_path / "archive", SID)
    unsafe = (
        "CON",
        "con",
        "aux.txt",
        "nested/AUX.log",
        "COM1.bin",
        "com0",
        "LPT9",
        "nested/LPT1/data.json",
        "PRN",
        "NUL",
        "foo.",
        "bar ",
        "a/foo./b",
        "a/b ",
        " ",
        "a/ /b",
    )
    for bad in unsafe:
        assert _error(partial(archive_file, workspace, bad, BARS, as_of=T0)).code == (
            "INVALID_SCHEMA"
        ), bad
        assert _error(partial(read_snapshot_file, workspace, bad)).code == (
            "INVALID_SCHEMA"
        ), bad
    digest = archive_file(workspace, "nested/ok.json", BARS, as_of=T0)
    assert len(digest) == 64
    manifest = _manifest(content_digest=sealed_index_digest(workspace))
    finalize_snapshot(workspace, manifest)
    assert read_snapshot_file(workspace, "nested/ok.json") == BARS
    verify_snapshot(workspace)


def test_partial_finalize_without_manifest_digest_fails_closed(tmp_path: Path) -> None:
    """Crash between finalize's writes: fail closed, never auto-repaired."""
    workspace = create_snapshot_workspace(tmp_path / "archive", SID)
    archive_file(workspace, "bars.json", BARS, as_of=T0)
    manifest = _manifest(content_digest=sealed_index_digest(workspace))
    (workspace / MANIFEST_NAME).write_bytes(canonical_bytes(manifest))
    state = _snapshot_state(workspace)
    assert _error(lambda: verify_snapshot(workspace)).code == "HASH_MISMATCH"
    assert _snapshot_state(workspace) == state
    assert not (workspace / MANIFEST_DIGEST_NAME).exists()
    assert _error(lambda: finalize_snapshot(workspace, manifest)).code == "CONFLICT"
    assert _error(lambda: archive_file(workspace, "late.json", NEWS, as_of=T0)).code == (
        "CONFLICT"
    )
    assert _snapshot_state(workspace) == state
