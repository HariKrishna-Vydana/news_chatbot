# News Chatbot - Voice-Powered News Assistant

A voice-enabled chatbot that provides news updates using WebRTC, LangGraph, and modern AI services.

## Architecture

```
┌─────────────┐     WebRTC      ┌──────────────┐     LangGraph    ┌─────────────┐
│ Web Client  │ ◄─────────────► │ Voice Backend│ ◄──────────────► │ Chat Backend│
│  (React)    │   Audio/Video   │  (Pipecat)   │    Agent Flow    │  (LangChain)│
└─────────────┘                 └──────────────┘                  └─────────────┘
                                       │                                  │
                                       ▼                                  ▼
                                 ┌──────────┐                      ┌──────────┐
                                 │ Deepgram │                      │  OpenAI  │
                                 │ElevenLabs│                      │  Google  │
                                 └──────────┘                      └──────────┘
```

## Quick Start

### 1. Initial Setup

```bash
# Clone and navigate to the project
cd news_chatbot

# Copy environment files and install dependencies
make setup

# Edit .env files with your API keys
# - OPENAI_API_KEY
# - DEEPGRAM_API_KEY
# - ELEVENLABS_API_KEY (or CARTESIA_API_KEY)
# - GOOGLE_SEARCH_API_KEY & GOOGLE_SEARCH_ENGINE_ID
```

### 2. Start the Application

```bash
# Start all services
make up

# Check status
make status

# View logs
make logs
```

### 3. Access the Application

Open http://localhost in your browser and click "Connect"

## Transport Options

The application supports two transport methods:

- **Daily WebRTC** (default): Uses Daily.co's infrastructure for reliable WebRTC connections with built-in NAT traversal
- **WebSocket**: Fallback option using WebSocket for audio streaming

Configure in `voice_backend/.env`:
```env
TRANSPORT_TYPE=daily  # Options: daily, websocket
```

## Available Commands

Run `make help` to see all available commands:

### Setup & Installation
- `make setup` - Initialize project and create .env files
- `make install` - Install dependencies locally

### Running Services
- `make up` - Start all services (production)
- `make down` - Stop all services
- `make restart` - Restart all services
- `make dev` - Run in development mode

### Building
- `make build` - Build all services
- `make rebuild-all` - Force rebuild all (no cache)
- `make build-web` - Rebuild just web client
- `make build-voice` - Rebuild just voice backend
- `make build-chat` - Rebuild just chat backend

### Monitoring
- `make status` - Show container status and health
- `make health` - Check health of all services
- `make logs` - Follow all logs
- `make logs-voice` - Follow voice backend logs

### Troubleshooting
- `make fix-webrtc` - Fix WebRTC connection issues
- `make fix-cache` - Clear build cache and rebuild

### Cleanup
- `make clean` - Stop and remove containers
- `make clean-all` - Complete cleanup (containers + deps)

## Common Issues

### WebRTC Connection Timeout

**Symptom**: Connection stuck in "Connecting..." state for 20 seconds, then fails

**Cause**: NAT/firewall blocking direct P2P connection, no TURN server configured

**Fix**:
```bash
make fix-webrtc
```

Or manually configure TURN servers in `web_client/.env`

### Docker Build Cache Issues

**Symptom**: Code changes not reflected after rebuild

**Fix**:
```bash
make fix-cache
```

### Container Won't Start

**Check Status**:
```bash
make status
make health
```

**View Logs**:
```bash
make logs-voice  # or logs-chat, logs-web
```

## Development

### Local Development (without Docker)

```bash
# Terminal 1 - Chat Backend
cd chat_backend
uv sync
uv run uvicorn app:app --reload --port 8000

# Terminal 2 - Voice Backend
cd voice_backend
uv sync
uv run uvicorn app:app --reload --port 7860

# Terminal 3 - Web Client
cd web_client
npm install
npm run dev
```

### Environment Variables

Each service has its own `.env` file:

- **Root `.env`**: Transport and TTS provider config
- **`chat_backend/.env`**: OpenAI, Google Search API keys
- **`voice_backend/.env`**: Deepgram, ElevenLabs/Cartesia API keys
- **`web_client/.env`**: Backend URL, TURN/STUN servers

## Services

### Chat Backend (Port 8000)
- LangGraph agent orchestration
- News search via Google API
- OpenAI LLM integration
- Health endpoint: http://localhost:8000/api/health

### Voice Backend (Port 7860)
- Pipecat real-time voice pipeline
- Deepgram STT (Speech-to-Text)
- ElevenLabs/Cartesia TTS (Text-to-Speech)
- Daily WebRTC or WebSocket transport
- Health endpoint: http://localhost:7860/health

### Web Client (Port 80)
- React frontend
- WebRTC client
- Real-time audio streaming
- Conversation transcript display

## Troubleshooting Guide

| Issue | Command | Notes |
|-------|---------|-------|
| Connection timeout | `make fix-webrtc` | Rebuilds with proper TURN config |
| Old code running | `make fix-cache` | Clears Docker build cache |
| Service unhealthy | `make health` | Shows which service is down |
| Check logs | `make logs-voice` | Replace `voice` with service name |
| Complete reset | `make clean-all && make up` | Nuclear option |

## License

MIT