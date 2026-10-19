from fastapi import FastAPI, HTTPException, Path, Query

from app.clients.gbizinfo import GBizInfoClient
from app.models.company import CompanyDetail, CompanySummary
from app.settings import get_settings
from app.clients.edinet import EdinetClient



app = FastAPI(
    title="Company Research Assistant API",
    version="0.1.0",
)


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

    edinet_code = await client.get_edinet_code(
        corporate_number
    )

    if edinet_code is None:
        raise HTTPException(
            status_code=404,
            detail="EDINET code not found",
        )

    return {
        "corporate_number": corporate_number,
        "edinet_code": edinet_code,
    }