from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "FastAPI App"
    api_prefix: str = ""

    database_url: str = ""

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
    telegram_moderator_chat_id: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
