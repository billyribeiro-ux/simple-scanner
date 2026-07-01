from app.data.symbols import normalize_symbol, normalize_symbols


def test_normalizes_appl_to_aapl() -> None:
    assert normalize_symbol("appl") == "AAPL"


def test_deduplicates_symbols() -> None:
    assert normalize_symbols(["AAPL", "appl", "TSLA"]) == ["AAPL", "TSLA"]
