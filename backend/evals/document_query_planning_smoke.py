import asyncio

from agents import set_default_openai_key

from app.services.document_query_planning import (
    DocumentQueryPlanningService,
)
from app.settings import get_settings


async def main() -> None:
    settings = get_settings()

    set_default_openai_key(
        settings.openai_api_key,
    )

    service = DocumentQueryPlanningService()

    plan = await service.plan(
        "任天堂のサイバー攻撃による事業へのリスクは？"
    )

    print(f"query_text: {plan.query_text}")


if __name__ == "__main__":
    asyncio.run(main())