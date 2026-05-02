-- Weekly Substack macro memos: full body for reader UI; JSON thesis bullets for daily LLM grounding only.

CREATE TABLE IF NOT EXISTS public.research_memos (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    date date NOT NULL,
    title text NOT NULL,
    raw_content text NOT NULL,
    ai_thesis_summary jsonb NOT NULL DEFAULT '[]'::jsonb,
    link_url text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT research_memos_link_url_key UNIQUE (link_url)
);

CREATE INDEX IF NOT EXISTS research_memos_date_desc ON public.research_memos (date DESC);

ALTER TABLE public.research_memos ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_read_research_memos"
ON public.research_memos
FOR SELECT
TO anon
USING (true);

CREATE POLICY "anon_deny_insert_research_memos"
ON public.research_memos
FOR INSERT
TO anon
WITH CHECK (false);

CREATE POLICY "anon_deny_update_research_memos"
ON public.research_memos
FOR UPDATE
TO anon
USING (false);

CREATE POLICY "anon_deny_delete_research_memos"
ON public.research_memos
FOR DELETE
TO anon
USING (false);

COMMENT ON TABLE public.research_memos IS 'Ingested Substack weekly memos; ai_thesis_summary feeds desk-card briefs (not raw_content).';
