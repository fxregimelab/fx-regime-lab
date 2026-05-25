#!/usr/bin/env python3
"""Recompute validation_stats with net win rates + Clopper-Pearson CIs."""

import os
import psycopg2
from scipy.stats import beta
from dotenv import load_dotenv

load_dotenv(".env")

DB_HOST = os.getenv("SUPABASE_DB_HOST", "db.weaaacohvzzgkgxzpaee.supabase.co")
DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "6bT2H0t6FwBZtOr0H70qEYx3")
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PORT = "5432"

PAIRS = ["EURUSD", "USDJPY", "USDINR", "ALL"]
HORIZONS = ["t5", "t20"]


def clopper_pearson_ci(successes, n, alpha=0.05):
    if n == 0:
        return (0.0, 0.0)
    lower = beta.ppf(alpha / 2, successes, n - successes + 1) if successes > 0 else 0.0
    upper = beta.ppf(1 - alpha / 2, successes + 1, n - successes) if successes < n else 1.0
    return (lower, upper)


def run():
    print(f"Connecting to {DB_HOST}...")
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        sslmode="require",
    )
    conn.autocommit = True
    cur = conn.cursor()

    for pair in PAIRS:
        for horizon in HORIZONS:
            correct_col = f"correct_{horizon}"
            net_correct_col = f"correct_net_{horizon}"
            cost_col = f"cost_bps_{horizon}"
            return_col = f"log_return_{horizon}_bps"
            net_return_col = f"log_return_net_bps_{horizon}"

            # Fetch validation rows
            if pair == "ALL":
                cur.execute(
                    f"""
                    SELECT {correct_col}, {net_correct_col}, {cost_col}, {return_col}, {net_return_col}
                    FROM validation_log
                    WHERE {correct_col} IS NOT NULL;
                    """
                )
            else:
                cur.execute(
                    f"""
                    SELECT {correct_col}, {net_correct_col}, {cost_col}, {return_col}, {net_return_col}
                    FROM validation_log
                    WHERE pair = %s AND {correct_col} IS NOT NULL;
                    """,
                    (pair,),
                )

            rows = cur.fetchall()
            n = len(rows)
            if n == 0:
                print(f"  {pair} {horizon}: no data")
                continue

            wins = sum(1 for r in rows if r[0] is True)
            net_wins = sum(1 for r in rows if r[1] is True)
            win_rate = wins / n
            net_win_rate = net_wins / n

            ci_lower, ci_upper = clopper_pearson_ci(wins, n)
            net_ci_lower, net_ci_upper = clopper_pearson_ci(net_wins, n)

            costs = [r[2] for r in rows if r[2] is not None]
            avg_cost = sum(costs) / len(costs) if costs else 0.0

            # Update validation_stats — upsert by pair (only latest row)
            cur.execute(
                """
                UPDATE validation_stats
                SET
                    %(prefix)s_win_rate_ci_lower = %(ci_lower)s,
                    %(prefix)s_win_rate_ci_upper = %(ci_upper)s,
                    %(prefix)s_net_win_rate = %(net_wr)s,
                    %(prefix)s_net_win_rate_ci_lower = %(net_ci_lower)s,
                    %(prefix)s_net_win_rate_ci_upper = %(net_ci_upper)s,
                    %(prefix)s_cost_bps = %(cost)s
                WHERE pair = %(pair)s;
                """
                % {
                    "prefix": horizon,
                    "ci_lower": ci_lower,
                    "ci_upper": ci_upper,
                    "net_wr": net_win_rate,
                    "net_ci_lower": net_ci_lower,
                    "net_ci_upper": net_ci_upper,
                    "cost": avg_cost,
                    "pair": repr(pair),
                },
            )

            print(
                f"  {pair} {horizon}: n={n} WR={win_rate:.3f} NetWR={net_win_rate:.3f} "
                f"CI=[{ci_lower:.3f},{ci_upper:.3f}] cost={avg_cost:.2f}bps"
            )

    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    run()
