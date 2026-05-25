-- FX Regime Lab V3 — CMS-like site content table
-- Allows editing hero text, principles, about bio without code deploys

CREATE TABLE IF NOT EXISTS site_content (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key         TEXT NOT NULL UNIQUE,
  section     TEXT NOT NULL,
  content     TEXT NOT NULL,
  content_type TEXT DEFAULT 'text',
  version     INTEGER DEFAULT 1,
  is_active   BOOLEAN DEFAULT true,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE site_content ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_read_site_content" ON site_content;
CREATE POLICY "anon_read_site_content"
  ON site_content FOR SELECT TO anon USING (is_active = true);

DROP POLICY IF EXISTS "anon_deny_write_site_content" ON site_content;
CREATE POLICY "anon_deny_write_site_content"
  ON site_content FOR ALL TO anon USING (false);

-- Seed initial content
INSERT INTO site_content (key, section, content, content_type) VALUES
('hero.headline', 'hero', 'FX Regime Classification System', 'text'),
('hero.subheadline', 'hero', 'Daily macro regime calls for EUR/USD, USD/JPY, and USD/INR. Published before the outcome is known. Validated after.', 'text'),
('hero.cta_primary', 'hero', 'Read Today''s Brief', 'text'),
('hero.cta_secondary', 'hero', 'Explore the Framework', 'text'),
('principle.quote', 'principles', 'Credibility compounds through calendar discipline and honest validation, not marketing.', 'text'),
('principle.explanation', 'principles', 'Any discretionary framework can be constructed to look correct in hindsight. The only meaningful test is publishing the call before the outcome is known — and logging the result without revision.', 'text'),
('about.bio', 'about', 'Macro researcher focused on systematic FX regime classification. Built FX Regime Lab to bridge the gap between institutional-grade quantitative research and publicly accessible daily regime classifications.', 'text'),
('about.credentials', 'about', 'EE Undergrad · Discretionary Macro Research', 'text'),
('footer.tagline', 'footer', 'Built with institutional discipline. Validated out-of-sample.', 'text'),
('about.data_sources', 'about', 'Data sourced from FRED (Federal Reserve Economic Data), CFTC Commitments of Traders, Alpha Vantage, CME Group, and RBI. Cross-asset proxies from Bloomberg-equivalent public feeds.', 'text'),
('about.legal_entity', 'about', 'FX Regime Lab is an independent research publication. Not registered as an investment adviser.', 'text')
ON CONFLICT (key) DO NOTHING;
