WITH status_transitions AS (
    SELECT
        leilao_id,
        run_id,
        scraped_at,
        status,
        LAG(status) OVER (
            PARTITION BY leilao_id
            ORDER BY scraped_at
        ) AS prev_status
    FROM {{ ref('stg_raw_editais') }}
),

changes AS (
    SELECT
        leilao_id,
        run_id,
        prev_status AS old_status,
        status AS new_status,
        scraped_at AS changed_at
    FROM status_transitions
    WHERE prev_status IS NOT NULL
        AND prev_status IS DISTINCT FROM status
)

SELECT
    ROW_NUMBER() OVER (
        ORDER BY leilao_id, changed_at
    )::BIGINT AS id,
    leilao_id,
    run_id,
    old_status,
    new_status,
    changed_at
FROM changes
