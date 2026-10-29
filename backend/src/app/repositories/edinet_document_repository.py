from typing import Protocol

from app.models.edinet import EdinetDocument


class EdinetDocumentRepositoryProtocol(Protocol):
    def find_latest_annual_report(
        self,
        edinet_code: str,
    ) -> EdinetDocument | None: ...

    def find_annual_report_doc_id_by_period_end_year(
        self,
        *,
        edinet_code: str,
        year: int,
    ) -> str | None: ...
