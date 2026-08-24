-- Enriquecimento de lotes + histórico de lances.
-- Idempotente e aditivo: nao remove tabela, coluna ou linha. Volumes Docker ja
-- inicializados com 001 não reexecutam aquele arquivo; o scraper aplica este.

ALTER TABLE raw.lotes ADD COLUMN IF NOT EXISTS cor VARCHAR(50);
ALTER TABLE raw.lotes ADD COLUMN IF NOT EXISTS ano_modelo INTEGER;
ALTER TABLE raw.lotes ADD COLUMN IF NOT EXISTS ano_fabricacao INTEGER;
ALTER TABLE raw.lotes ADD COLUMN IF NOT EXISTS combustivel VARCHAR(50);
ALTER TABLE raw.lotes ADD COLUMN IF NOT EXISTS valor_incremento NUMERIC(12, 2);
ALTER TABLE raw.lotes ADD COLUMN IF NOT EXISTS status_lote VARCHAR(8);

ALTER TABLE mart.lotes ADD COLUMN IF NOT EXISTS cor VARCHAR(50);
ALTER TABLE mart.lotes ADD COLUMN IF NOT EXISTS ano_modelo INTEGER;
ALTER TABLE mart.lotes ADD COLUMN IF NOT EXISTS ano_fabricacao INTEGER;
ALTER TABLE mart.lotes ADD COLUMN IF NOT EXISTS combustivel VARCHAR(50);
ALTER TABLE mart.lotes ADD COLUMN IF NOT EXISTS valor_incremento NUMERIC(12, 2);
ALTER TABLE mart.lotes ADD COLUMN IF NOT EXISTS status_lote VARCHAR(8);

CREATE TABLE IF NOT EXISTS raw.lotes_lances (
    id           BIGSERIAL PRIMARY KEY,
    run_id       UUID NOT NULL REFERENCES raw.scrape_runs (run_id),
    scraped_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    lote_id      INTEGER NOT NULL,
    leilao_id    INTEGER NOT NULL,
    valor        NUMERIC(12, 2) NOT NULL,
    lance_em     TIMESTAMP,
    arrematante  TEXT,
    peso         NUMERIC(12, 4),
    valor_quilo  NUMERIC(12, 2)
);

CREATE INDEX IF NOT EXISTS idx_raw_lotes_lances_run ON raw.lotes_lances (run_id);
CREATE INDEX IF NOT EXISTS idx_raw_lotes_lances_lote ON raw.lotes_lances (lote_id);

CREATE TABLE IF NOT EXISTS mart.lotes_lances (
    id            BIGSERIAL PRIMARY KEY,
    lote_id       INTEGER NOT NULL REFERENCES mart.lotes (lote_id),
    leilao_id     INTEGER NOT NULL,
    valor         NUMERIC(12, 2) NOT NULL,
    lance_em      TIMESTAMP,
    arrematante   TEXT,
    peso          NUMERIC(12, 4),
    valor_quilo   NUMERIC(12, 2),
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at  TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_mart_lotes_lances
    ON mart.lotes_lances (lote_id, valor, lance_em, arrematante)
    NULLS NOT DISTINCT;
CREATE INDEX IF NOT EXISTS idx_mart_lotes_lances_lote ON mart.lotes_lances (lote_id);
