import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  DataSource,
  LIVE_CUTOFF_DATE,
  applyDataSourceDateFilter,
  matchesDataSource,
} from "../adapters/data-source";

describe("LIVE_CUTOFF_DATE", () => {
  it("is the canonical live/backtest boundary", () => {
    assert.equal(LIVE_CUTOFF_DATE, "2026-05-01");
  });
});

describe("matchesDataSource", () => {
  it("includes dates on or after cutoff for live", () => {
    assert.equal(matchesDataSource("2026-05-01", DataSource.Live), true);
    assert.equal(matchesDataSource("2026-06-01", DataSource.Live), true);
    assert.equal(matchesDataSource("2026-04-30", DataSource.Live), false);
  });

  it("includes dates before cutoff for backtest", () => {
    assert.equal(matchesDataSource("2026-04-30", DataSource.Backtest), true);
    assert.equal(matchesDataSource("2026-05-01", DataSource.Backtest), false);
    assert.equal(matchesDataSource("2025-01-01", DataSource.Backtest), true);
  });
});

describe("applyDataSourceDateFilter", () => {
  it("applies gte for live data source", () => {
    const calls: string[] = [];
    const query = {
      gte: (col: string, val: string) => {
        calls.push(`gte:${col}:${val}`);
        return query;
      },
      lt: (col: string, val: string) => {
        calls.push(`lt:${col}:${val}`);
        return query;
      },
    };

    applyDataSourceDateFilter(query, DataSource.Live, "date");
    assert.deepEqual(calls, [`gte:date:${LIVE_CUTOFF_DATE}`]);
  });

  it("applies lt for backtest data source", () => {
    const calls: string[] = [];
    const query = {
      gte: (col: string, val: string) => {
        calls.push(`gte:${col}:${val}`);
        return query;
      },
      lt: (col: string, val: string) => {
        calls.push(`lt:${col}:${val}`);
        return query;
      },
    };

    applyDataSourceDateFilter(query, DataSource.Backtest, "date");
    assert.deepEqual(calls, [`lt:date:${LIVE_CUTOFF_DATE}`]);
  });
});
