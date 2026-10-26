from datetime import date

import pytest

from app.models.edinet_sync import EdinetSyncResult
from app.services.edinet_backfill import EdinetBackfillService
from app.services.edinet_sync import EdinetSyncService


class FakeEdinetSyncService(EdinetSyncService):
    def __init__(self) -> None:
        self.calls: list[
            tuple[
                date,
                date,
                bool,
            ]
        ] = []

    async def sync_range(
        self,
        *,
        start_date: date,
        end_date: date,
        force: bool = False,
    ) -> EdinetSyncResult:
        self.calls.append(
            (
                start_date,
                end_date,
                force,
            )
        )

        return EdinetSyncResult.model_construct()


@pytest.mark.anyio
async def test_backfill_splits_450_days_into_31_day_batches() -> None:
    sync_service = FakeEdinetSyncService()

    service = EdinetBackfillService(
        sync_service=sync_service,
    )

    result = await service.backfill(
        days=450,
    )

    assert result.requested_days == 450
    assert result.batch_count == 15
    assert len(sync_service.calls) == 15

    for start_date, end_date, force in sync_service.calls:
        batch_days = (
            end_date - start_date
        ).days + 1

        assert batch_days <= 31
        assert force is False

    assert sync_service.calls[0][1] == result.end_date
    assert sync_service.calls[-1][0] == result.start_date

    for index in range(
        len(sync_service.calls) - 1
    ):
        current_start = sync_service.calls[index][0]
        next_end = sync_service.calls[index + 1][1]

        assert (
            current_start - next_end
        ).days == 1


@pytest.mark.anyio
async def test_backfill_passes_force_to_sync_range() -> None:
    sync_service = FakeEdinetSyncService()

    service = EdinetBackfillService(
        sync_service=sync_service,
    )

    await service.backfill(
        days=62,
        force=True,
    )

    assert len(sync_service.calls) == 2

    assert all(
        force
        for _, _, force in sync_service.calls
    )


@pytest.mark.anyio
async def test_backfill_rejects_non_positive_days() -> None:
    sync_service = FakeEdinetSyncService()

    service = EdinetBackfillService(
        sync_service=sync_service,
    )

    with pytest.raises(
        ValueError,
        match="days must be greater than 0",
    ):
        await service.backfill(
            days=0,
        )