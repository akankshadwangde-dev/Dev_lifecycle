from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime settings. Override with STUDIO_* environment variables or backend/.env."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_prefix="STUDIO_", extra="ignore")

    # Demo mode seeds sample work items, Confluence pages and SAP code, and uses
    # sample connectors and a sample model wherever no real one is configured.
    demo_mode: bool = True
    data_dir: Path = BACKEND_DIR / "data"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    default_project: str = "O2C Rollout"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'studio.db'}"

    @property
    def checkpoint_path(self) -> Path:
        return self.data_dir / "flows.db"

    @property
    def knowledge_path(self) -> Path:
        return self.data_dir / "knowledge.db"


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
