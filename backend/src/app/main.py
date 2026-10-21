import logging
import zipfile
from datetime import date
from time import perf_counter

from fastapi import FastAPI, HTTPException, Path, Query

from app.clients.databricks import DatabricksClient
from app.clients.edinet import EdinetClient
from app.clients.gbizinfo import GBizInfoClient
from app.models.company import CompanyDetail, CompanySummary
from app.models.edinet import EdinetDocument
from app.models.edinet_sync import (
    EdinetSyncLatestResult,
    EdinetSyncResult,
)
from app.models.financial import FinancialHistory, FinancialTrend
from app.models.research import CompanyResearchResult
from app.models.research_analysis import CompanyResearchAnalysisResult
from app.repositories.databricks_edinet_document import (
    DatabricksEdinetDocumentRepository,
)
from app.services.company_analysis import CompanyAnalysisService
from app.services.company_research import CompanyResearchService
from app.services.edinet_sync import EdinetSyncService
from app.settings import get_settings

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Company Research Assistant API",
    version="0.1.0",
)


databricks_edinet_document_repository = DatabricksEdinetDocumentRepository()

edinet_sync_service = EdinetSyncService(databricks_edinet_document_repository)

company_research_service = CompanyResearchService(databricks_edinet_document_repository)

company_analysis_service = CompanyAnalysisService()


@app.get("/health")
def health():
    settings = get_settings()

    return {
        "status": "ok",
        "openai_configured": bool(settings.openai_api_key),
        "edinet_configured": bool(settings.edinet_api_key),
        "gbizinfo_configured": bool(settings.gbizinfo_api_key),
    }


@app.get(
    "/companies/search",
    response_model=list[CompanySummary],
)
async def search_companies(
    name: str = Query(..., min_length=1),
):
    client = GBizInfoClient()

    return await client.search_companies(name)


@app.get(
    "/companies/{corporate_number}",
    response_model=CompanyDetail,
)
async def get_company(
    corporate_number: str = Path(
        ...,
        pattern=r"^\d{13}$",
    ),
):
    client = GBizInfoClient()
    company = await client.get_company(corporate_number)

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    return company


@app.get("/edinet/documents")
async def get_edinet_documents(
    date: str = Query(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
):
    client = EdinetClient()

    return await client.get_documents(date)


@app.get("/edinet/code/{corporate_number}")
async def get_edinet_code(
    corporate_number: str = Path(
        ...,
        pattern=r"^\d{13}$",
    ),
):
    client = EdinetClient()

    edinet_code = await client.get_edinet_code(corporate_number)

    if edinet_code is None:
        raise HTTPException(
            status_code=404,
            detail="EDINET code not found",
        )

    return {
        "corporate_number": corporate_number,
        "edinet_code": edinet_code,
    }


@app.get("/edinet/annual-report/{edinet_code}")
async def get_annual_report(
    edinet_code: str,
    date: str = Query(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
):
    client = EdinetClient()

    document = await client.find_annual_report(
        edinet_code=edinet_code,
        date=date,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Annual report not found",
        )

    return document


@app.get("/edinet/documents/{doc_id}/csv-files")
async def get_edinet_csv_files(
    doc_id: str,
):
    client = EdinetClient()

    try:
        files = await client.get_csv_file_list(doc_id)
    except zipfile.BadZipFile as exc:
        raise HTTPException(
            status_code=502,
            detail="EDINET returned an invalid ZIP file",
        ) from exc

    return {
        "doc_id": doc_id,
        "files": files,
    }


@app.get("/edinet/documents/{doc_id}/csv-preview")
async def get_edinet_csv_preview(
    doc_id: str,
    limit: int = Query(
        20,
        ge=1,
        le=100,
    ),
):
    client = EdinetClient()

    return await client.get_main_report_csv_preview(
        doc_id=doc_id,
        limit=limit,
    )


@app.get("/edinet/documents/{doc_id}/csv-search")
async def search_edinet_csv(
    doc_id: str,
    keyword: str = Query(
        ...,
        min_length=1,
    ),
):
    client = EdinetClient()

    results = await client.search_main_report_csv(
        doc_id=doc_id,
        keyword=keyword,
    )

    return {
        "doc_id": doc_id,
        "keyword": keyword,
        "count": len(results),
        "results": results,
    }


@app.get(
    "/edinet/documents/{doc_id}/financial-history",
    response_model=FinancialHistory,
)
async def get_edinet_financial_history(
    doc_id: str,
) -> FinancialHistory:
    client = EdinetClient()

    return await client.get_financial_history(doc_id)


@app.get(
    "/edinet/documents/{doc_id}/financial-trend",
    response_model=FinancialTrend,
)
async def get_edinet_financial_trend(
    doc_id: str,
) -> FinancialTrend:
    client = EdinetClient()

    history = await client.get_financial_history(doc_id)

    return company_analysis_service.build_financial_trend(history)


@app.get(
    "/research/company",
    response_model=CompanyResearchResult,
)
async def research_company(
    name: str = Query(
        ...,
        min_length=1,
    ),
):
    try:
        return await company_research_service.research(
            name=name,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@app.post(
    "/research/company/analysis",
    response_model=CompanyResearchAnalysisResult,
)
async def analyze_company(
    name: str = Query(
        ...,
        min_length=1,
    ),
) -> CompanyResearchAnalysisResult:
    total_start = perf_counter()

    research_start = perf_counter()

    try:
        research = await company_research_service.research(
            name=name,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    logger.info(
        "company research: %.2fs",
        perf_counter() - research_start,
    )

    calculation_start = perf_counter()

    derived_financials = company_analysis_service.calculate_derived_financials(research)

    display_financials = company_analysis_service.build_financial_display_values(
        research
    )

    logger.info(
        "financial calculations: %.2fs",
        perf_counter() - calculation_start,
    )

    history_start = perf_counter()

    client = EdinetClient()

    financial_history = await client.get_financial_history(
        research.annual_report.doc_id
    )

    logger.info(
        "financial history: %.2fs",
        perf_counter() - history_start,
    )

    trend_start = perf_counter()

    financial_trend = company_analysis_service.build_financial_trend(financial_history)

    logger.info(
        "financial trend: %.2fs",
        perf_counter() - trend_start,
    )

    analysis_start = perf_counter()

    analysis = await company_analysis_service.analyze(
        research=research,
        display_financials=display_financials,
        financial_trend=financial_trend,
    )

    logger.info(
        "AI analysis: %.2fs",
        perf_counter() - analysis_start,
    )

    logger.info(
        "total analysis: %.2fs",
        perf_counter() - total_start,
    )

    return CompanyResearchAnalysisResult(
        research=research,
        derived_financials=derived_financials,
        display_financials=display_financials,
        financial_trend=financial_trend,
        analysis=analysis,
    )


@app.get(
    "/edinet/document-index",
    response_model=list[EdinetDocument],
)
async def get_edinet_document_index(
    date: str = Query(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
):
    client = EdinetClient()

    return await client.get_document_list(date)


@app.get("/databricks/health")
def databricks_health():
    client = DatabricksClient()

    result = client.test_connection()

    return {
        "status": "ok",
        "result": result,
    }


@app.get("/databricks/namespace")
def databricks_namespace():
    client = DatabricksClient()

    return client.get_current_namespace()


@app.post("/databricks/edinet-documents/table")
def create_edinet_documents_table():
    databricks_edinet_document_repository.create_table()

    return {
        "status": "ok",
        "table": (databricks_edinet_document_repository.table_name),
    }


@app.get("/databricks/edinet-documents/count")
def count_databricks_edinet_documents():
    count = databricks_edinet_document_repository.count()

    return {
        "table": (databricks_edinet_document_repository.table_name),
        "count": count,
    }


@app.post("/databricks/edinet-documents/sync-range")
async def sync_edinet_documents_range(
    start_date: date,
    end_date: date,
    force: bool = False,
) -> EdinetSyncResult:
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date",
        )

    max_days = 31

    total_days = (end_date - start_date).days + 1

    if total_days > max_days:
        raise HTTPException(
            status_code=400,
            detail=f"Date range must be {max_days} days or less",
        )

    return await edinet_sync_service.sync_range(
        start_date=start_date,
        end_date=end_date,
        force=force,
    )


@app.post("/databricks/edinet-documents/sync-latest")
async def sync_edinet_documents_latest() -> EdinetSyncLatestResult:
    try:
        return await edinet_sync_service.sync_latest(max_days=7)
    except LookupError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
