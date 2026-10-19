"""Distância em linha reta até Betim, sem Postgres."""

import math

from detran_ui.distancia import distancia_betim_km, haversine_km


def test_haversine_um_grau_no_equador():
    km = haversine_km((0.0, 0.0), (0.0, 1.0))
    assert abs(km - 6371 * math.radians(1)) < 1e-6


def test_betim_e_zero():
    assert distancia_betim_km("Betim") == 0


def test_nome_sem_acento_e_caixa():
    assert distancia_betim_km("TEOFILO OTONI") == distancia_betim_km("Teófilo Otoni")
    assert distancia_betim_km("TEOFILO OTONI") is not None


def test_cidade_desconhecida():
    assert distancia_betim_km("Cidade Inexistente") is None
    assert distancia_betim_km(None) is None
    assert distancia_betim_km("  ") is None


def test_belo_horizonte_bate_com_a_formula():
    km = round(haversine_km((-19.9102, -43.9266), (-19.9668, -44.2008)))
    assert distancia_betim_km("Belo Horizonte") == km
    assert 20 < km < 40
