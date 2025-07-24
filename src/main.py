from fastapi import FastAPI
from src.api import app , health
import uvicorn

server = FastAPI(title="AI-Chatbot", version="0.1.0")

server.include_router(app.router)
server.include_router(health.router, tags=["Health"])

if __name__ == "__main__":
    uvicorn.run("main:server", host="0.0.0.0", port=8000, reload=True)
