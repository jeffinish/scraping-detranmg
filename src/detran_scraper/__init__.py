"""Cliente HTTP para o portal de leilões DETRAN/MG."""

from detran_scraper.client import DetranClient, normalize_cookie
from detran_scraper.models import Edital, Lance, Lote
from detran_scraper.parsers import (
    compute_card_hash,
    lista_lotes_path,
    parse_brl,
    parse_editais,
    parse_lote_detalhe,
    parse_lotes,
    parse_lotes_from_pages,
    parse_lotes_max_page,
    parse_update_countdown,
    parse_update_single,
)

__all__ = [
    "DetranClient",
    "Edital",
    "Lance",
    "Lote",
    "compute_card_hash",
    "lista_lotes_path",
    "normalize_cookie",
    "parse_brl",
    "parse_editais",
    "parse_lote_detalhe",
    "parse_lotes",
    "parse_lotes_from_pages",
    "parse_lotes_max_page",
    "parse_update_countdown",
    "parse_update_single",
]
