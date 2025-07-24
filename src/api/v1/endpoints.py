from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from uuid import uuid4
from typing import Dict, Any
import re

# from src.api.v1.posting import category, content
from src.api.v1.models import generate_conversational_question, create_dynamic_response_model, ParamDefinitionModel, extract_user_info_with_llm

router = APIRouter(prefix="/v1", tags=["posting-agent"])

# Enhanced in-memory session store
# {session_id: {step, category, subcategory, answers, attribute_index}}
session_store: Dict[str, Dict[str, Any]] = {}

class StartChatResponse(BaseModel):
    session_id: str
    message: str

class AnswerRequest(BaseModel):
    session_id: str
    answer: str  # Always a string, parsed/validated per step

class AnswerResponse(BaseModel):
    message: str
    completed: bool = False

# Helper: get available categories
def get_category_names(category_data):
    return [cat.name for cat in category_data.data]

# Helper: get available subcategories for a category
def get_subcategory_names(category):
    return [subcat.name for subcat in (category.sub_categories or [])]

@router.post("/chat/start", response_model=StartChatResponse)
def start_chat(request: Request):
    session_id = str(uuid4())
    session_store[session_id] = {
        "step": "category",
        "category": None,
        "subcategory": None,
        "answers": [],
        "attribute_index": 0
    }
    category_data = request.app.state.category_data
    categories = get_category_names(category_data)
    prompt = (
        f"Greet the user in a friendly way and ask what category they are interested in. "
        f"Available categories: {', '.join(categories)}."
    )
    message = generate_conversational_question(prompt)
    return StartChatResponse(session_id=session_id, message=message)

@router.post("/chat/answer", response_model=AnswerResponse)
def answer_chat(request: Request, req: AnswerRequest):
    if req.session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session not found.")
    session = session_store[req.session_id]
    category_data = request.app.state.category_data
    step = session["step"]

    # Gather available options
    categories = get_category_names(category_data)
    category = session.get("category")
    subcategories = get_subcategory_names(category) if category else []
    subcategory = session.get("subcategory")
    param_defs = (subcategory.params_definitions.posting if subcategory and subcategory.params_definitions and subcategory.params_definitions.posting else [])
    attributes = [p.key for p in param_defs] if param_defs else []

    # Use LLM to extract as much info as possible from user input
    extracted = extract_user_info_with_llm(
        req.answer,
        categories=categories,
        subcategories=subcategories if step != "category" else None,
        attributes=attributes if step == "attribute" else None
    )

    # Update session with extracted info
    if not category and extracted.get("category"):
        matched = next((cat for cat in category_data.data if cat.name.lower() == extracted["category"].lower()), None)
        if matched:
            session["category"] = matched
            session["step"] = "subcategory"
            category = matched
            subcategories = get_subcategory_names(category)
    if session.get("category") and not subcategory and extracted.get("subcategory"):
        matched = next((sub for sub in session["category"].sub_categories or [] if sub.name.lower() == extracted["subcategory"].lower()), None)
        if matched:
            session["subcategory"] = matched
            session["step"] = "attribute"
            subcategory = matched
            param_defs = (subcategory.params_definitions.posting if subcategory.params_definitions and subcategory.params_definitions.posting else [])
            attributes = [p.key for p in param_defs]
            session["attribute_index"] = 0
    # Gather attributes
    if session.get("subcategory") and param_defs:
        if not session.get("answers"):
            session["answers"] = []
        # Fill in any attributes provided
        if extracted.get("attributes"):
            for k, v in extracted["attributes"].items():
                # Only add if not already answered
                if k in attributes and not any(ans.get(k) for ans in session["answers"]):
                    # Validate
                    param_def = next((p for p in param_defs if p.key == k), None)
                    if param_def:
                        # If expecting a number, extract it from the string if needed
                        if param_def.data_type == "numeric" and isinstance(v, str):
                            match = re.search(r"\d+", v.replace(',', ''))
                            if match:
                                v = int(match.group(0))
                        DynamicModel = create_dynamic_response_model(param_def)
                        try:
                            validated = DynamicModel(**{k: v})
                            session["answers"].append({k: v})
                        except ValidationError:
                            continue
        # Move attribute index to next unanswered
        answered_keys = [list(ans.keys())[0] for ans in session["answers"]]
        for idx, param_def in enumerate(param_defs):
            if param_def.key not in answered_keys:
                session["attribute_index"] = idx
                break
        else:
            session["attribute_index"] = len(param_defs)

    # Now, decide what to ask next or finish
    if not session.get("category"):
        prompt = f"The user did not provide a valid category. Ask for their interest again. Available categories: {', '.join(categories)}."
        message = generate_conversational_question(prompt)
        return AnswerResponse(message=message)
    if not session.get("subcategory"):
        prompt = f"The user did not provide a valid subcategory for '{session['category'].name}'. Ask for their interest again. Available subcategories: {', '.join(get_subcategory_names(session['category']))}."
        message = generate_conversational_question(prompt)
        return AnswerResponse(message=message)
    if param_defs and session.get("attribute_index", 0) < len(param_defs):
        param_def = param_defs[session["attribute_index"]]
        prompt = f"Ask the user for '{param_def.name}' (type: {param_def.data_type}) in a friendly, conversational way."
        message = generate_conversational_question(prompt)
        return AnswerResponse(message=message)
    # All info gathered
    summary = {
        "category": session["category"].name,
        "subcategory": session["subcategory"].name,
        "attributes": {k: v for d in session["answers"] for k, v in d.items()}
    }
    prompt = f"Thank the user for providing all the details. Summarize the collected information: {summary}. End the conversation politely."
    message = generate_conversational_question(prompt)
    session["step"] = "completed"
    return AnswerResponse(message=message, completed=True)