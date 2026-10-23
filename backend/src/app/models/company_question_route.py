from typing import Literal

from pydantic import BaseModel, Field

CompanyQuestionRouteType = Literal[
    "company_facts",
    "financial",
    "document",
    "analysis",
]


class CompanyQuestionRoute(BaseModel):
    route: CompanyQuestionRouteType
    reason: str = Field(min_length=1)
