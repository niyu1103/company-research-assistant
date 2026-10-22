import asyncio

from agents import set_default_openai_key

from app.services.document_groundedness_evaluation import (
    DocumentGroundednessEvaluationService,
)
from app.settings import get_settings


async def main() -> None:
    settings = get_settings()

    set_default_openai_key(
        settings.openai_api_key,
    )

    answer = """
任天堂のオンラインサービス等がサイバー攻撃を受けると、
システムの停止・破壊、データ流出や不正利用が発生する可能性があります。
その結果、事業活動の停止、将来の経営成績・財務状況への悪影響、
ブランド評価や株価の低下につながるリスクがあります。
""".strip()

    context = """
当社グループは、情報発信だけではなく、
ゲームのオンラインプレイやソフトウェアのダウンロード販売、
インターネットを介した様々なサービスを提供しています。

しかし、万一これらの運営システムに対し、
サイバー攻撃が行われるなどして、
システムの停止や破壊、データの流出や不正利用等が起きた場合には、
事業活動の停止、将来の経営成績、当社ブランドへの評価、
株価及び財務状況等に悪影響を及ぼす可能性があります。
""".strip()

    evaluator = (
        DocumentGroundednessEvaluationService()
    )

    judgment = await evaluator.evaluate(
        answer=answer,
        context=context,
    )

    print(f"grounded: {judgment.grounded}")
    print(f"score: {judgment.score}")
    print(
        "unsupported_claims: "
        f"{judgment.unsupported_claims}"
    )
    print(f"reasoning: {judgment.reasoning}")


if __name__ == "__main__":
    asyncio.run(main())