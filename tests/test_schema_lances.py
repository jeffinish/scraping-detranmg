"""Guards: 003 is additive; never DROP/TRUNCATE existing data."""

from pathlib import Path

from detran_scraper.storage import UPDATE_MART_LOTE, _sql_statements

ROOT = Path(__file__).resolve().parents[1]
SQL_003 = ROOT / "sql" / "003_lotes_lances.sql"

FORBIDDEN_PREFIXES = (
    "drop ",
    "truncate ",
    "delete from",
)


def test_003_is_additive_only():
    sql = SQL_003.read_text(encoding="utf-8")
    for stmt in _sql_statements(sql):
        lowered = stmt.lower().lstrip()
        for needle in FORBIDDEN_PREFIXES:
            assert not lowered.startswith(needle), f"forbidden statement: {stmt}"
            assert f" {needle}" not in f" {lowered}"


def test_003_uses_if_not_exists():
    sql = SQL_003.read_text(encoding="utf-8").lower()
    assert "add column if not exists" in sql
    assert "create table if not exists raw.lotes_lances" in sql
    assert "create table if not exists mart.lotes_lances" in sql


def test_mart_lote_update_does_not_blank_enrichment():
    sql = str(UPDATE_MART_LOTE).lower()
    for col in (
        "valor_inicial",
        "cor",
        "ano_modelo",
        "ano_fabricacao",
        "combustivel",
        "valor_incremento",
        "status_lote",
    ):
        assert f"coalesce(:{col}, {col})" in sql
