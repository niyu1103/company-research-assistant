from pydantic import BaseModel, Field


class AnswerRelevanceEvalCase(BaseModel):
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    expected_relevant: bool


class AnswerRelevanceJudgeOutput(BaseModel):
    relevant: bool
    reason: str = Field(min_length=1)


class AnswerRelevanceEvalResult(BaseModel):
    relevant: bool
    reason: str = Field(min_length=1)


class AnswerRelevanceQAEvalCase(BaseModel):
    id: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    question: str = Field(min_length=1)
    expected_relevant: bool
