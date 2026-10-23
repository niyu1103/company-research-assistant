from datetime import timedelta

from databricks.ai_search.client import AISearchClient  # type: ignore[import-untyped]

from app.settings import get_settings


class DatabricksDocumentIndexSyncRepository:
    def __init__(
        self,
        *,
        endpoint_name: str,
        index_basename: str = ("edinet_document_chunks_index"),
    ) -> None:
        settings = get_settings()

        workspace_url = f"https://{settings.databricks_server_hostname}"

        index_name = (
            f"{settings.databricks_catalog}."
            f"{settings.databricks_schema}."
            f"{index_basename}"
        )

        client = AISearchClient(
            workspace_url=workspace_url,
            personal_access_token=(settings.databricks_token),
        )

        self.index = client.get_index(
            endpoint_name=endpoint_name,
            index_name=index_name,
        )

    def sync_and_wait(self) -> None:
        self.index.sync()

        self.index.wait_until_ready(
            wait_for_updates=True,
            timeout=timedelta(minutes=10),
        )
