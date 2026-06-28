"""Persistência em Postgres (camadas raw e mart)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from detran_scraper.models import Edital, Lote

INSERT_RAW_EDITAL = text("""
    INSERT INTO raw.editais (
        run_id, scraped_at, leilao_id, numero_edital, municipio, patio,
        status, data_encerramento, url_detalhes, raw_hash
    ) VALUES (
        :run_id, :scraped_at, :leilao_id, :numero_edital, :municipio, :patio,
        :status, :data_encerramento, :url_detalhes, :raw_hash
    )
""")

SELECT_MART_STATUS = text("""
    SELECT status FROM mart.editais WHERE leilao_id = :leilao_id
""")

INSERT_MART_EDITAL = text("""
    INSERT INTO mart.editais (
        leilao_id, numero_edital, municipio, patio, status, data_encerramento,
        url_detalhes, first_seen_at, last_seen_at, status_changed_at,
        raw_hash, last_run_id
    ) VALUES (
        :leilao_id, :numero_edital, :municipio, :patio, :status, :data_encerramento,
        :url_detalhes, :seen_at, :seen_at, :seen_at,
        :raw_hash, :run_id
    )
""")

UPDATE_MART_EDITAL = text("""
    UPDATE mart.editais SET
        numero_edital     = :numero_edital,
        municipio         = :municipio,
        patio             = :patio,
        status            = :status,
        data_encerramento = :data_encerramento,
        url_detalhes      = :url_detalhes,
        last_seen_at      = :seen_at,
        status_changed_at = CASE
            WHEN status IS DISTINCT FROM :status THEN :seen_at
            ELSE status_changed_at
        END,
        raw_hash          = :raw_hash,
        last_run_id       = :run_id
    WHERE leilao_id = :leilao_id
""")

INSERT_STATUS_HISTORY = text("""
    INSERT INTO mart.editais_status_history (
        leilao_id, run_id, old_status, new_status, changed_at
    ) VALUES (
        :leilao_id, :run_id, :old_status, :new_status, :changed_at
    )
""")

INSERT_RAW_LOTE = text("""
    INSERT INTO raw.lotes (
        run_id, scraped_at, leilao_id, lote_id, numero_lote, condicao,
        marca_modelo, valor_inicial, valor_atual, url_detalhes, raw_hash
    ) VALUES (
        :run_id, :scraped_at, :leilao_id, :lote_id, :numero_lote, :condicao,
        :marca_modelo, :valor_inicial, :valor_atual, :url_detalhes, :raw_hash
    )
""")

SELECT_MART_LOTE = text("""
    SELECT 1 FROM mart.lotes WHERE lote_id = :lote_id
""")

INSERT_MART_LOTE = text("""
    INSERT INTO mart.lotes (
        lote_id, leilao_id, numero_lote, condicao, marca_modelo,
        valor_inicial, valor_atual, url_detalhes,
        first_seen_at, last_seen_at, raw_hash, last_run_id
    ) VALUES (
        :lote_id, :leilao_id, :numero_lote, :condicao, :marca_modelo,
        :valor_inicial, :valor_atual, :url_detalhes,
        :seen_at, :seen_at, :raw_hash, :run_id
    )
""")

UPDATE_MART_LOTE = text("""
    UPDATE mart.lotes SET
        leilao_id     = :leilao_id,
        numero_lote   = :numero_lote,
        condicao      = :condicao,
        marca_modelo  = :marca_modelo,
        valor_inicial = :valor_inicial,
        valor_atual   = :valor_atual,
        url_detalhes  = :url_detalhes,
        last_seen_at  = :seen_at,
        raw_hash      = :raw_hash,
        last_run_id   = :run_id
    WHERE lote_id = :lote_id
""")


def create_db_engine(database_url: str) -> Engine:
    """Cria engine SQLAlchemy para o Postgres."""
    return create_engine(database_url, pool_pre_ping=True)


def start_scrape_run(engine: Engine) -> uuid.UUID:
    """Registra início de execução e retorna run_id."""
    run_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO raw.scrape_runs (run_id, status)
                VALUES (:run_id, 'running')
            """),
            {"run_id": run_id},
        )
    return run_id


def finish_scrape_run(
    engine: Engine,
    run_id: uuid.UUID,
    *,
    editais_count: int,
    status: str = "success",
    error_message: str | None = None,
) -> None:
    """Atualiza metadados ao final da execução."""
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE raw.scrape_runs
                SET finished_at = NOW(),
                    editais_count = :editais_count,
                    status = :status,
                    error_message = :error_message
                WHERE run_id = :run_id
            """),
            {
                "run_id": run_id,
                "editais_count": editais_count,
                "status": status,
                "error_message": error_message,
            },
        )


def persist_editais(
    engine: Engine,
    editais: list[Edital],
    run_id: uuid.UUID,
) -> int:
    """Grava editais na camada raw e atualiza mart (com histórico de status).

    Returns:
        Quantidade de mudanças de status registradas.
    """
    seen_at = datetime.now(UTC)
    status_changes = 0

    with engine.begin() as conn:
        for edital in editais:
            params = _edital_params(edital, run_id, seen_at)

            conn.execute(INSERT_RAW_EDITAL, params)

            existing = conn.execute(
                SELECT_MART_STATUS, {"leilao_id": edital.leilao_id}
            ).fetchone()

            if existing is None:
                conn.execute(INSERT_MART_EDITAL, params)
            else:
                old_status = existing[0]
                conn.execute(UPDATE_MART_EDITAL, params)
                if old_status != edital.status:
                    conn.execute(
                        INSERT_STATUS_HISTORY,
                        {
                            "leilao_id": edital.leilao_id,
                            "run_id": run_id,
                            "old_status": old_status,
                            "new_status": edital.status,
                            "changed_at": seen_at,
                        },
                    )
                    status_changes += 1

    return status_changes


def persist_lotes(
    engine: Engine,
    lotes: list[Lote],
    run_id: uuid.UUID,
) -> int:
    """Grava lotes na camada raw e atualiza mart.

    Returns:
        Quantidade de lotes gravados.
    """
    if not lotes:
        return 0

    seen_at = datetime.now(UTC)

    with engine.begin() as conn:
        for lote in lotes:
            params = _lote_params(lote, run_id, seen_at)
            conn.execute(INSERT_RAW_LOTE, params)

            existing = conn.execute(
                SELECT_MART_LOTE, {"lote_id": lote.lote_id}
            ).fetchone()

            if existing is None:
                conn.execute(INSERT_MART_LOTE, params)
            else:
                conn.execute(UPDATE_MART_LOTE, params)

    return len(lotes)


def _edital_params(
    edital: Edital,
    run_id: uuid.UUID,
    seen_at: datetime,
) -> dict:
    """Monta dict de parâmetros para INSERT/UPDATE."""
    return {
        "run_id": run_id,
        "scraped_at": seen_at,
        "seen_at": seen_at,
        "leilao_id": edital.leilao_id,
        "numero_edital": edital.numero_edital,
        "municipio": edital.municipio,
        "patio": edital.patio,
        "status": edital.status,
        "data_encerramento": edital.data_encerramento,
        "url_detalhes": edital.url_detalhes,
        "raw_hash": edital.raw_hash,
    }


def _lote_params(
    lote: Lote,
    run_id: uuid.UUID,
    seen_at: datetime,
) -> dict:
    """Monta dict de parâmetros para INSERT/UPDATE de lote."""
    return {
        "run_id": run_id,
        "scraped_at": seen_at,
        "seen_at": seen_at,
        "leilao_id": lote.leilao_id,
        "lote_id": lote.lote_id,
        "numero_lote": lote.numero_lote,
        "condicao": lote.condicao,
        "marca_modelo": lote.marca_modelo,
        "valor_inicial": lote.valor_inicial,
        "valor_atual": lote.valor_atual,
        "url_detalhes": lote.url_detalhes,
        "raw_hash": lote.raw_hash,
    }
