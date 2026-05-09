#!/usr/bin/env python3
"""
Workaround for Prefect managed worker base-image bug where task_engine.py
expects _aget_default_persist_result but results.py doesn't define it.

This patches results.py at runtime to add the missing symbol.
"""
import inspect
import os
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

    # Verify
    import importlib

    importlib.reload(sys.modules["prefect.results"])
    from prefect.results import _aget_default_persist_result

    print(f"Verification OK: {_aget_default_persist_result}")


if __name__ == "__main__":
    patch()
