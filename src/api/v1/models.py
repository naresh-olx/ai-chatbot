import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, create_model, Field, ValidationError
import requests

class RangeModel(BaseModel):
    id: str
    description: str
    min_value: int
    max_value: int

class ValueModel(BaseModel):
    key: str
    name: str
    display_order: int
    popular_order: Optional[int] = None

class ParamModel(BaseModel):
    key: str
    range: Optional[List[RangeModel]] = None
    values: Optional[List[ValueModel]] = None
    default_search_value: Optional[ValueModel] = None

class RuleModel(BaseModel):
    id: str
    value: Union[str, int, bool]
    message: Optional[str] = None

class ParamDefinitionModel(BaseModel):
    key: str
    display_order: int
    name: str
    field: str
    type: str
    data_type: str
    render_as: str
    rules: Optional[List[RuleModel]] = None

class ParamsDefinitionsModel(BaseModel):
    base: Optional[List[ParamDefinitionModel]] = None
    posting: Optional[List[ParamDefinitionModel]] = None

class PhotosModel(BaseModel):
    c2c: int
    b2c: int

class SortingModel(BaseModel):
    options: List[str]
    default: str

class SuggestionsModel(BaseModel):
    image_count: int

class SubCategoryModel(BaseModel):
    id: str
    key: str
    display_order: int
    name: str
    search_allowed: bool
    adding_allowed: bool
    disable_monet: bool
    max_photos: PhotosModel
    min_photos: PhotosModel
    params: List[ParamModel]
    params_definitions: Optional[ParamsDefinitionsModel] = None
    default_layout: str
    card_info_template: str
    default_location_level: str
    sorting: SortingModel
    suggestions: SuggestionsModel
    icon_url: str

class CategoryModel(BaseModel):
    id: str
    key: str
    display_order: int
    name: str
    search_allowed: bool
    adding_allowed: bool
    disable_monet: bool
    max_photos: PhotosModel
    min_photos: PhotosModel
    params: List[ParamModel]
    params_definitions: Optional[ParamsDefinitionsModel] = None
    default_layout: str
    card_info_template: str
    default_location_level: str
    sorting: SortingModel
    suggestions: SuggestionsModel
    icon_url: str
    sub_categories: Optional[List[SubCategoryModel]] = None

class CategoryDataModel(BaseModel):
    data: List[CategoryModel]

def create_dynamic_response_model(param_def: ParamDefinitionModel):
    """
    Dynamically create a Pydantic model for user response validation based on a ParamDefinitionModel.
    """
    field_type = str  # Default type
    field_args = {}
    validators = []

    # Set field type based on data_type
    if param_def.data_type == "numeric":
        field_type = int
    elif param_def.data_type == "string":
        field_type = str
    # Add more types as needed

    # Set field constraints from rules
    if param_def.rules:
        for rule in param_def.rules:
            if rule.id == "required" and rule.value:
                field_args["..."] = ...
            if param_def.data_type == "numeric":
                if rule.id == "min":
                    field_args["ge"] = rule.value
                if rule.id == "max":
                    field_args["le"] = rule.value
            if param_def.data_type == "string":
                if rule.id == "max_length":
                    field_args["max_length"] = rule.value
    # Create the model
    model = create_model(
        "DynamicResponseModel",
        **{
            param_def.key: (field_type, Field(**field_args))
        }
    )
    return model

# Example usage:
# param_def = ParamDefinitionModel(...)
# DynamicModel = create_dynamic_response_model(param_def)
# try:
#     validated = DynamicModel(**{"price": 100})
# except ValidationError as e:
#     print(e) 

def load_category_data(json_path: str) -> CategoryDataModel:
    """
    Load and parse the category information JSON file into a CategoryDataModel instance.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return CategoryDataModel(**data) 

def generate_conversational_question(prompt: str, model: str = "mistral", ollama_url: str = "http://localhost:11434/api/generate") -> str:
    """
    Query the local Ollama LLM to generate a conversational question.
    Args:
        prompt (str): The prompt to send to the LLM.
        model (str): The model to use (default: 'mistral').
        ollama_url (str): The Ollama API endpoint.
    Returns:
        str: The generated conversational question.
    Raises:
        RuntimeError: If the LLM call fails.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(ollama_url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
    except Exception as e:
        raise RuntimeError(f"Failed to generate question from LLM: {e}") 

def extract_user_info_with_llm(user_message: str, categories: list, subcategories: list = None, attributes: list = None, model: str = "mistral", ollama_url: str = "http://localhost:11434/api/generate") -> dict:
    """
    Use the LLM to extract structured information (category, subcategory, attributes) from user input.
    Args:
        user_message (str): The user's free-form message.
        categories (list): List of available category names.
        subcategories (list): List of available subcategory names (optional).
        attributes (list): List of attribute names (optional).
        model (str): LLM model name.
        ollama_url (str): Ollama API endpoint.
    Returns:
        dict: Extracted info, e.g. {"category": ..., "subcategory": ..., "attributes": {...}}
    """
    prompt = f"""
You are an intelligent assistant. Your job is to understand the user's intent and extract as much structured information as possible from their message, even if they use indirect or conversational language.

The available categories are: {', '.join(categories)}.
"""
    if subcategories:
        prompt += f" The available subcategories are: {', '.join(subcategories)}."
    if attributes:
        prompt += f" The available attributes are: {', '.join(attributes)}."

    prompt += """

Here are some examples:
User: 'I am interested in mobile phones and my budget is 10000 rs'
Extracted: {"category": "Mobiles", "subcategory": "Mobile Phones", "attributes": {"price": 10000}}

User: 'Looking for jobs in IT, salary around 50000'
Extracted: {"category": "Jobs", "subcategory": "IT", "attributes": {"salary": 50000}}

User: 'I want a Samsung phone, can spend up to 15000'
Extracted: {"category": "Mobiles", "subcategory": "Mobile Phones", "attributes": {"brand": "Samsung", "price": 15000}}

User: 'I am looking for a bike, preferably Honda, under 60000'
Extracted: {"category": "Bikes", "subcategory": null, "attributes": {"brand": "Honda", "price": 60000}}

User: 'Interested in electronics, especially laptops'
Extracted: {"category": "Electronics & Appliances", "subcategory": null, "attributes": {"type": "laptops"}}

Now, given the following user message, extract as much information as possible in the same JSON format. If something is missing, set it to null.

User message: '""" + user_message + """'
"""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    import requests, json as pyjson
    try:
        response = requests.post(ollama_url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        # Try to extract JSON from LLM response
        import re
        match = re.search(r'\{.*\}', data.get("response", ""), re.DOTALL)
        if match:
            return pyjson.loads(match.group(0))
        # fallback: try to parse whole response
        return pyjson.loads(data.get("response", ""))
    except Exception as e:
        raise RuntimeError(f"Failed to extract user info from LLM: {e}") 