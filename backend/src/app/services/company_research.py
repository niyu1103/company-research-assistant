from app.clients.edinet import EdinetClient
from app.clients.gbizinfo import GBizInfoClient
from app.models.research import AnnualReportInfo, CompanyResearchResult
from app.repositories.edinet_document_repository import (
    EdinetDocumentRepositoryProtocol,
)


class CompanyResearchService:
    def __init__(
        self,
        edinet_document_repository: (EdinetDocumentRepositoryProtocol),
    ) -> None:
        self.gbizinfo = GBizInfoClient()
        self.edinet = EdinetClient()
        self.edinet_documents = edinet_document_repository

    async def research(
        self,
        name: str,
    ) -> CompanyResearchResult:
        companies = await self.gbizinfo.search_companies(name)

        if not companies:
            raise LookupError(f"Company not found: {name}")

        company_summary = companies[0]

        company = await self.gbizinfo.get_company(company_summary.corporate_number)

        if company is None:
            raise LookupError(f"Company detail not found: {name}")

        edinet_code = await self.edinet.get_edinet_code(company.corporate_number)

        if edinet_code is None:
            raise LookupError(f"EDINET code not found: {name}")

        document = self.edinet_documents.find_latest_annual_report(edinet_code)

        if document is None:
            raise LookupError(
                (f"Annual report not found in document index: {edinet_code}")
            )

        financials = await self.edinet.get_financial_summary(document.doc_id)

        annual_report = AnnualReportInfo(
            doc_id=document.doc_id,
            edinet_code=edinet_code,
            sec_code=document.sec_code,
            period_start=document.period_start,
            period_end=document.period_end,
            submitted_at=document.submitted_at,
            description=document.description,
        )

        return CompanyResearchResult(
            company=company,
            edinet_code=edinet_code,
            annual_report=annual_report,
            financials=financials,
        )
