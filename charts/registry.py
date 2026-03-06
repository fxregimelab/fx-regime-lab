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

    ("usdjpy", 0): (build_fundamentals_chart,    "usdjpy", 360),
    ("usdjpy", 1): (build_positioning_chart,     "usdjpy", 400),
    ("usdjpy", 2): (build_vol_correlation_chart, "usdjpy", 360),
    ("usdjpy", 3): (build_cross_asset_chart,     "usdjpy", 460),

    ("usdinr", 0): (build_fundamentals_chart,    "usdinr", 320),
    ("usdinr", 1): (build_cross_asset_chart,     "usdinr", 460),
}
