from typing import Literal

from pydantic import BaseModel

from app.models.financial_question import (
    FinancialQuestionPlan,
)

ConversationPendingAction = Literal[
    "confirm_period",
    "change_period",
    "confirm_period_override",
]

ConversationConfirmationType = Literal[
    "period",
    "period_override",
]


class ConversationState(BaseModel):
    conversation_id: str

    company_name: str | None = None
    original_question: str | None = None

    financial_plan: FinancialQuestionPlan | None = None

    awaiting_period_confirmation: bool = False

    pending_action: ConversationPendingAction | None = None
    confirmation_type: ConversationConfirmationType | None = None

    period_label: str | None = None
    proposed_start_year: int | None = None
    proposed_end_year: int | None = None

    period_resolution_reason: str | None = None

    requested_start_year: int | None = None
    requested_end_year: int | None = None
