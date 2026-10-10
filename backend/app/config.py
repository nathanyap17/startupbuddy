"""Settings. Local vs cloud differs only by env vars (see docs/CREDENTIALS.md)."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://startupbuddy:startupbuddy@localhost:5433/startupbuddy"
    google_cloud_project: str = "dormathon-workspace-1"
    google_cloud_location: str = "global"
    gemini_model: str = "gemini-3.5-flash"
    thinking_level: str = "LOW"
    maps_api_key: str = ""
    mcp_api_key: str = ""
    public_base_url: str = "http://localhost:8000"
    frontend_origin: str = "http://localhost:5173"
    agent_turn_timeout_s: int = 90
    workbuddy_task_deadline_s: int = 300
    gws_token_file: str = "token.json"
    gws_client_secret_file: str = "client_secret.json"
    artifact_bucket: str = ""
    knowledge_dir: str = str(BACKEND_DIR.parent / "knowledge")
    timezone: str = "Asia/Kuching"


settings = Settings()

# ADK / google-genai read these from the environment (Vertex AI via ADC).
import os  # noqa: E402

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", settings.google_cloud_project)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", settings.google_cloud_location)
