from pydantic import BaseModel, Field


class DocumentQueryPlan(BaseModel):
    query_text: str = Field(min_length=1)
