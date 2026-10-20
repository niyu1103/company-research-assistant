from databricks import sql

from app.models.edinet import EdinetDocument
from app.settings import get_settings


class DatabricksEdinetDocumentRepository:
    def __init__(self) -> None:
        settings = get_settings()

        self.server_hostname = settings.databricks_server_hostname
        self.http_path = settings.databricks_http_path
        self.access_token = settings.databricks_token

        self.catalog = settings.databricks_catalog
        self.schema = settings.databricks_schema

    @property
    def table_name(self) -> str:
        return f"{self.catalog}.{self.schema}.edinet_documents"

    def create_table(self) -> None:
        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        doc_id STRING,
                        edinet_code STRING,
                        sec_code STRING,
                        corporate_number STRING,
                        filer_name STRING,
                        doc_type_code STRING,
                        form_code STRING,
                        ordinance_code STRING,
                        period_start DATE,
                        period_end DATE,
                        submitted_at TIMESTAMP,
                        description STRING,
                        xbrl_available BOOLEAN,
                        pdf_available BOOLEAN,
                        csv_available BOOLEAN,
                        source_updated_at TIMESTAMP,
                        fetched_at TIMESTAMP
                    )
                    USING DELTA
                    """)

    def replace_for_date(
        self,
        sync_date: str,
        documents: list[EdinetDocument],
    ) -> None:
        if not documents:
            return

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
                    WHERE CAST(submitted_at AS DATE) = ?
                    """,
                    [sync_date],
                )

                batch_size = 500

                for start in range(
                    0,
                    len(documents),
                    batch_size,
                ):
                    batch = documents[start : start + batch_size]

                    placeholders = ", ".join(
                        ["(" + ", ".join(["?"] * 17) + ")" for _ in batch]
                    )

                    insert_sql = f"""
                        INSERT INTO {self.table_name} (
                            doc_id,
                            edinet_code,
                            sec_code,
                            corporate_number,
                            filer_name,
                            doc_type_code,
                            form_code,
                            ordinance_code,
                            period_start,
                            period_end,
                            submitted_at,
                            description,
                            xbrl_available,
                            pdf_available,
                            csv_available,
                            source_updated_at,
                            fetched_at
                        )
                        VALUES {placeholders}
                    """

                    parameters = []

                    for document in batch:
                        parameters.extend(
                            [
                                document.doc_id,
                                document.edinet_code,
                                document.sec_code,
                                document.corporate_number,
                                document.filer_name,
                                document.doc_type_code,
                                document.form_code,
                                document.ordinance_code,
                                document.period_start,
                                document.period_end,
                                document.submitted_at,
                                document.description,
                                document.xbrl_available,
                                document.pdf_available,
                                document.csv_available,
                                document.source_updated_at,
                                document.fetched_at,
                            ]
                        )

                    cursor.execute(
                        insert_sql,
                        parameters,
                    )

    def find_latest_annual_report(
        self,
        edinet_code: str,
    ) -> EdinetDocument | None:
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
                        edinet_code,
                        sec_code,
                        corporate_number,
                        filer_name,
                        doc_type_code,
                        form_code,
                        ordinance_code,
                        period_start,
                        period_end,
                        submitted_at,
                        description,
                        xbrl_available,
                        pdf_available,
                        csv_available,
                        source_updated_at,
                        fetched_at
                    FROM {self.table_name}
                    WHERE edinet_code = ?
                      AND doc_type_code = '120'
                    ORDER BY submitted_at DESC
                    LIMIT 1
                    """,
                    [edinet_code],
                )

                row = cursor.fetchone()

                if row is None:
                    return None

                return EdinetDocument(
                    doc_id=row[0],
                    edinet_code=row[1],
                    sec_code=row[2],
                    corporate_number=row[3],
                    filer_name=row[4],
                    doc_type_code=row[5],
                    form_code=row[6],
                    ordinance_code=row[7],
                    period_start=row[8],
                    period_end=row[9],
                    submitted_at=row[10],
                    description=row[11],
                    xbrl_available=row[12],
                    pdf_available=row[13],
                    csv_available=row[14],
                    source_updated_at=row[15],
                    fetched_at=row[16],
                )

    def count(self) -> int:
        self.create_table()

        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT COUNT(*)
                    FROM {self.table_name}
                    """)

                row = cursor.fetchone()

                if row is None:
                    return 0

                return int(row[0])

    @property
    def sync_history_table_name(self) -> str:
        return f"{self.catalog}.{self.schema}.edinet_sync_history"

    def create_sync_history_table(self) -> None:
        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                  CREATE TABLE IF NOT EXISTS
                  {self.sync_history_table_name} (
                      sync_date DATE,
                      document_count INT,
                      synced_at TIMESTAMP
                  )
                  USING DELTA
                  """)

    def is_date_synced(
        self,
        sync_date: str,
    ) -> bool:
        self.create_sync_history_table()

        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM {self.sync_history_table_name}
                    WHERE sync_date = ?
                    """,
                    [sync_date],
                )

                row = cursor.fetchone()

                return bool(row and row[0] > 0)

    def save_sync_history(
        self,
        sync_date: str,
        document_count: int,
    ) -> None:
        self.create_sync_history_table()

        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    MERGE INTO
                        {self.sync_history_table_name} AS target
                    USING (
                        SELECT
                            CAST(? AS DATE) AS sync_date,
                            ? AS document_count,
                            current_timestamp() AS synced_at
                    ) AS source
                    ON target.sync_date = source.sync_date

                    WHEN MATCHED THEN
                        UPDATE SET
                            document_count =
                                source.document_count,
                            synced_at =
                                source.synced_at

                    WHEN NOT MATCHED THEN
                        INSERT (
                            sync_date,
                            document_count,
                            synced_at
                        )
                        VALUES (
                            source.sync_date,
                            source.document_count,
                            source.synced_at
                        )
                    """,
                    [
                        sync_date,
                        document_count,
                    ],
                )

    def get_latest_sync_date(self):
        self.create_sync_history_table()

        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT MAX(sync_date)
                    FROM {self.sync_history_table_name}
                    """)

                row = cursor.fetchone()

                if row is None:
                    return None

                return row[0]

    def get_synced_dates(
        self,
        start_date: str,
        end_date: str,
    ) -> set[str]:
        self.create_sync_history_table()

        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT sync_date
                    FROM {self.sync_history_table_name}
                    WHERE sync_date BETWEEN ? AND ?
                    """,
                    [
                        start_date,
                        end_date,
                    ],
                )

                return {str(row[0]) for row in cursor.fetchall()}
