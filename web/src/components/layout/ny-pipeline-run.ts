/** Next daily pipeline anchor: 17:05 America/New_York (NYSE cash close + 5m). */

const NY_TZ = 'America/New_York';

function nyKeyAtUtc(ms: number): number {
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone: NY_TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
  const parts = fmt.formatToParts(new Date(ms));
  const g = (t: Intl.DateTimeFormatPartTypes) =>
    Number(parts.find((p) => p.type === t)!.value);
  return (
    g('year') * 1e8 +
    g('month') * 1e6 +
    g('day') * 1e4 +
    g('hour') * 100 +
    g('minute')
  );
}

/** UTC millis for wall-clock `year-month-day hour:minute` in America/New_York. */
function nyWallToUtc(
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number,
): number {
  const want = year * 1e8 + month * 1e6 + day * 1e4 + hour * 100 + minute;
  let lo = Date.UTC(year, month - 1, day - 1, 0, 0, 0);
  let hi = Date.UTC(year, month - 1, day + 2, 0, 0, 0);
  for (let i = 0; i < 56; i++) {
    const mid = (lo + hi) / 2;
    if (nyKeyAtUtc(mid) < want) {
      lo = mid;
    } else {
      hi = mid;
    }
  }
  let t = Math.floor(hi);
  while (t > lo && nyKeyAtUtc(t) >= want) {
    t -= 1000;
  }
  while (nyKeyAtUtc(t) < want) {
    t += 1000;
  }
  return t;
}

/** UTC instant of the next 17:05 America/New_York strictly after `from`. */
export function getNextPipelineRunUtc(from: Date = new Date()): Date {
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone: NY_TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  let probeMs = from.getTime();
  for (let i = 0; i < 16; i++) {
    const parts = fmt.formatToParts(new Date(probeMs));
    const y = Number(parts.find((p) => p.type === 'year')!.value);
    const m = Number(parts.find((p) => p.type === 'month')!.value);
    const d = Number(parts.find((p) => p.type === 'day')!.value);
    const targetMs = nyWallToUtc(y, m, d, 17, 5);
    if (targetMs > from.getTime()) {
      return new Date(targetMs);
    }
    probeMs = targetMs + 36 * 3600 * 1000;
  }
  return new Date(from.getTime() + 3600_000);
}

export function formatCountdownHms(msRemaining: number): string {
  const s = Math.max(0, Math.floor(msRemaining / 1000));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
}
