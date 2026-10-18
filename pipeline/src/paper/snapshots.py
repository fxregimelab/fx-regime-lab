"""AD-T05 immutable snapshots: strict layout, digest chains, isolated restore.

A snapshot workspace is a directory ``root/<snapshot_id>`` created by
``create_snapshot_workspace`` and populated only through this module. Its
on-disk contract:

- data files written by ``archive_file`` (relative POSIX paths, parents created);
- ``archive.index.json`` — the module-owned sealed listing of every archived
  data file with its SHA-256, ``as_of`` and row count when known;
- ``manifest.json`` — ``contracts.canonical_bytes`` of one ``SnapshotManifest``
  record, committed by ``finalize_snapshot`` after the content exists;
- ``manifest.sha256`` — ``contracts.digest_record`` of that record.

The frozen ``SnapshotManifest`` record (contracts.py, used exactly as defined,
never redefined) carries a single ``content_digest``/``content_relative_path``
slot, and this module binds that slot to the sealed listing itself: the
manifest must name ``archive.index.json`` and its ``content_digest`` must equal
the SHA-256 of the index's exact canonical bytes (use ``sealed_index_digest``
to read it before building the record). ``manifest.sha256`` therefore
transitively anchors every archived file: manifest -> sealed index -> per-file
digests. ``finalize_snapshot`` and ``verify_snapshot`` both enforce the
binding, so flipping or consistently rewriting any payload and/or the index
without also rewriting the manifest record is always ``HASH_MISMATCH``.

External-witness boundary (spec 01 section 7): local verification cannot
detect an attacker who consistently rewrites every local artifact (payloads +
index + ``manifest.json`` + ``manifest.sha256``). Detecting that requires the
externally witnessed head hash that later tasks journal and compare — a local
chain alone cannot prove tail integrity.

Fail-closed reason codes: ``INVALID_SCHEMA`` (unsafe/non-normalized relpaths,
reserved names, Windows-reserved or trailing-space/dot path segments, wrong
parameter types, malformed documents, manifest/index binding violations,
unlisted reads, allowlist violations), ``SOURCE_STALE`` (row timestamp later
than ``as_of``), ``HASH_MISMATCH`` (any digest, byte-identity,
directory-equality, symlink, canonical-form or missing-evidence failure),
``CONFLICT`` (duplicate/revised archive of the same relpath, any archiving or
second finalize after ``manifest.json`` exists, non-empty workspace reuse),
``SNAPSHOT_NOT_AVAILABLE`` (missing workspace/index/manifest where the
operation needs it).

Duplicate behavior: re-archiving identical bytes with identical ``as_of`` and
row count returns the original digest; any other duplicate or revision of the
same relpath is ``CONFLICT`` — revised input must become another snapshot.

Commit order and crash behavior: ``archive_file`` writes payload bytes first
and the updated sealed index second; ``finalize_snapshot`` writes
``manifest.json`` third and ``manifest.sha256`` last. Each write is
temp-file+replace, so a crash can leave an ``.ad-tmp`` leftover or a partial
snapshot with ``manifest.json`` but no ``manifest.sha256``. Every partial state
fails closed: a retry of ``archive_file`` or ``finalize_snapshot`` is
``CONFLICT``, ``verify_snapshot`` is ``HASH_MISMATCH``, and nothing is
auto-repaired — recovery is a manual, reviewed operation.

No DB, broker, network or production client is touched. ``restore_snapshot``
gates every listed path against an fnmatch allowlist before writing any byte
and refuses targets inside the snapshot directory. ``fnmatch.fnmatchcase`` is
used deliberately: pattern matching is case-sensitive and platform-independent.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath

from src.paper.contracts import (
    ContractError,
    SnapshotManifest,
    canonical_bytes,
    digest_record,
    parse_record,
)

MANIFEST_NAME = "manifest.json"
MANIFEST_DIGEST_NAME = "manifest.sha256"
INDEX_NAME = "archive.index.json"

_RESERVED_RELPATHS = frozenset({MANIFEST_NAME, MANIFEST_DIGEST_NAME, INDEX_NAME})
# Microsoft's reserved device names: a path segment whose stem (text before the
# first dot) matches one is unusable on Windows regardless of extension, e.g.
# ``aux.txt`` aliases ``AUX``. COM0/LPT0 are included per Microsoft's reserved
# names list.
_WINDOWS_RESERVED_STEMS = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(10)}
    | {f"LPT{index}" for index in range(10)}
)
_SNAPSHOT_ID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_DIGEST_RE = re.compile(r"[0-9a-f]{64}")
_ZERO_OFFSET = timedelta(0)
_ENTRY_FIELDS = frozenset({"path", "sha256", "as_of", "row_count"})
_INDEX_FIELDS = frozenset({"files"})


@dataclass(frozen=True)
class _ArchiveEntry:
    """One sealed index row; per-file metadata the transport record cannot carry."""

    path: str
    sha256: str
    as_of: datetime | None
    row_count: int | None


def _validated_snapshot_id(snapshot_id: object) -> str:
    if type(snapshot_id) is not str or _SNAPSHOT_ID_RE.fullmatch(snapshot_id) is None:
        raise ContractError("INVALID_SCHEMA", "snapshot_id: lowercase UUID string required")
    return snapshot_id


def _validate_relpath(name: str, value: object) -> str:
    if type(value) is not str or not value:
        raise ContractError("INVALID_SCHEMA", f"{name}: non-empty relative POSIX path required")
    if value in _RESERVED_RELPATHS:
        raise ContractError("INVALID_SCHEMA", f"{name}: reserved snapshot file name {value!r}")
    if value.startswith(("/", "\\")) or "\\" in value or ":" in value:
        raise ContractError("INVALID_SCHEMA", f"{name}: relative POSIX path required")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise ContractError("INVALID_SCHEMA", f"{name}: control characters are not allowed")
    parts = PurePosixPath(value).parts
    if not parts or any(part in ("..", ".") for part in parts):
        raise ContractError("INVALID_SCHEMA", f"{name}: '..'/'./' segments are not allowed")
    for part in parts:
        if part.endswith((" ", ".")):
            raise ContractError(
                "INVALID_SCHEMA",
                f"{name}: path segment {part!r} must not end with a space or dot"
                " (Windows normalizes/aliases them)",
            )
        if part.split(".", 1)[0].upper() in _WINDOWS_RESERVED_STEMS:
            raise ContractError(
                "INVALID_SCHEMA", f"{name}: Windows-reserved path segment {part!r}"
            )
    if "/".join(parts) != value:
        raise ContractError("INVALID_SCHEMA", f"{name}: paths must be POSIX-normalized")
    return value


def _require_utc(name: str, value: object) -> datetime:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() is None
        or value.utcoffset() != _ZERO_OFFSET
    ):
        raise ContractError("INVALID_SCHEMA", f"{name}: timezone-aware UTC datetime required")
    return value


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _format_timestamp(value: datetime) -> str:
    if value.microsecond:
        return value.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    return value.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def _read_file(path: Path, *, missing_code: str, name: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise ContractError(missing_code, f"{name}: unreadable ({error})") from None


def _write_atomic(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.ad-tmp")
    if temporary.exists():
        temporary.unlink()
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _assert_no_symlink_in_path(workspace: Path, target: Path) -> None:
    relative = target.relative_to(workspace)
    current = workspace
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ContractError("INVALID_SCHEMA", f"symlinked path component refused: {part!r}")


# --- Sealed index ---------------------------------------------------------------


def _canonical_index_bytes(entries: Sequence[_ArchiveEntry]) -> bytes:
    document = {
        "files": [
            {
                "path": entry.path,
                "sha256": entry.sha256,
                "as_of": None if entry.as_of is None else _format_timestamp(entry.as_of),
                "row_count": entry.row_count,
            }
            for entry in sorted(entries, key=lambda entry: entry.path)
        ]
    }
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _index_timestamp(name: str, raw: object) -> datetime | None:
    if raw is None:
        return None
    if type(raw) is not str:
        raise ContractError("INVALID_SCHEMA", f"{name}: timestamp string or null required")
    try:
        if raw.endswith("Z"):
            return datetime.fromisoformat(raw[:-1] + "+00:00")
        return datetime.fromisoformat(raw)
    except ValueError:
        raise ContractError("INVALID_SCHEMA", f"{name}: invalid timestamp {raw!r}") from None


def _parse_index_entry(raw: object, position: int) -> _ArchiveEntry:
    name = f"{INDEX_NAME}.files[{position}]"
    if not isinstance(raw, Mapping):
        raise ContractError("INVALID_SCHEMA", f"{name}: object required")
    unknown = sorted(key for key in raw if not isinstance(key, str) or key not in _ENTRY_FIELDS)
    if unknown:
        raise ContractError("INVALID_SCHEMA", f"{name}: unknown fields {unknown!r}")
    missing = sorted(field for field in _ENTRY_FIELDS if field not in raw)
    if missing:
        raise ContractError("INVALID_SCHEMA", f"{name}: missing fields {missing!r}")
    path = _validate_relpath(f"{name}.path", raw["path"])
    digest = raw["sha256"]
    if type(digest) is not str or _DIGEST_RE.fullmatch(digest) is None:
        raise ContractError("INVALID_SCHEMA", f"{name}.sha256: lowercase sha256 hex required")
    as_of = _index_timestamp(f"{name}.as_of", raw["as_of"])
    row_count = raw["row_count"]
    if row_count is not None and (type(row_count) is not int or row_count < 0):
        raise ContractError("INVALID_SCHEMA", f"{name}.row_count: non-negative integer or null")
    return _ArchiveEntry(path=path, sha256=digest, as_of=as_of, row_count=row_count)


def _parse_index(raw: bytes) -> tuple[_ArchiveEntry, ...]:
    try:
        document: object = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError(
            "INVALID_SCHEMA", f"{INDEX_NAME}: invalid UTF-8 JSON ({error})"
        ) from None
    if not isinstance(document, Mapping):
        raise ContractError("INVALID_SCHEMA", f"{INDEX_NAME}: JSON object required")
    unknown = sorted(
        key for key in document if not isinstance(key, str) or key not in _INDEX_FIELDS
    )
    if unknown:
        raise ContractError("INVALID_SCHEMA", f"{INDEX_NAME}: unknown fields {unknown!r}")
    if "files" not in document:
        raise ContractError("INVALID_SCHEMA", f"{INDEX_NAME}.files: missing required field")
    raw_files = document["files"]
    if not isinstance(raw_files, list):
        raise ContractError("INVALID_SCHEMA", f"{INDEX_NAME}.files: JSON array required")
    entries = tuple(
        _parse_index_entry(item, position) for position, item in enumerate(raw_files)
    )
    paths = [entry.path for entry in entries]
    if len(set(paths)) != len(paths):
        raise ContractError("INVALID_SCHEMA", f"{INDEX_NAME}: duplicate file paths")
    return entries


def _load_index(workspace: Path, *, missing_code: str = "SNAPSHOT_NOT_AVAILABLE") -> tuple[
    _ArchiveEntry, ...
]:
    raw = _read_file(workspace / INDEX_NAME, missing_code=missing_code, name=INDEX_NAME)
    entries = _parse_index(raw)
    if raw != _canonical_index_bytes(entries):
        raise ContractError(
            "HASH_MISMATCH", f"{INDEX_NAME}: bytes are not the canonical sealed listing"
        )
    return entries


def _entries_by_path(entries: Sequence[_ArchiveEntry]) -> dict[str, _ArchiveEntry]:
    return {entry.path: entry for entry in entries}


# --- Public workspace operations ------------------------------------------------


def snapshot_dir(root: Path, snapshot_id: str) -> Path:
    """Return ``root / snapshot_id`` after validating the id shape."""
    return Path(root) / _validated_snapshot_id(snapshot_id)


def create_snapshot_workspace(root: Path, snapshot_id: str) -> Path:
    """Create the (empty) snapshot directory; reuse only an existing empty one."""
    workspace = snapshot_dir(root, snapshot_id)
    if workspace.exists():
        if workspace.is_dir() and not any(workspace.iterdir()):
            return workspace
        raise ContractError(
            "CONFLICT", f"snapshot workspace {snapshot_id!r} already exists and is not empty"
        )
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def archive_file(
    snapshot_dir: Path,
    relpath: str,
    payload: bytes,
    *,
    as_of: datetime,
    row_timestamps: Sequence[datetime] | None = None,
) -> str:
    """Write one immutable content file and seal its metadata into the index.

    ``as_of`` must be aware UTC; every given row timestamp must be aware UTC
    and not later than ``as_of`` (equal is allowed) or ``SOURCE_STALE``.
    Returns the file's lowercase SHA-256 hex digest. Writes the payload bytes
    first and the updated sealed index second (temp-file+replace each), so a
    crash can leave at most an unlisted payload — never a listed ghost. Once
    ``manifest.json`` (or ``manifest.sha256``) exists the snapshot is a
    finalized single commit: any further archiving is ``CONFLICT`` with no
    write.
    """
    clean = _validate_relpath("relpath", relpath)
    if type(payload) is not bytes:
        raise ContractError("INVALID_SCHEMA", "payload: bytes required")
    as_of_utc = _require_utc("as_of", as_of)
    row_count: int | None = None
    if row_timestamps is not None:
        if isinstance(row_timestamps, (str, bytes)) or not isinstance(row_timestamps, Sequence):
            raise ContractError("INVALID_SCHEMA", "row_timestamps: sequence of datetimes required")
        stamps = tuple(row_timestamps)
        for position, stamp in enumerate(stamps):
            _require_utc(f"row_timestamps[{position}]", stamp)
        for position, stamp in enumerate(stamps):
            if stamp > as_of_utc:
                raise ContractError(
                    "SOURCE_STALE",
                    f"row_timestamps[{position}]: {stamp.isoformat()} is later than as_of"
                    f" {as_of_utc.isoformat()}",
                )
        row_count = len(stamps)
    workspace = Path(snapshot_dir)
    if not workspace.is_dir():
        raise ContractError("SNAPSHOT_NOT_AVAILABLE", "snapshot workspace does not exist")
    if (workspace / MANIFEST_NAME).exists() or (workspace / MANIFEST_DIGEST_NAME).exists():
        raise ContractError(
            "CONFLICT",
            "snapshot already shows a committed manifest; no file may be archived afterwards",
        )
    entries = _load_index(workspace) if (workspace / INDEX_NAME).exists() else ()
    digest = _sha256(payload)
    existing = _entries_by_path(entries).get(clean)
    target = workspace / clean
    if existing is not None:
        if (
            existing.sha256 == digest
            and existing.as_of == as_of_utc
            and existing.row_count == row_count
            and target.is_file()
            and not target.is_symlink()
            and _sha256(target.read_bytes()) == digest
        ):
            return digest
        raise ContractError("CONFLICT", f"{clean!r}: already archived with other content")
    if target.exists() or target.is_symlink():
        raise ContractError("CONFLICT", f"{clean!r}: path already occupied by unlisted content")
    _assert_no_symlink_in_path(workspace, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(target, payload)
    entry = _ArchiveEntry(path=clean, sha256=digest, as_of=as_of_utc, row_count=row_count)
    _write_atomic(workspace / INDEX_NAME, _canonical_index_bytes((*entries, entry)))
    return digest


def sealed_index_digest(snapshot_dir: Path) -> str:
    """SHA-256 of the sealed index's exact canonical bytes.

    Callers put this digest into ``SnapshotManifest.content_digest`` with
    ``content_relative_path`` set to ``INDEX_NAME`` before calling
    ``finalize_snapshot``; the committed manifest record then anchors every
    listed file transitively.
    """
    workspace = Path(snapshot_dir)
    if not workspace.is_dir():
        raise ContractError("SNAPSHOT_NOT_AVAILABLE", "snapshot workspace does not exist")
    entries = _load_index(workspace)
    return _sha256(_canonical_index_bytes(entries))


def finalize_snapshot(snapshot_dir: Path, manifest: SnapshotManifest) -> str:
    """Commit canonical ``manifest.json`` + ``manifest.sha256``; return the digest.

    The manifest's single content slot must be bound to the sealed listing
    itself: ``content_relative_path`` must equal ``INDEX_NAME`` and
    ``content_digest`` must equal the SHA-256 of the index's exact canonical
    bytes (see ``sealed_index_digest``), else ``INVALID_SCHEMA`` /
    ``HASH_MISMATCH``. ``snapshot_id`` must equal the directory name, else
    ``INVALID_SCHEMA``. Commit order is payloads -> sealed index ->
    ``manifest.json`` -> ``manifest.sha256`` last, so a crash can leave a
    partial snapshot with ``manifest.json`` but no ``manifest.sha256``; that
    state fails closed (verification is ``HASH_MISMATCH``, retries are
    ``CONFLICT``) and is never auto-repaired — recovery is a manual, reviewed
    operation. A second finalize of the same workspace is ``CONFLICT``
    (manifests are immutable; another revision means another snapshot id).
    """
    if type(manifest) is not SnapshotManifest:
        raise ContractError("INVALID_SCHEMA", "manifest: SnapshotManifest record required")
    workspace = Path(snapshot_dir)
    if not workspace.is_dir():
        raise ContractError("SNAPSHOT_NOT_AVAILABLE", "snapshot workspace does not exist")
    if manifest.snapshot_id != workspace.name:
        raise ContractError(
            "INVALID_SCHEMA",
            f"manifest.snapshot_id {manifest.snapshot_id!r} does not match directory name"
            f" {workspace.name!r}",
        )
    if manifest.content_relative_path != INDEX_NAME:
        raise ContractError(
            "INVALID_SCHEMA",
            f"manifest.content_relative_path must be the sealed listing {INDEX_NAME!r}",
        )
    if (workspace / MANIFEST_NAME).exists() or (workspace / MANIFEST_DIGEST_NAME).exists():
        raise ContractError(
            "CONFLICT",
            "snapshot already shows a committed manifest; revised input requires a new snapshot id",
        )
    entries = _load_index(workspace)
    if manifest.content_digest != _sha256(_canonical_index_bytes(entries)):
        raise ContractError(
            "HASH_MISMATCH", "manifest content_digest disagrees with the sealed index bytes"
        )
    payload = canonical_bytes(manifest)
    _write_atomic(workspace / MANIFEST_NAME, payload)
    digest = digest_record(manifest)
    _write_atomic(workspace / MANIFEST_DIGEST_NAME, digest.encode("ascii"))
    return digest


# --- Verification ---------------------------------------------------------------


def _parse_manifest(raw: bytes) -> SnapshotManifest:
    try:
        document: object = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError(
            "INVALID_SCHEMA", f"{MANIFEST_NAME}: invalid UTF-8 JSON ({error})"
        ) from None
    if not isinstance(document, Mapping):
        raise ContractError("INVALID_SCHEMA", f"{MANIFEST_NAME}: JSON object required")
    record = parse_record(document, "SnapshotManifest")
    if not isinstance(record, SnapshotManifest):
        raise ContractError("INVALID_SCHEMA", "manifest record kind mismatch")
    return record


def _scan_tree(workspace: Path) -> tuple[str, ...]:
    found: list[str] = []
    stack: list[Path] = [workspace]
    while stack:
        current = stack.pop()
        for child in sorted(current.iterdir(), key=lambda item: item.name):
            relative = child.relative_to(workspace).as_posix()
            if child.is_symlink():
                raise ContractError(
                    "HASH_MISMATCH", f"snapshot tree contains a symlink: {relative}"
                )
            if child.is_dir():
                stack.append(child)
            else:
                found.append(relative)
    return tuple(found)


def verify_snapshot(
    snapshot_dir: Path,
    *,
    dependency_lookup: Mapping[str, bytes] | None = None,
) -> SnapshotManifest:
    """Verify every digest, byte and directory entry; return the parsed manifest.

    Checks, in order: manifest digest vs ``manifest.sha256``; manifest file
    bytes vs the record's canonical bytes; the content-slot binding
    (``content_relative_path`` must be ``INDEX_NAME`` and ``content_digest``
    must equal the SHA-256 of the index's exact canonical bytes, so flipping or
    consistently rewriting payloads and/or the listing breaks the chain);
    sealed-index parse and canonical-form check; strict directory equality
    (only the three module files plus listed data files may exist — equality
    is file-level, so an extra empty directory is not detected); every listed
    file exists, is not a symlink, hashes to its recorded digest and carries
    an aware-UTC ``as_of``; and, when ``dependency_lookup`` is given, each
    provided artifact's bytes must hash to the digest recorded for that listed
    name. Verification never writes or repairs anything. Any failure is a
    typed ``ContractError`` (``HASH_MISMATCH`` / ``INVALID_SCHEMA``). A full
    consistent local rewrite (payloads + index + manifest + manifest.sha256)
    is not detectable here; spec 01 section 7 requires the externally
    witnessed head hash for that.
    """
    workspace = Path(snapshot_dir)
    if not workspace.is_dir():
        raise ContractError("SNAPSHOT_NOT_AVAILABLE", "snapshot workspace does not exist")
    manifest_bytes = _read_file(
        workspace / MANIFEST_NAME, missing_code="SNAPSHOT_NOT_AVAILABLE", name=MANIFEST_NAME
    )
    manifest = _parse_manifest(manifest_bytes)
    stored_bytes = _read_file(
        workspace / MANIFEST_DIGEST_NAME, missing_code="HASH_MISMATCH", name=MANIFEST_DIGEST_NAME
    )
    try:
        stored_digest = stored_bytes.decode("ascii").strip()
    except UnicodeDecodeError:
        raise ContractError("HASH_MISMATCH", f"{MANIFEST_DIGEST_NAME}: not ASCII") from None
    if stored_digest != digest_record(manifest):
        raise ContractError("HASH_MISMATCH", "manifest digest does not match manifest.sha256")
    if manifest_bytes != canonical_bytes(manifest):
        raise ContractError("HASH_MISMATCH", "manifest.json is not the canonical record bytes")
    if manifest.content_relative_path != INDEX_NAME:
        raise ContractError(
            "INVALID_SCHEMA",
            f"manifest.content_relative_path must be the sealed listing {INDEX_NAME!r}",
        )
    entries = _load_index(workspace, missing_code="HASH_MISMATCH")
    if manifest.content_digest != _sha256(_canonical_index_bytes(entries)):
        raise ContractError(
            "HASH_MISMATCH", "manifest content_digest disagrees with the sealed index bytes"
        )
    by_path = _entries_by_path(entries)
    expected = {MANIFEST_NAME, MANIFEST_DIGEST_NAME, INDEX_NAME} | set(by_path)
    found = set(_scan_tree(workspace))
    missing = sorted(expected - found)
    unexpected = sorted(found - expected)
    if missing or unexpected:
        raise ContractError(
            "HASH_MISMATCH",
            f"snapshot directory mismatch: missing {missing!r}, unexpected {unexpected!r}",
        )
    for entry in entries:
        full = workspace / entry.path
        if not full.is_file() or full.is_symlink():
            raise ContractError("HASH_MISMATCH", f"{entry.path!r}: listed file is missing")
        try:
            data = full.read_bytes()
        except OSError as error:
            raise ContractError("HASH_MISMATCH", f"{entry.path!r}: unreadable ({error})") from None
        if _sha256(data) != entry.sha256:
            raise ContractError("HASH_MISMATCH", f"{entry.path!r}: content digest mismatch")
        if (
            entry.as_of is None
            or entry.as_of.tzinfo is None
            or entry.as_of.utcoffset() != _ZERO_OFFSET
        ):
            raise ContractError("HASH_MISMATCH", f"{entry.path!r}: as_of is missing or not UTC")
    if dependency_lookup is not None:
        if not isinstance(dependency_lookup, Mapping):
            raise ContractError("INVALID_SCHEMA", "dependency_lookup: mapping required")
        for name, payload in dependency_lookup.items():
            if type(name) is not str:
                raise ContractError("INVALID_SCHEMA", "dependency_lookup: string keys required")
            dependency = by_path.get(name)
            if dependency is None:
                raise ContractError(
                    "INVALID_SCHEMA",
                    f"dependency_lookup[{name!r}]: not a listed artifact of this snapshot",
                )
            if type(payload) is not bytes:
                raise ContractError(
                    "INVALID_SCHEMA", f"dependency_lookup[{name!r}]: bytes required"
                )
            if _sha256(payload) != dependency.sha256:
                raise ContractError(
                    "HASH_MISMATCH", f"dependency_lookup[{name!r}]: digest changed"
                )
    return manifest


def read_snapshot_file(snapshot_dir: Path, relpath: str) -> bytes:
    """Read one listed file, recomputing its digest before returning bytes."""
    workspace = Path(snapshot_dir)
    if not workspace.is_dir():
        raise ContractError("SNAPSHOT_NOT_AVAILABLE", "snapshot workspace does not exist")
    clean = _validate_relpath("relpath", relpath)
    entries = _load_index(workspace)
    entry = _entries_by_path(entries).get(clean)
    if entry is None:
        raise ContractError("INVALID_SCHEMA", f"{clean!r}: not listed in the snapshot index")
    full = workspace / clean
    if full.is_symlink() or not full.is_file():
        raise ContractError("HASH_MISMATCH", f"{clean!r}: listed file is missing")
    try:
        data = full.read_bytes()
    except OSError as error:
        raise ContractError("HASH_MISMATCH", f"{clean!r}: unreadable ({error})") from None
    if _sha256(data) != entry.sha256:
        raise ContractError("HASH_MISMATCH", f"{clean!r}: content digest mismatch")
    return data


def restore_snapshot(
    snapshot_dir: Path,
    target_dir: Path,
    *,
    allowlist: Sequence[str],
) -> None:
    """Restore verified files byte-for-byte into ``target_dir``.

    The snapshot is verified first, then every listed path must match at least
    one fnmatch pattern in ``allowlist`` before the first byte is written;
    ``target_dir`` equal to or inside the snapshot directory is refused.
    """
    workspace = Path(snapshot_dir)
    target = Path(target_dir)
    verify_snapshot(workspace)
    entries = _load_index(workspace, missing_code="HASH_MISMATCH")
    resolved_target = target.resolve()
    resolved_workspace = workspace.resolve()
    if resolved_target == resolved_workspace or resolved_workspace in resolved_target.parents:
        raise ContractError(
            "INVALID_SCHEMA", "restore target must be outside the snapshot directory"
        )
    if target.exists() and not target.is_dir():
        raise ContractError("INVALID_SCHEMA", "restore target is not a directory")
    if isinstance(allowlist, (str, bytes)) or not isinstance(allowlist, Sequence):
        raise ContractError("INVALID_SCHEMA", "allowlist: sequence of fnmatch patterns required")
    patterns: list[str] = []
    for position, pattern in enumerate(allowlist):
        if type(pattern) is not str or not pattern:
            raise ContractError(
                "INVALID_SCHEMA", f"allowlist[{position}]: non-empty string required"
            )
        patterns.append(pattern)
    for entry in entries:
        if not any(fnmatch.fnmatchcase(entry.path, pattern) for pattern in patterns):
            raise ContractError(
                "INVALID_SCHEMA",
                f"{entry.path!r}: restore allowlist does not cover this file; nothing was written",
            )
    for entry in entries:
        destination = target / entry.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((workspace / entry.path).read_bytes())
    for entry in entries:
        restored = (target / entry.path).read_bytes()
        if _sha256(restored) != entry.sha256:
            raise ContractError("HASH_MISMATCH", f"{entry.path!r}: restore round-trip mismatch")
