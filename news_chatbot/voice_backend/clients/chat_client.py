import json
import httpx
from typing import AsyncIterator, Optional, Dict, Any
from loguru import logger
from utils.settings import settings


class ChatClient:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.base_url = f"http://{settings.chat_backend_host}:{settings.chat_backend_port}"
        self.stream_endpoint = f"{self.base_url}/api/chat/stream"
        self.client: Optional[httpx.AsyncClient] = None

        logger.info(f"ChatClient initialized: {self.base_url}, session: {session_id}")

    async def connect(self):
        if not self.client:
            self.client = httpx.AsyncClient(timeout=settings.chat_timeout)
            logger.debug("HTTP client created")

    async def disconnect(self):
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.debug("HTTP client closed")

    async def stream_response(self, message: str) -> AsyncIterator[Dict[str, Any]]:
        """Stream response from chat backend. Server manages session history."""
        if not self.client:
            await self.connect()

        logger.info(f"Streaming request: {message[:50]}...")

        async with self.client.stream(
            "POST",
            self.stream_endpoint,
            json={
                "message": message,
                "session_id": self.session_id,
                "history": []  # Server manages history via session_id
            },
            timeout=settings.chat_timeout
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                try:
                    data = json.loads(line[6:])

                    if data.get("error"):
                        logger.error(f"Stream error from backend: {data['error']}")
                        raise Exception(data["error"])

                    event_type = data.get("type", "text")

                    if event_type == "text":
                        content = data.get("content", "")
                        if content:
                            yield {"type": "text", "content": content}

                    elif event_type == "done":
                        logger.info(f"Stream completed for session {self.session_id}")
                        break

                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse SSE data: {line}, error: {e}")
                    continue

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
