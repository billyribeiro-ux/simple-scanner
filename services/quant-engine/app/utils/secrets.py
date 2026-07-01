from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SECRET_KEYS = {"apikey", "api_key", "key", "token", "authorization", "password", "secret"}


def redact_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:2]}***{value[-2:]}"


def redact_url(url: str) -> str:
    parts = urlsplit(url)
    redacted_query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() in SECRET_KEYS:
            redacted_query.append((key, "***"))
        else:
            redacted_query.append((key, value))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(redacted_query), parts.fragment))


def redact_text(text: str) -> str:
    text = re.sub(r"(?i)(apikey|api_key|token|password|secret)=([^&\s]+)", r"\1=***", text)
    text = re.sub(r"(?i)(authorization:\s*bearer\s+)[^\s]+", r"\1***", text)
    return text
