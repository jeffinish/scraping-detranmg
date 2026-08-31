SELECT
    id,
    run_id,
    scraped_at,
    leilao_id,
    numero_edital,
    municipio,
    patio,
    status,
    data_encerramento,
    url_detalhes,
    raw_hash
FROM {{ source('raw', 'editais') }}
