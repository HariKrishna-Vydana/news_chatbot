from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

dotenv_path = Path(__file__).parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path, override=True)


class ChatBackendSettings(BaseSettings):
    host: str = Field(default="0.0.0.0", alias="CHAT_BACKEND_HOST")
    port: int = Field(default=8000, alias="CHAT_BACKEND_PORT")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")

    google_search_api_key: str = Field(default="", alias="GOOGLE_SEARCH_API_KEY")
    google_search_engine_id: str = Field(default="", alias="GOOGLE_SEARCH_ENGINE_ID")

    model_config = SettingsConfigDict(
        env_file=str(dotenv_path) if dotenv_path.exists() else None,
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",
    )


settings = ChatBackendSettings()
