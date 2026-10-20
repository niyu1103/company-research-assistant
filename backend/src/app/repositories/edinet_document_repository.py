from typing import Protocol

from app.models.edinet import EdinetDocument


class EdinetDocumentRepositoryProtocol(Protocol):
    def find_latest_annual_report(
        self,
        edinet_code: str,
    ) -> EdinetDocument | None: ...
