-- Flag de interesse (UI). Idempotente; a UI aplica na subida.
-- Requer mart_dbt.mart_lotes (rode dbt run antes de python -m detran_ui).

CREATE TABLE IF NOT EXISTS mart.lotes_interesse (
    lote_id    INTEGER PRIMARY KEY,
    flagged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lotes_interesse_flagged_at
    ON mart.lotes_interesse (flagged_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_mart_dbt_mart_lotes_lote_id
    ON mart_dbt.mart_lotes (lote_id);

ALTER TABLE mart.lotes_interesse DROP CONSTRAINT IF EXISTS lotes_interesse_lote_id_fkey;

ALTER TABLE mart.lotes_interesse
    ADD CONSTRAINT lotes_interesse_lote_id_fkey
    FOREIGN KEY (lote_id) REFERENCES mart_dbt.mart_lotes (lote_id);
