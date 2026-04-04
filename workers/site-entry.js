/**
 * Minimal Worker + static assets: enables Cloudflare dashboard Variables/Secrets
 * (asset-only Workers cannot have env vars). Serves /assets/supabase-env.js from env.
 */
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    if (path === "/assets/supabase-env.js") {
      const supabaseUrl = env.SUPABASE_URL ?? "";
      const supabaseAnon = env.SUPABASE_ANON_KEY ?? "";
      const body = [
        "// Injected by Worker from Cloudflare Variables (anon key is public; protected by RLS).",
        `window.__SUPABASE_URL__ = ${JSON.stringify(supabaseUrl)};`,
        `window.__SUPABASE_ANON_KEY__ = ${JSON.stringify(supabaseAnon)};`,
        "",
      ].join("\n");
      return new Response(body, {
        headers: {
          "content-type": "application/javascript; charset=utf-8",
          "cache-control": "private, no-store",
        },
      });
    }
    return env.ASSETS.fetch(request);
  },
};
