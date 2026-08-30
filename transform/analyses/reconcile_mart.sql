-- Compara mart Python (mart.*) vs mart dbt (mart_dbt.*).
-- Rode após `dbt run`. Divergências = linhas em EXCEPT (deve retornar vazio no cutover).

-- Contagens
SELECT 'editais' AS entity,
    (SELECT COUNT(*) FROM mart.editais) AS mart_py,
    (SELECT COUNT(*) FROM mart_dbt.mart_editais) AS mart_dbt
UNION ALL
SELECT 'lotes',
    (SELECT COUNT(*) FROM mart.lotes),
    (SELECT COUNT(*) FROM mart_dbt.mart_lotes)
UNION ALL
SELECT 'lotes_lances',
    (SELECT COUNT(*) FROM mart.lotes_lances),
    (SELECT COUNT(*) FROM mart_dbt.mart_lotes_lances)
UNION ALL
SELECT 'status_history',
    (SELECT COUNT(*) FROM mart.editais_status_history),
    (SELECT COUNT(*) FROM mart_dbt.mart_editais_status_history);

-- Editais: diff por PK (ignora microsegundos se necessário — compare colunas de negócio)
SELECT 'mart_only' AS side, m.*
FROM mart.editais m
FULL OUTER JOIN mart_dbt.mart_editais d USING (leilao_id)
WHERE d.leilao_id IS NULL

UNION ALL

SELECT 'mart_dbt_only', d.*
FROM mart.editais m
FULL OUTER JOIN mart_dbt.mart_editais d USING (leilao_id)
WHERE m.leilao_id IS NULL;

-- Lotes: colunas com divergência de valor (mesma PK)
SELECT l.lote_id, l.leilao_id
FROM mart.lotes l
INNER JOIN mart_dbt.mart_lotes d ON l.lote_id = d.lote_id
WHERE l.numero_lote IS DISTINCT FROM d.numero_lote
   OR l.condicao IS DISTINCT FROM d.condicao
   OR l.marca_modelo IS DISTINCT FROM d.marca_modelo
   OR l.valor_inicial IS DISTINCT FROM d.valor_inicial
   OR l.valor_atual IS DISTINCT FROM d.valor_atual
   OR l.cor IS DISTINCT FROM d.cor
   OR l.ano_modelo IS DISTINCT FROM d.ano_modelo
   OR l.ano_fabricacao IS DISTINCT FROM d.ano_fabricacao
   OR l.combustivel IS DISTINCT FROM d.combustivel
   OR l.valor_incremento IS DISTINCT FROM d.valor_incremento
   OR l.status_lote IS DISTINCT FROM d.status_lote
   OR l.last_run_id IS DISTINCT FROM d.last_run_id
LIMIT 50;

-- Histórico de status (chave de negócio, sem id serial)
SELECT 'mart_only' AS side, h.*
FROM (
    SELECT leilao_id, run_id, old_status, new_status, changed_at
    FROM mart.editais_status_history
) h
EXCEPT
SELECT 'mart_only', d.*
FROM (
    SELECT leilao_id, run_id, old_status, new_status, changed_at
    FROM mart_dbt.mart_editais_status_history
) d;
