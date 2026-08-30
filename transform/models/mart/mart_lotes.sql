WITH latest_listing AS (
    SELECT DISTINCT ON (lote_id)
        lote_id,
        leilao_id,
        numero_lote,
        condicao,
        marca_modelo,
        valor_atual,
        url_detalhes,
        raw_hash,
        run_id,
        scraped_at
    FROM {{ ref('stg_raw_lotes') }}
    ORDER BY lote_id, scraped_at DESC
),

enrichment AS (
    SELECT
        lote_id,
        {{ last_non_null('valor_inicial') }} AS valor_inicial,
        {{ last_non_null('cor') }} AS cor,
        {{ last_non_null('ano_modelo') }} AS ano_modelo,
        {{ last_non_null('ano_fabricacao') }} AS ano_fabricacao,
        {{ last_non_null('combustivel') }} AS combustivel,
        {{ last_non_null('valor_incremento') }} AS valor_incremento,
        {{ last_non_null('status_lote') }} AS status_lote
    FROM {{ ref('stg_raw_lotes') }}
    GROUP BY lote_id
),

bounds AS (
    SELECT
        lote_id,
        MIN(scraped_at) AS first_seen_at,
        MAX(scraped_at) AS last_seen_at
    FROM {{ ref('stg_raw_lotes') }}
    GROUP BY lote_id
)

SELECT
    ll.lote_id,
    ll.leilao_id,
    ll.numero_lote,
    ll.condicao,
    ll.marca_modelo,
    e.valor_inicial,
    ll.valor_atual,
    ll.url_detalhes,
    b.first_seen_at,
    b.last_seen_at,
    ll.raw_hash,
    ll.run_id AS last_run_id,
    e.cor,
    e.ano_modelo,
    e.ano_fabricacao,
    e.combustivel,
    e.valor_incremento,
    e.status_lote
FROM latest_listing AS ll
INNER JOIN bounds AS b ON ll.lote_id = b.lote_id
LEFT JOIN enrichment AS e ON ll.lote_id = e.lote_id
