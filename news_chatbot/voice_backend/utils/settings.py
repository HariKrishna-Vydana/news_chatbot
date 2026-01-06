from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

dotenv_path = Path(__file__).parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path, override=True)


class VoiceBackendSettings(BaseSettings):
    host: str = Field(default="0.0.0.0", alias="VOICE_BACKEND_HOST")
    port: int = Field(default=7860, alias="VOICE_BACKEND_PORT")

    transport_type: Literal["daily", "websocket", "smallwebrtc"] = Field(
        default="smallwebrtc", alias="TRANSPORT_TYPE"
    )

    tts_provider: Literal["elevenlabs", "cartesia", "openai"] = Field(
        default="cartesia", alias="TTS_PROVIDER"
    )

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    deepgram_api_key: str = Field(default="", alias="DEEPGRAM_API_KEY")
    daily_api_key: str = Field(default="", alias="DAILY_API_KEY")
    cartesia_api_key: str = Field(default="", alias="CARTESIA_API_KEY")
    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")

    chat_backend_host: str = Field(default="chat_backend", alias="CHAT_BACKEND_HOST")
    chat_backend_port: int = Field(default=8000, alias="CHAT_BACKEND_PORT")
    chat_timeout: int = Field(default=60, alias="CHAT_TIMEOUT")

    model_config = SettingsConfigDict(
        env_file=str(dotenv_path) if dotenv_path.exists() else None,
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",
    )


settings = VoiceBackendSettings()
