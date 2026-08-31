-- Ano extraído do card deve ser um ano de veículo plausível.
SELECT lote_id, marca_modelo, ano_veiculo
FROM {{ ref('mart_lotes') }}
WHERE ano_veiculo IS NOT NULL
  AND (
      ano_veiculo < 1950
      OR ano_veiculo > EXTRACT(YEAR FROM CURRENT_DATE)::integer + 1
  )
