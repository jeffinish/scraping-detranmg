-- Civic fica veiculo; Honda CG e Yamaha ficam moto.
SELECT lote_id, marca, modelo, categoria
FROM {{ ref('mart_lotes') }}
WHERE (
    marca = 'HONDA'
    AND modelo ILIKE 'CIVIC%'
    AND categoria <> 'veiculo'
)
OR (
    marca = 'HONDA'
    AND UPPER(modelo) ~ '^CG'
    AND categoria <> 'moto'
)
OR (
    marca = 'YAMAHA'
    AND categoria <> 'moto'
)
