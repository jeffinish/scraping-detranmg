-- Metadado de scrape limitado. Idempotente e aditivo.
-- NULL = scrape de lotes sem --max-editais (ou run só de editais).
-- O dbt usa o último success com max_editais IS NULL e linhas em raw.lotes
-- como referência de "lote ativo".

ALTER TABLE raw.scrape_runs ADD COLUMN IF NOT EXISTS max_editais INTEGER;
