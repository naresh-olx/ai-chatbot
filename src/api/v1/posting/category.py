from fastapi import APIRouter
from src.agents.category.categoryFinder import categorize as getCategory
from src.dto.categoryRequest import CategoryRequest

router = APIRouter(prefix="/agents/posting")

@router.post("/categorize")
def categorize(payload: CategoryRequest):
    
    try:
        categorized_content = getCategory(payload)
    except Exception as e:
        return {"error": str(e)}
    
    return categorized_content