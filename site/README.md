# FX Regime Lab static site (Cloudflare Pages)

- **Publish directory:** `site/` (root = `index.html`).
- **Newsletter:** `_redirects` sends `/newsletter` → Substack (301).
- **Supabase in browser (Phase 0B):** inject before other scripts on pages that need live data, e.g. in Cloudflare **Custom code** or an HTML transform:

```html
<script>
  window.__SUPABASE_URL__ = 'https://YOUR_PROJECT.supabase.co';
  window.__SUPABASE_ANON_KEY__ = 'YOUR_ANON_KEY';
</script>
```

Never put the **service role** key in Pages. See `CLOUDFLARE_SETUP.md` for DNS and project wiring.
