import re

from databricks import sql

from app.models.document_chunk import DocumentChunk
from app.settings import get_settings


class DatabricksDocumentChunkRepository:
    def __init__(
        self,
        *,
        table_basename: str = "edinet_document_chunks",
    ) -> None:
        if not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*",
            table_basename,
        ):
            raise ValueError("table_basename contains invalid characters")

        settings = get_settings()

        self.server_hostname = settings.databricks_server_hostname
        self.http_path = settings.databricks_http_path
        self.access_token = settings.databricks_token

        self.catalog = settings.databricks_catalog
        self.schema = settings.databricks_schema

        self.table_basename = table_basename

    @property
    def table_name(self) -> str:
        return f"{self.catalog}.{self.schema}.{self.table_basename}"

    def create_table(self) -> None:
        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        chunk_id STRING,
                        doc_id STRING,
                        edinet_code STRING,
                        section STRING,
                        chunk_index INT,
                        content STRING
                    )
                    USING DELTA
                    TBLPROPERTIES (
                        delta.enableChangeDataFeed = true
                    )
                """)

    def replace_for_document(
        self,
        doc_id: str,
        chunks: list[DocumentChunk],
    ) -> None:
        if any(chunk.doc_id != doc_id for chunk in chunks):
            raise ValueError("All chunks must belong to the specified doc_id")

        self.create_table()

        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    DELETE FROM {self.table_name}
                    WHERE doc_id = ?
                    """,
                    [doc_id],
                )

                if not chunks:
                    return

                batch_size = 500

                for start in range(
                    0,
                    len(chunks),
                    batch_size,
                ):
                    batch = chunks[start : start + batch_size]

                    placeholders = ", ".join(
                        ["(" + ", ".join(["?"] * 6) + ")" for _ in batch]
                    )

                    insert_sql = f"""
                        INSERT INTO {self.table_name} (
                            chunk_id,
                            doc_id,
                            edinet_code,
                            section,
                            chunk_index,
                            content
                        )
                        VALUES {placeholders}
                    """

                    parameters = []

                    for chunk in batch:
                        parameters.extend(
                            [
                                chunk.chunk_id,
                                chunk.doc_id,
                                chunk.edinet_code,
                                chunk.section,
                                chunk.chunk_index,
                                chunk.content,
                            ]
                        )

                    cursor.execute(
                        insert_sql,
                        parameters,
                    )
