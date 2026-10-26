import argparse
import asyncio
import logging

from app.repositories.databricks_edinet_document import (
    DatabricksEdinetDocumentRepository,
)
from app.services.edinet_backfill import EdinetBackfillService
from app.services.edinet_sync import EdinetSyncService


async def run(
    *,
    days: int,
    force: bool,
) -> None:
    repository = DatabricksEdinetDocumentRepository()

    sync_service = EdinetSyncService(
        repository
    )

    backfill_service = EdinetBackfillService(
        sync_service=sync_service
    )

    result = await backfill_service.backfill(
        days=days,
        force=force,
    )

    print()
    print("EDINET backfill completed")
    print(f"start_date: {result.start_date}")
    print(f"end_date: {result.end_date}")
    print(f"requested_days: {result.requested_days}")
    print(f"batch_count: {result.batch_count}")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--days",
        type=int,
        default=450,
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    asyncio.run(
        run(
            days=args.days,
            force=args.force,
        )
    )


if __name__ == "__main__":
    main()