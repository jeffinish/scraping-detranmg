-- Flag de interesse (UI). Idempotente: volume Docker existente não reexecuta 001.
-- A UI aplica este arquivo na subida; volumes novos também rodam via initdb.

CREATE TABLE IF NOT EXISTS mart.lotes_interesse (
    lote_id    INTEGER PRIMARY KEY REFERENCES mart.lotes (lote_id),
    flagged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lotes_interesse_flagged_at
    ON mart.lotes_interesse (flagged_at DESC);
