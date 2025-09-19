"""
API endpoints for model selection and switching
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import json

from auth import verify_token
from services.model_abstraction_layer import get_model_abstraction_layer

router = APIRouter(prefix="/api/models", tags=["Model Selection"])


class ModelListRequest(BaseModel):
    """Request for getting available models."""
    privacy_required: Optional[bool] = False
    budget_conscious: Optional[bool] = False
    needs_vision: Optional[bool] = False
    language: Optional[str] = "en"
    medical_specialized: Optional[bool] = False


class ModelSwitchRequest(BaseModel):
    """Request for switching models."""
    model_id: str = Field(..., min_length=1, max_length=100, description="Target model identifier")
    conversation_id: str = Field(..., min_length=1, max_length=100, description="Conversation identifier")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for model switch")

    @validator('model_id')
    def validate_model_id(cls, v):
        allowed_models = [
            'claude-3-opus-20240229',
            'claude-3-5-sonnet-20241022',
            'medical-llama-3',
            'gpt-4-turbo',
            'gemini-pro'
        ]
        if v not in allowed_models:
            raise ValueError(f'Model ID must be one of: {", ".join(allowed_models)}')
        return v


class ModelCompareRequest(BaseModel):
    """Request for comparing multiple models."""
    message: str = Field(..., min_length=1, max_length=2000, description="Message to compare across models")
    models: List[str] = Field(..., min_items=2, max_items=5, description="List of model IDs to compare")
    conversation_id: str = Field(..., min_length=1, max_length=100, description="Conversation identifier")

    @validator('models')
    def validate_models(cls, v):
        allowed_models = [
            'claude-3-opus-20240229',
            'claude-3-5-sonnet-20241022',
            'medical-llama-3',
            'gpt-4-turbo',
            'gemini-pro'
        ]
        for model in v:
            if model not in allowed_models:
                raise ValueError(f'All models must be from: {", ".join(allowed_models)}')
        return v


class ModelRecommendRequest(BaseModel):
    """Request for model recommendation."""
    use_case: str = Field(..., min_length=1, max_length=100, description="Medical use case category")
    needs_vision: Optional[bool] = Field(default=False, description="Requires image analysis capabilities")
    privacy_required: Optional[bool] = Field(default=False, description="Requires local/private processing")
    speed_priority: Optional[bool] = Field(default=False, description="Prioritize response speed")
    accuracy_priority: Optional[bool] = Field(default=True, description="Prioritize response accuracy")
    budget_conscious: Optional[bool] = Field(default=False, description="Prioritize cost-effectiveness")

    @validator('use_case')
    def validate_use_case(cls, v):
        allowed_cases = [
            'complex_diagnosis', 'mental_health', 'nutrition', 'general_consultation',
            'emergency_triage', 'chronic_care', 'pediatrics', 'geriatrics',
            'women_health', 'preventive_care', 'drug_interactions'
        ]
        if v not in allowed_cases:
            raise ValueError(f'Use case must be one of: {", ".join(allowed_cases)}')
        return v


class ModelChatRequest(BaseModel):
    """Request for chat with specific model."""
    message: str = Field(..., min_length=1, max_length=8000, description="Chat message content")
    conversation_id: str = Field(..., min_length=1, max_length=100, description="Conversation identifier")
    model_id: Optional[str] = Field(None, description="Optional model override")
    include_image: Optional[bool] = Field(default=False, description="Include image processing")
    include_audio: Optional[bool] = Field(default=False, description="Include audio processing")

    @validator('model_id')
    def validate_model_id(cls, v):
        if v is None:
            return v
        allowed_models = [
            'claude-3-opus-20240229',
            'claude-3-5-sonnet-20241022',
            'medical-llama-3',
            'gpt-4-turbo',
            'gemini-pro'
        ]
        if v not in allowed_models:
            raise ValueError(f'Model ID must be one of: {", ".join(allowed_models)}')
        return v


class AvailableModelsQuery(BaseModel):
    """Query parameters for available models endpoint."""
    privacy_required: bool = Field(default=False, description="Filter for privacy-focused models")
    budget_conscious: bool = Field(default=False, description="Filter for cost-effective models")
    needs_vision: bool = Field(default=False, description="Filter for vision-capable models")
    language: str = Field(default="en", description="Preferred language code")

    @validator('language')
    def validate_language(cls, v):
        allowed_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'nl', 'pl', 'ja', 'ko', 'zh']
        if v not in allowed_languages:
            raise ValueError(f'Language must be one of: {", ".join(allowed_languages)}')
        return v


@router.get("/available")
async def get_available_models(
    query: AvailableModelsQuery = Depends(),
    current_user: str = Depends(verify_token)
):
    """
    Get list of available AI models based on user preferences.

    Returns models with their capabilities and recommendations.
    """
    try:
        abstraction_layer = get_model_abstraction_layer()

        preferences = {
            "privacy_required": query.privacy_required,
            "budget_conscious": query.budget_conscious,
            "needs_vision": query.needs_vision,
            "language": query.language
        }

        models = await abstraction_layer.get_available_models(preferences)

        return {
            "models": models,
            "total": len(models),
            "preferences_applied": preferences
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available models: {str(e)}"
        )


@router.post("/switch")
async def switch_model(
    request: ModelSwitchRequest,
    current_user: str = Depends(verify_token)
):
    """
    Switch to a different AI model during conversation.

    Maintains conversation context across model switch.
    """
    try:
        abstraction_layer = get_model_abstraction_layer()

        result = await abstraction_layer.switch_model(
            model_id=request.model_id,
            conversation_id=request.conversation_id,
            reason=request.reason
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to switch model")
            )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to switch model: {str(e)}"
        )


@router.post("/compare")
async def compare_models(
    request: ModelCompareRequest,
    current_user: str = Depends(verify_token)
):
    """
    Compare responses from multiple models side-by-side.

    Useful for patients to see different AI perspectives.
    """
    try:
        abstraction_layer = get_model_abstraction_layer()

        comparisons = await abstraction_layer.compare_models(
            message=request.message,
            models=request.models,
            conversation_id=request.conversation_id
        )

        return {
            "comparisons": comparisons,
            "models_compared": len(request.models),
            "message": request.message
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare models: {str(e)}"
        )


@router.post("/recommend")
async def get_model_recommendation(
    request: ModelRecommendRequest,
    current_user: str = Depends(verify_token)
):
    """
    Get AI model recommendation based on use case and requirements.
    """
    try:
        abstraction_layer = get_model_abstraction_layer()

        requirements = {
            "needs_vision": request.needs_vision,
            "privacy_required": request.privacy_required,
            "speed_priority": request.speed_priority,
            "accuracy_priority": request.accuracy_priority,
            "budget_conscious": request.budget_conscious
        }

        recommended_model = await abstraction_layer.get_model_recommendation(
            use_case=request.use_case,
            requirements=requirements
        )

        # Get model details
        model_details = abstraction_layer.MODEL_REGISTRY.get(
            next((m for m in abstraction_layer.MODEL_REGISTRY.keys()
                  if m.value == recommended_model), None)
        )

        return {
            "recommended_model": recommended_model,
            "model_details": model_details.__dict__ if model_details else None,
            "use_case": request.use_case,
            "requirements": requirements
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendation: {str(e)}"
        )


@router.post("/chat")
async def chat_with_model(
    request: ModelChatRequest,
    current_user: str = Depends(verify_token)
):
    """
    Chat with a specific AI model or the current default.
    """
    try:
        abstraction_layer = get_model_abstraction_layer()

        # Process with optional model override
        response = await abstraction_layer.process_message(
            message=request.message,
            conversation_id=request.conversation_id,
            model_override=request.model_id
        )

        return {
            "response": response["content"],
            "model_used": response["model"],
            "conversation_id": request.conversation_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


@router.post("/chat/stream")
async def chat_with_model_stream(
    request: ModelChatRequest,
    current_user: str = Depends(verify_token)
):
    """
    Stream chat response from selected model.
    """
    async def generate():
        try:
            abstraction_layer = get_model_abstraction_layer()

            # For streaming, we'll need to modify the abstraction layer
            # This is a placeholder for SSE streaming
            yield f"data: {json.dumps({'type': 'start', 'model': request.model_id or 'default'})}\n\n"

            response = await abstraction_layer.process_message(
                message=request.message,
                conversation_id=request.conversation_id,
                model_override=request.model_id
            )

            # Stream the response in chunks
            content = response["content"]
            chunk_size = 50
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size]
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/performance")
async def get_model_performance(
    current_user: str = Depends(verify_token)
):
    """
    Get performance metrics for all models used in this session.
    """
    try:
        abstraction_layer = get_model_abstraction_layer()

        metrics = {}
        for model, perf_data in abstraction_layer.model_performance_metrics.items():
            metrics[model.value] = perf_data

        return {
            "metrics": metrics,
            "current_model": abstraction_layer.current_model.value
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )