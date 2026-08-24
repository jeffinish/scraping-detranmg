"""Modelos de domínio do scraper."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Edital:
    """Edital de leilão listado na página inicial do portal."""

    leilao_id: int
    numero_edital: str
    municipio: str
    patio: str
    status: str
    data_encerramento: datetime
    url_detalhes: str
    scraped_at: datetime | None = None
    raw_hash: str | None = None


@dataclass(frozen=True, slots=True)
class Lote:
    """Veículo/lote listado na página de lotes de um edital."""

    lote_id: int
    leilao_id: int
    numero_lote: str
    condicao: str
    marca_modelo: str
    valor_inicial: Decimal | None
    valor_atual: Decimal | None
    url_detalhes: str
    scraped_at: datetime | None = None
    raw_hash: str | None = None
    cor: str | None = None
    ano_modelo: int | None = None
    ano_fabricacao: int | None = None
    combustivel: str | None = None
    valor_incremento: Decimal | None = None
    status_lote: str | None = None


@dataclass(frozen=True, slots=True)
class Lance:
    """Lance efetivado de um lote (JSON da zona logada)."""

    lote_id: int
    leilao_id: int
    valor: Decimal
    lance_em: datetime | None
    arrematante: str | None
    peso: Decimal | None = None
    valor_quilo: Decimal | None = None
