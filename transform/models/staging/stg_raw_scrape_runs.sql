SELECT
    run_id,
    started_at,
    finished_at,
    editais_count,
    status,
    error_message
FROM {{ source('raw', 'scrape_runs') }}
