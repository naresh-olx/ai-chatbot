from fastapi import FastAPI
from src.api import app, health
from src.api.v1.models import load_category_data
from pathlib import Path
import logging

server = FastAPI(title="AI-Chatbot", version="0.1.0")

# Efficiently load category data at startup and store in app state for global access
@server.on_event("startup")
async def load_data():
    data_path = Path(__file__).parent.parent / "data" / "category-information.json"
    try:
        server.state.category_data = load_category_data(str(data_path))
        logging.info("Category data loaded successfully.")
    except Exception as e:
        logging.error(f"Failed to load category data: {e}")
        server.state.category_data = None

server.include_router(app.router)
server.include_router(health.router, tags=["Health"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:server", host="0.0.0.0", port=8000, reload=True)
