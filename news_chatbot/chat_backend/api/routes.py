import json
from typing import Dict, Any
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agents import Runner
from openai.types.responses import ResponseTextDeltaEvent
from loguru import logger

from business_agents.agents.news_agent import create_news_agent
from business_agents.agents.agent_definitions import get_agents

router = APIRouter()

# Session cache: stores agent and message history per session
session_cache: Dict[str, Dict[str, Any]] = {}


def get_or_create_session(session_id: str, system_prompt: str = None) -> Dict[str, Any]:
    if session_id not in session_cache:
        logger.info(f"Creating new session: {session_id}, custom_prompt: {system_prompt is not None}")
        session_cache[session_id] = {
            "agent": create_news_agent(system_prompt),
            "messages": []
        }
    return session_cache[session_id]


def clear_session(session_id: str):
    """Clear a session from cache."""
    if session_id in session_cache:
        del session_cache[session_id]
        logger.info(f"Cleared session: {session_id}")


class ChatRequest(BaseModel):
    message: str
    session_id: str
    history: list[dict] = []
    system_prompt: str = None


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "chat_backend"}


@router.get("/agents")
async def list_agents():
    return {"agents": get_agents()}


@router.post("/chat/stream")
async def stream_chat(request: ChatRequest):
    async def generate():
        try:
            # Get or create cached session
            session = get_or_create_session(request.session_id, request.system_prompt)
            agent = session["agent"]
            messages = session["messages"]

            # Add new user message to history
            messages.append({"role": "user", "content": request.message})

            logger.info(f"Session {request.session_id}: {len(messages)} messages")

            # Pass messages to agent
            result = Runner.run_streamed(agent, input=messages)

            full_response = []
            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    chunk = event.data.delta
                    if chunk:
                        full_response.append(chunk)
                        data = json.dumps({"type": "text", "content": chunk})
                        yield f"data: {data}\n\n"

            # Add assistant response to history
            if full_response:
                messages.append({"role": "assistant", "content": "".join(full_response)})

            done_data = json.dumps({"type": "done", "session_id": request.session_id})
            yield f"data: {done_data}\n\n"
            logger.info(f"Completed response for session {request.session_id}")

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            error_data = json.dumps({"type": "error", "error": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        # Get or create cached session
        session = get_or_create_session(request.session_id, request.system_prompt)
        agent = session["agent"]
        messages = session["messages"]

        # Add new user message to history
        messages.append({"role": "user", "content": request.message})

        logger.info(f"Session {request.session_id}: {len(messages)} messages")

        result = await Runner.run(agent, input=messages)
        response_text = result.final_output

        # Add assistant response to history
        if response_text:
            messages.append({"role": "assistant", "content": response_text})

        logger.info(f"Completed response for session {request.session_id}")
        return {"response": response_text, "session_id": request.session_id}

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return {"response": f"Error: {str(e)}", "session_id": request.session_id}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and free resources."""
    clear_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get session info."""
    if session_id in session_cache:
        session = session_cache[session_id]
        return {
            "session_id": session_id,
            "message_count": len(session["messages"]),
            "messages": session["messages"]
        }
    return {"error": "Session not found", "session_id": session_id}
