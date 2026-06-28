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
