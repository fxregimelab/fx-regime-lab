import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/** Canonical pair slugs — short URLs `/terminal/eurusd` rewrite to `/terminal/fx-regime/eurusd` (OG + page). */
const PAIR_SLUGS = new Set([
  'eurusd',
  'usdjpy',
  'usdinr',
  'gbpusd',
  'audusd',
  'usdcad',
  'usdchf',
]);

export function middleware(request: NextRequest) {
  const segments = request.nextUrl.pathname.split('/').filter(Boolean);
  if (segments.length === 2 && segments[0] === 'terminal') {
    const slug = segments[1].toLowerCase();
    if (PAIR_SLUGS.has(slug)) {
      const url = request.nextUrl.clone();
      url.pathname = `/terminal/fx-regime/${slug}`;
      return NextResponse.rewrite(url);
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/terminal/:path*'],
};
