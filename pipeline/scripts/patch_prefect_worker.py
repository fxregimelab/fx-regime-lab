#!/usr/bin/env python3
"""
Workaround for Prefect managed worker base-image bug where task_engine.py
expects _aget_default_persist_result but results.py doesn't define it.

This patches results.py at runtime and clears the pycache so the patched
version is loaded by the flow runner process.
"""
import inspect
import os
import shutil
import sys


def find_results_path() -> str:
    import prefect.results as pr

    return inspect.getfile(pr)


def patch() -> None:
    results_path = find_results_path()
    print(f"Patching {results_path}")

    patch_code = """
# PATCH: managed worker missing symbol workaround
async def _aget_default_persist_result() -> bool:
    persist_result = should_persist_result()
    if persist_result or _has_current_run_context():
        return persist_result
    default_block = get_current_settings().results.default_storage_block
    if default_block is not None:
        return True
    return await _aread_server_default_result_storage_block_id() is not None
"""

    with open(results_path, "a") as f:
        f.write(patch_code)

    print("Patch applied successfully")

    # Clear pycache so the patched version is loaded by the flow runner
    prefect_pkg_dir = os.path.dirname(results_path)
    pycache_dir = os.path.join(prefect_pkg_dir, "__pycache__")
    if os.path.isdir(pycache_dir):
        shutil.rmtree(pycache_dir)
        print(f"Cleared pycache: {pycache_dir}")

    # Also remove any .pyc files in the prefect package
    for root, dirs, files in os.walk(prefect_pkg_dir):
        for f in files:
            if f.endswith(".pyc"):
                os.remove(os.path.join(root, f))
        # Don't recurse into sub-packages
        break

    # Verify in this process
    import importlib

    importlib.invalidate_caches()
    if "prefect.results" in sys.modules:
        del sys.modules["prefect.results"]
    if "prefect.task_engine" in sys.modules:
        del sys.modules["prefect.task_engine"]

    from prefect.results import _aget_default_persist_result

    print(f"Verification OK: {_aget_default_persist_result}")


if __name__ == "__main__":
    patch()
