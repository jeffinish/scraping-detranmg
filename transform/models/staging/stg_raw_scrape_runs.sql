SELECT
    run_id,
    started_at,
    finished_at,
    editais_count,
    max_editais,
    status,
    error_message
FROM {{ source('raw', 'scrape_runs') }}
