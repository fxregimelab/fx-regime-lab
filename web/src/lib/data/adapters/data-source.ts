export const DataSource = {
  Live: "live",
  Backtest: "backtest",
} as const;

export type DataSource = (typeof DataSource)[keyof typeof DataSource];

/** Cutoff date separating live production calls from backtest history. */
export const LIVE_CUTOFF_DATE = "2026-05-01";

type DateFilterableQuery<T> = {
  gte: (column: string, value: string) => T;
  lt: (column: string, value: string) => T;
};

/** Apply live/backtest date filter to a Supabase query builder. */
export function applyDataSourceDateFilter<T extends DateFilterableQuery<T>>(
  query: T,
  dataSource: DataSource,
  dateColumn = "date",
): T {
  if (dataSource === DataSource.Live) {
    return query.gte(dateColumn, LIVE_CUTOFF_DATE);
  }
  if (dataSource === DataSource.Backtest) {
    return query.lt(dateColumn, LIVE_CUTOFF_DATE);
  }
  return query;
}

/** In-memory date filter for rows that already fetched. */
export function matchesDataSource(
  date: string,
  dataSource: DataSource,
): boolean {
  if (dataSource === DataSource.Live) return date >= LIVE_CUTOFF_DATE;
  if (dataSource === DataSource.Backtest) return date < LIVE_CUTOFF_DATE;
  return true;
}
