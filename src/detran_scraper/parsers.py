"""Parsers HTML para editais de leilão."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from decimal import Decimal

from detran_scraper.models import Edital, Lote

DEFAULT_BASE_URL = "https://leilao.detran.mg.gov.br"

NUMERO_EDITAL_RE = re.compile(r"\d+/\d+")
PATIO_RE = re.compile(r"^\s*\d+\s*-\s*(.+)$")
ENCERRAMENTO_RE = re.compile(
    r"Encerramento:\s*(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})"
)
LOTE_URL_RE = re.compile(r"/lotes/lista-lotes/(\d+)/(\d+)")
NUMERO_LOTE_RE = re.compile(r"\d+")
BRL_RE = re.compile(r"R\$\s*([\d.]+),(\d{2})")


def parse_editais(html: str, base_url: str = DEFAULT_BASE_URL) -> list[Edital]:
    """Extrai editais dos cards da página inicial.

    Args:
        html: HTML completo da home.
        base_url: URL base para links relativos.

    Returns:
        Lista de editais parseados (ordem da página).
    """
    soup = BeautifulSoup(html, "lxml")
    editais: list[Edital] = []
    for title in soup.select("h5.capa-titulo"):
        card = title.find_parent("div", class_="card")
        if card is None:
            continue
        edital = _parse_card(card, base_url)
        if edital is not None:
            editais.append(edital)
    return editais


def compute_card_hash(card_html: str) -> str:
    """Hash SHA-256 do HTML do card para detecção de mudanças."""
    return hashlib.sha256(card_html.encode("utf-8")).hexdigest()


def parse_lotes(
    html: str,
    leilao_id: int,
    base_url: str = DEFAULT_BASE_URL,
) -> list[Lote]:
    """Extrai lotes/veículos dos cards da listagem de um edital.

    Args:
        html: HTML de uma página de `/lotes/lista-lotes/{id}/{ano}`.
        leilao_id: ID do leilão (do path ou do edital pai).
        base_url: URL base para links relativos.

    Returns:
        Lista de lotes parseados (ordem da página).
    """
    soup = BeautifulSoup(html, "lxml")
    lotes: list[Lote] = []
    for card in soup.select("div.card.listaLotes"):
        lote = _parse_lote_card(card, leilao_id, base_url)
        if lote is not None:
            lotes.append(lote)
    return lotes


def parse_lotes_max_page(html: str) -> int:
    """Retorna o número da última página na paginação da listagem de lotes."""
    soup = BeautifulSoup(html, "lxml")
    pages = [1]
    for link in soup.select("ul.pagination a.page-link[href*='page=']"):
        href = link.get("href", "")
        match = re.search(r"page=(\d+)", href)
        if match:
            pages.append(int(match.group(1)))
    return max(pages)


def parse_lotes_from_pages(
    pages_html: list[str],
    leilao_id: int,
    base_url: str = DEFAULT_BASE_URL,
) -> list[Lote]:
    """Agrega lotes de múltiplas páginas HTML (sem deduplicar)."""
    lotes: list[Lote] = []
    for html in pages_html:
        lotes.extend(parse_lotes(html, leilao_id, base_url))
    return lotes


def lista_lotes_path(url_detalhes: str, base_url: str = DEFAULT_BASE_URL) -> str:
    """Extrai path `/lotes/lista-lotes/...` de uma URL de edital."""
    if url_detalhes.startswith("/"):
        return url_detalhes
    prefix = base_url.rstrip("/")
    if url_detalhes.startswith(prefix):
        return url_detalhes[len(prefix) :]
    match = LOTE_URL_RE.search(url_detalhes)
    if match is None:
        raise ValueError(f"URL de listagem inválida: {url_detalhes}")
    return match.group(0)


def leilao_id_from_lista_url(url_or_path: str) -> int:
    """Extrai leilao_id de URL/path de listagem de lotes."""
    match = LOTE_URL_RE.search(url_or_path)
    if match is None:
        raise ValueError(f"URL de listagem inválida: {url_or_path}")
    return int(match.group(1))


def parse_brl(value: str) -> Decimal | None:
    """Converte texto `R$ 1.234,56` em Decimal."""
    match = BRL_RE.search(value.replace("\xa0", " "))
    if match is None:
        return None
    inteiro = match.group(1).replace(".", "")
    return Decimal(f"{inteiro}.{match.group(2)}")


def _parse_card(card: Tag, base_url: str) -> Edital | None:
    numero_edital = _parse_numero_edital(card)
    municipio = _parse_municipio(card)
    patio = _parse_patio(card)
    status = _parse_status(card)
    data_encerramento = _parse_encerramento(card)
    leilao_id, url_detalhes = _parse_detalhes_link(card, base_url)

    if None in (numero_edital, municipio, patio, status, data_encerramento, leilao_id, url_detalhes):
        return None

    return Edital(
        leilao_id=leilao_id,
        numero_edital=numero_edital,
        municipio=municipio,
        patio=patio,
        status=status,
        data_encerramento=data_encerramento,
        url_detalhes=url_detalhes,
        raw_hash=compute_card_hash(str(card)),
    )


def _parse_numero_edital(card: Tag) -> str | None:
    title = card.select_one("h5.capa-titulo")
    if title is None:
        return None
    match = NUMERO_EDITAL_RE.search(title.get_text())
    return match.group() if match else None


def _parse_municipio(card: Tag) -> str | None:
    el = card.select_one("p.capa-municipio")
    if el is None:
        return None
    return _normalize_text(el.get_text())


def _parse_patio(card: Tag) -> str | None:
    body = card.select_one("div.card-body.p-1.border-top")
    if body is None:
        return None
    bold = body.find("b")
    if bold is None:
        return None
    match = PATIO_RE.match(bold.get_text())
    return _normalize_text(match.group(1)) if match else None


def _parse_status(card: Tag) -> str | None:
    el = card.select_one("div.text-primary, div.text-danger, div.text-success")
    if el is None:
        return None
    status = _normalize_text(el.get_text())
    return status if status in {"Publicado", "Finalizado", "Em Andamento"} else None


def _parse_encerramento(card: Tag) -> datetime | None:
    for el in card.select("div.col-12.text-center"):
        text = el.get_text(strip=True)
        match = ENCERRAMENTO_RE.match(text)
        if match:
            return datetime.strptime(
                f"{match.group(1)} {match.group(2)}",
                "%d/%m/%Y %H:%M",
            )
    return None


def _parse_detalhes_link(card: Tag, base_url: str) -> tuple[int | None, str | None]:
    link = card.select_one("a[href*='/lotes/lista-lotes/']")
    if link is None or not link.get("href"):
        return None, None
    href = link["href"]
    match = LOTE_URL_RE.search(href)
    if match is None:
        return None, None
    return int(match.group(1)), urljoin(base_url, href)


def _normalize_text(value: str) -> str:
    """Colapsa espaços e aplica title case."""
    return " ".join(value.split()).strip().title()


def _parse_lote_card(card: Tag, leilao_id: int, base_url: str) -> Lote | None:
    lote_id_raw = card.get("id")
    if lote_id_raw is None or not str(lote_id_raw).isdigit():
        return None
    lote_id = int(lote_id_raw)

    header = card.select_one("div.card-body b")
    numero_lote: str | None = None
    condicao: str | None = None
    if header is not None:
        spans = header.find_all("span")
        if len(spans) >= 2:
            numero_match = NUMERO_LOTE_RE.search(spans[0].get_text())
            numero_lote = numero_match.group() if numero_match else spans[0].get_text(strip=True)
            condicao = spans[1].get_text(strip=True).upper()

    marca_modelo: str | None = None
    for row in card.select("div.card-body div.row"):
        col = row.select_one("div.col-12.text-center")
        if col is None:
            continue
        bold = col.find("b")
        if bold is None or bold is header:
            continue
        text = " ".join(bold.get_text().split()).strip()
        if text:
            marca_modelo = text
            break

    valor_el = card.select_one(f"p#valor_atual_lote_{lote_id}")
    valor_atual = parse_brl(valor_el.get_text()) if valor_el is not None else None

    if None in (numero_lote, condicao, marca_modelo):
        return None

    url_detalhes = urljoin(base_url, f"/lotes/detalhes/{lote_id}")

    return Lote(
        lote_id=lote_id,
        leilao_id=leilao_id,
        numero_lote=numero_lote,
        condicao=condicao,
        marca_modelo=marca_modelo,
        valor_inicial=None,
        valor_atual=valor_atual,
        url_detalhes=url_detalhes,
        raw_hash=compute_card_hash(str(card)),
    )
