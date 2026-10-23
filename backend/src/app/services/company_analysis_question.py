from agents import Agent, Runner

from app.models.company_analysis_question import (
    CompanyAnalysisDocumentContext,
    CompanyAnalysisQuestionAnswer,
    CompanyAnalysisQuestionInput,
)
from app.models.document_chunk import (
    RetrievedDocumentChunk,
)
from app.models.financial import FinancialTrend
from app.models.research import CompanyResearchResult


class CompanyAnalysisQuestionService:
    def __init__(self) -> None:
        self.agent = Agent(
            name="Company Analysis Question Answerer",
            model="gpt-5.6-luna",
            instructions="""
あなたは企業分析アシスタントです。

入力として与えられた情報だけを根拠に、
ユーザーの質問に回答してください。

利用できる情報は以下です。

- company_name
- financial_trend
- documents

financial_trend に含まれる増減率や利益率は、
アプリ側で計算済みです。

財務数値や比率を自分で再計算しないでください。

documents は有価証券報告書から検索された
関連文書です。

外部知識を追加しないでください。

将来について質問された場合は、
将来を断定してはいけません。

たとえば「今後成長しそう？」という質問では、

- 現在確認できる財務傾向
- 事業上の強み
- リスク
- 成長を支える材料
- 成長を妨げる可能性のある材料

を整理したうえで、
「入力情報からはこう考えられる」
という形で回答してください。

documents の内容を根拠として使用した場合は、
対応する chunk_id を
evidence_chunk_ids に含めてください。

financial_trend の情報だけを使った場合は、
evidence_chunk_ids は空でも構いません。

情報が不足していて質問に答えられない場合は、
insufficient_context=true にしてください。
""",
            output_type=CompanyAnalysisQuestionAnswer,
        )

    async def answer(
        self,
        *,
        question: str,
        research: CompanyResearchResult,
        financial_trend: FinancialTrend,
        chunks: list[RetrievedDocumentChunk],
    ) -> CompanyAnalysisQuestionAnswer:
        analysis_input = CompanyAnalysisQuestionInput(
            question=question,
            company_name=research.company.name,
            financial_trend=financial_trend,
            documents=[
                CompanyAnalysisDocumentContext(
                    chunk_id=chunk.chunk_id,
                    section=chunk.section,
                    content=chunk.content,
                )
                for chunk in chunks
            ],
        )

        result = await Runner.run(
            self.agent,
            input=analysis_input.model_dump_json(ensure_ascii=False),
        )

        answer = CompanyAnalysisQuestionAnswer.model_validate(result.final_output)

        valid_chunk_ids = {chunk.chunk_id for chunk in chunks}

        evidence_chunk_ids = [
            chunk_id
            for chunk_id in answer.evidence_chunk_ids
            if chunk_id in valid_chunk_ids
        ]

        return CompanyAnalysisQuestionAnswer(
            answer=answer.answer,
            evidence_chunk_ids=(evidence_chunk_ids),
            insufficient_context=(answer.insufficient_context),
        )
