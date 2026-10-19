#!/usr/bin/env python3
"""Registro histórico do gate de cutover (fechado em 2026-10-12, exit 0).

O scraper não grava mais mart.editais, mart.lotes, mart.lotes_lances nem
mart.editais_status_history. Um scrape novo deixa essas tabelas paradas, então
este script passa a mostrar DIFF de propósito. Não entra no pipeline.

Uso (só para reler o último alinhamento, antes de um scrape novo):
    python scripts/reconcile_mart.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

COUNTS_SQL = text("""
SELECT 'editais' AS entity,
    (SELECT COUNT(*)::int FROM mart.editais) AS mart_py,
    (SELECT COUNT(*)::int FROM mart_dbt.mart_editais) AS mart_dbt
UNION ALL
SELECT 'lotes',
    (SELECT COUNT(*)::int FROM mart.lotes),
    (SELECT COUNT(*)::int FROM mart_dbt.mart_lotes)
UNION ALL
SELECT 'lotes_lances',
    (SELECT COUNT(*)::int FROM mart.lotes_lances),
    (SELECT COUNT(*)::int FROM mart_dbt.mart_lotes_lances)
UNION ALL
SELECT 'status_history',
    (SELECT COUNT(*)::int FROM mart.editais_status_history),
    (SELECT COUNT(*)::int FROM mart_dbt.mart_editais_status_history)
ORDER BY entity
""")

EDITAIS_DIFF_SQL = text("""
SELECT COUNT(*)::int AS n
FROM mart.editais m
FULL OUTER JOIN mart_dbt.mart_editais d USING (leilao_id)
WHERE m.leilao_id IS NULL OR d.leilao_id IS NULL
   OR m.numero_edital IS DISTINCT FROM d.numero_edital
   OR m.status IS DISTINCT FROM d.status
   OR m.municipio IS DISTINCT FROM d.municipio
   OR m.patio IS DISTINCT FROM d.patio
   OR m.data_encerramento IS DISTINCT FROM d.data_encerramento
   OR m.url_detalhes IS DISTINCT FROM d.url_detalhes
   OR m.raw_hash IS DISTINCT FROM d.raw_hash
   OR m.last_run_id IS DISTINCT FROM d.last_run_id
""")

LOTES_DIFF_SQL = text("""
SELECT COUNT(*)::int AS n
FROM mart.lotes l
FULL OUTER JOIN mart_dbt.mart_lotes d USING (lote_id)
WHERE l.lote_id IS NULL OR d.lote_id IS NULL
   OR l.leilao_id IS DISTINCT FROM d.leilao_id
   OR l.numero_lote IS DISTINCT FROM d.numero_lote
   OR l.condicao IS DISTINCT FROM d.condicao
   OR l.marca_modelo IS DISTINCT FROM d.marca_modelo
   OR l.valor_inicial IS DISTINCT FROM d.valor_inicial
   OR l.valor_atual IS DISTINCT FROM d.valor_atual
   OR l.cor IS DISTINCT FROM d.cor
   OR l.ano_modelo IS DISTINCT FROM d.ano_modelo
   OR l.ano_fabricacao IS DISTINCT FROM d.ano_fabricacao
   OR l.combustivel IS DISTINCT FROM d.combustivel
   OR l.valor_incremento IS DISTINCT FROM d.valor_incremento
   OR l.status_lote IS DISTINCT FROM d.status_lote
   OR l.last_run_id IS DISTINCT FROM d.last_run_id
""")


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL não definida.", file=sys.stderr)
        return 2

    engine = create_engine(url, pool_pre_ping=True)
    ok = True

    with engine.connect() as conn:
        print("=== Contagens mart vs mart_dbt ===")
        for row in conn.execute(COUNTS_SQL):
            entity, py_n, dbt_n = row
            match = "OK" if py_n == dbt_n else "DIFF"
            if py_n != dbt_n:
                ok = False
            print(f"  {entity:16} mart={py_n:6}  mart_dbt={dbt_n:6}  [{match}]")

        editais_diff = conn.execute(EDITAIS_DIFF_SQL).scalar_one()
        lotes_diff = conn.execute(LOTES_DIFF_SQL).scalar_one()
        print(f"\n=== Divergências de colunas (PK presente em ambos) ===")
        print(f"  editais: {editais_diff}")
        print(f"  lotes:   {lotes_diff}")
        if editais_diff or lotes_diff:
            ok = False

    if ok:
        print("\nTabelas analíticas Python e mart_dbt ainda coincidem (snapshot congelado).")
        return 0
    print("\nDivergência esperada depois de um scrape novo: o mart Python analítico não é mais escrito.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
