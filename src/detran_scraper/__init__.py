"""Scraper de editais de leilão do DETRAN/MG."""

from detran_scraper.client import DetranClient
from detran_scraper.models import Edital, Lote
from detran_scraper.parsers import (
    compute_card_hash,
    lista_lotes_path,
    parse_brl,
    parse_editais,
    parse_lotes,
    parse_lotes_from_pages,
    parse_lotes_max_page,
)

__all__ = [
    "DetranClient",
    "Edital",
    "Lote",
    "compute_card_hash",
    "lista_lotes_path",
    "parse_brl",
    "parse_editais",
    "parse_lotes",
    "parse_lotes_from_pages",
    "parse_lotes_max_page",
]
