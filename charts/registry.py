# charts/registry.py
# Mapping of (pair, pane_index) → chart builder.
# This is the single place to add/remove chart tabs and pairs.
# create_html_brief.py iterates this dict — no hardcoded per-pair logic there.
#
# To add GBPUSD:
#   1. Add "gbpusd" entry in config.PAIRS
#   2. Add ("gbpusd", 0), ("gbpusd", 1) etc. entries below
#   3. Add a card block to reports/template.py (Step 9)
#   That's it — html.py, chart injection, everything else scales automatically.

from create_charts_plotly import (
    build_fundamentals_chart,
    build_positioning_chart,
    build_vol_correlation_chart,
    build_cross_asset_chart,
    build_boj_signal_chart,
    build_fpi_flows_chart,
    build_momentum_chart,
    build_composite_trend_chart,
)
from charts.workspace import build_global_workspace_html

# Each entry: (pair, pane_index) → (builder_callable, pair_str, height_px)
# builder_callable receives pair as its only argument.
# If builder returns a str (raw HTML), it is written directly to charts/{pair}_{pane}.html
CHART_REGISTRY = {
    ("eurusd", 0): (build_fundamentals_chart,    "eurusd", 360),
    ("eurusd", 1): (build_positioning_chart,     "eurusd", 400),
    ("eurusd", 2): (build_vol_correlation_chart, "eurusd", 360),
    ("eurusd", 3): (build_cross_asset_chart,     "eurusd", 460),
    ("eurusd", 4): (build_momentum_chart,        "eurusd", 280),
    ("eurusd", 5): (build_composite_trend_chart, "eurusd", 360),

    ("usdjpy", 0): (build_fundamentals_chart,    "usdjpy", 360),
    ("usdjpy", 1): (build_positioning_chart,     "usdjpy", 400),
    ("usdjpy", 2): (build_vol_correlation_chart, "usdjpy", 360),
    ("usdjpy", 3): (build_cross_asset_chart,     "usdjpy", 460),
    ("usdjpy", 4): (build_boj_signal_chart,      "usdjpy", 400),
    ("usdjpy", 5): (build_momentum_chart,        "usdjpy", 280),
    ("usdjpy", 6): (build_composite_trend_chart, "usdjpy", 360),

    ("usdinr", 0): (build_fundamentals_chart,    "usdinr", 320),
    ("usdinr", 1): (build_cross_asset_chart,     "usdinr", 460),
    ("usdinr", 2): (build_vol_correlation_chart, "usdinr", 360),
    ("usdinr", 3): (build_fpi_flows_chart,       "usdinr", 380),
    ("usdinr", 4): (build_momentum_chart,        "usdinr", 280),
    ("usdinr", 5): (build_composite_trend_chart, "usdinr", 360),
}


def _validate_registry():
    for (pair, idx), (builder, pair_str, height) in CHART_REGISTRY.items():
        assert pair == pair_str, \
            f"Registry mismatch: key pair '{pair}' != entry pair_str '{pair_str}'"


_validate_registry()
