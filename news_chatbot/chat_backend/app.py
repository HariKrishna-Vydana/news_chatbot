import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from api.routes import router
from utils.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Chat backend starting on {settings.host}:{settings.port}")
    yield
    logger.info("Chat backend shutting down")


app = FastAPI(
    title="News Chatbot - Chat Backend",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run("app:app", host=settings.host, port=settings.port, reload=True)
