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
),

-- Último scrape de home com sucesso e pelo menos um edital.
-- --max-editais não entra: a home sempre grava a lista completa.
-- ponytail: um miss nesse run marca o edital inativo (upgrade: 2 runs).
-- Home vazia (parser/HTML quebrado) não vira referência.
latest_full_run AS (
    SELECT s.run_id
    FROM {{ ref('stg_raw_scrape_runs') }} AS s
    WHERE s.status = 'success'
        AND EXISTS (
            SELECT 1
            FROM {{ ref('stg_raw_editais') }} AS e
            WHERE e.run_id = s.run_id
        )
    ORDER BY s.finished_at DESC NULLS LAST, s.started_at DESC
    LIMIT 1
),

presentes AS (
    SELECT DISTINCT e.leilao_id
    FROM {{ ref('stg_raw_editais') }} AS e
    INNER JOIN latest_full_run AS r ON e.run_id = r.run_id
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
    l.run_id AS last_run_id,
    (p.leilao_id IS NOT NULL) AS ativo
FROM latest AS l
INNER JOIN bounds AS b ON l.leilao_id = b.leilao_id
LEFT JOIN status_changed AS sc ON l.leilao_id = sc.leilao_id
LEFT JOIN presentes AS p ON l.leilao_id = p.leilao_id
