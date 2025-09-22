from pydantic import BaseModel
from typing import Optional, List

class PromptResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    content: str
    version: int
    created_at: str
    updated_at: str
    is_active: bool

class PromptUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None

class PromptCreateRequest(BaseModel):
    id: str
    name: str
    description: str
    content: str
    category: str = "custom"
    is_active: bool = True
