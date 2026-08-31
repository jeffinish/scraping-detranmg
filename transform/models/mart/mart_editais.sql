WITH latest AS (
    SELECT DISTINCT ON (leilao_id)
        leilao_id,
        numero_edital,
        municipio,
        patio,
        status,
        data_encerramento,
        url_detalhes,
        raw_hash,
        run_id,
        scraped_at
    FROM {{ ref('stg_raw_editais') }}
    ORDER BY leilao_id, scraped_at DESC
),

bounds AS (
    SELECT
        leilao_id,
        MIN(scraped_at) AS first_seen_at,
        MAX(scraped_at) AS last_seen_at
    FROM {{ ref('stg_raw_editais') }}
    GROUP BY leilao_id
),

status_transitions AS (
    SELECT
        leilao_id,
        scraped_at,
        status,
        LAG(status) OVER (
            PARTITION BY leilao_id
            ORDER BY scraped_at
        ) AS prev_status
    FROM {{ ref('stg_raw_editais') }}
),

status_changed AS (
    SELECT DISTINCT ON (leilao_id)
        leilao_id,
        scraped_at AS status_changed_at
    FROM status_transitions
    WHERE prev_status IS NULL
        OR prev_status IS DISTINCT FROM status
    ORDER BY leilao_id, scraped_at DESC
)

SELECT
    l.leilao_id,
    l.numero_edital,
    l.municipio,
    l.patio,
    l.status,
    l.data_encerramento,
    l.url_detalhes,
    b.first_seen_at,
    b.last_seen_at,
    COALESCE(sc.status_changed_at, b.first_seen_at) AS status_changed_at,
    l.raw_hash,
    l.run_id AS last_run_id
FROM latest AS l
INNER JOIN bounds AS b ON l.leilao_id = b.leilao_id
LEFT JOIN status_changed AS sc ON l.leilao_id = sc.leilao_id
