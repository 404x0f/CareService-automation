from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    project_name: str = "FastAPI App"
    api_prefix: str = ""

    database_host: str = "localhost"
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_port: int

    debounce_seconds: int = 0
    avito_account_id: int = 0
    avito_access_token: str = ""
    avito_client_id: str = ""
    avito_client_secret: str = ""

    openai_api_key: str = ""
    openai_base_url: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: str = ""

    telegram_bot_token: str = ""
    telegram_moderator_chat_ids: list[int] = []

    @property
    def resolved_database_url(self) -> URL:
        if self.database_host:
            return URL.create(
                "postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.database_host,
                port=self.postgres_port,
                database=self.postgres_db,
            )
        raise ValueError("DATABASE_HOST must not be empty")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
