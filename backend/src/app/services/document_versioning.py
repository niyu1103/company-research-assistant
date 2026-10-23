import hashlib


class DocumentVersioningService:
    def create_version(
        self,
        *,
        doc_id: str,
        business_overview: str | None,
        business_risks: str | None,
    ) -> str:
        content = "\n".join(
            [
                doc_id,
                business_overview or "",
                business_risks or "",
            ]
        )

        return hashlib.sha256(content.encode("utf-8")).hexdigest()
