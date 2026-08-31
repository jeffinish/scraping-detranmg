"""Checks da camada de query da UI (sem Postgres)."""

from detran_ui.queries import (
    SCHEMA_SQL,
    LoteFiltros,
    _sql_statements,
    _where,
    format_brl,
    url_imagem,
)


def test_url_imagem_derivada_do_padrao_da_listagem():
    url = url_imagem(3416, 312935)
    assert url.endswith("/Imagens/visualizar/leiloes/leilao_3416/img_312935_1.jpg")


def test_where_somente_interesse():
    sql, params = _where(LoteFiltros(somente_interesse=True))
    assert "i.lote_id IS NOT NULL" in sql
    assert params == {}


def test_where_marca_e_valor():
    sql, params = _where(LoteFiltros(marcas=["fiat"], valor_min=500, valor_max=10_000))
    assert params["marca_0"] == "FIAT"
    assert params["valor_min"] == 500
    assert params["valor_max"] == 10_000
    assert "l.marca" in sql
    assert "valor_atual >=" in sql


def test_where_modelo_e_ano():
    sql, params = _where(LoteFiltros(modelo_contem="gol", ano_min=2010, ano_max=2020))
    assert params["modelo"] == "%gol%"
    assert params["ano_min"] == 2010
    assert params["ano_max"] == 2020
    assert "l.modelo ILIKE" in sql
    assert "l.ano_veiculo >=" in sql
    assert "l.ano_veiculo <=" in sql


def test_format_brl():
    assert format_brl(None) == "—"
    assert format_brl(1234.5) == "R$ 1.234,50"


def test_sql_004_nao_executa_comentario_com_ponto_e_virgula():
    stmts = _sql_statements(SCHEMA_SQL.read_text(encoding="utf-8"))
    assert len(stmts) == 5
    assert stmts[0].upper().startswith("CREATE TABLE")
    assert stmts[1].upper().startswith("CREATE INDEX")
    assert "UNIQUE INDEX" in stmts[2].upper()
    assert "DROP CONSTRAINT" in stmts[3].upper()
    assert "ADD CONSTRAINT" in stmts[4].upper()


def test_mart_schema_default(monkeypatch):
    monkeypatch.delenv("MART_SCHEMA", raising=False)
    from detran_ui import queries

    assert queries.mart_schema() == "mart_dbt"
    assert queries._tbl_lotes() == "mart_dbt.mart_lotes"
    assert queries._tbl_editais() == "mart_dbt.mart_editais"
