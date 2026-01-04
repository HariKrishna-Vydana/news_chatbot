"""News Bot Pipeline

Pipecat pipeline that uses:
- Deepgram STT for speech-to-text
- Custom NewsAgentLLMService that calls chat_backend
- Configurable TTS (ElevenLabs, Cartesia, OpenAI)
"""
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.transports.base_transport import BaseTransport

from services.news_llm import NewsAgentLLMService
from services.tts_factory import create_tts_service
from utils.settings import settings


SYSTEM_INSTRUCTION = """You are a helpful news assistant that provides the latest news updates.
Your output will be converted to audio so don't include special characters in your answers.
Be conversational and concise. Keep responses brief and clear."""


async def run_bot(transport: BaseTransport, session_id: str = "default"):
    logger.info(f"Starting news bot with session: {session_id}")

    stt = DeepgramSTTService(api_key=settings.deepgram_api_key)
    tts = create_tts_service()
    llm = NewsAgentLLMService(session_id=session_id)

    context = LLMContext([
        {
            "role": "system",
            "content": SYSTEM_INSTRUCTION,
        },
        {
            "role": "user",
            "content": "Start by greeting the user and asking what news they'd like to hear about.",
        }
    ])
    context_aggregator = LLMContextAggregatorPair(context)

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        rtvi,
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        logger.info("Client ready")
        await rtvi.set_bot_ready()
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected: {client}")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected: {client}")
        await task.cancel()

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.info(f"Participant left: {participant}, reason: {reason}")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)
