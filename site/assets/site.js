/**
 * Shared helpers: pipeline status JSON + optional Supabase (Phase 0B).
 * Set window.__SUPABASE_URL__ and window.__SUPABASE_ANON_KEY__ via Cloudflare
 * injection or a small inline script in each page (never commit real keys).
 */
(function () {
  'use strict';

  async function loadPipelineStatus() {
    try {
      const r = await fetch('/data/pipeline_status.json', { cache: 'no-store' });
      if (!r.ok) return null;
      return await r.json();
    } catch (e) {
      return null;
    }
  }

  function formatTs(iso) {
    if (!iso) return '—';
    try {
      const d = new Date(iso);
      return d.toISOString().replace('T', ' ').slice(0, 16) + ' UTC';
    } catch (e) {
      return iso;
    }
  }

  window.FXRegimeSite = {
    loadPipelineStatus,
    formatTs,
  };
})();
