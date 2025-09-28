"""
API endpoints for model selection and switching
"""

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import json
import os
import logging

from auth import verify_token as verify_jwt_token
from services.model_abstraction_layer import (
    get_model_abstraction_layer,
    ModelProvider,
)
from services.agents import (
    Orchestrator,
    AgentContext,
)
from services.vision_processing import MedicalVisionService, AnalysisLevel  # safe import; unused when flag is off
from services.direct_llm_service import direct_llm_service

# Lazy local .env load (no-op if already loaded by services)
# This helps when this module is imported in isolation and
# ensures AGENTS_ENABLED is available without disturbing globals.
try:
    if "AGENTS_ENABLED" not in os.environ:
        from pathlib import Path
        from dotenv import load_dotenv  # type: ignore
        backend_dir = Path(__file__).resolve().parent.parent
        env_path = backend_dir / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
except Exception:
    # Safe fallback: simply proceed with current environment
    pass

router = APIRouter(prefix="/api/models", tags=["Model Selection"])
logger = logging.getLogger(__name__)


class ModelListRequest(BaseModel):
    """Request for getting available models."""
    privacy_required: Optional[bool] = False
    budget_conscious: Optional[bool] = False
    needs_vision: Optional[bool] = False
    language: Optional[str] = "en"
    medical_specialized: Optional[bool] = False


# Backward-compatible aliases to accept legacy model IDs from older frontends
LEGACY_MODEL_ALIASES = {
    # OpenAI
    "gpt-4o": "openai/gpt-4o-2024-08-06",
    "gpt4o": "openai/gpt-4o-2024-08-06",
    # Gemini
    "gemini/gemini-1.5-pro": "gemini/gemini-1.5-pro-002",
    "gemini/gemini-1.5-flash": "gemini/gemini-1.5-flash-002",
}


class ModelSwitchRequest(BaseModel):
    """Request for switching models."""
    model_id: str = Field(
        ..., min_length=1, max_length=100,
        description="Target model identifier"
    )
    conversation_id: str = Field(
        ..., min_length=1, max_length=100,
        description="Conversation identifier"
    )
    reason: Optional[str] = Field(
        None, max_length=500,
        description="Reason for model switch"
    )

    @validator('model_id', pre=True)
    def validate_model_id(cls, v):
        # Map legacy identifiers to the canonical LiteLLM IDs
        if isinstance(v, str) and v in LEGACY_MODEL_ALIASES:
            v = LEGACY_MODEL_ALIASES[v]
        allowed_models = [model.value for model in ModelProvider]
        if v not in allowed_models:
            raise ValueError(
                f'Model ID must be one of: {", ".join(allowed_models)}'
            )
        return v


class ModelCompareRequest(BaseModel):
    """Request for comparing multiple models."""
    message: str = Field(
        ..., min_length=1, max_length=2000,
        description="Message to compare across models"
    )
    models: List[str] = Field(..., description="List of model IDs to compare")
    conversation_id: str = Field(
        ..., min_length=1, max_length=100,
        description="Conversation identifier"
    )

    @validator('models')
    def validate_models(cls, v):
        if not isinstance(v, list) or len(v) < 2 or len(v) > 5:
            raise ValueError("Provide between 2 and 5 model IDs to compare")
        allowed_models = [model.value for model in ModelProvider]
        for model in v:
            if model not in allowed_models:
                raise ValueError(
                    f'All models must be from: {", ".join(allowed_models)}'
                )
        return v


class ModelRecommendRequest(BaseModel):
    """Request for model recommendation."""
    use_case: str = Field(
        ..., min_length=1, max_length=100,
        description="Medical use case category"
    )
    needs_vision: Optional[bool] = Field(
        default=False,
        description="Requires image analysis capabilities"
    )
    privacy_required: Optional[bool] = Field(
        default=False,
        description="Requires local/private processing"
    )
    speed_priority: Optional[bool] = Field(
        default=False, description="Prioritize response speed"
    )
    accuracy_priority: Optional[bool] = Field(
        default=True, description="Prioritize response accuracy"
    )
    budget_conscious: Optional[bool] = Field(
        default=False, description="Prioritize cost-effectiveness"
    )

    @validator('use_case')
    def validate_use_case(cls, v):
        allowed_cases = [
            'complex_diagnosis', 'mental_health', 'nutrition',
            'general_consultation', 'emergency_triage', 'chronic_care',
            'pediatrics', 'geriatrics', 'women_health', 'preventive_care',
            'drug_interactions'
        ]
        if v not in allowed_cases:
            raise ValueError(
                f'Use case must be one of: {", ".join(allowed_cases)}'
            )
        return v


class ModelChatRequest(BaseModel):
    """Request for chat with specific model."""
    message: str = Field(
        ..., min_length=1, max_length=8000,
        description="Chat message content"
    )
    conversation_id: str = Field(
        ..., min_length=1, max_length=100,
        description="Conversation identifier"
    )
    model_id: Optional[str] = Field(
        None, description="Optional model override"
    )
    include_image: Optional[bool] = Field(
        default=False, description="Include image processing"
    )
    include_audio: Optional[bool] = Field(
        default=False, description="Include audio processing"
    )

    @validator('model_id', pre=True)
    def validate_model_id(cls, v):
        if v is None:
            return v
        # Map legacy identifiers to the canonical LiteLLM IDs
        if isinstance(v, str) and v in LEGACY_MODEL_ALIASES:
            v = LEGACY_MODEL_ALIASES[v]
        allowed_models = [model.value for model in ModelProvider]
        if v not in allowed_models:
            raise ValueError(
                f'Model ID must be one of: {", ".join(allowed_models)}'
            )
        return v


class AvailableModelsQuery(BaseModel):
    """Query parameters for available models endpoint."""
    privacy_required: bool = Field(
        default=False, description="Filter for privacy-focused models"
    )
    budget_conscious: bool = Field(
        default=False, description="Filter for cost-effective models"
    )
    needs_vision: bool = Field(
        default=False, description="Filter for vision-capable models"
    )
    language: str = Field(default="en", description="Preferred language code")

    @validator('language')
    def validate_language(cls, v):
        allowed_languages = [
            'en', 'es', 'fr', 'de', 'it', 'pt', 'nl', 'pl', 'ja', 'ko', 'zh'
        ]
        if v not in allowed_languages:
            raise ValueError(
                f'Language must be one of: {", ".join(allowed_languages)}'
            )
        return v


@router.get("/agent/health")
async def agent_health(
    current_user: str = Depends(verify_jwt_token)  # type: ignore[arg-type]
):
    """Lightweight diagnostics for the agent flag and orchestrator import.

    This does not change any behavior; it simply reports whether the agent
    would be considered enabled in this running process.
    """
    try:
        raw = os.getenv("AGENTS_ENABLED", "false") or "false"
        enabled = raw.strip().lower() in {"1", "true", "yes", "y", "on"}
        # Basic import check
        orch_ok = Orchestrator is not None  # type: ignore[name-defined]
        return {
            "agents_enabled": enabled,
            "env_value": raw,
            "orchestrator_loaded": orch_ok,
        }
    except Exception as e:
        return {"agents_enabled": False, "error": str(e)}


@router.get("/available")
async def get_available_models(
    query: AvailableModelsQuery = Depends(),
    current_user: str = Depends(verify_jwt_token)  # type: ignore[arg-type]
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
    current_user: str = Depends(verify_jwt_token)  # type: ignore[arg-type]
):
    """
    Switch to a different AI model during conversation.

    Maintains conversation context across model switch.
    """
    try:
        abstraction_layer = get_model_abstraction_layer()

    # Ensure target is actually available
    # (respects feature flags and credentials)
        available = await abstraction_layer.get_available_models({})
        if not any(m.get("id") == request.model_id for m in available):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Selected model is not available in this environment."
                ),
            )

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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to switch model: {str(e)}"
        )


@router.post("/compare")
async def compare_models(
    request: ModelCompareRequest,
    current_user: str = Depends(verify_jwt_token)  # type: ignore[arg-type]
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
    current_user: str = Depends(verify_jwt_token)  # type: ignore[arg-type]
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
        model_key = next(
            (
                m
                for m in abstraction_layer.MODEL_REGISTRY
                if m.value == recommended_model
            ),
            None,
        )
        model_details = (
            abstraction_layer.MODEL_REGISTRY[model_key] if model_key else None
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
    current_user: str = Depends(verify_jwt_token)  # type: ignore[arg-type]
):
    """
    Chat with a specific AI model or the current default.
    """
    try:
        abstraction_layer = get_model_abstraction_layer()

        flag_val = os.getenv("AGENTS_ENABLED", "false") or "false"
        agents_enabled = flag_val.strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "on",
        }
        logger.info("/api/models/chat -> agents_enabled=%s", agents_enabled)

        if agents_enabled:
            logger.info(f"🤖 Starting agent chain for message: {request.message[:100]}...")
            orch = Orchestrator()
            
            # Create LLM wrapper for agents
            def llm_wrapper(messages):
                try:
                    logger.info(f"🧠 LLM wrapper called with {len(messages)} messages")
                    # Use synchronous call for now
                    import asyncio
                    from services.direct_llm_service import direct_llm_service
                    response = asyncio.run(direct_llm_service.generate_response(
                        messages=messages,
                        model_preference="anthropic"
                    ))
                    content = response.get("content", "I apologize, but I'm having trouble generating a response right now.")
                    logger.info(f"🧠 LLM response: {content[:100]}...")
                    return content
                except Exception as e:
                    logger.error(f"❌ LLM wrapper failed: {e}")
                    return "I apologize, but I'm having trouble generating a response right now."
            
            agent_out = orch.handle_turn(
                request.message,
                ctx=AgentContext(user_id=current_user),
                llm=llm_wrapper,
            )
            logger.info(f"🤖 Agent chain completed. Response: {agent_out.text[:100] if agent_out.text else 'None'}...")
            return {
                "response": agent_out.text,
                "model_used": "agentic/orchestrator",
                "conversation_id": request.conversation_id,
                "agent": agent_out.data,
                "avatar": agent_out.avatar,
            }
        else:
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
    current_user: str = Depends(verify_jwt_token)  # type: ignore[arg-type]
):
    """
    Stream chat response from selected model.
    """
    async def generate():
        try:
            abstraction_layer = get_model_abstraction_layer()

            # Yield a start event with conversation_id
            start_evt = {
                "type": "start",
                "conversation_id": request.conversation_id,
            }
            yield f"data: {json.dumps(start_evt)}\n\n"

            # Toggle agentic chain via environment flag - ENABLED for agent testing
            flag_val = os.getenv("AGENTS_ENABLED", "false") or "false"
            agents_enabled = True  # Enable agents to test the full chain
            logger.info(
                "/api/models/chat/stream -> agents_enabled=%s",
                agents_enabled,
            )

            if agents_enabled:
                # Run the MVP chain: Avatar → History → Triage → Summarisation
                logger.info(f"🤖 Starting agent chain for message: {request.message[:100]}...")
                orch = Orchestrator()
                
                # Create LLM wrapper for agents
                def llm_wrapper(messages):
                    try:
                        logger.info(f"🧠 LLM wrapper called with {len(messages)} messages")
                        # Use synchronous call for now
                        import asyncio
                        import threading
                        from services.direct_llm_service import direct_llm_service
                        
                        # Run in a separate thread to avoid event loop conflicts
                        result = [None]
                        exception = [None]
                        
                        def run_llm():
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    response = loop.run_until_complete(direct_llm_service.generate_response(
                                        messages=messages,
                                        model_preference="anthropic"
                                    ))
                                    result[0] = response
                                finally:
                                    loop.close()
                            except Exception as e:
                                exception[0] = e
                        
                        thread = threading.Thread(target=run_llm)
                        thread.start()
                        thread.join()
                        
                        if exception[0]:
                            raise exception[0]
                            
                        response = result[0]
                        content = response.get("content", "I apologize, but I'm having trouble generating a response right now.")
                        logger.info(f"🧠 LLM response: {content[:100]}...")
                        return content
                    except Exception as e:
                        logger.error(f"❌ LLM wrapper failed: {e}")
                        return "I apologize, but I'm having trouble generating a response right now."
                
                agent_out = orch.handle_turn(
                    request.message,
                    ctx=AgentContext(user_id=current_user),
                    llm=llm_wrapper,
                )
                logger.info(f"🤖 Agent chain completed. Response: {agent_out.text[:100] if agent_out.text else 'None'}...")
                content = agent_out.text or ""

                # Stream minimal content (single burst) for smooth UI
                evt = {"type": "content", "text": content}
                yield f"data: {json.dumps(evt)}\n\n"

                # Finalize with agent meta (frontend ignores
                # unknown fields safely)
                complete_evt = {
                    "type": "complete",
                    "full_response": content,
                    "conversation_id": request.conversation_id,
                    "model_used": "agentic/orchestrator",
                    "agent_enabled": True,
                    "agent": agent_out.data,
                    "avatar": agent_out.avatar,
                }
                yield f"data: {json.dumps(complete_evt)}\n\n"
            else:
                # Use Direct LLM Service for real AI responses
                from services.direct_llm_service import direct_llm_service
                
                messages = [{"role": "user", "content": request.message}]
                
                try:
                    direct_response = await direct_llm_service.generate_response(
                        messages=messages,
                        model_preference="anthropic"
                    )
                    
                    if direct_response and direct_response.get("content"):
                        content = direct_response["content"]
                        model_used = direct_response.get("model_used", "anthropic/claude-3-5-sonnet-20240620")
                        
                        # Stream the response in chunks
                        chunk_size = 200
                        for i in range(0, len(content), chunk_size):
                            chunk = content[i:i+chunk_size]
                            evt = {"type": "content", "text": chunk}
                            yield f"data: {json.dumps(evt)}\n\n"

                        # Yield final complete event
                        complete_evt = {
                            "type": "complete",
                            "full_response": content,
                            "conversation_id": request.conversation_id,
                            "model_used": model_used,
                            "agent_enabled": False,
                        }
                        yield f"data: {json.dumps(complete_evt)}\n\n"
                    else:
                        # Fallback to abstraction layer if direct service fails
                        response = await abstraction_layer.process_message(
                            message=request.message,
                            conversation_id=request.conversation_id,
                            model_override=request.model_id
                        )
                        content = response["content"]
                        
                        chunk_size = 200
                        for i in range(0, len(content), chunk_size):
                            chunk = content[i:i+chunk_size]
                            evt = {"type": "content", "text": chunk}
                            yield f"data: {json.dumps(evt)}\n\n"

                        complete_evt = {
                            "type": "complete",
                            "full_response": content,
                            "conversation_id": request.conversation_id,
                            "model_used": response.get("model"),
                            "agent_enabled": False,
                        }
                        yield f"data: {json.dumps(complete_evt)}\n\n"
                        
                except Exception as e:
                    logger.error(f"Direct LLM service failed: {e}")
                    # Fallback to abstraction layer
                    response = await abstraction_layer.process_message(
                        message=request.message,
                        conversation_id=request.conversation_id,
                        model_override=request.model_id
                    )
                content = response["content"]

                chunk_size = 200
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i+chunk_size]
                    evt = {"type": "content", "text": chunk}
                    yield f"data: {json.dumps(evt)}\n\n"

                complete_evt = {
                    "type": "complete",
                    "full_response": content,
                    "conversation_id": request.conversation_id,
                    "model_used": response.get("model"),
                    "agent_enabled": False,
                }
                yield f"data: {json.dumps(complete_evt)}\n\n"

        except Exception as e:
            # Yield an error event if something goes wrong
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
    current_user: str = Depends(verify_jwt_token)  # type: ignore[arg-type]
):
    """
    Get performance metrics for all models used in this session.
    """
    try:
        abstraction_layer = get_model_abstraction_layer()

        metrics = {}
        for (
            model,
            perf_data,
        ) in abstraction_layer.model_performance_metrics.items():
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


@router.post("/chat/with-images")
async def chat_with_model_and_images(
    message: str = Form(..., description="Chat message content"),
    conversation_id: str = Form(..., description="Conversation identifier"),
    model_id: Optional[str] = Form(None, description="Optional model override"),
    images: List[UploadFile] = File(None, description="Multiple image files"),
    current_user: str = Depends(verify_jwt_token)
):
    """
    Chat with a specific AI model including multiple images.
    """
    try:
        abstraction_layer = get_model_abstraction_layer()

        # Process images if provided
        image_analyses = []
        if images:
            # Initialize vision service
            from services.llm_router import DigiClinicLLMRouter
            from services.nhs_terminology import NHSTerminologyService
            llm_router = DigiClinicLLMRouter()
            nhs_term = NHSTerminologyService()
            vision_service = MedicalVisionService(llm_router, nhs_term)
            
            for i, image in enumerate(images):
                try:
                    image_data = await image.read()
                    analysis = await vision_service.process_medical_image(
                        image_data=image_data,
                        filename=image.filename or f"image_{i+1}.jpg",
                        analysis_level=AnalysisLevel.CLINICAL,
                        patient_id=None,
                        patient_context={}
                    )
                    # Extract the description or summary
                    analysis_text = analysis.get("description", "No description available")
                    image_analyses.append(f"Image {i+1} ({image.filename}): {analysis_text}")
                except Exception as e:
                    logger.warning(f"Failed to analyze image {i+1}: {e}")
                    image_analyses.append(f"Image {i+1} ({image.filename}): Analysis failed - {str(e)}")
        
        # Combine message with image analyses
        full_message = message
        if image_analyses:
            full_message += "\n\nImage Analyses:\n" + "\n".join(image_analyses)

        flag_val = os.getenv("AGENTS_ENABLED", "false") or "false"
        agents_enabled = flag_val.strip().lower() in {
            "1", "true", "yes", "y", "on",
        }
        logger.info("/api/models/chat/with-images -> agents_enabled=%s, images=%d", agents_enabled, len(images) if images else 0)

        if agents_enabled:
            orch = Orchestrator()
            agent_out = orch.handle_turn(
                full_message,
                ctx=AgentContext(user_id=current_user),
                llm=None,
            )
            return {
                "response": agent_out.text,
                "model_used": "agentic/orchestrator",
                "conversation_id": conversation_id,
                "agent": agent_out.data,
                "avatar": agent_out.avatar,
                "images_processed": len(images) if images else 0,
            }
        else:
            # Process with optional model override
            response = await abstraction_layer.process_message(
                message=full_message,
                conversation_id=conversation_id,
                model_override=model_id
            )

            return {
                "response": response["content"],
                "model_used": response["model"],
                "conversation_id": conversation_id,
                "images_processed": len(images) if images else 0,
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat with images failed: {str(e)}"
        )


@router.post("/chat/stream/with-images")
async def chat_with_model_stream_and_images(
    message: str = Form(..., description="Chat message content"),
    conversation_id: str = Form(..., description="Conversation identifier"),
    model_id: Optional[str] = Form(None, description="Optional model override"),
    images: List[UploadFile] = File(None, description="Multiple image files"),
    current_user: str = Depends(verify_jwt_token)
):
    """
    Stream chat response from selected model with multiple images.
    """
    async def generate():
        try:
            abstraction_layer = get_model_abstraction_layer()

            # Yield a start event with conversation_id
            start_evt = {
                "type": "start",
                "conversation_id": conversation_id,
                "images_processing": len(images) if images else 0,
            }
            yield f"data: {json.dumps(start_evt)}\n\n"

            # Process images if provided
            image_analyses = []
            if images:
                # Initialize vision service
                from services.llm_router import DigiClinicLLMRouter
                from services.nhs_terminology import NHSTerminologyService
                llm_router = DigiClinicLLMRouter()
                nhs_term = NHSTerminologyService()
                vision_service = MedicalVisionService(llm_router, nhs_term)
                
                for i, image in enumerate(images):
                    try:
                        image_data = await image.read()
                        analysis = await vision_service.process_medical_image(
                            image_data=image_data,
                            filename=image.filename or f"image_{i+1}.jpg",
                            analysis_level=AnalysisLevel.CLINICAL,
                            patient_id=None,
                            patient_context={}
                        )
                        # Extract the description or summary
                        analysis_text = analysis.get("description", "No description available")
                        image_analyses.append(f"Image {i+1} ({image.filename}): {analysis_text}")
                    except Exception as e:
                        logger.warning(f"Failed to analyze image {i+1}: {e}")
                        image_analyses.append(f"Image {i+1} ({image.filename}): Analysis failed - {str(e)}")

            # Combine message with image analyses
            full_message = message
            if image_analyses:
                full_message += "\n\nImage Analyses:\n" + "\n".join(image_analyses)

            # Toggle agentic chain via environment flag
            flag_val = os.getenv("AGENTS_ENABLED", "false") or "false"
            agents_enabled = flag_val.strip().lower() in {
                "1", "true", "yes", "y", "on",
            }
            logger.info(
                "/api/models/chat/stream/with-images -> agents_enabled=%s, images=%d",
                agents_enabled, len(images) if images else 0
            )

            if agents_enabled:
                # Run the MVP chain: Avatar → History → Triage → Summarisation
                orch = Orchestrator()
                agent_out = orch.handle_turn(
                    full_message,
                    ctx=AgentContext(user_id=current_user),
                    llm=None,
                )
                content = agent_out.text or ""

                # Stream minimal content (single burst) for smooth UI
                evt = {"type": "content", "text": content}
                yield f"data: {json.dumps(evt)}\n\n"

                # Finalize with agent meta
                complete_evt = {
                    "type": "complete",
                    "full_response": content,
                    "conversation_id": conversation_id,
                    "model_used": "agentic/orchestrator",
                    "agent_enabled": True,
                    "agent": agent_out.data,
                    "avatar": agent_out.avatar,
                    "images_processed": len(images) if images else 0,
                }
                yield f"data: {json.dumps(complete_evt)}\n\n"
            else:
                # Default: existing LLM flow
                response = await abstraction_layer.process_message(
                    message=full_message,
                    conversation_id=conversation_id,
                    model_override=model_id
                )

                content = response["content"]

                # Stream the response in larger chunks
                chunk_size = 200
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i+chunk_size]
                    evt = {"type": "content", "text": chunk}
                    yield f"data: {json.dumps(evt)}\n\n"

                # Yield a final 'complete' event
                complete_evt = {
                    "type": "complete",
                    "full_response": content,
                    "conversation_id": conversation_id,
                    "model_used": response.get("model"),
                    "agent_enabled": False,
                    "images_processed": len(images) if images else 0,
                }
                yield f"data: {json.dumps(complete_evt)}\n\n"

        except Exception as e:
            # Yield an error event if something goes wrong
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
