from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App
    environment: str = "development"
    port: int = 8000
    database_url: str = "sqlite:///./data/documind.db"
    frontend_base_url: str = "http://127.0.0.1:3000"
    
    # Models / AI
    openai_api_key: str = ""
    gemini_api_key: str = ""
    
    # Auth
    session_cookie_name: str = "dokukit_session"
    session_max_age_days: int = 30
    session_cookie_secure: bool | None = None
    session_cookie_samesite: str = "lax"
    session_cookie_domain: str | None = None
    auth_rate_limit_window_seconds: int = 900
    auth_rate_limit_attempts: int = 10
    sign_up_rate_limit_window_seconds: int = 3600
    sign_up_rate_limit_attempts: int = 5
    query_rate_limit_window_seconds: int = 60
    query_rate_limit_attempts: int = 60
    upload_rate_limit_window_seconds: int = 600
    upload_rate_limit_attempts: int = 12
    max_upload_size_bytes: int = 50 * 1024 * 1024
    max_question_length: int = 5000
    max_note_length: int = 20000
    max_notebook_title_length: int = 160

    # Storage
    faiss_index_path: str = "./data/faiss/index.bin"
    pdf_upload_dir: str = "./data/uploads/"

    @field_validator("session_cookie_samesite", mode="before")
    @classmethod
    def normalize_session_cookie_samesite(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("SESSION_COOKIE_SAMESITE must be one of: lax, strict, none.")
        return normalized

    @property
    def resolved_session_cookie_secure(self) -> bool:
        if self.session_cookie_secure is not None:
            return self.session_cookie_secure
        return self.environment.lower() == "production"

    @property
    def session_max_age_seconds(self) -> int:
        return self.session_max_age_days * 24 * 60 * 60

    @property
    def trusted_frontend_origins(self) -> set[str]:
        frontend_origin = urlparse(self.frontend_base_url).scheme + "://" + urlparse(self.frontend_base_url).netloc
        return {
            frontend_origin,
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://127.0.0.1:3001",
            "http://localhost:3001",
        }

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
