from app.services.company_research import (
    build_company_search_names,
)
from datetime import date as Date
from datetime import datetime, timezone

from datetime import date, datetime, timezone

import pytest

from app.clients.edinet import EdinetClient
from app.models.edinet import (
    EdinetApiDocument,
    EdinetDocument,
)
from app.models.edinet_sync import EdinetSyncResult
from app.repositories.databricks_edinet_document import (
    DatabricksEdinetDocumentRepository,
)
from app.services.company_research import (
    CompanyResearchService,
    build_company_search_names,
)
from app.services.edinet_sync import EdinetSyncService

class FakeEdinetDocumentRepository(
    DatabricksEdinetDocumentRepository
):
    def __init__(self) -> None:
        self.historical_doc_id: str | None = None

    def find_latest_annual_report(
        self,
        edinet_code: str,
    ) -> EdinetDocument | None:
        del edinet_code

        return EdinetDocument.model_construct(
            doc_id="LATEST",
            edinet_code="E35941",
            period_end=Date(2025, 12, 31),
            submitted_at=datetime(
                2026,
                3,
                27,
                12,
                10,
                tzinfo=timezone.utc,
            ),
        )

    def find_annual_report_doc_id_by_period_end_year(
        self,
        *,
        edinet_code: str,
        year: int,
    ) -> str | None:
        del edinet_code, year

        return self.historical_doc_id

class FakeEdinetClient(EdinetClient):
    def __init__(self) -> None:
        self.requested_dates: list[str] = []

    async def find_annual_report(
        self,
        edinet_code: str,
        date: str,
    ) -> EdinetApiDocument | None:
        del edinet_code

        self.requested_dates.append(date)

        if date != "2022-03-29":
            return None

        return EdinetApiDocument.model_construct(
            doc_id="S100NRTJ",
            edinet_code="E35941",
            doc_type_code="120",
            period_end=Date(2021, 12, 31),
        )

class FakeEdinetSyncService(EdinetSyncService):
    def __init__(
        self,
        repository: FakeEdinetDocumentRepository,
    ) -> None:
        self.repository = repository
        self.synced_dates: list[Date] = []

    async def sync_range(
        self,
        *,
        start_date: Date,
        end_date: Date,
        force: bool = False,
    ) -> EdinetSyncResult:
        assert start_date == end_date
        assert force is True

        self.synced_dates.append(start_date)

        self.repository.historical_doc_id = "S100NRTJ"

        return EdinetSyncResult(
            start_date=start_date,
            end_date=end_date,
            days=1,
            total_saved=1,
            results=[],
        )


def test_build_company_search_names_without_corporate_type() -> None:
    assert build_company_search_names(
        "ヘッドウォータース"
    ) == [
        "ヘッドウォータース",
    ]


def test_build_company_search_names_with_prefix() -> None:
    assert build_company_search_names(
        "株式会社ヘッドウォータース"
    ) == [
        "株式会社ヘッドウォータース",
        "ヘッドウォータース",
    ]


def test_build_company_search_names_with_suffix() -> None:
    assert build_company_search_names(
        "ヘッドウォータース株式会社"
    ) == [
        "ヘッドウォータース株式会社",
        "ヘッドウォータース",
    ]

@pytest.mark.anyio
async def test_find_historical_annual_report_syncs_when_missing() -> None:
    repository = FakeEdinetDocumentRepository()

    sync_service = FakeEdinetSyncService(
        repository
    )

    service = CompanyResearchService(
        repository,
        edinet_sync_service=sync_service,
    )

    edinet_client = FakeEdinetClient()
    service.edinet = edinet_client

    doc_id = await (
        service
        .find_annual_report_doc_id_by_period_end_year(
            edinet_code="E35941",
            year=2021,
        )
    )

    assert doc_id == "S100NRTJ"

    assert sync_service.synced_dates == [
        Date(2022, 3, 29),
    ]

    assert "2022-03-29" in edinet_client.requested_dates