"""Distância em linha reta entre a sede do município e Betim.

Coordenadas: sedes municipais de MG em data/municipios_mg.csv
(kelvins/Municipios-Brasileiros, códigos IBGE).
"""

from __future__ import annotations

import csv
import math
import unicodedata
from pathlib import Path

_EARTH_KM = 6371.0
_CSV = Path(__file__).parent / "data" / "municipios_mg.csv"


def _norm(nome: str) -> str:
    folded = unicodedata.normalize("NFD", nome)
    stripped = "".join(c for c in folded if unicodedata.category(c) != "Mn")
    return " ".join(stripped.casefold().split())


def _load() -> dict[str, tuple[float, float]]:
    table: dict[str, tuple[float, float]] = {}
    with _CSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            table[_norm(row["nome"])] = (float(row["latitude"]), float(row["longitude"]))
    if "betim" not in table:
        raise RuntimeError("sede de Betim ausente em municipios_mg.csv")
    return table


_SEDES = _load()


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_KM * math.asin(math.sqrt(h))


def distancia_betim_km(municipio: str | None) -> int | None:
    if not isinstance(municipio, str) or not municipio.strip():
        return None
    ponto = _SEDES.get(_norm(municipio))
    if ponto is None:
        return None
    return round(haversine_km(ponto, _SEDES["betim"]))
