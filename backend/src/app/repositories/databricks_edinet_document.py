import logging
from time import perf_counter

from databricks import sql

from app.models.edinet import EdinetDocument
from app.settings import get_settings

logger = logging.getLogger("uvicorn.error")


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
                        fetched_at TIMESTAMP,
                        source_date DATE,
                        withdrawal_status STRING,
                        doc_info_edit_status STRING,
                        disclosure_status STRING,
                        legal_status STRING
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
                doc_id_placeholders = ", ".join("?" for _ in documents)
                cursor.execute(
                    f"""
                    DELETE FROM {self.table_name}
                    WHERE source_date = CAST(? AS DATE)
                    OR (
                            source_date IS NULL
                            AND CAST(submitted_at AS DATE) = CAST(? AS DATE)
                    )
                    OR doc_id IN ({doc_id_placeholders})
                    """,
                    [
                        sync_date,
                        sync_date,
                        *[document.doc_id for document in documents],
                    ],
                )

                batch_size = 400

                for start in range(
                    0,
                    len(documents),
                    batch_size,
                ):
                    batch = documents[start : start + batch_size]

                    placeholders = ", ".join(
                        ["(" + ", ".join(["?"] * 22) + ")" for _ in batch]
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
                            fetched_at,
                            withdrawal_status,
                            doc_info_edit_status,
                            disclosure_status,
                            legal_status,
                            source_date
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
                                document.withdrawal_status,
                                document.doc_info_edit_status,
                                document.disclosure_status,
                                document.legal_status,
                                document.source_date,
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
        connect_start = perf_counter()

        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            logger.info(
                "databricks - connect: %.2fs",
                perf_counter() - connect_start,
            )

            with connection.cursor() as cursor:
                query_start = perf_counter()

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
                        fetched_at,
                        source_date,
                        withdrawal_status,
                        doc_info_edit_status,
                        disclosure_status,
                        legal_status
                    FROM {self.table_name}
                    WHERE edinet_code = ?
                    AND doc_type_code = '120'
                    ORDER BY submitted_at DESC
                    LIMIT 1
                    """,
                    [edinet_code],
                )

                row = cursor.fetchone()

                logger.info(
                    "databricks - latest annual report query: %.2fs",
                    perf_counter() - query_start,
                )

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
                    source_date=row[17],
                    withdrawal_status=row[18],
                    doc_info_edit_status=row[19],
                    disclosure_status=row[20],
                    legal_status=row[21],
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

    def replace_dates_and_save_history(
        self,
        documents_by_date: dict[
            str,
            list[EdinetDocument],
        ],
    ) -> None:
        if not documents_by_date:
            return

        sync_dates = sorted(documents_by_date)

        documents_by_id: dict[str, EdinetDocument] = {}

        for sync_date in sync_dates:
            for document in documents_by_date[sync_date]:
                documents_by_id[document.doc_id] = document

        all_documents = list(documents_by_id.values())

        doc_ids = [document.doc_id for document in all_documents]

        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS
                    {self.table_name} (
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
                        fetched_at TIMESTAMP,
                        source_date DATE,
                        withdrawal_status STRING,
                        doc_info_edit_status STRING,
                        disclosure_status STRING,
                        legal_status STRING
                    )
                    USING DELTA
                    """)

                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS
                    {self.sync_history_table_name} (
                        sync_date DATE,
                        document_count INT,
                        synced_at TIMESTAMP
                    )
                    USING DELTA
                    """)

                delete_placeholders = ", ".join("CAST(? AS DATE)" for _ in sync_dates)

                cursor.execute(
                    f"""
                    DELETE FROM {self.table_name}
                    WHERE source_date IN ({delete_placeholders})
                    OR (
                        source_date IS NULL
                        AND CAST(submitted_at AS DATE) IN ({delete_placeholders})
                    )
                    """,
                    [
                        *sync_dates,
                        *sync_dates,
                    ],
                )

                doc_id_batch_size = 5000

                for start in range(
                    0,
                    len(doc_ids),
                    doc_id_batch_size,
                ):
                    doc_id_batch = doc_ids[start : start + doc_id_batch_size]
                    doc_id_placeholders = ", ".join("?" for _ in doc_id_batch)

                    cursor.execute(
                        f"""
                        DELETE FROM {self.table_name}
                        WHERE doc_id IN ({doc_id_placeholders})
                        """,
                        doc_id_batch,
                    )

                batch_size = 400

                for start in range(
                    0,
                    len(all_documents),
                    batch_size,
                ):
                    batch = all_documents[start : start + batch_size]

                    placeholders = ", ".join(
                        ["(" + ", ".join(["?"] * 22) + ")" for _ in batch]
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
                            fetched_at,
                            withdrawal_status,
                            doc_info_edit_status,
                            disclosure_status,
                            legal_status,
                            source_date
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
                                document.withdrawal_status,
                                document.doc_info_edit_status,
                                document.disclosure_status,
                                document.legal_status,
                                document.source_date,
                            ]
                        )

                    cursor.execute(
                        insert_sql,
                        parameters,
                    )

                history_selects = []
                history_parameters = []

                for sync_date in sync_dates:
                    history_selects.append(
                        """
                        SELECT
                            CAST(? AS DATE) AS sync_date,
                            ? AS document_count
                        """
                    )

                    history_parameters.extend(
                        [
                            sync_date,
                            len(documents_by_date[sync_date]),
                        ]
                    )

                history_source_sql = "\nUNION ALL\n".join(history_selects)

                cursor.execute(
                    f"""
                    MERGE INTO
                        {self.sync_history_table_name}
                        AS target
                    USING (
                        {history_source_sql}
                    ) AS source
                    ON target.sync_date =
                        source.sync_date

                    WHEN MATCHED THEN
                        UPDATE SET
                            document_count =
                                source.document_count,
                            synced_at =
                                current_timestamp()

                    WHEN NOT MATCHED THEN
                        INSERT (
                            sync_date,
                            document_count,
                            synced_at
                        )
                        VALUES (
                            source.sync_date,
                            source.document_count,
                            current_timestamp()
                        )
                    """,
                    history_parameters,
                )
