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
),

parsed AS (
    SELECT
        ll.*,
        UPPER(TRIM(SPLIT_PART(ll.marca_modelo, '/', 1))) AS token1,
        NULLIF(TRIM(SPLIT_PART(ll.marca_modelo, '/', 2)), '') AS after_slash,
        POSITION('/' IN COALESCE(ll.marca_modelo, '')) > 0 AS has_slash
    FROM latest_listing AS ll
),

aliased AS (
    SELECT
        p.*,
        a.action AS token_action,
        a.marca_canonica AS token_marca
    FROM parsed AS p
    LEFT JOIN {{ ref('marca_aliases') }} AS a ON a.token = p.token1
),

identidade AS (
    SELECT
        aliased.*,
        CASE
            WHEN marca_modelo IS NULL OR TRIM(marca_modelo) = '' THEN NULL
            WHEN NOT has_slash THEN NULL
            WHEN token_action = 'skip' THEN
                UPPER(NULLIF(TRIM(SPLIT_PART(after_slash, ' ', 1)), ''))
            WHEN token_action = 'alias' THEN token_marca
            ELSE token1
        END AS marca_raw,
        CASE
            WHEN marca_modelo IS NULL OR TRIM(marca_modelo) = '' THEN NULL
            WHEN NOT has_slash THEN
                NULLIF(
                    TRIM(REGEXP_REPLACE(TRIM(marca_modelo), '\s+(19|20)\d{2}\s*$', '')),
                    ''
                )
            WHEN token_action = 'skip' THEN
                NULLIF(
                    TRIM(REGEXP_REPLACE(
                        TRIM(REGEXP_REPLACE(COALESCE(after_slash, ''), '^\S+\s*', '')),
                        '\s+(19|20)\d{2}\s*$',
                        ''
                    )),
                    ''
                )
            ELSE
                NULLIF(
                    TRIM(REGEXP_REPLACE(COALESCE(after_slash, ''), '\s+(19|20)\d{2}\s*$', '')),
                    ''
                )
        END AS modelo,
        -- Sufixo primeiro (AX0R 1933 S 2006 → 2006). Fallback: primeiro 19xx/20xx.
        -- POSIX não-capturante: (19|20) faria SUBSTRING devolver só 19/20.
        COALESCE(
            NULLIF(TRIM(SUBSTRING(marca_modelo FROM '(?:19|20)[0-9]{2}\s*$')), '')::integer,
            NULLIF(SUBSTRING(marca_modelo FROM '(?:19|20)[0-9]{2}'), '')::integer
        ) AS ano_veiculo
    FROM aliased
)

SELECT
    i.lote_id,
    i.leilao_id,
    i.numero_lote,
    i.condicao,
    i.marca_modelo,
    COALESCE(a2.marca_canonica, i.marca_raw) AS marca,
    i.modelo,
    i.ano_veiculo,
    e.valor_inicial,
    i.valor_atual,
    i.url_detalhes,
    b.first_seen_at,
    b.last_seen_at,
    i.raw_hash,
    i.run_id AS last_run_id,
    e.cor,
    e.ano_modelo,
    e.ano_fabricacao,
    e.combustivel,
    e.valor_incremento,
    e.status_lote
FROM identidade AS i
INNER JOIN bounds AS b ON i.lote_id = b.lote_id
LEFT JOIN enrichment AS e ON i.lote_id = e.lote_id
LEFT JOIN {{ ref('marca_aliases') }} AS a2
    ON a2.token = i.marca_raw AND a2.action = 'alias'
