from loguru import logger
from pipecat.services.ai_services import TTSService
from pipecat.utils.text.markdown_text_filter import MarkdownTextFilter
from utils.settings import settings


def create_tts_service() -> TTSService:
    text_filters = [MarkdownTextFilter()]
    provider = settings.tts_provider

    logger.info(f"Creating TTS service: {provider}")

    if provider == "elevenlabs":
        from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
        return ElevenLabsTTSService(
            api_key=settings.elevenlabs_api_key,
            voice_id="pNInz6obpgDQGcFmaJgB",  # Adam
            text_filters=text_filters,
        )

    elif provider == "cartesia":
        from pipecat.services.cartesia.tts import CartesiaTTSService
        return CartesiaTTSService(
            api_key=settings.cartesia_api_key,
            voice_id="71a7ad14-091c-4e8e-a314-022ece01c121",  # British Reading Lady
            text_filters=text_filters,
        )

    elif provider == "openai":
        from pipecat.services.openai.tts import OpenAITTSService
        return OpenAITTSService(
            api_key=settings.openai_api_key,
            voice="alloy",
            text_filters=text_filters,
        )

    raise ValueError(f"Unknown TTS provider: {provider}")
