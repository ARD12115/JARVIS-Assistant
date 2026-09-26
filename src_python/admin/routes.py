from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from src_python.intent.store import (
    IntentSchema,
    create_intent,
    get_intent,
    list_intents,
    update_intent,
    delete_intent,
    export_intents,
    import_intents,
)

router = APIRouter(prefix="/admin/intents", tags=["admin", "intents"])


@router.post("/")
async def create_intent_endpoint(intent: IntentSchema):
    """Create a new intent."""
    try:
        created = create_intent(intent)
        return created
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def read_intents():
    """Get all intents."""
    return list_intents()


# Specific routes MUST come before parameterized routes
@router.get("/export")
async def export_bot():
    """Export all intents and entities as JSON."""
    return export_intents()


@router.post("/import")
async def import_bot(data: Dict[str, Any]):
    """Import intents from JSON."""
    try:
        imported = import_intents(data)
        return {"status": "success", "imported": len(imported)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{intent_id}")
async def read_intent(intent_id: str):
    """Get a specific intent by ID."""
    intent = get_intent(intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    return intent


@router.put("/{intent_id}")
async def update_intent_endpoint(intent_id: str, intent_data: Dict[str, Any]):
    """Update an intent."""
    updated = update_intent(intent_id, intent_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Intent not found")
    return {"status": "success", "intent": updated}


@router.delete("/{intent_id}")
async def delete_intent_endpoint(intent_id: str):
    """Delete an intent."""
    success = delete_intent(intent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Intent not found")
    return {"status": "success"}