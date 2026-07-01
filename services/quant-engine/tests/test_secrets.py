from app.utils.secrets import redact_text, redact_url


def test_redacts_api_key_from_url() -> None:
    safe = redact_url("https://example.test/stable/quote?symbol=AAPL&apikey=super-secret")
    assert "super-secret" not in safe
    assert "apikey=%2A%2A%2A" in safe or "apikey=***" in safe


def test_redacts_secret_text() -> None:
    safe = redact_text("apikey=super-secret token=another-secret")
    assert "super-secret" not in safe
    assert "another-secret" not in safe
