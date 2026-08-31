"""Leitura do mart dbt e persistência da flag de interesse.

Leitura analítica: mart_dbt.mart_lotes / mart_editais (dbt).
Estado da UI: mart.lotes_interesse (FK → mart_dbt.mart_lotes).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

from detran_scraper.client import DEFAULT_BASE_URL

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_SQL = REPO_ROOT / "sql" / "004_lotes_interesse.sql"

# ponytail: listing thumbnail is always img_{lote_id}_1.jpg.
_IMAGEM_PATH = "/Imagens/visualizar/leiloes/leilao_{leilao_id}/img_{lote_id}_1.jpg"


def mart_schema() -> str:
    """Schema analítico lido pela UI (default: mart_dbt).

    Filtros de marca/modelo/ano_veiculo exigem colunas do dbt.
    MART_SCHEMA=mart (hatch do dual-run Python) não tem essas colunas.
    """
    schema = os.getenv("MART_SCHEMA", "mart_dbt")
    if schema not in {"mart_dbt", "mart"}:
        raise ValueError(f"MART_SCHEMA inválido: {schema!r}")
    return schema


def _tbl_lotes() -> str:
    s = mart_schema()
    return f"{s}.mart_lotes" if s == "mart_dbt" else f"{s}.lotes"


def _tbl_editais() -> str:
    s = mart_schema()
    return f"{s}.mart_editais" if s == "mart_dbt" else f"{s}.editais"


@dataclass
class LoteFiltros:
    marcas: list[str] = field(default_factory=list)
    modelo_contem: str = ""
    municipios: list[str] = field(default_factory=list)
    condicoes: list[str] = field(default_factory=list)
    status_edital: list[str] = field(default_factory=list)
    valor_min: float | None = None
    valor_max: float | None = None
    ano_min: int | None = None
    ano_max: int | None = None
    somente_interesse: bool = False


def _sql_statements(sql: str) -> list[str]:
    """Parte o arquivo em statements, ignorando linhas `--` (podem ter `;`)."""
    code_lines = [
        line
        for line in sql.splitlines()
        if line.strip() and not line.strip().startswith("--")
    ]
    return [stmt.strip() for stmt in "\n".join(code_lines).split(";") if stmt.strip()]


def apply_schema(engine: Engine) -> None:
    """Cria mart.lotes_interesse e FK para mart_dbt.mart_lotes."""
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    with engine.begin() as conn:
        for stmt in _sql_statements(sql):
            conn.execute(text(stmt))


def url_imagem(leilao_id: int, lote_id: int, base_url: str = DEFAULT_BASE_URL) -> str:
    """Monta a URL do thumbnail da listagem (sem persistir)."""
    path = _IMAGEM_PATH.format(leilao_id=leilao_id, lote_id=lote_id)
    return f"{base_url.rstrip('/')}{path}"


def format_brl(value: Decimal | float | None) -> str:
    if value is None:
        return "—"
    numero = f"{float(value):,.2f}"
    return "R$ " + numero.replace(",", "X").replace(".", ",").replace("X", ".")


def list_opcoes(engine: Engine) -> dict[str, list[str]]:
    """Valores distintos para os selects (marca, município, condição, status)."""
    lotes = _tbl_lotes()
    editais = _tbl_editais()
    with engine.connect() as conn:
        marcas = conn.execute(
            text(f"""
                SELECT DISTINCT l.marca
                FROM {lotes} l
                WHERE l.marca IS NOT NULL
                ORDER BY 1
            """)
        ).scalars().all()
        municipios = conn.execute(
            text(f"""
                SELECT DISTINCT municipio
                FROM {editais}
                WHERE municipio IS NOT NULL AND TRIM(municipio) <> ''
                ORDER BY 1
            """)
        ).scalars().all()
        condicoes = conn.execute(
            text(f"""
                SELECT DISTINCT condicao
                FROM {lotes}
                WHERE condicao IS NOT NULL
                ORDER BY 1
            """)
        ).scalars().all()
        status = conn.execute(
            text(f"""
                SELECT DISTINCT status
                FROM {editais}
                WHERE status IS NOT NULL
                ORDER BY 1
            """)
        ).scalars().all()
    return {
        "marcas": [str(v) for v in marcas],
        "municipios": [str(v) for v in municipios],
        "condicoes": [str(v) for v in condicoes],
        "status_edital": [str(v) for v in status],
    }


def count_interesse(engine: Engine) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(text("SELECT COUNT(*) FROM mart.lotes_interesse")).scalar_one()
        )


def get_leilao_id(engine: Engine, lote_id: int) -> int | None:
    lotes = _tbl_lotes()
    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT leilao_id FROM {lotes} WHERE lote_id = :lote_id"),
            {"lote_id": lote_id},
        ).fetchone()
    return int(row[0]) if row else None


def set_interesse(engine: Engine, lote_id: int, flagged: bool) -> None:
    with engine.begin() as conn:
        if flagged:
            conn.execute(
                text("""
                    INSERT INTO mart.lotes_interesse (lote_id)
                    VALUES (:lote_id)
                    ON CONFLICT (lote_id) DO NOTHING
                """),
                {"lote_id": lote_id},
            )
        else:
            conn.execute(
                text("DELETE FROM mart.lotes_interesse WHERE lote_id = :lote_id"),
                {"lote_id": lote_id},
            )


def list_lotes(
    engine: Engine,
    filtros: LoteFiltros,
    *,
    page: int = 1,
    page_size: int = 24,
) -> tuple[list[dict], int]:
    """Retorna (linhas da página, total filtrado)."""
    lotes = _tbl_lotes()
    editais = _tbl_editais()
    where, params = _where(filtros)
    params["limit"] = page_size
    params["offset"] = max(page - 1, 0) * page_size

    sql = f"""
        SELECT
            l.lote_id,
            l.leilao_id,
            l.numero_lote,
            l.condicao,
            l.marca_modelo,
            l.valor_atual,
            l.url_detalhes,
            l.first_seen_at,
            l.last_seen_at,
            e.numero_edital,
            e.municipio,
            e.patio,
            e.status AS status_edital,
            e.data_encerramento,
            l.marca,
            l.modelo,
            l.ano_veiculo,
            (i.lote_id IS NOT NULL) AS interesse,
            COUNT(*) OVER() AS total_count
        FROM {lotes} l
        JOIN {editais} e ON e.leilao_id = l.leilao_id
        LEFT JOIN mart.lotes_interesse i ON i.lote_id = l.lote_id
        WHERE {where}
        ORDER BY l.valor_atual ASC NULLS LAST, e.data_encerramento ASC NULLS LAST
        LIMIT :limit OFFSET :offset
    """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    if not rows:
        return [], 0

    total = int(rows[0]["total_count"])
    lotes_out = []
    for row in rows:
        item = dict(row)
        item.pop("total_count", None)
        item["url_imagem"] = url_imagem(item["leilao_id"], item["lote_id"])
        item["valor_fmt"] = format_brl(item.get("valor_atual"))
        lotes_out.append(item)
    return lotes_out, total


def _in_clause(column: str, values: list[str], prefix: str, params: dict) -> str:
    placeholders = []
    for i, value in enumerate(values):
        key = f"{prefix}_{i}"
        params[key] = value
        placeholders.append(f":{key}")
    return f"{column} IN ({', '.join(placeholders)})"


def _where(filtros: LoteFiltros) -> tuple[str, dict]:
    clauses = ["TRUE"]
    params: dict = {}

    marcas = [m.strip().upper() for m in filtros.marcas if m and str(m).strip()]
    if marcas:
        clauses.append(_in_clause("l.marca", marcas, "marca", params))

    modelo = filtros.modelo_contem.strip()
    if modelo:
        params["modelo"] = f"%{modelo}%"
        clauses.append("l.modelo ILIKE :modelo")

    municipios = [m.strip() for m in filtros.municipios if m and str(m).strip()]
    if municipios:
        clauses.append(_in_clause("e.municipio", municipios, "mun", params))

    condicoes = [c.strip().upper() for c in filtros.condicoes if c and str(c).strip()]
    if condicoes:
        clauses.append(
            _in_clause("UPPER(l.condicao)", condicoes, "cond", params)
        )

    status = [s.strip() for s in filtros.status_edital if s and str(s).strip()]
    if status:
        clauses.append(_in_clause("e.status", status, "st", params))

    if filtros.valor_min is not None:
        params["valor_min"] = filtros.valor_min
        clauses.append("l.valor_atual >= :valor_min")

    if filtros.valor_max is not None:
        params["valor_max"] = filtros.valor_max
        clauses.append("l.valor_atual <= :valor_max")

    if filtros.ano_min is not None:
        params["ano_min"] = int(filtros.ano_min)
        clauses.append("l.ano_veiculo >= :ano_min")

    if filtros.ano_max is not None:
        params["ano_max"] = int(filtros.ano_max)
        clauses.append("l.ano_veiculo <= :ano_max")

    if filtros.somente_interesse:
        clauses.append("i.lote_id IS NOT NULL")

    return " AND ".join(clauses), params
