from __future__ import annotations


def normalize_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper()
    if cleaned == "APPL":
        return "AAPL"
    return cleaned


def normalize_symbols(symbols: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in symbols:
        symbol = normalize_symbol(raw)
        if symbol and symbol not in seen:
            seen.add(symbol)
            normalized.append(symbol)
    return normalized
