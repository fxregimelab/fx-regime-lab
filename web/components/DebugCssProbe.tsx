'use client';

import { useEffect } from 'react';

// #region agent log
const END = 'http://127.0.0.1:7535/ingest/e5bd7342-f3be-4e51-9b2f-3a19675a6208';
const SID = 'ff851f';

function send(payload: Record<string, unknown>) {
  fetch(END, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': SID },
    body: JSON.stringify({ sessionId: SID, timestamp: Date.now(), ...payload }),
  }).catch(() => {});
}
// #endregion

/** Localhost-only: HTTPS production cannot POST to http://127.0.0.1 (mixed content). */
export function DebugCssProbe() {
  useEffect(() => {
    const h = window.location.hostname;
    if (h !== 'localhost' && h !== '127.0.0.1') return;

    const sheets = document.styleSheets.length;
    const cssLink = document.querySelector('link[rel="stylesheet"][href*="static/css"]');
    const header = document.querySelector('header');
    let headerDisplay = '';
    try {
      headerDisplay = header ? getComputedStyle(header).display : 'no-header';
    } catch {
      headerDisplay = 'computed-error';
    }

    send({
      hypothesisId: 'H1',
      location: 'DebugCssProbe.tsx:mount',
      message: 'stylesheet_probe',
      data: { sheets, hasMainCssHref: !!cssLink, headerDisplay, path: window.location.pathname },
    });
  }, []);

  return null;
}
