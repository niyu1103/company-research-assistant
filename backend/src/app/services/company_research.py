import asyncio
import logging
from datetime import timedelta
from time import monotonic, perf_counter

from app.clients.edinet import EdinetClient
from app.clients.gbizinfo import GBizInfoClient
from app.models.edinet import EdinetDocument
from app.models.research import AnnualReportInfo, CompanyResearchResult
from app.repositories.edinet_document_repository import (
    EdinetDocumentRepositoryProtocol,
)
from app.services.edinet_sync import EdinetSyncService

logger = logging.getLogger("uvicorn.error")


CORPORATE_TYPES = (
    "株式会社",
    "合同会社",
    "有限会社",
)


def build_company_search_names(
    name: str,
) -> list[str]:
    normalized = name.strip()

    names = [normalized]

    for corporate_type in CORPORATE_TYPES:
        if normalized.startswith(corporate_type):
            base_name = normalized.removeprefix(corporate_type).strip()
        elif normalized.endswith(corporate_type):
            base_name = normalized.removesuffix(corporate_type).strip()
        else:
            continue

        if base_name and base_name not in names:
            names.append(base_name)

        break

    return names


class CompanyResearchService:
    def __init__(
        self,
        edinet_document_repository: EdinetDocumentRepositoryProtocol,
        edinet_sync_service: EdinetSyncService | None = None,
    ) -> None:
        self.gbizinfo = GBizInfoClient()
        self.edinet = EdinetClient()
        self.edinet_documents = edinet_document_repository
        self.edinet_sync_service = edinet_sync_service

        self._annual_report_cache: dict[
            str,
            tuple[float, EdinetDocument],
        ] = {}

        self._annual_report_cache_ttl = 3600.0

    async def research(
        self,
        name: str,
    ) -> CompanyResearchResult:
        total_start = perf_counter()

        companies = []

        for search_name in build_company_search_names(name):
            companies = await self.gbizinfo.search_companies(search_name)

            if companies:
                break

        if not companies:
            raise LookupError(f"Company not found: {name}")

        company_summary = companies[0]

        start = perf_counter()

        company = await self.gbizinfo.get_company(company_summary.corporate_number)

        logger.info(
            "research - company detail: %.2fs",
            perf_counter() - start,
        )

        if company is None:
            raise LookupError(f"Company detail not found: {name}")

        start = perf_counter()

        edinet_code = await self.edinet.get_edinet_code(company.corporate_number)

        logger.info(
            "research - edinet code: %.2fs",
            perf_counter() - start,
        )

        if edinet_code is None:
            raise LookupError(f"EDINET code not found: {name}")

        start = perf_counter()

        document = await self._find_latest_annual_report(edinet_code)

        logger.info(
            "research - annual report lookup: %.2fs",
            perf_counter() - start,
        )

        if document is None:
            raise LookupError(
                f"Annual report not found in document index: {edinet_code}"
            )

        start = perf_counter()

        financials = await self.edinet.get_financial_summary(document.doc_id)

        logger.info(
            "research - financial summary: %.2fs",
            perf_counter() - start,
        )

        start = perf_counter()

        narratives = await self.edinet.get_narrative_summary(document.doc_id)

        logger.info(
            "research - narratives: %.2fs",
            perf_counter() - start,
        )

        annual_report = AnnualReportInfo(
            doc_id=document.doc_id,
            edinet_code=edinet_code,
            sec_code=document.sec_code,
            period_start=document.period_start,
            period_end=document.period_end,
            submitted_at=document.submitted_at,
            description=document.description,
        )

        result = CompanyResearchResult(
            company=company,
            edinet_code=edinet_code,
            annual_report=annual_report,
            financials=financials,
            narratives=narratives,
        )

        logger.info(
            "research - total: %.2fs",
            perf_counter() - total_start,
        )

        return result

    async def find_annual_report_doc_id_by_period_end_year(
        self,
        *,
        edinet_code: str,
        year: int,
    ) -> str | None:
        doc_id = await asyncio.to_thread(
            self.edinet_documents.find_annual_report_doc_id_by_period_end_year,
            edinet_code=edinet_code,
            year=year,
        )

        if doc_id is not None:
            return doc_id

        if self.edinet_sync_service is None:
            return None

        latest_document = await self._find_latest_annual_report(edinet_code)

        if (
            latest_document is None
            or latest_document.period_end is None
            or latest_document.submitted_at is None
        ):
            return None

        try:
            target_period_end = latest_document.period_end.replace(year=year)
        except ValueError:
            target_period_end = latest_document.period_end.replace(
                year=year,
                day=28,
            )

        filing_delay = latest_document.submitted_at.date() - latest_document.period_end

        expected_submission_date = target_period_end + filing_delay

        search_offsets = [0]

        for days in range(1, 15):
            search_offsets.extend(
                [
                    -days,
                    days,
                ]
            )

        for offset in search_offsets:
            candidate_date = expected_submission_date + timedelta(days=offset)

            annual_report = await self.edinet.find_annual_report(
                edinet_code=edinet_code,
                date=candidate_date.isoformat(),
            )

            if annual_report is None:
                continue

            if (
                annual_report.period_end is None
                or annual_report.period_end.year != year
            ):
                continue

            await self.edinet_sync_service.sync_range(
                start_date=candidate_date,
                end_date=candidate_date,
                force=True,
            )

            return await asyncio.to_thread(
                self.edinet_documents.find_annual_report_doc_id_by_period_end_year,
                edinet_code=edinet_code,
                year=year,
            )

        return None

    async def _find_latest_annual_report(
        self,
        edinet_code: str,
    ) -> EdinetDocument | None:
        cached = self._annual_report_cache.get(edinet_code)

        if cached is not None:
            cached_at, cached_document = cached

            if monotonic() - cached_at < self._annual_report_cache_ttl:
                logger.info(
                    "research - annual report cache hit: %s",
                    edinet_code,
                )

                return cached_document

        document = await asyncio.to_thread(
            self.edinet_documents.find_latest_annual_report,
            edinet_code,
        )

        if document is not None:
            self._annual_report_cache[edinet_code] = (
                monotonic(),
                document,
            )

        return document
