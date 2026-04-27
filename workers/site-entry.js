/**
 * API-only Worker (no static HTML / marketing site).
 *
 * Optional secrets for Yahoo proxy (unchanged): none required for /api/health.
 * RSS and Yahoo routes work without Supabase env.
 */

export default {
  async fetch(request, _env, _ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/api/health") {
      return new Response(
        JSON.stringify({ status: "ok", timestamp: new Date().toISOString() }),
        {
          headers: {
            "Content-Type": "application/json",
            "Cache-Control": "no-store",
          },
        },
      );
    }

    if (url.pathname === "/api/substack-rss") {
      try {
        const rssResp = await fetch("https://fxregimelab.substack.com/feed", {
          headers: {
            "User-Agent": "FXRegimeLab/1.0",
            Accept: "application/rss+xml, application/xml",
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
      } catch (_e) {
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
            Accept: "application/json",
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
            },
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
          },
        );
      }
    }

    return new Response(JSON.stringify({ error: "not_found", path: url.pathname }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  },
};
