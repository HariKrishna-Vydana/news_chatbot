import uuid
from contextlib import asynccontextmanager
import aiohttp
import uvicorn
from fastapi import FastAPI, WebSocket, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer

from utils.settings import settings
from bots.news_bot import run_bot

daily_rest_helper = None
aiohttp_session = None

# ICE servers for WebRTC NAT traversal
ICE_SERVERS = [
    "stun:stun.l.google.com:19302",
    "stun:stun1.l.google.com:19302",
]

# TURN servers for NAT traversal when direct connection fails (OpenRelay Project)
TURN_SERVERS = [
    {
        "urls": "turn:openrelay.metered.ca:80",
        "username": "openrelayproject",
        "credential": "openrelayproject",
    },
    {
        "urls": "turn:openrelay.metered.ca:443",
        "username": "openrelayproject",
        "credential": "openrelayproject",
    },
    {
        "urls": "turn:openrelay.metered.ca:443?transport=tcp",
        "username": "openrelayproject",
        "credential": "openrelayproject",
    },
]

# Store active WebRTC connections
webrtc_connections: dict = {}


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


# SmallWebRTC Transport - P2P WebRTC without Daily
@app.post("/api/offer")
async def webrtc_offer(request: Request, background_tasks: BackgroundTasks):
    from aiortc import RTCIceServer
    from pipecat.transports.base_transport import TransportParams
    from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
    from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection

    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        return {"error": "Invalid JSON body"}

    sdp = body.get("sdp")
    if not sdp:
        return {"error": "Missing 'sdp' in request body"}

    sdp_type = body.get("type", "offer")
    session_id = body.get("session_id") or str(uuid.uuid4())

    logger.info(f"WebRTC offer received, session: {session_id}")

    # Build ICE servers list with proper RTCIceServer objects for TURN credentials
    ice_server_objects = [RTCIceServer(urls=[url]) for url in ICE_SERVERS]
    for turn in TURN_SERVERS:
        ice_server_objects.append(RTCIceServer(
            urls=[turn["urls"]],
            username=turn["username"],
            credential=turn["credential"],
        ))

    webrtc_connection = SmallWebRTCConnection(ice_servers=ice_server_objects)
    await webrtc_connection.initialize(sdp, sdp_type)

    webrtc_connections[session_id] = webrtc_connection

    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    async def run_webrtc_bot():
        try:
            await run_bot(transport, session_id)
        finally:
            webrtc_connections.pop(session_id, None)

    background_tasks.add_task(run_webrtc_bot)

    answer = webrtc_connection.get_answer()
    if not answer:
        return {"error": "Failed to create WebRTC answer"}

    return {
        "sdp": answer["sdp"],
        "type": answer["type"],
        "session_id": session_id,
        "pc_id": answer.get("pc_id", session_id),
        "ice_servers": [{"urls": url} for url in ICE_SERVERS],
    }


# Handle trickle ICE candidates
@app.patch("/api/offer")
async def webrtc_ice_candidate(request: Request):
    from aiortc import RTCIceCandidate

    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse ICE candidate body: {e}")
        return {"error": "Invalid JSON body"}

    pc_id = body.get("pc_id")
    candidate_data = body.get("candidate")

    if not pc_id:
        return {"error": "Missing 'pc_id' in request body"}

    # Find the connection by pc_id
    webrtc_connection = None
    for session_id, conn in webrtc_connections.items():
        if conn.pc_id == pc_id:
            webrtc_connection = conn
            break

    if not webrtc_connection:
        logger.warning(f"No WebRTC connection found for pc_id: {pc_id}")
        return {"error": f"No connection found for pc_id: {pc_id}"}

    if candidate_data:
        try:
            # Parse the ICE candidate
            candidate = RTCIceCandidate(
                component=candidate_data.get("component", 1),
                foundation=candidate_data.get("foundation", ""),
                ip=candidate_data.get("ip") or candidate_data.get("address"),
                port=candidate_data.get("port"),
                priority=candidate_data.get("priority", 0),
                protocol=candidate_data.get("protocol", "udp"),
                type=candidate_data.get("type", "host"),
                sdpMid=candidate_data.get("sdpMid"),
                sdpMLineIndex=candidate_data.get("sdpMLineIndex"),
            )
            await webrtc_connection.add_ice_candidate(candidate)
            logger.debug(f"Added ICE candidate for {pc_id}: {candidate_data.get('type')}")
        except Exception as e:
            logger.error(f"Failed to add ICE candidate: {e}")
            return {"error": str(e)}

    return {"status": "ok"}


# Mount the prebuilt WebRTC test UI (optional, for debugging)
try:
    from pipecat_ai_small_webrtc_prebuilt.frontend import SmallWebRTCPrebuiltUI
    app.mount("/webrtc-test", SmallWebRTCPrebuiltUI)

    @app.get("/webrtc", include_in_schema=False)
    async def webrtc_test_redirect():
        return RedirectResponse(url="/webrtc-test/")
except ImportError:
    logger.info("pipecat-ai-small-webrtc-prebuilt not installed, skipping test UI")


if __name__ == "__main__":
    uvicorn.run("app:app", host=settings.host, port=settings.port, reload=True)
