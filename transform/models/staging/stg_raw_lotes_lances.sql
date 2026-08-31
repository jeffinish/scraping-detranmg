SELECT
    id,
    run_id,
    scraped_at,
    lote_id,
    leilao_id,
    valor,
    lance_em,
    arrematante,
    peso,
    valor_quilo
FROM {{ source('raw', 'lotes_lances') }}
