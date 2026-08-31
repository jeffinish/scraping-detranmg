-- Token de action=skip (I, IMP, Y, …) não pode virar marca.
SELECT l.lote_id, l.marca_modelo, l.marca, a.token AS skip_token
FROM {{ ref('mart_lotes') }} AS l
INNER JOIN {{ ref('marca_aliases') }} AS a ON a.action = 'skip'
WHERE l.marca_modelo ILIKE a.token || '/%'
  AND l.marca = a.token
