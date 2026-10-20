from databricks import sql

from app.settings import get_settings


class DatabricksClient:
    def __init__(self) -> None:
        settings = get_settings()

        self.server_hostname = settings.databricks_server_hostname
        self.http_path = settings.databricks_http_path
        self.access_token = settings.databricks_token

    def test_connection(self) -> int:
        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

                row = cursor.fetchone()

                if row is None:
                    raise RuntimeError("Databricks returned no result")

                return int(row[0])

    def get_current_namespace(self) -> dict[str, str]:
        with sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        current_catalog(),
                        current_schema()
                    """)

                row = cursor.fetchone()

                if row is None:
                    raise RuntimeError("Databricks returned no namespace")

                return {
                    "catalog": str(row[0]),
                    "schema": str(row[1]),
                }
