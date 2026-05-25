-- Backfill validation_log per-horizon net columns
-- Uses CASE for per-pair costs

UPDATE validation_log
SET
    cost_bps_t5 = CASE pair
        WHEN 'EURUSD' THEN 0.2
        WHEN 'USDJPY' THEN 0.3
        WHEN 'USDINR' THEN 1.0
        ELSE 0.5
    END,
    cost_bps_t20 = CASE pair
        WHEN 'EURUSD' THEN 0.2
        WHEN 'USDJPY' THEN 0.3
        WHEN 'USDINR' THEN 1.0
        ELSE 0.5
    END,
    correct_net_t5 = (
        predicted_direction = actual_direction_t5
        AND predicted_direction IS NOT NULL
        AND actual_direction_t5 IS NOT NULL
        AND predicted_direction != 'NEUTRAL'
    ),
    correct_net_t20 = (
        predicted_direction = actual_direction_t20
        AND predicted_direction IS NOT NULL
        AND actual_direction_t20 IS NOT NULL
        AND predicted_direction != 'NEUTRAL'
    ),
    log_return_net_bps_t5 = log_return_t5_bps - CASE pair
        WHEN 'EURUSD' THEN 0.2
        WHEN 'USDJPY' THEN 0.3
        WHEN 'USDINR' THEN 1.0
        ELSE 0.5
    END,
    log_return_net_bps_t20 = log_return_t20_bps - CASE pair
        WHEN 'EURUSD' THEN 0.2
        WHEN 'USDJPY' THEN 0.3
        WHEN 'USDINR' THEN 1.0
        ELSE 0.5
    END
WHERE correct_net_t5 IS NULL;
