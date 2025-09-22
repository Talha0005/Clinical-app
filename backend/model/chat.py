from pydantic import BaseModel, field_validator
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    
    # Validation for message content
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        if len(v) > 5000:  # Reasonable message length limit
            raise ValueError('Message too long (max 5000 characters)')
        return v.strip()

class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    timestamp: str
    error: Optional[str] = None

class ConversationDataModel(BaseModel):
    """Validation for conversation data from frontend"""
    conversation_id: str
    created_at: str
    messages: List[dict]
    metadata: Optional[dict] = None
