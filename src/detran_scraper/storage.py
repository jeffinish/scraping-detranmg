"""Persistência em Postgres (camadas raw e mart)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from detran_scraper.models import Edital, Lance, Lote, LoteImagem

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
        marca_modelo, valor_inicial, valor_atual, url_detalhes, raw_hash,
        cor, ano_modelo, ano_fabricacao, combustivel,
        valor_incremento, status_lote
    ) VALUES (
        :run_id, :scraped_at, :leilao_id, :lote_id, :numero_lote, :condicao,
        :marca_modelo, :valor_inicial, :valor_atual, :url_detalhes, :raw_hash,
        :cor, :ano_modelo, :ano_fabricacao, :combustivel,
        :valor_incremento, :status_lote
    )
""")

SELECT_MART_LOTE = text("""
    SELECT 1 FROM mart.lotes WHERE lote_id = :lote_id
""")

INSERT_MART_LOTE = text("""
    INSERT INTO mart.lotes (
        lote_id, leilao_id, numero_lote, condicao, marca_modelo,
        valor_inicial, valor_atual, url_detalhes,
        first_seen_at, last_seen_at, raw_hash, last_run_id,
        cor, ano_modelo, ano_fabricacao, combustivel,
        valor_incremento, status_lote
    ) VALUES (
        :lote_id, :leilao_id, :numero_lote, :condicao, :marca_modelo,
        :valor_inicial, :valor_atual, :url_detalhes,
        :seen_at, :seen_at, :raw_hash, :run_id,
        :cor, :ano_modelo, :ano_fabricacao, :combustivel,
        :valor_incremento, :status_lote
    )
""")

UPDATE_MART_LOTE = text("""
    UPDATE mart.lotes SET
        leilao_id        = :leilao_id,
        numero_lote      = :numero_lote,
        condicao         = :condicao,
        marca_modelo     = :marca_modelo,
        valor_atual      = :valor_atual,
        url_detalhes     = :url_detalhes,
        last_seen_at     = :seen_at,
        raw_hash         = :raw_hash,
        last_run_id      = :run_id,
        valor_inicial    = COALESCE(:valor_inicial, valor_inicial),
        cor              = COALESCE(:cor, cor),
        ano_modelo       = COALESCE(:ano_modelo, ano_modelo),
        ano_fabricacao   = COALESCE(:ano_fabricacao, ano_fabricacao),
        combustivel      = COALESCE(:combustivel, combustivel),
        valor_incremento = COALESCE(:valor_incremento, valor_incremento),
        status_lote      = COALESCE(:status_lote, status_lote)
    WHERE lote_id = :lote_id
""")

INSERT_RAW_LANCE = text("""
    INSERT INTO raw.lotes_lances (
        run_id, scraped_at, lote_id, leilao_id, valor, lance_em,
        arrematante, peso, valor_quilo
    ) VALUES (
        :run_id, :scraped_at, :lote_id, :leilao_id, :valor, :lance_em,
        :arrematante, :peso, :valor_quilo
    )
""")

SELECT_MART_LANCE = text("""
    SELECT id FROM mart.lotes_lances
    WHERE lote_id = :lote_id
      AND valor IS NOT DISTINCT FROM :valor
      AND lance_em IS NOT DISTINCT FROM :lance_em
      AND arrematante IS NOT DISTINCT FROM :arrematante
""")

INSERT_MART_LANCE = text("""
    INSERT INTO mart.lotes_lances (
        lote_id, leilao_id, valor, lance_em, arrematante, peso, valor_quilo,
        first_seen_at, last_seen_at
    ) VALUES (
        :lote_id, :leilao_id, :valor, :lance_em, :arrematante, :peso, :valor_quilo,
        :seen_at, :seen_at
    )
""")

UPDATE_MART_LANCE = text("""
    UPDATE mart.lotes_lances SET
        last_seen_at = :seen_at,
        peso = COALESCE(:peso, peso),
        valor_quilo = COALESCE(:valor_quilo, valor_quilo)
    WHERE id = :id
""")

_SQL_DIR = Path(__file__).resolve().parents[2] / "sql"
SCHEMA_LANCES_SQL = _SQL_DIR / "003_lotes_lances.sql"
SCHEMA_RUNS_SQL = _SQL_DIR / "005_scrape_runs_max_editais.sql"
SCHEMA_IMAGENS_SQL = _SQL_DIR / "006_lotes_imagens.sql"


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
    max_editais: int | None = None,
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
                    max_editais = :max_editais,
                    status = :status,
                    error_message = :error_message
                WHERE run_id = :run_id
            """),
            {
                "run_id": run_id,
                "editais_count": editais_count,
                "max_editais": max_editais,
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


def _sql_statements(sql: str) -> list[str]:
    """Parte o arquivo em statements, ignorando linhas `--`."""
    code_lines = [
        line
        for line in sql.splitlines()
        if line.strip() and not line.strip().startswith("--")
    ]
    return [stmt.strip() for stmt in "\n".join(code_lines).split(";") if stmt.strip()]


def apply_lances_schema(engine: Engine) -> None:
    """Aplica sql/003, sql/005 e sql/006 (aditivos). Seguro em banco já populado."""
    with engine.begin() as conn:
        for path in (SCHEMA_LANCES_SQL, SCHEMA_RUNS_SQL, SCHEMA_IMAGENS_SQL):
            sql = path.read_text(encoding="utf-8")
            for stmt in _sql_statements(sql):
                conn.execute(text(stmt))


def persist_lances(
    engine: Engine,
    lances: list[Lance],
    run_id: uuid.UUID,
) -> int:
    """Append raw + upsert mart. Não apaga lances já gravados.

    Returns:
        Quantidade de lances novos inseridos no mart.
    """
    if not lances:
        return 0

    seen_at = datetime.now(UTC)
    inserted = 0
    with engine.begin() as conn:
        for lance in lances:
            params = _lance_params(lance, run_id, seen_at)
            conn.execute(INSERT_RAW_LANCE, params)
            existing = conn.execute(SELECT_MART_LOTE, {"lote_id": lance.lote_id}).fetchone()
            if existing is None:
                continue
            row = conn.execute(SELECT_MART_LANCE, params).fetchone()
            if row is None:
                conn.execute(INSERT_MART_LANCE, params)
                inserted += 1
            else:
                conn.execute(UPDATE_MART_LANCE, {**params, "id": row[0]})
    return inserted


SELECT_LATEST_FULL_RUN = text("""
    SELECT s.run_id
    FROM raw.scrape_runs AS s
    WHERE s.status = 'success'
        AND s.max_editais IS NULL
        AND EXISTS (
            SELECT 1 FROM raw.lotes AS l WHERE l.run_id = s.run_id
        )
    ORDER BY s.finished_at DESC NULLS LAST, s.started_at DESC
    LIMIT 1
""")

SELECT_CONSERVADOS_PENDENTES = text("""
    SELECT DISTINCT l.lote_id, l.leilao_id
    FROM raw.lotes AS l
    WHERE l.run_id = :run_id
        AND UPPER(l.condicao) = 'CONSERVADO'
        AND NOT EXISTS (
            SELECT 1 FROM mart.lotes_imagens AS i WHERE i.lote_id = l.lote_id
        )
    ORDER BY l.lote_id
    LIMIT :limite
""")

INSERT_RAW_IMAGEM = text("""
    INSERT INTO raw.lotes_imagens (
        run_id, scraped_at, lote_id, leilao_id, slot, sha256, byte_size,
        source_url, relpath, naive_valida, naive_motivo, is_placeholder
    ) VALUES (
        :run_id, :seen_at, :lote_id, :leilao_id, :slot, :sha256, :byte_size,
        :source_url, :relpath, :naive_valida, :naive_motivo, :is_placeholder
    )
    ON CONFLICT (run_id, lote_id, slot) DO NOTHING
""")

UPSERT_MART_IMAGEM = text("""
    INSERT INTO mart.lotes_imagens (
        lote_id, slot, leilao_id, sha256, byte_size, relpath,
        naive_valida, naive_motivo, is_placeholder,
        first_seen_at, last_seen_at, last_run_id
    ) VALUES (
        :lote_id, :slot, :leilao_id, :sha256, :byte_size, :relpath,
        :naive_valida, :naive_motivo, :is_placeholder,
        :seen_at, :seen_at, :run_id
    )
    ON CONFLICT (lote_id, slot) DO UPDATE SET
        leilao_id = EXCLUDED.leilao_id,
        sha256 = EXCLUDED.sha256,
        byte_size = EXCLUDED.byte_size,
        relpath = EXCLUDED.relpath,
        naive_valida = EXCLUDED.naive_valida,
        naive_motivo = EXCLUDED.naive_motivo,
        is_placeholder = EXCLUDED.is_placeholder,
        last_seen_at = EXCLUDED.last_seen_at,
        last_run_id = EXCLUDED.last_run_id
""")

UPSERT_IMAGEM_LABEL = text("""
    INSERT INTO mart.lotes_imagens_labels (sha256, valida, motivo, notes, labeled_at)
    VALUES (:sha256, :valida, :motivo, :notes, NOW())
    ON CONFLICT (sha256) DO UPDATE SET
        valida = EXCLUDED.valida,
        motivo = EXCLUDED.motivo,
        notes = EXCLUDED.notes,
        labeled_at = NOW()
""")


def latest_full_lotes_run_id(engine: Engine) -> uuid.UUID | None:
    """Último scrape completo de lotes (mesmo critério do dbt tombstone)."""
    with engine.connect() as conn:
        row = conn.execute(SELECT_LATEST_FULL_RUN).fetchone()
    return row[0] if row else None


def list_conservados_pendentes(
    engine: Engine,
    run_id: uuid.UUID,
    *,
    limit: int | None = None,
) -> list[tuple[int, int]]:
    """CONSERVADO do run ainda sem nenhuma foto no mart. (lote_id, leilao_id)."""
    limite = limit if limit is not None else 1_000_000
    with engine.connect() as conn:
        rows = conn.execute(
            SELECT_CONSERVADOS_PENDENTES,
            {"run_id": run_id, "limite": limite},
        ).fetchall()
    return [(int(row[0]), int(row[1])) for row in rows]


def persist_lotes_imagens(
    engine: Engine,
    imagens: list[LoteImagem],
    run_id: uuid.UUID,
) -> int:
    """Append raw + upsert mart por (lote_id, slot)."""
    if not imagens:
        return 0
    seen_at = datetime.now(UTC)
    with engine.begin() as conn:
        for img in imagens:
            params = {
                "run_id": run_id,
                "seen_at": seen_at,
                "lote_id": img.lote_id,
                "leilao_id": img.leilao_id,
                "slot": img.slot,
                "sha256": img.sha256,
                "byte_size": img.byte_size,
                "source_url": img.source_url,
                "relpath": img.relpath,
                "naive_valida": img.naive_valida,
                "naive_motivo": img.naive_motivo,
                "is_placeholder": img.is_placeholder,
            }
            conn.execute(INSERT_RAW_IMAGEM, params)
            conn.execute(UPSERT_MART_IMAGEM, params)
    return len(imagens)


def persist_imagem_labels(
    engine: Engine,
    rows: list[tuple[str, bool, str | None, str | None]],
) -> int:
    """Upsert rótulos humanos (sha256, valida, motivo, notes)."""
    if not rows:
        return 0
    with engine.begin() as conn:
        for digest, valida, motivo, notes in rows:
            conn.execute(
                UPSERT_IMAGEM_LABEL,
                {
                    "sha256": digest,
                    "valida": valida,
                    "motivo": motivo,
                    "notes": notes,
                },
            )
    return len(rows)


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
        "cor": lote.cor,
        "ano_modelo": lote.ano_modelo,
        "ano_fabricacao": lote.ano_fabricacao,
        "combustivel": lote.combustivel,
        "valor_incremento": lote.valor_incremento,
        "status_lote": lote.status_lote,
    }


def _lance_params(
    lance: Lance,
    run_id: uuid.UUID,
    seen_at: datetime,
) -> dict:
    """Parâmetros para INSERT/UPDATE de lance."""
    return {
        "run_id": run_id,
        "scraped_at": seen_at,
        "seen_at": seen_at,
        "lote_id": lance.lote_id,
        "leilao_id": lance.leilao_id,
        "valor": lance.valor,
        "lance_em": lance.lance_em,
        "arrematante": lance.arrematante,
        "peso": lance.peso,
        "valor_quilo": lance.valor_quilo,
    }
