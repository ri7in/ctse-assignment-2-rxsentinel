"""Centralized config loaded from environment variables."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Repo root = parent of backend/ = parent of this file's grandparent.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Runtime configuration loaded from environment + .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ollama_host: str = Field("http://localhost:11434", alias="OLLAMA_HOST")
    ollama_model: str = Field("qwen2.5:3b", alias="OLLAMA_MODEL")
    ollama_fallback_model: str = Field("llama3.2:3b", alias="OLLAMA_FALLBACK_MODEL")

    backend_host: str = Field("0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(8000, alias="BACKEND_PORT")

    rxnorm_base_url: str = Field("https://rxnav.nlm.nih.gov/REST", alias="RXNORM_BASE_URL")
    openfda_base_url: str = Field("https://api.fda.gov", alias="OPENFDA_BASE_URL")

    trace_dir: Path = Field(_REPO_ROOT / "backend" / "runs", alias="TRACE_DIR")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    temp_coordinator: float = Field(0.0, alias="LLM_TEMPERATURE_COORDINATOR")
    temp_parser: float = Field(0.1, alias="LLM_TEMPERATURE_PARSER")
    temp_analyzer: float = Field(0.1, alias="LLM_TEMPERATURE_ANALYZER")
    temp_communicator: float = Field(0.4, alias="LLM_TEMPERATURE_COMMUNICATOR")

    http_timeout: float = Field(10.0, alias="HTTP_TIMEOUT_SECONDS")
    http_retries: int = Field(3, alias="HTTP_MAX_RETRIES")

    cache_dir: Path = Field(_REPO_ROOT / "backend" / "data" / "cache", alias="CACHE_DIR")


settings = Settings()
settings.trace_dir.mkdir(parents=True, exist_ok=True)
settings.cache_dir.mkdir(parents=True, exist_ok=True)
