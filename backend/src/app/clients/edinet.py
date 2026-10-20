import csv
import io
import zipfile
from datetime import datetime, timezone
from typing import TypedDict

import httpx

from app.models.edinet import (
    EdinetApiDocument,
    EdinetCsvPreview,
    EdinetCsvRow,
    EdinetCsvSearchResult,
    EdinetDocument,
    EdinetDocumentsResponse,
)
from app.models.financial import FinancialMetric, FinancialSummary
from app.settings import get_settings


class FinancialMetricDefinition(TypedDict):
    elements: tuple[str, ...]
    context_id: str


BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"

EDINET_CODE_LIST_URL = (
    "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip"
)

FINANCIAL_METRIC_DEFINITIONS: dict[str, FinancialMetricDefinition] = {
    "revenue": {
        "elements": (
            "OperatingRevenuesIFRSKeyFinancialData",
            "RevenueIFRSSummaryOfBusinessResults",
            "RevenueIFRS",
            "NetSalesSummaryOfBusinessResults",
            "NetSales",
        ),
        "context_id": "CurrentYearDuration",
    },
    "operating_income": {
        "elements": (
            "OperatingProfitLossIFRS",
            "OperatingIncomeLossSummaryOfBusinessResults",
            "OperatingIncome",
        ),
        "context_id": "CurrentYearDuration",
    },
    "profit_before_tax": {
        "elements": (
            "ProfitLossBeforeTaxIFRSSummaryOfBusinessResults",
            "ProfitLossBeforeTaxIFRS",
            "IncomeBeforeIncomeTaxes",
        ),
        "context_id": "CurrentYearDuration",
    },
    "net_income": {
        "elements": (
            "ProfitLossAttributableToOwnersOfParentIFRSSummaryOfBusinessResults",
            "ProfitLossAttributableToOwnersOfParentIFRS",
            "ProfitLossAttributableToOwnersOfParentSummaryOfBusinessResults",
        ),
        "context_id": "CurrentYearDuration",
    },
    "total_assets": {
        "elements": (
            "TotalAssetsIFRSSummaryOfBusinessResults",
            "AssetsIFRS",
            "TotalAssetsSummaryOfBusinessResults",
            "Assets",
        ),
        "context_id": "CurrentYearInstant",
    },
    "operating_cash_flow": {
        "elements": (
            "CashFlowsFromUsedInOperatingActivitiesIFRSSummaryOfBusinessResults",
            "CashFlowsFromUsedInOperatingActivitiesIFRS",
            "NetCashProvidedByUsedInOperatingActivitiesSummaryOfBusinessResults",
            "NetCashProvidedByUsedInOperatingActivities",
        ),
        "context_id": "CurrentYearDuration",
    },
}


class EdinetClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.edinet_api_key

    async def get_documents(
        self,
        date: str,
    ) -> EdinetDocumentsResponse:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/documents.json",
                params={
                    "date": date,
                    "type": 2,
                    "Subscription-Key": self.api_key,
                },
                timeout=30.0,
            )

            response.raise_for_status()

            return EdinetDocumentsResponse.model_validate_json(response.text)

    async def get_edinet_code(
        self,
        corporate_number: str,
    ) -> str | None:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                EDINET_CODE_LIST_URL,
                timeout=30.0,
            )

            response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            csv_names = [
                name for name in zip_file.namelist() if name.lower().endswith(".csv")
            ]

            if not csv_names:
                return None

            raw = zip_file.read(csv_names[0])

        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp932")

        rows = list(csv.reader(io.StringIO(text)))

        if len(rows) < 3:
            return None

        headers = rows[1]

        try:
            edinet_code_index = headers.index("ＥＤＩＮＥＴコード")
        except ValueError:
            edinet_code_index = headers.index("EDINETコード")

        corporate_number_index = headers.index("提出者法人番号")

        for row in rows[2:]:
            if len(row) <= corporate_number_index:
                continue

            if row[corporate_number_index] == corporate_number:
                return row[edinet_code_index]

        return None

    async def find_annual_report(
        self,
        edinet_code: str,
        date: str,
    ) -> EdinetApiDocument | None:
        data = await self.get_documents(date)

        for document in data.results:
            if document.edinet_code == edinet_code and document.doc_type_code == "120":
                return document

        return None

    async def download_csv_zip(
        self,
        doc_id: str,
    ) -> bytes:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/documents/{doc_id}",
                params={
                    "type": 5,
                    "Subscription-Key": self.api_key,
                },
                timeout=60.0,
            )

            response.raise_for_status()

            return response.content

    async def get_csv_file_list(
        self,
        doc_id: str,
    ) -> list[str]:
        content = await self.download_csv_zip(doc_id)

        with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
            return zip_file.namelist()

    async def get_main_report_csv_preview(
        self,
        doc_id: str,
        limit: int = 20,
    ) -> EdinetCsvPreview:
        content = await self.download_csv_zip(doc_id)

        with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
            csv_names = [
                name
                for name in zip_file.namelist()
                if (name.lower().endswith(".csv") and "jpcrp030000-asr-001" in name)
            ]

            if not csv_names:
                return EdinetCsvPreview(
                    file_name=None,
                    headers=[],
                    rows=[],
                )

            file_name = csv_names[0]
            raw = zip_file.read(file_name)

        text = raw.decode("utf-16")

        reader = csv.reader(
            io.StringIO(text),
            delimiter="\t",
        )

        rows = list(reader)

        if not rows:
            return EdinetCsvPreview(
                file_name=file_name,
                headers=[],
                rows=[],
            )

        headers = rows[0]

        return EdinetCsvPreview(
            file_name=file_name,
            headers=headers,
            rows=rows[1 : limit + 1],
        )

    async def search_main_report_csv(
        self,
        doc_id: str,
        keyword: str,
    ) -> list[EdinetCsvSearchResult]:
        content = await self.download_csv_zip(doc_id)

        with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
            csv_names = [
                name
                for name in zip_file.namelist()
                if (name.lower().endswith(".csv") and "jpcrp030000-asr-001" in name)
            ]

            if not csv_names:
                return []

            raw = zip_file.read(csv_names[0])

        text = raw.decode("utf-16")

        reader = csv.DictReader(
            io.StringIO(text),
            delimiter="\t",
        )

        normalized_keyword = keyword.lower()

        results: list[EdinetCsvSearchResult] = []

        for row in reader:
            element_id = row.get("要素ID", "")
            item_name = row.get("項目名", "")

            searchable_text = (f"{element_id} {item_name}").lower()

            if normalized_keyword in searchable_text:
                results.append(
                    EdinetCsvSearchResult(
                        element_id=element_id,
                        item_name=item_name,
                        context_id=row.get("コンテキストID"),
                        relative_year=row.get("相対年度"),
                        consolidated_or_non_consolidated=row.get("連結・個別"),
                        period_type=row.get("期間・時点"),
                        unit=row.get("単位"),
                        value=row.get("値"),
                    )
                )

        return results

    async def _get_main_report_rows(
        self,
        doc_id: str,
    ) -> list[EdinetCsvRow]:
        content = await self.download_csv_zip(doc_id)

        with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
            csv_names = [
                name
                for name in zip_file.namelist()
                if (name.lower().endswith(".csv") and "jpcrp030000-asr-001" in name)
            ]

            if not csv_names:
                return []

            raw = zip_file.read(csv_names[0])

        text = raw.decode("utf-16")

        reader = csv.DictReader(
            io.StringIO(text),
            delimiter="\t",
        )

        rows: list[EdinetCsvRow] = []

        for row in reader:
            rows.append(
                EdinetCsvRow(
                    element_id=row.get("要素ID", ""),
                    item_name=row.get("項目名", ""),
                    context_id=row.get(
                        "コンテキストID",
                        "",
                    ),
                    relative_year=row.get(
                        "相対年度",
                        "",
                    ),
                    consolidated_or_non_consolidated=row.get(
                        "連結・個別",
                        "",
                    ),
                    period_type=row.get(
                        "期間・時点",
                        "",
                    ),
                    unit=row.get("単位", ""),
                    value=row.get("値", ""),
                )
            )

        return rows

    def _find_current_metric(
        self,
        rows: list[EdinetCsvRow],
        element_names: tuple[str, ...],
        context_id: str,
    ) -> FinancialMetric | None:
        for element_name in element_names:
            for row in rows:
                local_name = row.element_id.split(
                    ":",
                    1,
                )[-1]

                if local_name != element_name:
                    continue

                if row.context_id != context_id:
                    continue

                if not row.value:
                    continue

                try:
                    value = int(row.value)
                except ValueError:
                    continue

                return FinancialMetric(
                    value=value,
                    unit=row.unit or None,
                    element_id=row.element_id,
                    item_name=row.item_name or None,
                    context_id=context_id,
                    relative_year=(row.relative_year or None),
                )

        return None

    async def get_financial_summary(
        self,
        doc_id: str,
    ) -> FinancialSummary:
        rows = await self._get_main_report_rows(doc_id)

        metrics = {}

        for metric_name, definition in FINANCIAL_METRIC_DEFINITIONS.items():
            metrics[metric_name] = self._find_current_metric(
                rows=rows,
                element_names=definition["elements"],
                context_id=definition["context_id"],
            )

        return FinancialSummary(
            doc_id=doc_id,
            revenue=metrics["revenue"],
            operating_income=metrics["operating_income"],
            profit_before_tax=metrics["profit_before_tax"],
            net_income=metrics["net_income"],
            total_assets=metrics["total_assets"],
            operating_cash_flow=metrics["operating_cash_flow"],
        )

    async def get_document_list(
        self,
        date: str,
    ) -> list[EdinetDocument]:
        data = await self.get_documents(date)

        documents = []

        fetched_at = datetime.now(timezone.utc)

        for item in data.results:
            documents.append(
                EdinetDocument(
                    doc_id=item.doc_id,
                    edinet_code=item.edinet_code,
                    sec_code=item.sec_code,
                    corporate_number=item.corporate_number,
                    filer_name=item.filer_name,
                    doc_type_code=item.doc_type_code,
                    form_code=item.form_code,
                    ordinance_code=item.ordinance_code,
                    period_start=item.period_start,
                    period_end=item.period_end,
                    submitted_at=item.submitted_at,
                    description=item.description,
                    xbrl_available=item.xbrl_flag == "1",
                    pdf_available=item.pdf_flag == "1",
                    csv_available=item.csv_flag == "1",
                    fetched_at=fetched_at,
                )
            )

        return documents
