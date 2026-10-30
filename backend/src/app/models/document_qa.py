from typing import Literal

from pydantic import BaseModel, Field

CompanyDocumentQAInputType = Literal[
    "period_confirmation",
    "period_range",
    "period_scope_confirmation",
]

CompanyDocumentQAAction = Literal[
    "confirm_period",
    "change_period",
    "use_resolved_period",
    "use_requested_period",
]


class CompanyDocumentQAInput(BaseModel):
    name: str = Field(min_length=1)
    question: str = Field(min_length=1)

    conversation_id: str | None = None
    action: CompanyDocumentQAAction | None = None


class CompanyDocumentQAOption(BaseModel):
    label: str
    value: CompanyDocumentQAAction


class CompanyDocumentQASource(BaseModel):
    chunk_id: str
    section: str
    score: float


class CompanyDocumentQAResult(BaseModel):
    name: str
    question: str
    query_text: str
    answer: str
    evidence_chunk_ids: list[str]
    insufficient_context: bool
    sources: list[CompanyDocumentQASource]

    conversation_id: str | None = None
    requires_user_input: bool = False

    input_type: CompanyDocumentQAInputType | None = None
    options: list[CompanyDocumentQAOption] = Field(
        default_factory=list,
    )
