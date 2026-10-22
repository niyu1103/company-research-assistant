from app.models.document_chunk import DocumentChunk


class DocumentChunkingService:
    def __init__(
        self,
        *,
        chunk_size: int = 1_000,
        overlap: int = 150,
    ) -> None:
        self._validate_config(
            chunk_size=chunk_size,
            overlap=overlap,
        )

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(
        self,
        *,
        doc_id: str,
        edinet_code: str,
        section: str,
        text: str | None,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> list[DocumentChunk]:
        if text is None:
            return []

        text = text.strip()

        if not text:
            return []

        effective_chunk_size = chunk_size if chunk_size is not None else self.chunk_size

        effective_overlap = overlap if overlap is not None else self.overlap

        self._validate_config(
            chunk_size=effective_chunk_size,
            overlap=effective_overlap,
        )

        chunks: list[DocumentChunk] = []

        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(
                start + effective_chunk_size,
                len(text),
            )

            content = text[start:end].strip()

            if content:
                chunks.append(
                    DocumentChunk(
                        chunk_id=(f"{doc_id}_{section}_{chunk_index}"),
                        doc_id=doc_id,
                        edinet_code=edinet_code,
                        section=section,
                        chunk_index=chunk_index,
                        content=content,
                    )
                )

            if end >= len(text):
                break

            start = end - effective_overlap

            chunk_index += 1

        return chunks

    def _validate_config(
        self,
        *,
        chunk_size: int,
        overlap: int,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")

        if overlap < 0:
            raise ValueError("overlap must be 0 or greater")

        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
