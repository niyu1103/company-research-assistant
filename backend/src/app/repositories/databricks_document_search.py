from databricks.ai_search.client import AISearchClient  # type: ignore[import-untyped]

from app.models.ai_search import (
    AISearchChunkRow,
    AISearchResponse,
)
from app.models.document_chunk import RetrievedDocumentChunk
from app.settings import get_settings


class DatabricksDocumentSearchRepository:
    def __init__(
        self,
        endpoint_name: str,
    ) -> None:
        settings = get_settings()

        workspace_url = f"https://{settings.databricks_server_hostname}"

        self.index_name = (
            f"{settings.databricks_catalog}."
            f"{settings.databricks_schema}."
            "edinet_document_chunks_index"
        )

        client = AISearchClient(
            workspace_url=workspace_url,
            personal_access_token=settings.databricks_token,
        )

        self.index = client.get_index(
            endpoint_name=endpoint_name,
            index_name=self.index_name,
        )

    def search(
        self,
        *,
        query_text: str,
        edinet_code: str,
        doc_id: str,
        num_results: int = 5,
    ) -> list[RetrievedDocumentChunk]:
        if num_results <= 0:
            raise ValueError("num_results must be greater than 0")

        response = AISearchResponse.model_validate(
            self.index.similarity_search(
                query_text=query_text,
                columns=[
                    "chunk_id",
                    "doc_id",
                    "edinet_code",
                    "section",
                    "chunk_index",
                    "content",
                ],
                filters={
                    "edinet_code": edinet_code,
                    "doc_id": doc_id,
                },
                num_results=num_results,
                query_type="hybrid",
            )
        )

        expected_columns = (
            "chunk_id",
            "doc_id",
            "edinet_code",
            "section",
            "chunk_index",
            "content",
            "score",
        )

        actual_columns = tuple(column.name for column in response.manifest.columns)

        if actual_columns != expected_columns:
            raise RuntimeError(
                f"Unexpected AI Search response columns: {actual_columns}"
            )

        chunks: list[RetrievedDocumentChunk] = []

        for raw_row in response.result.data_array:
            row = AISearchChunkRow.model_validate(raw_row).root

            chunks.append(
                RetrievedDocumentChunk(
                    chunk_id=row[0],
                    doc_id=row[1],
                    edinet_code=row[2],
                    section=row[3],
                    chunk_index=row[4],
                    content=row[5],
                    score=row[6],
                )
            )

        return chunks
