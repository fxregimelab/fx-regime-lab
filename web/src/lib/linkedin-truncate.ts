const LINKEDIN_MAX_CHARS = 1200;

/** Hard cap ~1,200 chars; prefer cutting at last sentence boundary before the limit. */
export function truncateLinkedInPost(text: string): string {
  const t = text.trim();
  if (t.length <= LINKEDIN_MAX_CHARS) return t;
  const slice = t.slice(0, LINKEDIN_MAX_CHARS);
  const lastPeriod = slice.lastIndexOf('.');
  if (lastPeriod > 0) {
    return slice.slice(0, lastPeriod + 1).trim();
  }
  return slice.trim();
}
