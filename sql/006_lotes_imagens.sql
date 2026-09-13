-- Imagens de lote (CAS no disco + metadado no Postgres). Idempotente e aditivo.
-- Blobs em data/imagens/blobs/{sha256[:2]}/{sha256}.jpg (não commitar).
-- Rótulo humano é por conteúdo (sha256), independente da heurística naive_*.

CREATE TABLE IF NOT EXISTS raw.lotes_imagens (
    id            BIGSERIAL PRIMARY KEY,
    run_id        UUID NOT NULL REFERENCES raw.scrape_runs (run_id),
    scraped_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    lote_id       INTEGER NOT NULL,
    leilao_id     INTEGER NOT NULL,
    slot          SMALLINT NOT NULL,
    sha256        CHAR(64) NOT NULL,
    byte_size     INTEGER NOT NULL,
    source_url    TEXT NOT NULL,
    relpath       TEXT,
    naive_valida  BOOLEAN NOT NULL,
    naive_motivo  VARCHAR(40) NOT NULL,
    is_placeholder BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (run_id, lote_id, slot)
);

CREATE INDEX IF NOT EXISTS idx_raw_lotes_imagens_lote
    ON raw.lotes_imagens (lote_id, slot);
CREATE INDEX IF NOT EXISTS idx_raw_lotes_imagens_sha
    ON raw.lotes_imagens (sha256);

CREATE TABLE IF NOT EXISTS mart.lotes_imagens (
    lote_id        INTEGER NOT NULL,
    slot           SMALLINT NOT NULL,
    leilao_id      INTEGER NOT NULL,
    sha256         CHAR(64) NOT NULL,
    byte_size      INTEGER NOT NULL,
    relpath        TEXT,
    naive_valida   BOOLEAN NOT NULL,
    naive_motivo   VARCHAR(40) NOT NULL,
    is_placeholder BOOLEAN NOT NULL DEFAULT FALSE,
    first_seen_at  TIMESTAMPTZ NOT NULL,
    last_seen_at   TIMESTAMPTZ NOT NULL,
    last_run_id    UUID REFERENCES raw.scrape_runs (run_id),
    PRIMARY KEY (lote_id, slot)
);

CREATE INDEX IF NOT EXISTS idx_mart_lotes_imagens_sha
    ON mart.lotes_imagens (sha256);
CREATE INDEX IF NOT EXISTS idx_mart_lotes_imagens_naive
    ON mart.lotes_imagens (naive_valida);

CREATE TABLE IF NOT EXISTS mart.lotes_imagens_labels (
    sha256     CHAR(64) PRIMARY KEY,
    valida     BOOLEAN NOT NULL,
    motivo     VARCHAR(40),
    labeled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes      TEXT
);
