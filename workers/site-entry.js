/**
 * Minimal Worker + static assets: enables Cloudflare dashboard Variables/Secrets
 * (asset-only Workers cannot have env vars). Serves /assets/supabase-env.js from env.
 *
 * REQUIRED Worker env vars (set in Cloudflare dashboard → Workers → Settings → Variables):
 *   SUPABASE_URL — project URL (https://xxx.supabase.co)
 *   SUPABASE_ANON_KEY — public anon key (RLS enforced; browser reads only)
 *
 */

/** Injected on HTML responses so the browser can load Supabase + inline methodology scripts. */
const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com data:",
  "img-src 'self' data: https: blob:",
  "connect-src 'self' https://*.supabase.co https://weaaacohvzzgkgxzpaee.supabase.co",
  "frame-src 'self' https:",
].join("; ");

function withHtmlCsp(response) {
  const ct = response.headers.get("content-type") || "";
  if (!ct.includes("text/html")) {
    return response;
  }
  const headers = new Headers(response.headers);
  headers.set("Content-Security-Policy", CONTENT_SECURITY_POLICY);
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

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

    if (url.pathname === "/api/fx-price") {
      const symbol = url.searchParams.get("symbol");
      if (!symbol) {
        return new Response(JSON.stringify({ error: "no symbol" }), {
          headers: { "Content-Type": "application/json" },
        });
      }
      const yahooUrl =
        "https://query1.finance.yahoo.com/v8/finance/chart/" +
        encodeURIComponent(symbol) +
        "?interval=1m&range=1d";
      try {
        const resp = await fetch(yahooUrl, {
          headers: {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
          },
          signal: AbortSignal.timeout(5000),
        });
        const data = await resp.json();
        return new Response(JSON.stringify(data), {
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=30",
          },
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), {
          status: 502,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
          },
        });
      }
    }

    if (url.pathname === "/proxy/yahoo" || url.pathname.startsWith("/proxy/yahoo/")) {
      if (request.method === "OPTIONS") {
        return new Response(null, {
          status: 200,
          headers: {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Accept, Content-Type",
            "Access-Control-Max-Age": "86400",
          },
        });
      }

      const rest = url.pathname.slice("/proxy/yahoo".length);
      const upstreamPath = rest === "" ? "/" : rest;
      const upstreamUrl = "https://query1.finance.yahoo.com" + upstreamPath + url.search;

      try {
        const upstreamResp = await fetch(upstreamUrl, {
          method: request.method,
          headers: {
            "User-Agent": "Mozilla/5.0",
            Accept: "application/json",
          },
          signal: AbortSignal.timeout(15000),
        });

        if (!upstreamResp.ok) {
          return new Response(
            JSON.stringify({
              error: "upstream error",
              status: upstreamResp.status,
            }),
            {
              status: 502,
              headers: {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
              },
            }
          );
        }

        const outHeaders = new Headers();
        outHeaders.set("Access-Control-Allow-Origin", "*");
        const ct = upstreamResp.headers.get("Content-Type");
        if (ct) outHeaders.set("Content-Type", ct);

        return new Response(upstreamResp.body, {
          status: upstreamResp.status,
          statusText: upstreamResp.statusText,
          headers: outHeaders,
        });
      } catch (e) {
        return new Response(
          JSON.stringify({ error: e.message || "upstream fetch failed" }),
          {
            status: 502,
            headers: {
              "Content-Type": "application/json",
              "Access-Control-Allow-Origin": "*",
            },
          }
        );
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
      return withHtmlCsp(response);
    }

    return withHtmlCsp(await env.ASSETS.fetch(request));
  },
};
