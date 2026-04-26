/** Map MOCK_EQUITY date labels like "Apr 7" to YYYY-MM-DD in `year` (backtest: 2026). */
export function mockEquityDateToYmd(label: string, year: number): string {
  const d = new Date(`${label}, ${year}`);
  if (Number.isNaN(d.getTime())) {
    return `${year}-01-01`;
  }
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${m}-${day}`;
}
