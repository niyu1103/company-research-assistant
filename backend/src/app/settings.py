from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    edinet_api_key: str = ""
    gbizinfo_api_key: str = ""

    databricks_server_hostname: str = ""
    databricks_http_path: str = ""
    databricks_token: str = ""
    databricks_catalog: str = "workspace"
    databricks_schema: str = "default"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
