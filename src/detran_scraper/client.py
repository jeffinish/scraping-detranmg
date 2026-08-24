"""Cliente HTTP para o portal de leilões DETRAN/MG."""

from __future__ import annotations

import json
import time
from typing import Any, Self

import httpx

DEFAULT_BASE_URL = "https://leilao.detran.mg.gov.br"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

RETRYABLE_STATUS = frozenset({403, 429, 503})


def normalize_cookie(raw: str | None) -> str | None:
    """Normaliza o header Cookie colado do browser (sem logar o valor)."""
    if not raw:
        return None
    cookie = raw.strip().strip('"').strip("'")
    if cookie.lower().startswith("cookie:"):
        cookie = cookie.split(":", 1)[1].strip()
    return cookie or None


class DetranClient:
    """Cliente com sessão persistente (cookies) e retry exponencial."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
        cookie: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        headers = dict(DEFAULT_HEADERS)
        normalized = normalize_cookie(cookie)
        if normalized:
            headers["Cookie"] = normalized
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )

    def _get(self, path: str, params: Any = None) -> httpx.Response:
        if path.startswith("http"):
            path = path.replace(self.base_url, "", 1)
        if not path.startswith("/"):
            path = f"/{path}"

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self._client.get(path, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code not in RETRYABLE_STATUS:
                    raise
            except httpx.RequestError as exc:
                last_error = exc
            if attempt < self.max_retries - 1:
                time.sleep(2**attempt)
        assert last_error is not None
        raise last_error

    def fetch(self, path: str) -> str:
        """Baixa HTML de um path relativo ao portal.

        Args:
            path: Path ou URL relativa (ex.: `/` ou `/lotes/lista-lotes/1/2026`).

        Returns:
            HTML da página.

        Raises:
            httpx.HTTPError: Se todas as tentativas falharem.
        """
        return self._get(path).text

    def fetch_json(self, path: str, params: Any = None) -> Any:
        """GET JSON. Falha se a resposta não for JSON (cookie expirado vira HTML)."""
        response = self._get(path, params=params)
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise ValueError(f"Resposta não-JSON em {path} (sessão expirada?)") from exc

    def fetch_home(self) -> str:
        """Baixa o HTML da página inicial com lista de editais."""
        return self.fetch("/")

    def fetch_lotes_pages(self, lista_path: str) -> list[str]:
        """Baixa todas as páginas HTML da listagem de lotes de um edital.

        Args:
            lista_path: Path da listagem (ex.: `/lotes/lista-lotes/3416/2026`).

        Returns:
            HTML de cada página, em ordem.
        """
        from detran_scraper.parsers import parse_lotes_max_page

        first_html = self.fetch(lista_path)
        max_page = parse_lotes_max_page(first_html)
        pages = [first_html]
        for page in range(2, max_page + 1):
            pages.append(self.fetch(f"{lista_path}?page={page}"))
        return pages

    def fetch_lote_detalhe(self, lote_id: int) -> str:
        """HTML estático de `/lotes/detalhes/{id}` (lances vêm no JSON)."""
        return self.fetch(f"/lotes/detalhes/{lote_id}")

    def fetch_update_countdown(self, user_id: str, lote_ids: list[int]) -> Any:
        """Último lance dos cards: `GET /PDO/updateCountdown.php`."""
        params = [("user", user_id), *[("data[]", str(lote_id)) for lote_id in lote_ids]]
        return self.fetch_json("/PDO/updateCountdown.php", params=params)

    def fetch_update_single(self, user_id: str, lote_id: int) -> Any:
        """Histórico de lances: `GET /PDO/updateSingleCountdown.php`."""
        return self.fetch_json(
            "/PDO/updateSingleCountdown.php",
            params={"user": user_id, "data": str(lote_id)},
        )

    def close(self) -> None:
        """Fecha a sessão HTTP."""
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
