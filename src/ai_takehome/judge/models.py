from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Winner = Literal["LEFT", "RIGHT", "TIE"]


class CriterionVerdict(BaseModel):
    name: str
    left_score: float = Field(ge=1, le=5)
    right_score: float = Field(ge=1, le=5)
    rationale: str
    evidence: str


class PairVerdict(BaseModel):
    criteria: list[CriterionVerdict]
    left_overall: float = Field(ge=1, le=5)
    right_overall: float = Field(ge=1, le=5)
    winner: Winner
    rationale: str


class ParsedVerdict(BaseModel):
    valid: bool
    verdict: PairVerdict | None = None
    parse_error: str | None = None
    parse_strategy: str

