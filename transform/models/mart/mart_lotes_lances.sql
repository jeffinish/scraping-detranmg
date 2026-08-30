WITH deduped AS (
    SELECT
        lote_id,
        leilao_id,
        valor,
        lance_em,
        arrematante,
        MIN(scraped_at) AS first_seen_at,
        MAX(scraped_at) AS last_seen_at,
        {{ last_non_null('peso') }} AS peso,
        {{ last_non_null('valor_quilo') }} AS valor_quilo
    FROM {{ ref('stg_raw_lotes_lances') }}
    GROUP BY
        lote_id,
        leilao_id,
        valor,
        lance_em,
        arrematante
)

SELECT
    ROW_NUMBER() OVER (
        ORDER BY d.lote_id, d.valor, d.lance_em NULLS LAST, d.arrematante NULLS LAST
    )::BIGINT AS id,
    d.lote_id,
    d.leilao_id,
    d.valor,
    d.lance_em,
    d.arrematante,
    d.peso,
    d.valor_quilo,
    d.first_seen_at,
    d.last_seen_at
FROM deduped AS d
INNER JOIN {{ ref('mart_lotes') }} AS l ON d.lote_id = l.lote_id
