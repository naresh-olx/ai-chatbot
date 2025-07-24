import json
from fastapi import APIRouter
from src.agents.posting.postingContent import generateContent
from src.dto.contentRequest import ContentRequest

router = APIRouter(prefix="/agents/posting")

@router.post("/generate-content")
def generate_content(request: ContentRequest):
    
    try:
        generated_content = generateContent(request)
        return json.loads(generated_content)
    except Exception as e:
        return {"error": str(e)}