from agents import Agent, Runner

from app.models.document_answer import DocumentAnswer
from app.models.document_chunk import RetrievedDocumentChunk


class DocumentAnsweringService:
    def __init__(self) -> None:
        self.agent = Agent(
            name="Company Document Q&A",
            instructions="""
あなたは企業文書Q&Aアシスタントです。

必ず提供されたCONTEXTだけを根拠に回答してください。

ルール:
- CONTEXTにない情報を外部知識から補完しない
- 推測しない
- 質問に直接答える
- 根拠として使用したchunk_idをevidence_chunk_idsに入れる
- evidence_chunk_idsにはCONTEXT内に存在するchunk_idだけを使う
- 十分な根拠がない場合はinsufficient_context=trueにする
- 十分な根拠がない場合は、分からないことを明確に回答する
- 根拠が十分な場合はinsufficient_context=falseにする
""".strip(),
            model="gpt-5.6-luna",
            output_type=DocumentAnswer,
        )

    async def answer(
        self,
        *,
        question: str,
        chunks: list[RetrievedDocumentChunk],
    ) -> DocumentAnswer:
        question = question.strip()

        if not question:
            raise ValueError("question must not be empty")

        if not chunks:
            return DocumentAnswer(
                answer=("検索された文書内に、質問へ回答できる根拠がありません。"),
                evidence_chunk_ids=[],
                insufficient_context=True,
            )

        context = build_document_context(chunks)

        agent_input = f"QUESTION:\n{question}\n\nCONTEXT:\n{context}"

        result = await Runner.run(
            self.agent,
            agent_input,
        )

        answer = DocumentAnswer.model_validate(result.final_output)

        available_chunk_ids = {chunk.chunk_id for chunk in chunks}

        invalid_chunk_ids = [
            chunk_id
            for chunk_id in answer.evidence_chunk_ids
            if chunk_id not in available_chunk_ids
        ]

        if invalid_chunk_ids:
            raise ValueError(
                f"Answer referenced unavailable chunks: {invalid_chunk_ids}"
            )

        return answer


def build_document_context(
    chunks: list[RetrievedDocumentChunk],
) -> str:
    return "\n\n".join(
        (f"[chunk_id={chunk.chunk_id}]\n{chunk.content}") for chunk in chunks
    )
