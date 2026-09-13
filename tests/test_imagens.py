"""Heurística ingênua, CAS de blobs e CSV de rótulos (offline)."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from detran_scraper.imagens import (
    blob_relpath,
    imagem_url,
    import_rotulos_csv,
    naive_avaliar,
    write_blob,
)
from detran_scraper.storage import _sql_statements

ROOT = Path(__file__).resolve().parents[1]
SQL_006 = ROOT / "sql" / "006_lotes_imagens.sql"


def _jpeg(size: tuple[int, int], color: tuple[int, int, int], quality: int = 90) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _noisy_jpeg(width: int = 400, height: int = 300) -> bytes:
    img = Image.new("RGB", (width, height))
    img.putdata(
        [
            ((i * 17) % 256, (i * 31) % 256, (i * 53) % 256)
            for i in range(width * height)
        ]
    )
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def test_url_galeria_slot():
    url = imagem_url(3416, 312935, slot=3)
    assert url.endswith("/Imagens/visualizar/leiloes/leilao_3416/img_312935_3.jpg")


def test_blob_relpath_cas():
    digest = "ab" + "c" * 62
    assert blob_relpath(digest) == f"blobs/ab/{digest}.jpg"


def test_naive_too_small():
    ok, motivo = naive_avaliar(b"tiny")
    assert ok is False
    assert motivo == "too_small"


def test_naive_not_image():
    payload = b"not a jpeg" * 2000
    ok, motivo = naive_avaliar(payload)
    assert ok is False
    assert motivo == "not_image"


def test_naive_black():
    content = _jpeg((640, 480), (0, 0, 0), quality=100)
    if len(content) < 10_000:
        content = _jpeg((1200, 800), (2, 2, 2), quality=100)
    ok, motivo = naive_avaliar(content)
    assert ok is False
    assert motivo in {"black", "too_small", "flat"}


def test_naive_ok_varied():
    content = _noisy_jpeg()
    assert len(content) >= 10_000
    ok, motivo = naive_avaliar(content)
    assert ok is True
    assert motivo == "ok"


def test_write_blob_dedup(tmp_path: Path):
    content = _noisy_jpeg()
    digest = "aa" + "b" * 62
    rel = write_blob(tmp_path, digest, content)
    path = tmp_path / rel
    assert path.is_file()
    write_blob(tmp_path, digest, b"other")
    assert path.read_bytes() == content


def test_import_rotulos_csv_parses_sim_nao(tmp_path: Path, monkeypatch):
    digest = "a" * 64
    csv_path = tmp_path / "labels.csv"
    csv_path.write_text(
        "sha256,valida,motivo,notes\n"
        f"{digest},sim,ok,n1\n"
        f"{'b' * 64},nao,black,\n"
        f"{'c' * 10},sim,,skip\n",
        encoding="utf-8",
    )
    captured: list[tuple] = []

    def fake_persist(_engine, rows):
        captured.extend(rows)
        return len(rows)

    monkeypatch.setattr(
        "detran_scraper.imagens.persist_imagem_labels", fake_persist
    )
    n = import_rotulos_csv(object(), csv_path)  # type: ignore[arg-type]
    assert n == 2
    assert captured[0][0] == digest
    assert captured[0][1] is True
    assert captured[1][1] is False


def test_006_is_additive_only():
    sql = SQL_006.read_text(encoding="utf-8")
    for stmt in _sql_statements(sql):
        lowered = stmt.lower().lstrip()
        assert not lowered.startswith("drop ")
        assert not lowered.startswith("truncate ")
        assert not lowered.startswith("delete from")
    assert "create table if not exists raw.lotes_imagens" in sql.lower()
    assert "mart.lotes_imagens_labels" in sql.lower()
