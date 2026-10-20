from datetime import datetime

from app.models.edinet import EdinetDocument


class EdinetDocumentRepository:
    def __init__(self) -> None:
        self.documents: dict[str, EdinetDocument] = {}

    def save_all(
        self,
        documents: list[EdinetDocument],
    ) -> None:
        for document in documents:
            self.documents[document.doc_id] = document

    def find_latest_annual_report(
        self,
        edinet_code: str,
    ) -> EdinetDocument | None:
        annual_reports = [
            document
            for document in self.documents.values()
            if (document.edinet_code == edinet_code and document.doc_type_code == "120")
        ]

        if not annual_reports:
            return None

        return max(
            annual_reports,
            key=lambda document: document.submitted_at or datetime.min,
        )
