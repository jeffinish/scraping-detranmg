"""CLI validation for --lances (no network, no Postgres)."""

from detran_scraper.run import main


def test_lances_requires_cookie(monkeypatch):
    monkeypatch.setenv("DETRAN_COOKIE", "")
    monkeypatch.setenv("DATABASE_URL", "postgresql://scraper:scraper@localhost:5435/detran_leiloes")
    assert main(["--lances", "--database-url", "postgresql://x"]) == 1
