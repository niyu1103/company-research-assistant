import asyncio
from datetime import date, timedelta

from app.clients.edinet import EdinetClient
from app.models.edinet import EdinetDocument
from app.models.edinet_sync import (
    EdinetSyncItem,
    EdinetSyncLatestResult,
    EdinetSyncResult,
    EdinetSyncUpToDateResult,
)
from app.repositories.databricks_edinet_document import (
    DatabricksEdinetDocumentRepository,
)


class EdinetSyncService:
    def __init__(
        self,
        repository: DatabricksEdinetDocumentRepository,
    ) -> None:
        self.edinet = EdinetClient()
        self.repository = repository

    async def sync_range(
        self,
        *,
        start_date: date,
        end_date: date,
        force: bool = False,
    ) -> EdinetSyncResult:
        synced_dates = await asyncio.to_thread(
            self.repository.get_synced_dates,
            start_date.isoformat(),
            end_date.isoformat(),
        )

        results: list[EdinetSyncItem] = []

        documents_by_date: dict[
            str,
            list[EdinetDocument],
        ] = {}

        current_date = start_date

        while current_date <= end_date:
            date_string = current_date.isoformat()

            if not force and date_string in synced_dates:
                results.append(
                    EdinetSyncItem(
                        date=current_date,
                        status="skipped",
                        saved_count=0,
                    )
                )

                current_date += timedelta(days=1)
                continue

            documents = await self.edinet.get_document_list(date_string)

            documents_by_date[date_string] = documents

            results.append(
                EdinetSyncItem(
                    date=current_date,
                    status="synced",
                    saved_count=len(documents),
                )
            )

            current_date += timedelta(days=1)

        if documents_by_date:
            await asyncio.to_thread(
                self.repository.replace_dates_and_save_history,
                documents_by_date,
            )

        total_saved = sum(
            item.saved_count for item in results if item.status == "synced"
        )

        return EdinetSyncResult(
            status="ok",
            start_date=start_date,
            end_date=end_date,
            days=(end_date - start_date).days + 1,
            total_saved=total_saved,
            results=results,
        )

    async def sync_latest(
        self,
        max_days: int = 7,
    ) -> EdinetSyncLatestResult:
        latest_sync_date = await asyncio.to_thread(self.repository.get_latest_sync_date)

        if latest_sync_date is None:
            raise LookupError("No sync history found")

        start_date = latest_sync_date + timedelta(days=1)
        today = date.today()

        if start_date > today:
            return EdinetSyncUpToDateResult(
                latest_sync_date=latest_sync_date,
            )

        end_date = min(
            start_date + timedelta(days=max_days - 1),
            today,
        )

        result = await self.sync_range(
            start_date=start_date,
            end_date=end_date,
            force=False,
        )

        has_more = end_date < today

        return result.model_copy(
            update={
                "has_more": has_more,
                "next_start_date": (end_date + timedelta(days=1) if has_more else None),
            }
        )
