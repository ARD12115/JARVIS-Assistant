from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict
import uuid


class ParameterSchema(BaseModel):
    name: str
    required: bool = False
    type: Optional[str] = None
    prompt: Optional[str] = None


class ApiDetailsSchema(BaseModel):
    url: str
    request_type: str
    headers: List[Dict[str, str]] = Field(default_factory=list)
    is_json: bool = False
    json_data: str = "{}"


class IntentSchema(BaseModel):
    name: str
    intent_id: str
    speech_response: str
    user_defined: bool = True
    api_trigger: bool = False
    api_details: Optional[ApiDetailsSchema] = None
    parameters: List[ParameterSchema] = Field(default_factory=list)


# In-memory storage for intents (in production, use database)
_intents_db: Dict[str, IntentSchema] = {}


def create_intent(intent: IntentSchema) -> IntentSchema:
    """Create a new intent."""
    _intents_db[intent.intent_id] = intent
    return intent


def get_intent(intent_id: str) -> Optional[IntentSchema]:
    """Get a specific intent by ID."""
    return _intents_db.get(intent_id)


def list_intents() -> List[IntentSchema]:
    """Get all intents."""
    return list(_intents_db.values())


def update_intent(intent_id: str, intent_data: Dict[str, Any]) -> Optional[IntentSchema]:
    """Update an intent."""
    if intent_id not in _intents_db:
        return None
    
    existing = _intents_db[intent_id]
    updated_data = existing.model_dump()
    updated_data.update(intent_data)
    
    # Preserve the stored ID when merging intent_data
    if "intent_id" in intent_data and intent_data["intent_id"] != intent_id:
        # Reject conflicting intent_id
        return None
    updated_data["intent_id"] = intent_id
    
    updated = IntentSchema(**updated_data)
    _intents_db[intent_id] = updated
    return updated


def delete_intent(intent_id: str) -> bool:
    """Delete an intent."""
    if intent_id in _intents_db:
        del _intents_db[intent_id]
        return True
    return False


def export_intents() -> Dict[str, Any]:
    """Export all intents as JSON."""
    return {
        "intents": [intent.model_dump() for intent in _intents_db.values()]
    }


def import_intents(data: Dict[str, Any]) -> List[IntentSchema]:
    """Import intents from JSON."""
    imported = []
    for intent_data in data.get("intents", []):
        intent = IntentSchema(**intent_data)
        _intents_db[intent.intent_id] = intent
        imported.append(intent)
    return imported


# Initialize with default intents
def init_default_intents():
    """Initialize default JARVIS intents."""
    defaults = [
        IntentSchema(
            name="Get Time",
            intent_id="get_time",
            speech_response="The current time in {{ parameters.timezone or 'UTC' }} is {{ result.time }}.",
            user_defined=False,
            parameters=[
                ParameterSchema(
                    name="timezone",
                    required=False,
                    type="timezone",
                    prompt="Which timezone would you like the time for?",
                )
            ],
        ),
        IntentSchema(
            name="Web Search",
            intent_id="web_search",
            speech_response="Here are the search results for {{ parameters.query }}.",
            user_defined=False,
            parameters=[
                ParameterSchema(
                    name="query",
                    required=True,
                    type="free_text",
                    prompt="What would you like me to search for?",
                )
            ],
        ),
        IntentSchema(
            name="File Operations",
            intent_id="file_ops",
            speech_response="File operation completed.",
            user_defined=False,
            parameters=[
                ParameterSchema(
                    name="operation",
                    required=True,
                    type="file_operation",
                    prompt="What file operation would you like to perform?",
                ),
                ParameterSchema(
                    name="path",
                    required=True,
                    type="file_path",
                    prompt="What is the file path?",
                ),
            ],
        ),
        IntentSchema(
            name="Weather",
            intent_id="weather",
            speech_response="The weather in {{ parameters.location }} is {{ result.weather }}.",
            user_defined=False,
            api_trigger=True,
            parameters=[
                ParameterSchema(
                    name="location",
                    required=True,
                    type="location",
                    prompt="Which location would you like the weather for?",
                )
            ],
        ),
        IntentSchema(
            name="Cancel",
            intent_id="cancel",
            speech_response="Cancelled.",
            user_defined=False,
        ),
        IntentSchema(
            name="Fallback",
            intent_id="fallback",
            speech_response="I'm not sure how to help with that. Could you rephrase or try asking about time, weather, search, or files?",
            user_defined=False,
        ),
    ]
    
    for intent in defaults:
        _intents_db[intent.intent_id] = intent


# Initialize on import
init_default_intents()