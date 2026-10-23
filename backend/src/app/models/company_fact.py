from typing import Literal

from pydantic import BaseModel

CompanyFactKey = Literal[
    "employee_number",
    "location",
    "date_of_establishment",
    "corporate_number",
    "representative_name",
    "capital_stock",
    "edinet_code",
]


class CompanyFactAnswer(BaseModel):
    fact_key: CompanyFactKey | None
    answer: str
    insufficient_context: bool
