-- Independently observable invariants after Python drives actual transactions.
DO $$ BEGIN
  IF (SELECT count(*) FROM validation_log WHERE call_id=1 AND evaluation_version='legacy-unversioned'
      AND is_superseded=false AND correct_t5=false AND log_return_t5_bps=-20) <> 1 THEN
    RAISE EXCEPTION 'Legacy evidence was changed';
  END IF;
  IF (SELECT count(*) FROM validation_log WHERE call_id=1 AND evaluation_version='published-direction-v1'
      AND is_superseded=false AND log_return_t5_bps IS NOT NULL AND log_return_t20_bps IS NOT NULL) <> 1 THEN
    RAISE EXCEPTION 'Current version is missing or ambiguous';
  END IF;
  IF has_function_privilege('anon','public.append_validation_evaluation(jsonb)','EXECUTE')
     OR has_function_privilege('authenticated','public.append_validation_evaluation(jsonb)','EXECUTE')
     OR NOT has_function_privilege('service_role','public.append_validation_evaluation(jsonb)','EXECUTE') THEN
    RAISE EXCEPTION 'RPC privileges are wrong';
  END IF;
END $$;
