"""CLI: scrape editais e lotes, persiste no Postgres."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

from detran_scraper.client import DetranClient, normalize_cookie
from detran_scraper.models import Lance, Lote
from detran_scraper.parsers import (
    apply_lote_enriquecimento,
    leilao_id_from_lista_url,
    lista_lotes_path,
    parse_editais,
    parse_lote_detalhe,
    parse_lotes_from_pages,
    parse_pre_arrematante_id,
    parse_update_countdown,
    parse_update_single,
)
from detran_scraper.storage import (
    apply_lances_schema,
    create_db_engine,
    finish_scrape_run,
    persist_editais,
    persist_lances,
    persist_lotes,
    start_scrape_run,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

LOTE_DETAIL_PAUSE_S = 0.25


def scrape_lotes_for_editais(
    client: DetranClient,
    editais: list,
    base_url: str,
) -> tuple[list[Lote], dict[int, str]]:
    """Baixa e parseia lotes de cada edital da lista.

    Returns:
        Lotes e o HTML da primeira página de listagem por leilao_id.
    """
    all_lotes: list[Lote] = []
    first_pages: dict[int, str] = {}
    for edital in editais:
        path = lista_lotes_path(edital.url_detalhes, base_url=base_url)
        logger.info(
            "Lotes: edital %s (%s)",
            edital.numero_edital,
            path,
        )
        pages_html = client.fetch_lotes_pages(path)
        leilao_id = leilao_id_from_lista_url(path)
        if pages_html:
            first_pages[leilao_id] = pages_html[0]
        lotes = parse_lotes_from_pages(
            pages_html,
            leilao_id=leilao_id,
            base_url=base_url,
        )
        logger.info("  → %d lotes", len(lotes))
        all_lotes.extend(lotes)
    return all_lotes, first_pages


def enrich_lotes_em_andamento(
    client: DetranClient,
    editais: list,
    lotes: list[Lote],
    first_pages: dict[int, str],
) -> tuple[list[Lote], list[Lance]]:
    """JSON de lances + HTML de detalhe só para editais Em Andamento."""
    em_andamento_ids = {e.leilao_id for e in editais if e.status == "Em Andamento"}
    if not em_andamento_ids:
        logger.info("Lances: nenhum edital Em Andamento")
        return lotes, []

    by_leilao: dict[int, list[Lote]] = {}
    for lote in lotes:
        by_leilao.setdefault(lote.leilao_id, []).append(lote)

    enriched: dict[int, Lote] = {lote.lote_id: lote for lote in lotes}
    lances: list[Lance] = []
    n_json_ok = 0
    n_detalhe_ok = 0
    n_skip = 0

    for leilao_id in sorted(em_andamento_ids):
        grupo = by_leilao.get(leilao_id, [])
        if not grupo:
            continue
        user_id = parse_pre_arrematante_id(first_pages.get(leilao_id, ""))
        if not user_id:
            logger.warning("Lances: sem pré-arrematante no edital %s (cookie?)", leilao_id)
            n_skip += len(grupo)
            continue

        lote_ids = [lote.lote_id for lote in grupo]
        try:
            countdown = parse_update_countdown(
                client.fetch_update_countdown(user_id, lote_ids)
            )
        except Exception as exc:
            logger.warning("Lances: countdown falhou edital %s: %s", leilao_id, exc)
            countdown = {}

        for lote in grupo:
            estado = countdown.get(lote.lote_id)
            detalhe = None
            try:
                payload = client.fetch_update_single(user_id, lote.lote_id)
                estado_single, lote_lances = parse_update_single(
                    payload,
                    lote_id=lote.lote_id,
                    leilao_id=leilao_id,
                )
                if estado_single:
                    estado = estado_single
                    n_json_ok += 1
                lances.extend(lote_lances)
            except Exception as exc:
                logger.warning("Lances: single falhou lote %s: %s", lote.lote_id, exc)
                n_skip += 1

            try:
                detalhe = parse_lote_detalhe(client.fetch_lote_detalhe(lote.lote_id))
                n_detalhe_ok += 1
            except Exception as exc:
                logger.warning("Detalhe: falhou lote %s: %s", lote.lote_id, exc)

            enriched[lote.lote_id] = apply_lote_enriquecimento(
                lote, estado=estado, detalhe=detalhe
            )
            time.sleep(LOTE_DETAIL_PAUSE_S)

    unique_lances = _dedupe_lances(lances)
    logger.info(
        "Lances: json_ok=%d detalhe_ok=%d skip=%d lances=%d (unicos=%d)",
        n_json_ok,
        n_detalhe_ok,
        n_skip,
        len(lances),
        len(unique_lances),
    )
    return list(enriched.values()), unique_lances


def _dedupe_lances(lances: list[Lance]) -> list[Lance]:
    seen: set[tuple] = set()
    out: list[Lance] = []
    for lance in lances:
        key = (lance.lote_id, lance.valor, lance.lance_em, lance.arrematante)
        if key in seen:
            continue
        seen.add(key)
        out.append(lance)
    return out


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
        "--lances",
        action="store_true",
        help="Zona logada: histórico de lances + detalhe (implica --lotes)",
    )
    parser.add_argument(
        "--max-editais",
        type=int,
        default=None,
        help="Limita quantidade de editais ao extrair lotes (útil para testes)",
    )
    args = parser.parse_args(argv)

    if args.lances:
        args.lotes = True

    if not args.database_url:
        logger.error("DATABASE_URL não configurada")
        return 1

    cookie = normalize_cookie(os.getenv("DETRAN_COOKIE"))
    if args.lances and not cookie:
        logger.error("DETRAN_COOKIE obrigatório para --lances (cole o header Cookie no .env)")
        return 1

    engine = create_db_engine(args.database_url)
    apply_lances_schema(engine)
    run_id = start_scrape_run(engine)
    logger.info("run_id=%s", run_id)

    try:
        with DetranClient(base_url=args.base_url, cookie=cookie) as client:
            html = client.fetch_home()
            editais = parse_editais(html, base_url=args.base_url)

            lotes: list[Lote] = []
            lances: list[Lance] = []
            if args.lotes:
                target_editais = editais
                if args.max_editais is not None:
                    target_editais = editais[: args.max_editais]
                lotes, first_pages = scrape_lotes_for_editais(
                    client,
                    target_editais,
                    base_url=args.base_url,
                )
                if args.lances:
                    lotes, lances = enrich_lotes_em_andamento(
                        client,
                        target_editais,
                        lotes,
                        first_pages,
                    )

        status_changes = persist_editais(engine, editais, run_id)
        lotes_saved = persist_lotes(engine, lotes, run_id) if lotes else 0
        lances_saved = persist_lances(engine, lances, run_id) if lances else 0
        finish_scrape_run(engine, run_id, editais_count=len(editais))

        logger.info(
            "Concluído: %d editais, %d mudanças de status, %d lotes, %d lances novos",
            len(editais),
            status_changes,
            lotes_saved,
            lances_saved,
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
