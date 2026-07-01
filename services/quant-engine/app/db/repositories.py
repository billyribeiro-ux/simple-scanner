from __future__ import annotations

from typing import Protocol, TypeVar


T = TypeVar("T")


class QuantRepository(Protocol[T]):
    def save_many(self, rows: list[T]) -> int:
        ...

    def list_all(self) -> list[T]:
        ...


class InMemoryQuantRepository:
    def __init__(self) -> None:
        self._rows: list[object] = []

    def save_many(self, rows: list[object]) -> int:
        self._rows.extend(rows)
        return len(rows)

    def list_all(self) -> list[object]:
        return list(self._rows)


class QuantRepositoryRegistry:
    def __init__(self) -> None:
        self.bars = InMemoryQuantRepository()
        self.features = InMemoryQuantRepository()
        self.labels = InMemoryQuantRepository()
        self.signals = InMemoryQuantRepository()
        self.model_runs = InMemoryQuantRepository()
