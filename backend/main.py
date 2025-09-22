#!/usr/bin/env python3
"""
FastAPI server to serve the React frontend with authentication.
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
# HTTPBearer now imported via auth module
from fastapi.middleware.cors import CORSMiddleware
from middleware.rate_limiter import RateLimitMiddleware, create_rate_limiter
from pydantic import BaseModel, field_validator
from typing import List
# JWT functionality now handled by auth module
from dotenv import load_dotenv
import uvicorn
import logging
import json

# Import chat service - add backend directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from services import get_chat_service
from services.prompts_service import prompts_service
from services.voice_service import get_voice_service
from auth import verify_password, create_access_token, verify_token, ACCESS_TOKEN_EXPIRE_MINUTES
from services.llm_router import get_llm_router
from api.nhs_terminology_api import router as nhs_router
from api.voice import router as voice_router
from api.medical_intelligence import router as medical_intelligence_router
from api.model_selection import router as model_selection_router
from services.medical_observability import init_medical_observability

logger = logging.getLogger(__name__)

# Load environment variables (for local development only)
# Don't load .env in production environments like Railway
if not os.getenv('RAILWAY_ENVIRONMENT_NAME'):
    load_dotenv()

# JWT settings
# Authentication handled by auth.py module

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    username: str

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
    
# Prompts management models
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

class ConversationDataModel(BaseModel):
    """Validation for conversation data from frontend"""
    conversation_id: str
    created_at: str
    messages: List[dict]
    metadata: Optional[dict] = None

# User database from environment variables
# Authentication functions now imported from auth.py module

# Create FastAPI app
app = FastAPI(title="DigiClinic Frontend Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000", "http://127.0.0.1:8080"],  # Restrict to known origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Only allow necessary methods
    allow_headers=["Content-Type", "Authorization"],  # Only allow necessary headers
)

# Include API routers
app.include_router(voice_router)
app.include_router(nhs_router)
app.include_router(medical_intelligence_router)
app.include_router(model_selection_router)

# NHS Service Search endpoints
@app.get("/api/services/search")
async def search_services_by_postcode(
    postcode: str,
    service_types: Optional[str] = None,
    radius: int = 10,
    limit: int = 20
):
    """Search for NHS services near a postcode"""
    try:
        from api.nhs_service_search import NHSServiceSearch
        
        service_types_list = service_types.split(",") if service_types else None
        
        async with NHSServiceSearch() as search_client:
            services = await search_client.search_by_postcode(
                postcode=postcode,
                service_types=service_types_list,
                radius_miles=radius,
                limit=limit
            )
            
            return {
                "success": True,
                "postcode": postcode,
                "radius_miles": radius,
                "services": [service.to_dict() for service in services],
                "count": len(services)
            }
    
    except Exception as e:
        logger.error(f"Service search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/services/types")
async def get_service_types():
    """Get available NHS service types"""
    try:
        from api.nhs_service_search import NHSServiceSearch, NHS_SERVICE_TYPES
        
        async with NHSServiceSearch() as search_client:
            api_types = await search_client.get_service_types()
            
            return {
                "success": True,
                "api_types": api_types,
                "common_types": NHS_SERVICE_TYPES
            }
    
    except Exception as e:
        logger.error(f"Failed to get service types: {e}")
        return {
            "success": False,
            "api_types": [],
            "common_types": NHS_SERVICE_TYPES
        }

@app.get("/api/nhs/test-connection")
async def test_nhs_connection():
    """Test NHS API OAuth connection"""
    try:
        from api.nhs_oauth import get_nhs_oauth_client
        
        oauth_client = await get_nhs_oauth_client()
        if not oauth_client:
            return {
                "success": False,
                "error": "NHS OAuth client not configured. Please set NHS_CLIENT_ID and NHS_CLIENT_SECRET."
            }
        
        async with oauth_client as client:
            success, message = await client.test_connection()
            
            return {
                "success": success,
                "message": message,
                "environment": oauth_client.environment,
                "client_id": oauth_client.client_id[:8] + "..." if oauth_client.client_id else None
            }
    
    except Exception as e:
        logger.error(f"NHS connection test failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/health/llm-router")
async def health_check_llm_router():
    """Health check for LLM router service"""
    try:
        llm_router = get_llm_router()
        health_status = await llm_router.health_check()
        return {
            "success": True,
            "service": "llm_router",
            "status": health_status
        }
    except Exception as e:
        logger.error(f"LLM router health check failed: {e}")
        return {
            "success": False,
            "service": "llm_router", 
            "error": str(e)
        }

@app.get("/api/health/voice")
async def health_check_voice_service():
    """Health check for voice service"""
    try:
        voice_service = get_voice_service()
        health_status = await voice_service.health_check()
        return {
            "success": True,
            "service": "voice_service",
            "status": health_status
        }
    except Exception as e:
        logger.error(f"Voice service health check failed: {e}")
        return {
            "success": False,
            "service": "voice_service",
            "error": str(e)
        }

# Get paths - Railway runs from project root, so handle both scenarios
current_file_dir = os.path.dirname(os.path.abspath(__file__))
# If running from backend/ directory
if os.path.basename(current_file_dir) == "backend":
    project_root = os.path.dirname(current_file_dir)
    backend_dir = current_file_dir
else:
    # If running from project root (Railway deployment)
    project_root = current_file_dir
    backend_dir = os.path.join(current_file_dir, "backend")

frontend_dist = os.path.join(project_root, "frontend", "dist")

# Security: Remove path disclosure in production
logger.info("DigiClinic Phase 2 backend initialization complete")
logger.info(f"Frontend assets available: {os.path.exists(frontend_dist)}")

# Authentication endpoints
@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    
    # Security: No environment variable exposure in logs
    
    if not verify_password(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": request.username}, expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        username=request.username
    )

@app.get("/api/auth/verify")
async def verify_auth(current_user: str = Depends(verify_token)):
    """Verify current authentication status."""
    return {"username": current_user, "authenticated": True}

@app.post("/api/auth/logout")
async def logout():
    """Logout endpoint (token invalidation handled client-side)."""
    return {"message": "Logged out successfully"}

# Chat endpoints
@app.post("/api/chat/send", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest, 
    current_user: str = Depends(verify_token)
):
    """Send a chat message and get AI response."""
    try:
        # Get or create conversation
        conversation_id = request.conversation_id or ""
        service = get_chat_service()
        if conversation_id not in service.conversations:
            conversation_id = service.create_conversation(current_user)
        
        conversation = service.conversations[conversation_id]
        conversation_data = conversation.to_dict()
        
        result = await service.send_message(conversation_data, request.message)
        
        return ChatResponse(
            conversation_id=conversation_id,
            response=result.get("response", ""),
            timestamp=datetime.utcnow().isoformat(),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )

@app.get("/api/chat/history/{conversation_id}")
async def get_chat_history(
    conversation_id: str,
    current_user: str = Depends(verify_token)
):
    """Get conversation history."""
    service = get_chat_service()
    history = service.get_conversation_history(conversation_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return history

@app.get("/api/chat/health")
async def chat_health_check():
    """Check chat service health."""
    service = get_chat_service()
    health = await service.health_check()
    return health


@app.post("/api/chat/stream")
async def stream_chat_message(
    request: ChatRequest,
    current_user: str = Depends(verify_token)
):
    """Stream a chat message response from Claude API."""
    logger.info(f"🎤 Stream chat request from user: {current_user}")
    logger.info(f"🎤 Message: {request.message[:100]}...")
    
    try:
        async def generate_stream():
            logger.info("🔄 Starting stream generation...")
            
            # Get or create conversation
            conversation_id = request.conversation_id or ""
            logger.info(f"🔄 Getting chat service...")
            service = get_chat_service()
            logger.info(f"🔄 Chat service obtained: {service.__class__.__name__}")
            logger.info(f"🔄 LLM type: {service.llm.__class__.__name__ if service.llm else 'None'}")
            
            if conversation_id not in service.conversations:
                logger.info(f"🔄 Creating new conversation for user: {current_user}")
                conversation_id = service.create_conversation(current_user)
                logger.info(f"🔄 Created conversation: {conversation_id}")
            else:
                logger.info(f"🔄 Using existing conversation: {conversation_id}")
            
            conversation = service.conversations[conversation_id]
            logger.info(f"🔄 Conversation has {len(conversation.messages)} messages")
            
            # Check if LLM is available
            if not service.llm:
                logger.error("❌ LLM not available in service")
                error_data = {"error": "LLM not available", "conversation_id": conversation_id}
                yield f'data: {json.dumps(error_data)}\\n\\n'
                return
            
            # Check LLM configuration
            logger.info(f"🔄 LLM config valid: {service.llm.validate_config()}")
            if hasattr(service.llm, 'api_key'):
                api_key_status = "✅ Present" if service.llm.api_key else "❌ Missing"
                logger.info(f"🔄 LLM API key: {api_key_status}")
            
            # Start streaming response
            full_response = ""
            MAX_RESPONSE_LENGTH = 50000  # Limit response to 50KB to prevent memory issues
            start_data = {"type": "start", "conversation_id": conversation_id}
            yield f'data: {json.dumps(start_data)}\n\n'
            logger.info("🚀 Starting LLM streaming...")
            
            try:
                chunk_count = 0
                async for chunk in service.llm.generate_streaming_response(conversation, request.message):
                    chunk_count += 1
                    logger.info(f"📦 Received chunk #{chunk_count}: {chunk}")
                    
                    # Type check: ensure chunk is a dictionary
                    if not isinstance(chunk, dict):
                        logger.error(f"❌ Invalid chunk type: {type(chunk)}, expected dict")
                        continue
                        
                    if "error" in chunk:
                        logger.error(f"❌ LLM error in chunk: {chunk['error']}")
                        error_data = {"error": chunk["error"], "conversation_id": conversation_id}
                        yield f'data: {json.dumps(error_data)}\n\n'
                        return
                    elif chunk.get("type") == "content":
                        text = chunk.get("text", "")
                        logger.info(f"📝 Content chunk: '{text[:50]}...' ({len(text)} chars)")
                        
                        # Check response size limit
                        if len(full_response) + len(text) > MAX_RESPONSE_LENGTH:
                            logger.warning(f"⚠️  Response size limit exceeded for conversation {conversation_id}")
                            error_data = {"error": "Response too long - truncated for safety", "conversation_id": conversation_id}
                            yield f'data: {json.dumps(error_data)}\n\n'
                            break
                            
                        full_response += text
                        content_data = {"type": "content", "text": text, "conversation_id": conversation_id}
                        yield f'data: {json.dumps(content_data)}\n\n'
                    elif chunk.get("type") == "stop":
                        logger.info(f"🏁 Stream complete. Total response length: {len(full_response)}")
                        # Add complete response to conversation history
                        conversation.add_message("assistant", full_response)
                        complete_data = {"type": "complete", "conversation_id": conversation_id, "full_response": full_response}
                        yield f'data: {json.dumps(complete_data)}\n\n'
                        break
                    else:
                        logger.info(f"🔍 Unknown chunk type: {chunk.get('type')}")
                        
                if chunk_count == 0:
                    logger.warning("⚠️  No chunks received from LLM streaming")
                        
            except Exception as e:
                logger.error(f"❌ Streaming error: {str(e)}", exc_info=True)
                error_data = {"error": f"Streaming failed: {str(e)}", "conversation_id": conversation_id}
                yield f'data: {json.dumps(error_data)}\n\n'
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in streaming endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process streaming message"
        )

# Prompts management endpoints
@app.get("/api/prompts", response_model=List[PromptResponse])
async def get_all_prompts(current_user: str = Depends(verify_token)):
    """Get all prompts."""
    prompts = prompts_service.get_all_prompts()
    return [PromptResponse(**prompt_data) for prompt_data in prompts.values()]

@app.get("/api/prompts/{prompt_id}", response_model=PromptResponse)
async def get_prompt(prompt_id: str, current_user: str = Depends(verify_token)):
    """Get a specific prompt by ID."""
    prompt = prompts_service.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt not found: {prompt_id}"
        )
    return PromptResponse(**prompt)

@app.put("/api/prompts/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: str, 
    request: PromptUpdateRequest,
    current_user: str = Depends(verify_token)
):
    """Update a specific prompt."""
    # Check if prompt exists
    existing_prompt = prompts_service.get_prompt(prompt_id)
    if not existing_prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt not found: {prompt_id}"
        )
    
    # Update prompt with non-None values from request
    updates = request.dict(exclude_unset=True)
    success = prompts_service.update_prompt(prompt_id, updates, user_id=current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update prompt"
        )
    
    # Return updated prompt
    updated_prompt = prompts_service.get_prompt(prompt_id)
    return PromptResponse(**updated_prompt)

@app.post("/api/prompts", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(request: PromptCreateRequest, current_user: str = Depends(verify_token)):
    """Create a new prompt."""
    # Check if prompt ID already exists
    existing_prompt = prompts_service.get_prompt(request.id)
    if existing_prompt:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Prompt already exists: {request.id}"
        )
    
    # Create new prompt
    success = prompts_service.create_prompt(request.dict())
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create prompt"
        )
    
    # Return created prompt
    created_prompt = prompts_service.get_prompt(request.id)
    return PromptResponse(**created_prompt)

@app.delete("/api/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str, current_user: str = Depends(verify_token)):
    """Delete a specific prompt."""
    existing_prompt = prompts_service.get_prompt(prompt_id)
    if not existing_prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt not found: {prompt_id}"
        )
    
    success = prompts_service.delete_prompt(prompt_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete prompt"
        )
    
    return {"message": f"Prompt {prompt_id} deleted successfully"}

@app.get("/api/prompts/category/{category}", response_model=List[PromptResponse])
async def get_prompts_by_category(category: str, current_user: str = Depends(verify_token)):
    """Get all prompts in a specific category."""
    prompts = prompts_service.get_prompts_by_category(category)
    return [PromptResponse(**prompt_data) for prompt_data in prompts.values()]

if os.path.exists(frontend_dist):
    # Mount static assets (JS, CSS, images)
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        print(f"✅ Mounted /assets from: {assets_dir}")
    
    # Serve favicon and static files from project root
    @app.get("/favicon.svg")
    async def serve_favicon():
        return FileResponse(os.path.join(project_root, "favicon.svg"))
    
    @app.get("/medical.svg")
    async def serve_medical_icon():
        return FileResponse(os.path.join(project_root, "medical.svg"))
    
    @app.get("/site.webmanifest")
    async def serve_webmanifest():
        return FileResponse(os.path.join(project_root, "site.webmanifest"))
    
    # Serve index.html for root and SPA routing (no auth required for frontend)
    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dist, "index.html"))
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Skip auth for API routes and assets
        if full_path.startswith("api/") or full_path.startswith("assets/"):
            return
        # For SPA routing, serve index.html for non-asset requests
        return FileResponse(os.path.join(frontend_dist, "index.html"))
        
    print(f"✅ Frontend server configured for: {frontend_dist}")
else:
    @app.get("/")
    async def no_build():
        return {
            "error": "Frontend not built", 
            "message": "Run 'cd frontend && npm run build' first",
            "frontend_dist": frontend_dist
        }

@app.on_event("startup")
async def startup_event():
    """Initialize Phase 2 services and check environment variables."""
    print("🚀 DigiClinic Phase 2 - Enhanced Medical Intelligence Starting...")
    print("🔍 Post-startup environment variable check:")
    # Don't expose API key values in logs for security
    print(f"ANTHROPIC_KEY configured: {'✅' if os.getenv('ANTHROPIC_KEY') else '❌'}")
    print(f"OpenAI API configured: {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}")
    print(f"Google API configured: {'✅' if os.getenv('GOOGLE_API_KEY') else '❌'}")
    
    # Initialize Phase 2 Medical Observability
    print("🔬 Initializing Medical Observability...")
    try:
        init_medical_observability(
            langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            langfuse_host=os.getenv("LANGFUSE_HOST"),
            environment=os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")
        )
        print("✅ Medical Observability initialized")
    except Exception as e:
        print(f"⚠️ Medical Observability initialization failed (continuing without): {e}")
    
    print("🎯 Phase 2 Services Available:")
    print("  - Enhanced Clinical Reasoning Agents")
    print("  - NHS Terminology Server Integration (SNOMED CT, ICD-10, dm+d)")
    print("  - Medical Image Analysis with AI Vision")
    print("  - Evidence-Based Medical Knowledge Base") 
    print("  - Medical Compliance & Observability Tracking")
    print("🌟 DigiClinic Phase 2 Ready!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)