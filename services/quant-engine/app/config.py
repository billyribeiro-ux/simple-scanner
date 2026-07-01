from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:  # pragma: no cover - compatibility path for pure quant tests without venv
    def Field(default=None, alias: str | None = None):
        return default

    def SettingsConfigDict(**kwargs):
        return kwargs

    class BaseSettings:
        def __init__(self, **kwargs):
            annotations = getattr(type(self), "__annotations__", {})
            for name in annotations:
                if name == "model_config":
                    continue
                value = kwargs.get(name, getattr(type(self), name, None))
                setattr(self, name, value)
            env_map = {
                "app_name": "PUBLIC_APP_NAME",
                "fmp_api_key": "FMP_API_KEY",
                "database_url": "DATABASE_URL",
                "redis_url": "REDIS_URL",
                "default_symbols": "PUBLIC_DEFAULT_SYMBOLS",
            }
            for attr, env_name in env_map.items():
                if env_name in os.environ:
                    setattr(self, attr, os.environ[env_name])


DEFAULT_SYMBOLS = "AMZN,AAPL,TSLA,SPY,QQQ,IWM,NVDA,GOOGL,BABA,SHOP"
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", REPO_ROOT / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Adaptive Market Decoder", alias="PUBLIC_APP_NAME")
    fmp_api_key: str = Field(default="", alias="FMP_API_KEY")
    database_url: str = Field(default="", alias="DATABASE_URL")
    redis_url: str = Field(default="", alias="REDIS_URL")
    default_symbols: str = Field(default=DEFAULT_SYMBOLS, alias="PUBLIC_DEFAULT_SYMBOLS")
    timezone: str = "America/New_York"
    data_dir: Path = REPO_ROOT / "data"
    exports_dir: Path = REPO_ROOT / "exports"
    model_artifacts_dir: Path = REPO_ROOT / "model_artifacts"
    fmp_base_url: str = "https://financialmodelingprep.com/stable"
    fmp_websocket_url: str = "wss://websockets.financialmodelingprep.com"
    request_timeout_seconds: float = 20.0
    max_retries: int = 3
    rest_poll_seconds: float = 15.0
    min_confidence: float = 0.70
    max_hold_minutes: int = 60
    target_r: float = 1.5

    @property
    def symbol_list(self) -> list[str]:
        from app.data.symbols import normalize_symbols

        return normalize_symbols(self.default_symbols.split(","))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
