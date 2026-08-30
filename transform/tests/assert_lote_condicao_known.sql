-- Falha se o portal expuser condição fora do conjunto conhecido.
SELECT condicao
FROM {{ ref('mart_lotes') }}
WHERE condicao IS NOT NULL
  AND condicao NOT IN ('CONSERVADO', 'SUCATA', 'INSERVÍVEL')
