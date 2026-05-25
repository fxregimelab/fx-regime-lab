#!/usr/bin/env python3
"""Backfill validation_log net columns for all rows."""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env")

DB_HOST = os.getenv("SUPABASE_DB_HOST", "db.weaaacohvzzgkgxzpaee.supabase.co")
DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "6bT2H0t6FwBZtOr0H70qEYx3")
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PORT = "5432"

COST_BPS_ROUND_TRIP = {"EURUSD": 0.2, "USDJPY": 0.3, "USDINR": 1.0}


def is_correct(predicted, realized):
    if predicted == "UP" and realized == "UP":
        return True
    if predicted == "DOWN" and realized == "DOWN":
        return True
    return False


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

    # Count rows to backfill
    cur.execute("SELECT COUNT(*) FROM validation_log WHERE correct_net_t5 IS NULL;")
    total_to_backfill = cur.fetchone()[0]
    print(f"Rows to backfill: {total_to_backfill}")

    if total_to_backfill == 0:
        print("Nothing to backfill.")
        cur.close()
        conn.close()
        return

    batch_size = 2000
    offset = 0
    total_updated = 0

    while True:
        cur.execute(
            """
            SELECT id, pair, predicted_direction, actual_direction_t5, actual_direction_t20,
                   log_return_t5_bps, log_return_t20_bps
            FROM validation_log
            WHERE correct_net_t5 IS NULL
            ORDER BY id
            LIMIT %s OFFSET %s;
            """,
            (batch_size, offset),
        )
        rows = cur.fetchall()
        if not rows:
            break

        for row in rows:
            row_id, pair, predicted, actual_t5, actual_t20, gross_t5, gross_t20 = row
            cost_bps = COST_BPS_ROUND_TRIP.get(pair, 0.5)

            # T+5
            t5_net = (gross_t5 - cost_bps) if gross_t5 is not None else None
            t5_correct = is_correct(predicted, actual_t5)

            # T+20
            t20_net = (gross_t20 - cost_bps) if gross_t20 is not None else None
            t20_correct = is_correct(predicted, actual_t20)

            cur.execute(
                """
                UPDATE validation_log
                SET correct_net_t5 = %s,
                    correct_net_t20 = %s,
                    cost_bps_t5 = %s,
                    cost_bps_t20 = %s,
                    log_return_net_bps_t5 = %s,
                    log_return_net_bps_t20 = %s
                WHERE id = %s;
                """,
                (t5_correct, t20_correct, cost_bps, cost_bps, t5_net, t20_net, row_id),
            )

        total_updated += len(rows)
        print(f"Updated {total_updated}/{total_to_backfill} rows...")
        offset += batch_size

    cur.close()
    conn.close()
    print(f"Done! Total updated: {total_updated}")


if __name__ == "__main__":
    run()
