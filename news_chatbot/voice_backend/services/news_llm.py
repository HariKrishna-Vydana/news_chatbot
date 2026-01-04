"""News Agent LLM Service

Custom LLM service that connects to the chat_backend via HTTP SSE.
Based on the pattern from InnerDialogue's HealthcareAgent_LLMService.
"""
from typing import Optional, List, Dict, Any
from loguru import logger

from pipecat.frames.frames import (
    Frame,
    LLMFullResponseStartFrame,
    LLMFullResponseEndFrame,
    LLMMessagesFrame,
    LLMTextFrame,
    ErrorFrame,
    LLMContextFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.llm_service import LLMService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContextFrame

from clients.chat_client import ChatClient


class NewsAgentLLMService(LLMService):
    """Custom LLM service using news agent chat backend."""

    def __init__(self, session_id: str, **kwargs):
        super().__init__(**kwargs)
        self.client = ChatClient(session_id)
        logger.info(f"NewsAgentLLMService initialized with session: {session_id}")

    async def _process_context(self, messages: List[Dict[str, Any]]):
        """Process messages and stream response from chat backend."""
        try:
            logger.info(f"Processing {len(messages)} messages")

            user_message = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break

            if not user_message:
                logger.warning("No user message found")
                return

            logger.info(f"User message: {user_message[:50]}...")

            async for event in self.client.stream_response(user_message):
                if event.get("type") == "text":
                    chunk = event.get("content", "")
                    if chunk:
                        logger.debug(f"Text chunk: {chunk[:30]}...")
                        await self.push_frame(LLMTextFrame(text=chunk))

            logger.info("Response stream completed")

        except Exception as e:
            logger.error(f"Error processing context: {e}", exc_info=True)
            await self.push_frame(ErrorFrame(error=str(e)))

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames from the pipeline."""
        await super().process_frame(frame, direction)

        messages = None

        if isinstance(frame, OpenAILLMContextFrame):
            context = frame.context
            messages = context.get_messages()
            logger.info(f"OpenAILLMContextFrame with {len(messages)} messages")
        elif isinstance(frame, LLMContextFrame):
            context = frame.context
            messages = context.get_messages()
            logger.info(f"LLMContextFrame with {len(messages)} messages")
        elif isinstance(frame, LLMMessagesFrame):
            messages = frame.messages
            logger.info(f"LLMMessagesFrame with {len(messages)} messages")
        else:
            await self.push_frame(frame, direction)

        if messages:
            try:
                await self.push_frame(LLMFullResponseStartFrame())
                await self._process_context(messages)
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
            finally:
                await self.push_frame(LLMFullResponseEndFrame())

    def can_generate_metrics(self) -> bool:
        return True

    async def cleanup(self):
        logger.info("Cleaning up NewsAgentLLMService")
        try:
            await self.client.disconnect()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        finally:
            await super().cleanup()
