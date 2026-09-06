from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(Path.cwd().parent / ".env", Path.cwd() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    fred_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FRED_API_KEY", "FED_API"),
    )
    bea_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BEA_API_KEY", "BEA_API"),
    )
    census_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CENSUS_API_KEY", "CENSUS_API"),
    )
    fmp_api_key: str | None = Field(default=None, validation_alias="FMP_API_KEY")

    mcp_transport: str = "stdio"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000
    database_path: Path = Path("./data/us_economy.sqlite3")
    refresh_time: str = "18:00"
    refresh_timezone: str = "America/New_York"
    refresh_on_start: bool = True
    source_concurrency: int = 3
    http_timeout_seconds: float = 30
    max_retries: int = 3
    max_series_points: int = 5000
    enable_manual_refresh: bool = True
    cache_ttl_hours: int = 24

