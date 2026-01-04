import os
import uuid
from contextlib import asynccontextmanager
import aiohttp
import uvicorn
from fastapi import FastAPI, WebSocket, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer

from utils.settings import settings
from bots.news_bot import run_bot

daily_rest_helper = None
aiohttp_session = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global daily_rest_helper, aiohttp_session

    aiohttp_session = aiohttp.ClientSession()

    if settings.transport_type == "daily" and settings.daily_api_key:
        from pipecat.transports.daily.utils import DailyRESTHelper
        daily_rest_helper = DailyRESTHelper(
            daily_api_key=settings.daily_api_key,
            daily_api_url="https://api.daily.co/v1",
            aiohttp_session=aiohttp_session,
        )

    logger.info(f"Voice backend starting on {settings.host}:{settings.port}")
    logger.info(f"Transport type: {settings.transport_type}")
    logger.info(f"TTS provider: {settings.tts_provider}")
    yield

    if aiohttp_session:
        await aiohttp_session.close()
    logger.info("Voice backend shutting down")


app = FastAPI(
    title="News Chatbot - Voice Backend",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "voice_backend",
        "transport": settings.transport_type,
        "tts_provider": settings.tts_provider,
    }


@app.post("/connect")
async def connect():
    if settings.transport_type == "daily":
        if not daily_rest_helper:
            return {"error": "Daily API key not configured"}

        from pipecat.transports.daily.utils import DailyRoomParams
        room = await daily_rest_helper.create_room(DailyRoomParams())
        token = await daily_rest_helper.get_token(room.url)

        return {
            "transport": "daily",
            "room_url": room.url,
            "token": token
        }

    elif settings.transport_type == "websocket":
        return {
            "transport": "websocket",
            "ws_url": f"ws://localhost:{settings.port}/ws"
        }

    return {"error": f"Unknown transport type: {settings.transport_type}"}


# Daily Transport - Bot runs client-side initiated
@app.post("/connect/daily")
async def daily_connect(background_tasks: BackgroundTasks):
    if not daily_rest_helper:
        return {"error": "Daily API key not configured"}

    from pipecat.transports.daily.utils import DailyRoomParams
    room = await daily_rest_helper.create_room(DailyRoomParams())
    token = await daily_rest_helper.get_token(room.url)
    bot_token = await daily_rest_helper.get_token(room.url)

    session_id = str(uuid.uuid4())

    async def start_daily_bot():
        from pipecat.transports.daily.transport import DailyParams, DailyTransport
        transport = DailyTransport(
            room.url,
            bot_token,
            "News Bot",
            params=DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
            ),
        )
        await run_bot(transport, session_id)

    background_tasks.add_task(start_daily_bot)

    return {
        "transport": "daily",
        "room_url": room.url,
        "token": token,
        "session_id": session_id
    }


# WebSocket Transport
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    logger.info(f"WebSocket connected, session: {session_id}")

    from pipecat.serializers.protobuf import ProtobufFrameSerializer
    from pipecat.transports.websocket.fastapi import (
        FastAPIWebsocketParams,
        FastAPIWebsocketTransport,
    )

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(),
            serializer=ProtobufFrameSerializer(),
        ),
    )

    await run_bot(transport, session_id)


if __name__ == "__main__":
    uvicorn.run("app:app", host=settings.host, port=settings.port, reload=True)
