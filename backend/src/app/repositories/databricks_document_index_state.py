from databricks import sql

from app.models.document_freshness import (
    DocumentIndexState,
)
from app.settings import get_settings


class DatabricksDocumentIndexStateRepository:
    def __init__(self) -> None:
        settings = get_settings()

        self.server_hostname = settings.databricks_server_hostname
        self.http_path = settings.databricks_http_path
        self.access_token = settings.databricks_token

        self.catalog = settings.databricks_catalog
        self.schema = settings.databricks_schema

    @property
    def table_name(self) -> str:
        return f"{self.catalog}.{self.schema}.edinet_document_index_state"

    def create_table(self) -> None:
        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS
                    {self.table_name} (
                        doc_id STRING,
                        version STRING,
                        indexed_at TIMESTAMP
                    )
                    USING DELTA
                    """
                )

    def find_by_doc_id(
        self,
        doc_id: str,
    ) -> DocumentIndexState | None:
        self.create_table()

        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        doc_id,
                        version,
                        indexed_at
                    FROM {self.table_name}
                    WHERE doc_id = ?
                    LIMIT 1
                    """,
                    [doc_id],
                )

                row = cursor.fetchone()

                if row is None:
                    return None

                return DocumentIndexState(
                    doc_id=row[0],
                    version=row[1],
                    indexed_at=row[2],
                )

    def save(
        self,
        state: DocumentIndexState,
    ) -> None:
        self.create_table()

        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    MERGE INTO
                        {self.table_name} AS target
                    USING (
                        SELECT
                            ? AS doc_id,
                            ? AS version,
                            ? AS indexed_at
                    ) AS source
                    ON target.doc_id = source.doc_id

                    WHEN MATCHED THEN
                        UPDATE SET
                            version = source.version,
                            indexed_at =
                                source.indexed_at

                    WHEN NOT MATCHED THEN
                        INSERT (
                            doc_id,
                            version,
                            indexed_at
                        )
                        VALUES (
                            source.doc_id,
                            source.version,
                            source.indexed_at
                        )
                    """,
                    [
                        state.doc_id,
                        state.version,
                        state.indexed_at,
                    ],
                )
