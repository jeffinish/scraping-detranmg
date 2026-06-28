"""CLI: scrape editais e lotes, persiste no Postgres."""

from __future__ import annotations

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

from detran_scraper.client import DetranClient
from detran_scraper.models import Lote
from detran_scraper.parsers import (
    leilao_id_from_lista_url,
    lista_lotes_path,
    parse_editais,
    parse_lotes_from_pages,
)
from detran_scraper.storage import (
    create_db_engine,
    finish_scrape_run,
    persist_editais,
    persist_lotes,
    start_scrape_run,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def scrape_lotes_for_editais(
    client: DetranClient,
    editais: list,
    base_url: str,
) -> list[Lote]:
    """Baixa e parseia lotes de cada edital da lista."""
    all_lotes: list[Lote] = []
    for edital in editais:
        path = lista_lotes_path(edital.url_detalhes, base_url=base_url)
        logger.info(
            "Lotes: edital %s (%s)",
            edital.numero_edital,
            path,
        )
        pages_html = client.fetch_lotes_pages(path)
        lotes = parse_lotes_from_pages(
            pages_html,
            leilao_id=leilao_id_from_lista_url(path),
            base_url=base_url,
        )
        logger.info("  → %d lotes", len(lotes))
        all_lotes.extend(lotes)
    return all_lotes


def main(argv: list[str] | None = None) -> int:
    """Executa scrape de editais (e opcionalmente lotes) e grava nas camadas raw/mart."""
    load_dotenv()
    parser = argparse.ArgumentParser(description="Scrape DETRAN/MG → Postgres")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="URL Postgres (ou env DATABASE_URL)",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("DETRAN_BASE_URL", "https://leilao.detran.mg.gov.br"),
    )
    parser.add_argument(
        "--lotes",
        action="store_true",
        help="Também extrair lotes/veículos de cada edital",
    )
    parser.add_argument(
        "--max-editais",
        type=int,
        default=None,
        help="Limita quantidade de editais ao extrair lotes (útil para testes)",
    )
    args = parser.parse_args(argv)

    if not args.database_url:
        logger.error("DATABASE_URL não configurada")
        return 1

    engine = create_db_engine(args.database_url)
    run_id = start_scrape_run(engine)
    logger.info("run_id=%s", run_id)

    try:
        with DetranClient(base_url=args.base_url) as client:
            html = client.fetch_home()
            editais = parse_editais(html, base_url=args.base_url)

            lotes: list[Lote] = []
            if args.lotes:
                target_editais = editais
                if args.max_editais is not None:
                    target_editais = editais[: args.max_editais]
                lotes = scrape_lotes_for_editais(
                    client,
                    target_editais,
                    base_url=args.base_url,
                )

        status_changes = persist_editais(engine, editais, run_id)
        lotes_saved = persist_lotes(engine, lotes, run_id) if lotes else 0
        finish_scrape_run(engine, run_id, editais_count=len(editais))

        logger.info(
            "Concluído: %d editais, %d mudanças de status, %d lotes",
            len(editais),
            status_changes,
            lotes_saved,
        )
        return 0
    except Exception as exc:
        logger.exception("Falha no scrape")
        finish_scrape_run(
            engine,
            run_id,
            editais_count=0,
            status="failed",
            error_message=str(exc),
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
