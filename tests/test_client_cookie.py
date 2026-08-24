"""Cookie header normalization (no network)."""

from detran_scraper.client import normalize_cookie


def test_normalize_cookie_strips_prefix_and_quotes():
    assert normalize_cookie('Cookie: a=1; b=2') == "a=1; b=2"
    assert normalize_cookie('"a=1"') == "a=1"
    assert normalize_cookie("   ") is None
    assert normalize_cookie(None) is None
