import logging
from datetime import datetime, timedelta
from time import perf_counter
from zoneinfo import ZoneInfo

from app.models.edinet_backfill import EdinetBackfillResult
from app.models.edinet_sync import EdinetSyncResult
from app.services.edinet_sync import EdinetSyncService

logger = logging.getLogger(__name__)


class EdinetBackfillService:
    def __init__(
        self,
        sync_service: EdinetSyncService,
    ) -> None:
        self.sync_service = sync_service

    async def backfill(
        self,
        *,
        days: int = 450,
        force: bool = False,
    ) -> EdinetBackfillResult:
        if days <= 0:
            raise ValueError("days must be greater than 0")

        end_date = datetime.now(ZoneInfo("Asia/Tokyo")).date()

        start_date = end_date - timedelta(days=days - 1)

        batch_results: list[EdinetSyncResult] = []

        total_batches = (days + 30) // 31

        batch_number = 1
        current_end = end_date

        while current_end >= start_date:
            current_start = max(
                current_end - timedelta(days=30),
                start_date,
            )

            logger.info(
                "EDINET backfill [%d/%d] %s - %s",
                batch_number,
                total_batches,
                current_start,
                current_end,
            )

            batch_start = perf_counter()

            result = await self.sync_service.sync_range(
                start_date=current_start,
                end_date=current_end,
                force=force,
            )

            batch_results.append(result)

            logger.info(
                "EDINET backfill [%d/%d] completed in %.2fs",
                batch_number,
                total_batches,
                perf_counter() - batch_start,
            )

            current_end = current_start - timedelta(days=1)
            batch_number += 1

        return EdinetBackfillResult(
            start_date=start_date,
            end_date=end_date,
            requested_days=days,
            batch_count=len(batch_results),
            batches=batch_results,
        )
