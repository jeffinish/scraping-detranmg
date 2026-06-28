"""Cliente HTTP para o portal de leilões DETRAN/MG."""

from __future__ import annotations

import time
from typing import Self

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


class DetranClient:
    """Cliente com sessão persistente (cookies) e retry exponencial."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        )

    def fetch(self, path: str) -> str:
        """Baixa HTML de um path relativo ao portal.

        Args:
            path: Path ou URL relativa (ex.: `/` ou `/lotes/lista-lotes/1/2026`).

        Returns:
            HTML da página.

        Raises:
            httpx.HTTPError: Se todas as tentativas falharem.
        """
        if path.startswith("http"):
            path = path.replace(self.base_url, "", 1)
        if not path.startswith("/"):
            path = f"/{path}"

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self._client.get(path)
                response.raise_for_status()
                return response.text
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

    def close(self) -> None:
        """Fecha a sessão HTTP."""
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
