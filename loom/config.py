from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./loom.db"
    environment: str = "local"
    debug: bool = True
    session_secret_key: str = "dev-secret-change-me"

    # Anthropic API
    anthropic_api_key: str = ""

    # AI model assignments — configurable per feature category.
    # Lightweight tasks (classification) use a smaller/cheaper model.
    # Creative tasks (oracle, synthesis, world doc) use a more capable model.
    ai_model_classification: str = "claude-haiku-4-5-20251001"
    ai_model_creative: str = "claude-sonnet-4-6"

    # How many recent canon beats to include in scene-level AI context.
    ai_context_beat_history_window: int = 10


settings = Settings()
