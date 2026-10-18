"""The price bootstrap must import from outside the pipeline working directory."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_price_population_script_bootstraps_src_without_pythonpath(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/populate_historical_prices.py"
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    # A non-main run imports the real dependencies without fetching or writing prices.
    result = subprocess.run(
        [sys.executable, "-c", f"import runpy; runpy.run_path({str(script)!r})"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
