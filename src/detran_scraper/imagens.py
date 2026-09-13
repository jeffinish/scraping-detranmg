"""Download e avaliação ingênua das fotos da galeria (sem ML).

Layout no disco (content-addressed — um arquivo por JPEG distinto):

    {IMAGENS_DIR}/blobs/{sha256[:2]}/{sha256}.jpg

O Postgres indexa lote/slot → hash. O mesmo JPEG em dois lotes ou dois runs
não se duplica. Placeholder do portal (~5 KB, HTTP 200) pára a varredura de
slots e não vira “foto válida”.
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import os
import shutil
import threading
import time
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from sqlalchemy.engine import Engine

from detran_scraper.client import DEFAULT_BASE_URL, DetranClient
from detran_scraper.models import LoteImagem
from detran_scraper.storage import (
    latest_full_lotes_run_id,
    list_conservados_pendentes,
    persist_imagem_labels,
    persist_lotes_imagens,
)

logger = logging.getLogger(__name__)

_IMAGEM_PATH = "/Imagens/visualizar/leiloes/leilao_{leilao_id}/img_{lote_id}_{slot}.jpg"

# Fotos reais do pátio ~50–70 KB; placeholder do portal = 5491 B.
MIN_BYTES = 10_000
MIN_SIDE = 80
MAX_SLOT = 12
PAUSE_S = 0.1

_ensure_locks: dict[int, threading.Lock] = {}
_ensure_locks_guard = threading.Lock()


def imagens_root() -> Path:
    """Raiz dos blobs (env IMAGENS_DIR ou data/imagens no repo)."""
    raw = os.getenv("IMAGENS_DIR")
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parents[2] / "data" / "imagens"


def imagem_path(leilao_id: int, lote_id: int, slot: int = 1) -> str:
    """Path HTTP da galeria (slot 1 = thumbnail da listagem)."""
    return _IMAGEM_PATH.format(leilao_id=leilao_id, lote_id=lote_id, slot=slot)


def imagem_url(
    leilao_id: int,
    lote_id: int,
    slot: int = 1,
    base_url: str = DEFAULT_BASE_URL,
) -> str:
    """URL absoluta da foto N da galeria."""
    return f"{base_url.rstrip('/')}{imagem_path(leilao_id, lote_id, slot)}"


def blob_relpath(sha256: str) -> str:
    """Caminho relativo ao IMAGENS_DIR."""
    digest = sha256.lower()
    return f"blobs/{digest[:2]}/{digest}.jpg"


def blob_abs_path(root: Path, sha256: str) -> Path:
    return root / blob_relpath(sha256)


def write_blob(root: Path, sha256: str, content: bytes) -> str:
    """Grava o JPEG se ainda não existir. Returns relpath."""
    dest = blob_abs_path(root, sha256)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_bytes(content)
    return blob_relpath(sha256)


def naive_avaliar(content: bytes) -> tuple[bool, str]:
    """Filtro ingênuo: arquivo/pixels, sem olhar se é um automóvel.

    Returns:
        (valida, motivo) — motivo em {ok, too_small, not_image, tiny_resolution,
        black, flat}.
    """
    if len(content) < MIN_BYTES:
        return False, "too_small"
    try:
        with Image.open(io.BytesIO(content)) as img:
            img.load()
            width, height = img.size
            gray = img.convert("L")
            extrema = gray.getextrema()
    except (UnidentifiedImageError, OSError):
        return False, "not_image"
    if min(width, height) < MIN_SIDE:
        return False, "tiny_resolution"
    mn, mx = extrema
    if mx <= 16:
        return False, "black"
    if (mx - mn) <= 12:
        return False, "flat"
    return True, "ok"


def avaliar_bytes(content: bytes) -> tuple[str, tuple[bool, str]]:
    """Hash + heurística. Não grava disco."""
    digest = hashlib.sha256(content).hexdigest()
    return digest, naive_avaliar(content)


def fetch_galeria_lote(
    client: DetranClient,
    *,
    leilao_id: int,
    lote_id: int,
    root: Path,
    pause_s: float = PAUSE_S,
) -> list[LoteImagem]:
    """GET img_1.. até placeholder/404. Persiste blobs únicos."""
    out: list[LoteImagem] = []
    for slot in range(1, MAX_SLOT + 1):
        url = imagem_url(leilao_id, lote_id, slot, base_url=client.base_url)
        path = imagem_path(leilao_id, lote_id, slot)
        content = client.fetch_bytes(path)
        if pause_s:
            time.sleep(pause_s)
        if not content:
            break
        digest, (valida, motivo) = avaliar_bytes(content)
        placeholder = motivo == "too_small"
        relpath = write_blob(root, digest, content)
        out.append(
            LoteImagem(
                lote_id=lote_id,
                leilao_id=leilao_id,
                slot=slot,
                sha256=digest,
                byte_size=len(content),
                source_url=url,
                relpath=relpath,
                naive_valida=valida,
                naive_motivo=motivo,
                is_placeholder=placeholder,
            )
        )
        if placeholder:
            break
    return out


def _lock_lote(lote_id: int) -> threading.Lock:
    with _ensure_locks_guard:
        lock = _ensure_locks.get(lote_id)
        if lock is None:
            lock = threading.Lock()
            _ensure_locks[lote_id] = lock
        return lock


def ensure_galeria_lote(engine: Engine, *, lote_id: int, leilao_id: int) -> None:
    """Se o mart não tem linha deste lote, baixa a galeria e persiste (CAS).

    Anexa ao último scrape completo de lotes. Não cria scrape_run.
    """
    from sqlalchemy import text

    count_sql = text(
        "SELECT COUNT(*) FROM mart.lotes_imagens WHERE lote_id = :lote_id"
    )
    with engine.connect() as conn:
        n = int(conn.execute(count_sql, {"lote_id": lote_id}).scalar_one())
    if n > 0:
        return
    with _lock_lote(lote_id):
        with engine.connect() as conn:
            n = int(conn.execute(count_sql, {"lote_id": lote_id}).scalar_one())
        if n > 0:
            return
        run_id = latest_full_lotes_run_id(engine)
        if run_id is None:
            logger.warning("On-demand imagens: sem scrape completo para anexar lote %s", lote_id)
            return
        dest = imagens_root()
        dest.mkdir(parents=True, exist_ok=True)
        with DetranClient() as client:
            fotos = fetch_galeria_lote(
                client, leilao_id=leilao_id, lote_id=lote_id, root=dest
            )
        persist_lotes_imagens(engine, fotos, run_id)
        logger.info(
            "On-demand imagens: lote %s → %d slots",
            lote_id,
            len(fotos),
        )


def download_imagens_conservados(
    client: DetranClient,
    engine: Engine,
    *,
    max_lotes: int | None = None,
    root: Path | None = None,
) -> tuple[int, int]:
    """Baixa galeria dos CONSERVADO ainda sem linha em mart.lotes_imagens.

    Não cria scrape_run novo (tombstone de lotes usaria esse run). Anexa ao
    último scrape completo de lotes.

    Returns:
        (lotes_processados, fotos_gravadas_no_banco).
    """
    run_id = latest_full_lotes_run_id(engine)
    if run_id is None:
        logger.error("Nenhum scrape completo de lotes para anexar imagens")
        return 0, 0
    pendentes = list_conservados_pendentes(engine, run_id, limit=max_lotes)
    dest = root or imagens_root()
    dest.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Imagens: %d lotes CONSERVADO pendentes (run_id=%s dir=%s)",
        len(pendentes),
        run_id,
        dest,
    )
    n_fotos = 0
    for i, (lote_id, leilao_id) in enumerate(pendentes, start=1):
        fotos = fetch_galeria_lote(client, leilao_id=leilao_id, lote_id=lote_id, root=dest)
        persist_lotes_imagens(engine, fotos, run_id)
        n_fotos += len(fotos)
        validas = sum(1 for foto in fotos if foto.naive_valida)
        logger.info(
            "  [%d/%d] lote %s → %d slots (%d naive_valida)",
            i,
            len(pendentes),
            lote_id,
            len(fotos),
            validas,
        )
    return len(pendentes), n_fotos


_ROTULO_FIELDS = [
    "sha256",
    "lote_id",
    "slot",
    "arquivo",
    "naive_valida",
    "naive_motivo",
    "strato",
    "valida",
    "motivo",
    "notes",
]


def _gravar_csv_rotulos(dest: Path, blobs: Path, rows: list) -> Path:
    """Copia JPEGs e escreve labels.csv. `strato` é dica da amostra; import ignora."""
    csv_path = dest / "labels.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_ROTULO_FIELDS)
        writer.writeheader()
        for row in rows:
            digest = str(row["sha256"]).strip()
            src = blobs / str(row["relpath"])
            nome = f"{row['lote_id']}_{row['slot']}_{digest[:12]}.jpg"
            if src.is_file():
                shutil.copy2(src, dest / nome)
            writer.writerow(
                {
                    "sha256": digest,
                    "lote_id": row["lote_id"],
                    "slot": row["slot"],
                    "arquivo": nome,
                    "naive_valida": row["naive_valida"],
                    "naive_motivo": row["naive_motivo"],
                    "strato": row.get("strato") or "",
                    "valida": "",
                    "motivo": "",
                    "notes": "",
                }
            )
    logger.info("Amostra de rótulos: %d linhas em %s", len(rows), csv_path)
    return csv_path


def export_amostra_rotulos(
    engine: Engine,
    dest: Path,
    *,
    n: int = 200,
    root: Path | None = None,
    stress: bool = False,
) -> Path:
    """Copia N hashes ainda sem rótulo + labels.csv.

    Inclui placeholder (`too_small`) para amostrar `naive_valida = false`.
    Um JPEG por sha256. `stress=True`: bordas (arquivo pequeno, lote sem
    placeholder, slot 12, aleatório) + 1 placeholder de calibração.
    """
    from sqlalchemy import text

    dest.mkdir(parents=True, exist_ok=True)
    blobs = root or imagens_root()
    if stress:
        for old in dest.glob("*.jpg"):
            old.unlink()
        quota = max(1, n // 4)
        sql = text("""
            WITH lotes AS (
                SELECT lote_id,
                    COUNT(*) AS n_slots,
                    COUNT(*) FILTER (WHERE is_placeholder) AS n_ph
                FROM mart.lotes_imagens
                GROUP BY lote_id
            ),
            base AS (
                SELECT DISTINCT ON (i.sha256)
                    i.sha256, i.lote_id, i.slot, i.relpath,
                    i.naive_valida, i.naive_motivo, i.byte_size,
                    l.n_ph, i.is_placeholder
                FROM mart.lotes_imagens AS i
                JOIN lotes AS l ON l.lote_id = i.lote_id
                LEFT JOIN mart.lotes_imagens_labels AS lab ON lab.sha256 = i.sha256
                WHERE i.relpath IS NOT NULL
                    AND (lab.sha256 IS NULL OR i.is_placeholder)
                ORDER BY i.sha256, i.slot
            ),
            placeholder AS (
                SELECT sha256, lote_id, slot, relpath, naive_valida, naive_motivo,
                    'placeholder'::text AS strato
                FROM base
                WHERE is_placeholder
                LIMIT 1
            ),
            pequenas AS (
                SELECT sha256, lote_id, slot, relpath, naive_valida, naive_motivo,
                    'byte_pequeno'::text AS strato
                FROM base
                WHERE NOT is_placeholder
                    AND sha256 NOT IN (SELECT sha256 FROM placeholder)
                ORDER BY byte_size ASC, sha256
                LIMIT :q
            ),
            sem_ph AS (
                SELECT sha256, lote_id, slot, relpath, naive_valida, naive_motivo,
                    'sem_placeholder'::text AS strato
                FROM base
                WHERE n_ph = 0
                    AND sha256 NOT IN (SELECT sha256 FROM placeholder)
                    AND sha256 NOT IN (SELECT sha256 FROM pequenas)
                ORDER BY md5(sha256)
                LIMIT :q
            ),
            slot12 AS (
                SELECT sha256, lote_id, slot, relpath, naive_valida, naive_motivo,
                    'slot12'::text AS strato
                FROM base
                WHERE slot = 12
                    AND sha256 NOT IN (SELECT sha256 FROM placeholder)
                    AND sha256 NOT IN (SELECT sha256 FROM pequenas)
                    AND sha256 NOT IN (SELECT sha256 FROM sem_ph)
                ORDER BY md5(sha256)
                LIMIT :q
            ),
            resto AS (
                SELECT sha256, lote_id, slot, relpath, naive_valida, naive_motivo,
                    'aleatorio'::text AS strato
                FROM base
                WHERE NOT is_placeholder
                    AND sha256 NOT IN (SELECT sha256 FROM placeholder)
                    AND sha256 NOT IN (SELECT sha256 FROM pequenas)
                    AND sha256 NOT IN (SELECT sha256 FROM sem_ph)
                    AND sha256 NOT IN (SELECT sha256 FROM slot12)
                ORDER BY md5(sha256)
                LIMIT :q
            )
            SELECT * FROM placeholder
            UNION ALL SELECT * FROM pequenas
            UNION ALL SELECT * FROM sem_ph
            UNION ALL SELECT * FROM slot12
            UNION ALL SELECT * FROM resto
        """)
        with engine.connect() as conn:
            rows = conn.execute(sql, {"q": quota}).mappings().all()
        return _gravar_csv_rotulos(dest, blobs, rows)

    sql = text("""
        WITH unlabeled AS (
            SELECT DISTINCT ON (i.sha256)
                i.sha256, i.lote_id, i.slot, i.relpath, i.naive_valida, i.naive_motivo
            FROM mart.lotes_imagens AS i
            LEFT JOIN mart.lotes_imagens_labels AS lab ON lab.sha256 = i.sha256
            WHERE i.relpath IS NOT NULL
                AND lab.sha256 IS NULL
            ORDER BY i.sha256, i.slot
        )
        SELECT sha256, lote_id, slot, relpath, naive_valida, naive_motivo,
            ''::text AS strato
        FROM unlabeled
        ORDER BY naive_valida ASC, lote_id, slot
        LIMIT :n
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"n": n}).mappings().all()
    return _gravar_csv_rotulos(dest, blobs, rows)


def import_rotulos_csv(engine: Engine, csv_path: Path) -> int:
    """Lê labels.csv (coluna valida true/false/1/0/sim/nao) e grava no mart."""
    rows: list[tuple[str, bool, str | None, str | None]] = []
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            flag = _parse_bool(raw.get("valida"))
            if flag is None:
                continue
            digest = (raw.get("sha256") or "").strip().lower()
            if len(digest) != 64:
                continue
            motivo = (raw.get("motivo") or "").strip() or None
            notes = (raw.get("notes") or "").strip() or None
            rows.append((digest, flag, motivo, notes))
    n = persist_imagem_labels(engine, rows)
    logger.info("Importou %d rótulos de %s", n, csv_path)
    return n


def _parse_bool(value: object) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "sim", "s", "yes", "y", "valida", "válida"}:
        return True
    if text in {"0", "false", "f", "nao", "não", "n", "no", "invalida", "inválida"}:
        return False
    return None
