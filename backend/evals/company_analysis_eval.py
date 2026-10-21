import asyncio
from pathlib import Path

import httpx
from agents import Agent, Runner, set_default_openai_key
from pydantic import BaseModel, RootModel

from app.services.company_analysis import CompanyAnalysisService

from app.models.research_analysis import (
    BusinessAnalysis,
    CompanyResearchAnalysisResult,
    RiskAnalysis,
)
from app.settings import get_settings


class CompanyAnalysisEvalCase(BaseModel):
    id: str
    company_name: str
    expected_business_facts: list[str]
    expected_risk_facts: list[str]


class CompanyAnalysisEvalCases(
    RootModel[list[CompanyAnalysisEvalCase]]
):
    pass


class FactEvaluation(BaseModel):
    fact: str
    matched: bool
    evidence: str | None = None


class CompanyAnalysisJudgeResult(BaseModel):
    business_facts: list[FactEvaluation]
    risk_facts: list[FactEvaluation]


class CompanyAnalysisJudgeInput(BaseModel):
    company_name: str
    expected_business_facts: list[str]
    expected_risk_facts: list[str]
    actual_business: BusinessAnalysis
    actual_risks: list[RiskAnalysis]

class CompanyEvalScore(BaseModel):
    business_recall: float
    risk_recall: float


company_analysis_judge = Agent(
    name="Company Analysis Evaluator",
    model="gpt-5.6-luna",
    instructions="""
あなたは企業分析結果の評価者です。

expected_business_facts の各事実は、
actual_business の内容だけを根拠に評価してください。

expected_risk_facts の各事実は、
actual_risks の内容だけを根拠に評価してください。

business の評価に actual_risks を使用したり、
risk の評価に actual_business を使用してはいけません。

完全な文字列一致は必要ありません。
表現が異なっていても、同じ意味の内容が明確に含まれていれば
matched=true としてください。

ただし、部分的に関連するだけの場合や、
推測しなければ一致と判断できない場合は
matched=false としてください。

business_facts では expected_business_facts の全項目を
元の順序のまま1件ずつ評価してください。

risk_facts では expected_risk_facts の全項目を
元の順序のまま1件ずつ評価してください。

fact には expected 側の文字列を変更せず、そのまま入れてください。

matched=true の場合は、
評価対象の actual_business または actual_risks の
どの内容を根拠に一致と判断したかを
evidence に簡潔に記載してください。

matched=false の場合は evidence=null としてください。
""",
    output_type=CompanyAnalysisJudgeResult,
)


def load_eval_cases() -> list[CompanyAnalysisEvalCase]:
    path = Path(__file__).with_name(
        "company_analysis_cases.json"
    )

    cases = CompanyAnalysisEvalCases.model_validate_json(
        path.read_text(encoding="utf-8")
    )

    return cases.root


def calculate_recall(
    evaluations: list[FactEvaluation],
) -> float:
    if not evaluations:
        return 0.0

    matched_count = sum(
        1
        for evaluation in evaluations
        if evaluation.matched
    )

    return round(
        matched_count / len(evaluations),
        3,
    )


def validate_judge_result(
    case: CompanyAnalysisEvalCase,
    result: CompanyAnalysisJudgeResult,
) -> None:
    actual_business_facts = [
        evaluation.fact
        for evaluation in result.business_facts
    ]

    actual_risk_facts = [
        evaluation.fact
        for evaluation in result.risk_facts
    ]

    if actual_business_facts != case.expected_business_facts:
        raise RuntimeError(
            "Judge returned unexpected business fact order or content."
        )

    if actual_risk_facts != case.expected_risk_facts:
        raise RuntimeError(
            "Judge returned unexpected risk fact order or content."
        )


async def fetch_analysis(
    client: httpx.AsyncClient,
    company_name: str,
) -> CompanyResearchAnalysisResult:
    response = await client.post(
        "/research/company/analysis",
        params={
            "name": company_name,
        },
    )

    response.raise_for_status()

    return CompanyResearchAnalysisResult.model_validate_json(
        response.text
    )


async def evaluate_case(
    client: httpx.AsyncClient,
    case: CompanyAnalysisEvalCase,
) -> CompanyEvalScore:
    response = await fetch_analysis(
        client=client,
        company_name=case.company_name,
    )
    
    

    judge_input = CompanyAnalysisJudgeInput(
        company_name=case.company_name,
        expected_business_facts=case.expected_business_facts,
        expected_risk_facts=case.expected_risk_facts,
        actual_business=response.analysis.business,
        actual_risks=response.analysis.risks,
    )

    result = await Runner.run(
        company_analysis_judge,
        input=judge_input.model_dump_json(
            ensure_ascii=False
        ),
    )

    judge_result = CompanyAnalysisJudgeResult.model_validate(
        result.final_output
    )

    validate_judge_result(
        case=case,
        result=judge_result,
    )

    business_recall = calculate_recall(
        judge_result.business_facts
    )

    risk_recall = calculate_recall(
        judge_result.risk_facts
    )

    print()
    print(f"=== {case.id} / {case.company_name} ===")
    print(
        f"Business Recall: "
        f"{business_recall:.1%}"
    )
    print(
        f"Risk Recall: "
        f"{risk_recall:.1%}"
    )

    print()
    print("Business facts:")

    for evaluation in judge_result.business_facts:
        status = "PASS" if evaluation.matched else "MISS"

        print(
            f"  [{status}] {evaluation.fact}"
        )

        if evaluation.evidence is not None:
            print(
                f"         evidence: "
                f"{evaluation.evidence}"
            )

    

    print()
    print("Risk facts:")

    for evaluation in judge_result.risk_facts:
        status = "PASS" if evaluation.matched else "MISS"

        print(
            f"  [{status}] {evaluation.fact}"
        )

        if evaluation.evidence is not None:
            print(
                f"         evidence: "
                f"{evaluation.evidence}"
            )

    usage = result.context_wrapper.usage

    print()
    print(
        f"Judge tokens: "
        f"input={usage.input_tokens}, "
        f"output={usage.output_tokens}, "
        f"total={usage.total_tokens}"
    )
    
    return CompanyEvalScore(
            business_recall=business_recall,
            risk_recall=risk_recall,
        )
    





async def main() -> None:
    settings = get_settings()

    set_default_openai_key(
        settings.openai_api_key
    )

    cases = load_eval_cases()

    run_count = 3

    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8000",
        timeout=120.0,
    ) as client:
        for case in cases:
            scores: list[CompanyEvalScore] = []

            for run_number in range(
                1,
                run_count + 1,
            ):
                print()
                print(
                    f"### Run {run_number}/{run_count} "
                    f"- {case.company_name}"
                )

                score = await evaluate_case(
                    client=client,
                    case=case,
                )

                scores.append(score)

            business_scores = [
                score.business_recall
                for score in scores
            ]

            risk_scores = [
                score.risk_recall
                for score in scores
            ]

            average_business = (
                sum(business_scores)
                / len(business_scores)
            )

            average_risk = (
                sum(risk_scores)
                / len(risk_scores)
            )

            print()
            print(
                f"=== Summary: "
                f"{case.company_name} ==="
            )
            print(
                "Business Recall "
                f"average={average_business:.1%}, "
                f"min={min(business_scores):.1%}"
            )
            print(
                "Risk Recall "
                f"average={average_risk:.1%}, "
                f"min={min(risk_scores):.1%}"
            )
            
            


if __name__ == "__main__":
    asyncio.run(main())