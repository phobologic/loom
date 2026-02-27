from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./loom.db"
    environment: str = "local"
    debug: bool = True
    session_secret_key: str = "dev-secret-change-me"

    # OAuth providers
    google_client_id: str = ""
    google_client_secret: str = ""
    discord_client_id: str = ""
    discord_client_secret: str = ""

    # Anthropic API
    anthropic_api_key: str = ""

    # AI model assignments — configurable per feature category.
    # Lightweight tasks (classification) use a smaller/cheaper model.
    # Creative tasks (oracle, synthesis, world doc) use a more capable model.
    ai_model_classification: str = "claude-haiku-4-5-20251001"
    ai_model_creative: str = "claude-sonnet-4-6"

    # How many recent canon beats to include in scene-level AI context.
    ai_context_beat_history_window: int = 10

    # Email notifications — master switch defaults to False until an SMTP provider is configured.
    email_enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_address: str = "loom@example.com"
    smtp_use_tls: bool = True
    # Base URL used to build absolute links inside emails.
    app_base_url: str = "http://localhost:8000"
    # Shared secret for the POST /notifications/send-digests cron endpoint.
    # Leave empty to disable the endpoint entirely.
    digest_api_key: str = ""


settings = Settings()
