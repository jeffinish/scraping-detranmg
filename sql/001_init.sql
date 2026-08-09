-- Camadas: raw (histórico) → mart (último estado) + lotes (futuro)

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS mart;

-- Metadados de cada execução do scraper
CREATE TABLE raw.scrape_runs (
    run_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at   TIMESTAMPTZ,
    editais_count INTEGER,
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
    valor_inicial NUMERIC(12, 2),
    valor_atual   NUMERIC(12, 2),
    url_detalhes  TEXT,
    raw_hash      VARCHAR(64),
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
    valor_inicial NUMERIC(12, 2),
    valor_atual   NUMERIC(12, 2),
    url_detalhes  TEXT,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at  TIMESTAMPTZ NOT NULL,
    raw_hash      VARCHAR(64),
    last_run_id   UUID REFERENCES raw.scrape_runs (run_id)
);

CREATE INDEX idx_mart_lotes_leilao_id ON mart.lotes (leilao_id);
