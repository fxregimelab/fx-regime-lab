import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/** Stub: terminal routes are matched for future auth. */
export function middleware(_request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: ['/terminal/:path*'],
};
