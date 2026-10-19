"""Guards: 003 is additive; never DROP/TRUNCATE existing data."""

from pathlib import Path

from detran_scraper.storage import _sql_statements

ROOT = Path(__file__).resolve().parents[1]
SQL_003 = ROOT / "sql" / "003_lotes_lances.sql"
SQL_005 = ROOT / "sql" / "005_scrape_runs_max_editais.sql"

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


def test_storage_does_not_write_analytical_mart():
    src = (ROOT / "src" / "detran_scraper" / "storage.py").read_text(encoding="utf-8").lower()
    for needle in (
        "into mart.editais",
        "update mart.editais",
        "into mart.lotes ",
        "update mart.lotes ",
        "into mart.lotes_lances",
        "update mart.lotes_lances",
        "mart.editais_status_history",
    ):
        assert needle not in src


def test_005_is_additive_only():
    sql = SQL_005.read_text(encoding="utf-8")
    for stmt in _sql_statements(sql):
        lowered = stmt.lower().lstrip()
        for needle in FORBIDDEN_PREFIXES:
            assert not lowered.startswith(needle), f"forbidden statement: {stmt}"
            assert f" {needle}" not in f" {lowered}"
    assert "add column if not exists" in sql.lower()
    assert "max_editais" in sql.lower()


def test_006_is_additive_only():
    sql = (ROOT / "sql" / "006_lotes_imagens.sql").read_text(encoding="utf-8")
    for stmt in _sql_statements(sql):
        lowered = stmt.lower().lstrip()
        for needle in FORBIDDEN_PREFIXES:
            assert not lowered.startswith(needle), f"forbidden statement: {stmt}"
            assert f" {needle}" not in f" {lowered}"
    assert "create table if not exists raw.lotes_imagens" in sql.lower()
    assert "create table if not exists mart.lotes_imagens_labels" in sql.lower()
