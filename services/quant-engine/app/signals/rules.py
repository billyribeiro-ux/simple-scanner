from __future__ import annotations

from app.schemas.market import Side
from app.signals.candidates import CandidateSignalEngine


class SetupRuleEngine:
    def __init__(self) -> None:
        self.candidates = CandidateSignalEngine()

    def detect(self, features: dict[str, object]) -> tuple[Side, str, list[str]]:
        candidate = self.candidates.detect(features)[0]
        side = Side(candidate.side) if candidate.side in {Side.LONG.value, Side.SHORT.value} else Side.NO_TRADE
        return side, candidate.setup_type, list(candidate.reason_codes)
