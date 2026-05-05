-- Fix 3.2: Atomic AI request increment
CREATE OR REPLACE FUNCTION increment_ai_usage(p_date text, p_purpose text, p_model text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    INSERT INTO public.ai_usage_log (date, request_count, purpose, model)
    VALUES (p_date, 1, p_purpose, p_model);
    RETURN true;
END;
$$;
