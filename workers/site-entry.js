/**
 * Minimal Worker + static assets: enables Cloudflare dashboard Variables/Secrets
 * (asset-only Workers cannot have env vars). Serves /assets/supabase-env.js from env.
 *
 * REQUIRED Worker env vars (set in Cloudflare dashboard → Workers → Settings → Variables):
 *   SUPABASE_URL — project URL (https://xxx.supabase.co)
 *   SUPABASE_ANON_KEY — public anon key (RLS enforced; browser reads only)
 *
 */
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/api/health") {
      return new Response(
        JSON.stringify({ status: "ok", timestamp: new Date().toISOString() }),
        {
          headers: {
            "Content-Type": "application/json",
            "Cache-Control": "no-store",
          },
        }
      );
    }
    if (url.pathname === "/api/substack-rss") {
      try {
        const rssResp = await fetch("https://fxregimelab.substack.com/feed", {
          headers: {
            "User-Agent": "FXRegimeLab/1.0",
            "Accept": "application/rss+xml, application/xml",
          },
          cf: { cacheTtl: 3600 },
        });
        const rssText = await rssResp.text();
        return new Response(rssText, {
          headers: {
            "Content-Type": "application/xml",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600",
          },
        });
      } catch (e) {
        return new Response("RSS fetch failed", { status: 502 });
      }
    }

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

    if (path.startsWith("/data/") || path.startsWith("/static/")) {
      const response = await env.ASSETS.fetch(request);
      if (path.startsWith("/static/") && path.endsWith(".json")) {
        const headers = new Headers(response.headers);
        headers.set("Access-Control-Allow-Origin", "*");
        headers.set("Cache-Control", "public, max-age=3600");
        return new Response(response.body, {
          status: response.status,
          statusText: response.statusText,
          headers,
        });
      }
      return response;
    }

    return env.ASSETS.fetch(request);
  },
};
