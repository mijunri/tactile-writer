import json
from pathlib import Path

from pydantic_settings import BaseSettings

ROOT = Path(__file__).resolve().parents[2]
STATE_FILE = ROOT / "infra" / "state.json"


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


_state = _load_state()


class Settings(BaseSettings):
    tactile_api_base: str = _state.get("tactile_api_base", "https://cloudagentlab.com/api")
    tactile_service_email: str = ""
    tactile_service_password: str = ""
    tactile_workspace_id: int = int(_state.get("workspace_id") or 0)
    tactile_agent_id: int = int(_state.get("agent_id") or 0)
    moxie_upload_token: str = "change-me-upload-token"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 168
    database_url: str = "sqlite+aiosqlite:///./data/writer.db"
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
