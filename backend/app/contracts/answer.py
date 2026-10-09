"""Answer fact registry and response answer contracts.

Source of truth: docs/design/contracts.md "Context and answer response"
and the POC core decision C-04 (engine fact registry, constrained
explanations, final validity checks).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class AnswerMode(str, Enum):
    LLM = "LLM"
    DETERMINISTIC = "DETERMINISTIC"


class FactQualifier(str, Enum):
    """Value qualifiers enforced by the response validator.

    A citation ID cannot turn a transcript claim into verified operational
    state; observed/possible/reported remain distinct.
    """

    OBSERVED = "OBSERVED"
    POSSIBLE = "POSSIBLE"
    REPORTED = "REPORTED"  # transcript/statement claim, not source truth
    COMPUTED = "COMPUTED"
    UNKNOWN = "UNKNOWN"


class AnswerFact(BaseModel):
    fact_id: str
    subject_ids: List[str]
    predicate: str
    value: Any
    qualifier: FactQualifier
    observed_at: datetime
    evidence_ids: List[str] = Field(default_factory=list)
    qualifiers: Dict[str, str] = Field(default_factory=dict)


class Statement(BaseModel):
    text: str
    fact_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


class Answer(BaseModel):
    mode: AnswerMode
    summary: str
    facts: List[AnswerFact] = Field(default_factory=list)
    statements: List[Statement] = Field(default_factory=list)

    @model_validator(mode="after")
    def citations_resolve(self) -> "Answer":
        known = {fact.fact_id for fact in self.facts}
        for statement in self.statements:
            unknown = [f for f in statement.fact_ids if f not in known]
            if unknown:
                raise ValueError(f"statements cite unknown fact IDs: {unknown}")
        return self
