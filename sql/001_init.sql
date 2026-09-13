-- Camadas: raw (histórico) → mart (último estado) + lotes (futuro)

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS mart;

-- Metadados de cada execução do scraper
CREATE TABLE raw.scrape_runs (
    run_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at   TIMESTAMPTZ,
    editais_count INTEGER,
    max_editais   INTEGER,
    status        VARCHAR(20) NOT NULL DEFAULT 'running',
    error_message TEXT,
    CONSTRAINT scrape_runs_status_check
        CHECK (status IN ('running', 'success', 'failed'))
);

-- Raw: snapshot de cada edital a cada execução (append-only)
CREATE TABLE raw.editais (
    id                BIGSERIAL PRIMARY KEY,
    run_id            UUID NOT NULL REFERENCES raw.scrape_runs (run_id),
    scraped_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    leilao_id         INTEGER NOT NULL,
    numero_edital     VARCHAR(20) NOT NULL,
    municipio         VARCHAR(100),
    patio             TEXT,
    status            VARCHAR(20) NOT NULL,
    data_encerramento TIMESTAMPTZ,
    url_detalhes      TEXT,
    raw_hash          VARCHAR(64)
);

CREATE INDEX idx_raw_editais_run_id ON raw.editais (run_id);
CREATE INDEX idx_raw_editais_leilao_id ON raw.editais (leilao_id);
CREATE INDEX idx_raw_editais_scraped_at ON raw.editais (scraped_at);

-- Mart: último estado conhecido de cada leilão
CREATE TABLE mart.editais (
    leilao_id         INTEGER PRIMARY KEY,
    numero_edital     VARCHAR(20) NOT NULL,
    municipio         VARCHAR(100),
    patio             TEXT,
    status            VARCHAR(20) NOT NULL,
    data_encerramento TIMESTAMPTZ,
    url_detalhes      TEXT,
    first_seen_at     TIMESTAMPTZ NOT NULL,
    last_seen_at      TIMESTAMPTZ NOT NULL,
    status_changed_at TIMESTAMPTZ NOT NULL,
    raw_hash          VARCHAR(64),
    last_run_id       UUID REFERENCES raw.scrape_runs (run_id)
);

CREATE INDEX idx_mart_editais_status ON mart.editais (status);
CREATE INDEX idx_mart_editais_encerramento ON mart.editais (data_encerramento);

-- Histórico de mudança de status (ex.: Publicado → Finalizado)
CREATE TABLE mart.editais_status_history (
    id         BIGSERIAL PRIMARY KEY,
    leilao_id  INTEGER NOT NULL REFERENCES mart.editais (leilao_id),
    run_id     UUID NOT NULL REFERENCES raw.scrape_runs (run_id),
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_editais_status_history_leilao
    ON mart.editais_status_history (leilao_id, changed_at);

-- Raw: lotes/itens por edital (snapshot por run)
CREATE TABLE raw.lotes (
    id            BIGSERIAL PRIMARY KEY,
    run_id        UUID NOT NULL REFERENCES raw.scrape_runs (run_id),
    scraped_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    leilao_id     INTEGER NOT NULL,
    lote_id       INTEGER NOT NULL,
    numero_lote   VARCHAR(20),
    condicao      VARCHAR(20),
    marca_modelo  TEXT,
    valor_inicial    NUMERIC(12, 2),
    valor_atual      NUMERIC(12, 2),
    url_detalhes     TEXT,
    raw_hash         VARCHAR(64),
    cor              VARCHAR(50),
    ano_modelo       INTEGER,
    ano_fabricacao   INTEGER,
    combustivel      VARCHAR(50),
    valor_incremento NUMERIC(12, 2),
    status_lote      VARCHAR(8),
    UNIQUE (run_id, lote_id)
);

CREATE INDEX idx_raw_lotes_leilao_id ON raw.lotes (leilao_id);
CREATE INDEX idx_raw_lotes_run_id ON raw.lotes (run_id);

-- Mart: último estado de cada lote
CREATE TABLE mart.lotes (
    lote_id       INTEGER PRIMARY KEY,
    leilao_id     INTEGER NOT NULL REFERENCES mart.editais (leilao_id),
    numero_lote   VARCHAR(20),
    condicao      VARCHAR(20),
    marca_modelo  TEXT,
    valor_inicial    NUMERIC(12, 2),
    valor_atual      NUMERIC(12, 2),
    url_detalhes     TEXT,
    first_seen_at    TIMESTAMPTZ NOT NULL,
    last_seen_at     TIMESTAMPTZ NOT NULL,
    raw_hash         VARCHAR(64),
    last_run_id      UUID REFERENCES raw.scrape_runs (run_id),
    cor              VARCHAR(50),
    ano_modelo       INTEGER,
    ano_fabricacao   INTEGER,
    combustivel      VARCHAR(50),
    valor_incremento NUMERIC(12, 2),
    status_lote      VARCHAR(8)
);

CREATE INDEX idx_mart_lotes_leilao_id ON mart.lotes (leilao_id);

-- Raw: lances observados por run (append-only)
CREATE TABLE raw.lotes_lances (
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

CREATE INDEX idx_raw_lotes_lances_run ON raw.lotes_lances (run_id);
CREATE INDEX idx_raw_lotes_lances_lote ON raw.lotes_lances (lote_id);

-- Mart: lances únicos acumulados (não apaga se o portal sumir com o histórico)
CREATE TABLE mart.lotes_lances (
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

CREATE UNIQUE INDEX uq_mart_lotes_lances
    ON mart.lotes_lances (lote_id, valor, lance_em, arrematante)
    NULLS NOT DISTINCT;
CREATE INDEX idx_mart_lotes_lances_lote ON mart.lotes_lances (lote_id);

-- Imagens: blobs em data/imagens/; rótulo humano por sha256 (ver sql/006).
CREATE TABLE raw.lotes_imagens (
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

CREATE INDEX idx_raw_lotes_imagens_lote ON raw.lotes_imagens (lote_id, slot);
CREATE INDEX idx_raw_lotes_imagens_sha ON raw.lotes_imagens (sha256);

CREATE TABLE mart.lotes_imagens (
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

CREATE INDEX idx_mart_lotes_imagens_sha ON mart.lotes_imagens (sha256);
CREATE INDEX idx_mart_lotes_imagens_naive ON mart.lotes_imagens (naive_valida);

CREATE TABLE mart.lotes_imagens_labels (
    sha256     CHAR(64) PRIMARY KEY,
    valida     BOOLEAN NOT NULL,
    motivo     VARCHAR(40),
    labeled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes      TEXT
);
