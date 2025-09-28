import os
import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import (
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    HTTPException,
)
from fastapi.routing import APIRouter
import aiofiles

# Try absolute imports first; if that fails (dev), extend sys.path
try:
    from utils.file_validator import FileValidator
    from services.voice_service import get_voice_service
    from services.llm_router import get_llm_router, AgentType
    from services.clinical_codes_cache import (
        get_clinical_codes_for_symptoms,
    )
    from jose import JWTError, jwt
    import auth as _auth
    from services.agents import (
        Orchestrator as _Orchestrator,
        AgentContext as _AgentContext,
    )
except Exception:
    import sys as _sys
    from pathlib import Path as _Path

    _sys.path.insert(0, str(_Path(__file__).parent.parent))
    from utils.file_validator import FileValidator
    from services.voice_service import get_voice_service
    from services.llm_router import get_llm_router, AgentType
    try:
        from services.clinical_codes_cache import (
            get_clinical_codes_for_symptoms,
        )
    except Exception:
        get_clinical_codes_for_symptoms = None  # type: ignore
    from jose import JWTError, jwt
    try:
        import auth as _auth
    except Exception:
        _auth = None
    try:
        from services.agents import (
            Orchestrator as _Orchestrator,
            AgentContext as _AgentContext,
        )
    except Exception:
        _Orchestrator = None  # type: ignore
        _AgentContext = None  # type: ignore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

# JWT Configuration: reuse app's auth settings with safe dev fallback
# Note: SECRET_KEY is loaded via auth.py, which supports .env or dev fallback
JWT_EXPIRATION_HOURS = 24
# Load JWT settings from auth if available; otherwise use env/dev defaults
JWT_SECRET = (
    getattr(_auth, "SECRET_KEY", None)
    if "_auth" in globals() and _auth
    else None
) or os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or (
    "dev-secret-change-me"
)
JWT_ALGORITHM = (
    getattr(_auth, "ALGORITHM", None)
    if "_auth" in globals() and _auth
    else None
) or os.getenv("JWT_ALGORITHM") or os.getenv("ALGORITHM") or "HS256"

# Feature flags (defaults keep current behavior unchanged)
VOICE_INCLUDE_CODES_IN_WS = (
    os.getenv("VOICE_INCLUDE_CODES_IN_WS", "false").strip().lower() == "true"
)
VOICE_INCLUDE_AVATAR_IN_WS = (
    os.getenv("VOICE_INCLUDE_AVATAR_IN_WS", "false").strip().lower() == "true"
)
VOICE_DEFAULT_AVATAR = os.getenv("VOICE_DEFAULT_AVATAR", "doctor")

# Agents flag shared with chat
AGENTS_ENABLED = (
    os.getenv("AGENTS_ENABLED", "false").strip().lower()
    in {"1", "true", "yes"}
)


def _extract_codes_minimal_from_text(text: str):
    """
    Produce a compact list of clinical codes
    [{code, system, display}] from free text using the MVP cache via
    get_clinical_codes_for_symptoms, if available. Returns [] on any
    failure.
    """
    try:
        if not text:
            return []
        if (
            'get_clinical_codes_for_symptoms' not in globals()
            or not get_clinical_codes_for_symptoms
        ):
            return []
        report = get_clinical_codes_for_symptoms([text])
        codes = report.get("clinical_codes", []) or []
        # Minimize payload to essential fields
        minimized = []
        for c in codes:
            try:
                minimized.append(
                    {
                        "code": c.get("code"),
                        "system": c.get("system"),
                        "display": c.get("display"),
                    }
                )
            except Exception:
                continue
        return minimized
    except Exception:
        return []


def secure_filename(filename: str, max_length: int = 100) -> str:
    """
    Secure filename sanitization to prevent path traversal attacks
    
    Args:
        filename: Original filename from upload
        max_length: Maximum allowed filename length
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return "unnamed_file"
    
    # Remove path separators and dangerous characters
    filename = re.sub(r'[<>:"|?*]', '', filename)
    filename = re.sub(r'[\\/]', '_', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length-len(ext)] + ext
    
    # Ensure we have a valid filename
    if not filename or filename in ('', '.', '..'):
        return "unnamed_file"
        
    return filename


def verify_token_voice(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT for voice endpoints (duplicated from main.py)."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            return None
        return payload
    except JWTError:
        return None


def validate_session_id(session_id: str) -> bool:
    """Validate session ID format to prevent injection attacks"""
    if not session_id or len(session_id) > 100:
        return False
    # Allow alphanumeric, hyphens, underscores only
    return re.match(r'^[a-zA-Z0-9_-]+$', session_id) is not None


@router.websocket("/stream/{session_id}")
async def voice_stream_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time voice processing
    
    Protocol:
    1. Client connects with session_id
    2. Client sends auth: {"type": "auth", "token": "jwt_token"}
    3. Client sends audio chunks: {"type": "audio", "data": base64}
    4. Server responds with transcription updates
    5. Client sends {"type": "close"} to end session
    """
    
    # Validate session ID before accepting connection
    if not validate_session_id(session_id):
        await websocket.close(code=1003, reason="Invalid session ID format")
        return
        
    await websocket.accept()
    voice_service = get_voice_service()
    llm_router = get_llm_router()
    authenticated = False
    user_id = "anonymous"
    # Per-connection config (overrides env flags)
    include_codes = VOICE_INCLUDE_CODES_IN_WS
    include_avatar = VOICE_INCLUDE_AVATAR_IN_WS
    avatar_id = VOICE_DEFAULT_AVATAR
    
    try:
        logger.info(f"Voice WebSocket connected: session {session_id}")
        
        # Send welcome message
        await websocket.send_json(
            {
                "type": "status",
                "status": "connected",
                "session_id": session_id,
                "message": (
                    "Voice processing WebSocket connected. "
                    "Please authenticate."
                ),
            }
        )
        
        # Create audio generator for voice service
        async def audio_generator():
            """Generator to yield audio chunks from WebSocket"""
            stream_started = False
            while True:
                try:
                    message = await websocket.receive_json()
                    
                    if message["type"] == "auth":
                        # Handle authentication
                        token = message.get("token")
                        if not token:
                            await websocket.send_json({
                                "type": "error",
                                "error": "Authentication token required",
                            })
                            continue
                            
                        payload = verify_token_voice(token)
                        if not payload:
                            await websocket.send_json({
                                "type": "error",
                                "error": "Invalid authentication token"
                            })
                            continue
                            
                        nonlocal authenticated, user_id
                        authenticated = True
                        user_id = payload.get("sub", "authenticated_user")
                        
                        await websocket.send_json(
                            {
                                "type": "status",
                                "status": "authenticated",
                                "message": (
                                    f"Authenticated as {user_id}"
                                ),
                            }
                        )
                        continue
                        
                    elif message["type"] == "audio":
                        if not authenticated:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "error": (
                                        "Must authenticate before sending"
                                        " audio"
                                    ),
                                }
                            )
                            continue
                            
                        # Validate and decode base64 audio data
                        try:
                            import base64
                            
                            # Validate message has data field
                            if "data" not in message:
                                await websocket.send_json(
                                    {
                                        "type": "error",
                                        "error": (
                                            "Audio message missing 'data'"
                                            " field"
                                        ),
                                    }
                                )
                                continue
                                
                            # Validate data is not too large
                            # (1MB limit per chunk)
                            data_str = message["data"]
                            if len(data_str) > 1400000:  # ~1MB base64 encoded
                                await websocket.send_json(
                                    {
                                        "type": "error",
                                        "error": (
                                            "Audio chunk too large (max 1MB"
                                            " per chunk)"
                                        ),
                                    }
                                )
                                continue
                            
                            audio_data = base64.b64decode(data_str)
                            if not stream_started:
                                stream_started = True
                                await websocket.send_json(
                                    {
                                        "type": "status",
                                        "status": "audio_started",
                                        "message": (
                                            "Audio stream received."
                                            " Transcribing…"
                                        ),
                                    }
                                )
                            yield audio_data
                            
                        except Exception as e:
                            await websocket.send_json({
                                "type": "error",
                                "error": f"Invalid audio data: {str(e)}"
                            })
                            continue
                        
                    elif message["type"] == "close":
                        logger.info(
                            f"Voice stream close requested: {session_id}"
                        )
                        break
                    
                    elif message["type"] == "config":
                        # Optional per-connection config
                        try:
                            cfg = message.get("config", {}) or {}
                            nonlocal include_codes, include_avatar, avatar_id
                            if isinstance(cfg.get("include_codes"), bool):
                                include_codes = bool(cfg["include_codes"])
                            if isinstance(cfg.get("include_avatar"), bool):
                                include_avatar = bool(cfg["include_avatar"])
                            if (
                                isinstance(cfg.get("avatar"), str)
                                and cfg.get("avatar")
                            ):
                                avatar_id = str(cfg["avatar"]).strip()
                            await websocket.send_json(
                                {
                                    "type": "status",
                                    "status": "configured",
                                    "message": (
                                        "Voice session configuration updated"
                                    ),
                                    "config": {
                                        "include_codes": include_codes,
                                        "include_avatar": include_avatar,
                                        "avatar": avatar_id,
                                    },
                                }
                            )
                        except Exception as e:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "error": (
                                        f"Invalid config payload: {str(e)}"
                                    ),
                                }
                            )
                        continue
                        
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "error": f"Unknown message type: {message['type']}"
                        })
                        
                except WebSocketDisconnect:
                    logger.info(f"Voice WebSocket disconnected: {session_id}")
                    break
                except Exception as e:
                    logger.error(f"Error receiving audio: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Audio reception error: {str(e)}"
                    })
                    break

        # Process audio stream with voice service
        async for result in voice_service.process_audio_stream(
            audio_generator(),
            session_id,
            user_id,
        ):
            try:
                # Send transcription results to client
                await websocket.send_json(result)
                
                # If we have a final transcript, optionally process with LLM
                if result.get("type") == "final_transcript" and result.get(
                    "text"
                ):
                    transcript_text = result["text"]
                    
                    # Generate LLM response for the transcript
                    try:
                        messages = [
                            {
                                "role": "user",
                                "content": transcript_text,
                            }
                        ]

                        # If agents enabled, run the MVP orchestrator chain
                        agent_out = None
                        if (
                            AGENTS_ENABLED
                            and '_Orchestrator' in globals()
                            and _Orchestrator
                        ):
                            try:
                                orch = _Orchestrator()
                                ctx = (
                                    _AgentContext(user_id=user_id)
                                    if _AgentContext
                                    else None
                                )
                                agent_out = orch.handle_turn(
                                    transcript_text, ctx=ctx, llm=None
                                )
                                resp_text = agent_out.text or ""
                            except Exception as _e:
                                logger.error(
                                    "Agent orchestrator failed, falling back"
                                    f" to LLM: {_e}"
                                )
                                resp_text = await llm_router.route_request(
                                    messages=messages,
                                    agent_type=AgentType.AVATAR,
                                    session_id=session_id,
                                    user_id=user_id,
                                    complexity_hint="simple",
                                )
                        else:
                            # Use router's safe helper that always returns a
                            # string
                            resp_text = await llm_router.route_request(
                                messages=messages,
                                agent_type=AgentType.AVATAR,
                                session_id=session_id,
                                user_id=user_id,
                                complexity_hint="simple",
                            )

                        if not resp_text:
                            resp_text = (
                                "I'm experiencing technical difficulties. "
                                "Please try again."
                            )

                        # Optionally generate clinical coding report from the
                        # transcript
                        clinical_report = None
                        try:
                            if (
                                'get_clinical_codes_for_symptoms' in globals()
                                and get_clinical_codes_for_symptoms
                            ):
                                report = get_clinical_codes_for_symptoms(
                                    [transcript_text]
                                )
                                # Keep it compact for the UI payload
                                clinical_report = {
                                    "clinical_codes": report.get(
                                        "clinical_codes", []
                                    ),
                                    "differential_diagnoses": report.get(
                                        "differential_diagnoses", []
                                    ),
                                    "summary": report.get(
                                        "report_summary", ""
                                    ),
                                }
                        except Exception as e:
                            logger.error(f"Clinical coding failed: {e}")

                        # Send LLM response to client
                        payload = {
                            "type": "llm_response",
                            "response": resp_text,
                            "model_used": None,
                            "transcript": transcript_text,
                            # Preserve existing clinical_report field
                            "clinical_report": clinical_report,
                        }
                        # Attach agent meta when available
                        if AGENTS_ENABLED and agent_out is not None:
                            try:
                                payload["agent"] = agent_out.data
                                if include_avatar and agent_out.avatar:
                                    payload["avatar"] = agent_out.avatar
                                elif include_avatar and avatar_id:
                                    payload["avatar"] = avatar_id
                            except Exception:
                                pass
                        # Attach small codes payload behind a flag
                        if include_codes:
                            try:
                                payload["clinical"] = {
                                    "codes": _extract_codes_minimal_from_text(
                                        transcript_text
                                    ),
                                    "source": "cache",
                                }
                            except Exception:
                                payload["clinical"] = {"codes": []}
                        # Attach avatar when enabled
                        if include_avatar and avatar_id:
                            payload["avatar"] = avatar_id

                        await websocket.send_json(payload)

                    except Exception as e:
                        logger.error(f"LLM processing failed: {e}")
                        await websocket.send_json(
                            {
                                "type": "error",
                                "error": f"LLM processing failed: {str(e)}",
                            }
                        )
                
            except WebSocketDisconnect:
                logger.info(
                    "Client disconnected during voice processing: %s",
                    session_id,
                )
                break
            except Exception as e:
                logger.error(f"Error sending voice result: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "error": f"WebSocket error: {str(e)}"
            })
        except Exception:
            pass


@router.post("/upload")
async def upload_voice_file(
    file: UploadFile = File(...),
    session_id: Optional[str] = None,
    token: Optional[str] = None
):
    """
    Upload and transcribe audio file
    
    Args:
        file: Audio file (WAV, MP3, etc.)
        session_id: Optional session identifier
        token: Authentication token
        
    Returns:
        Transcription result
    """
    
    # Verify authentication
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication token required",
        )
    
    payload = verify_token_voice(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
        )
    
    user_id = payload.get("sub", "authenticated_user")
    current_session_id = (
        session_id
        or f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    voice_service = get_voice_service()
    
    try:
        # Comprehensive file validation with security checks
        FileValidator.validate_audio_file(file)
        
        # Read file content after validation
        content = await file.read()
        
        # Save uploaded file temporarily with secure filename
        upload_dir = "/tmp/digiclinic_uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Sanitize filename to prevent path traversal
        safe_filename = FileValidator.get_safe_filename(
            file.filename or "audio_upload"
        )
        file_path = os.path.join(
            upload_dir, f"{current_session_id}_{safe_filename}"
        )
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        logger.info(f"Audio file uploaded: {file_path} ({len(content)} bytes)")
        
        # Transcribe the file
        transcription_result = await voice_service.transcribe_audio_file(
            file_path,
            current_session_id,
            user_id
        )
        
        # Clean up temporary file with proper error logging
        try:
            os.remove(file_path)
            logger.info(f"Successfully cleaned up temporary file: {file_path}")
        except FileNotFoundError:
            logger.warning(
                "Temporary file not found during cleanup: %s",
                file_path,
            )
        except PermissionError:
            logger.error(
                "Permission denied when cleaning up temporary file: %s",
                file_path,
            )
        except Exception as e:
            logger.error(
                "Failed to clean up temporary file %s: %s",
                file_path,
                str(e),
            )
        
        # Return transcription result
        return {
            "success": True,
            "session_id": current_session_id,
            "filename": file.filename,
            "transcription": transcription_result,
            "uploaded_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice file upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Voice processing failed: {str(e)}",
        )


@router.get("/health")
async def voice_health_check():
    """Check voice service health"""
    voice_service = get_voice_service()
    
    try:
        health_status = await voice_service.health_check()
        return {
            "success": True,
            "voice_service": health_status,
            "endpoints": {
                "websocket": "/api/voice/stream/{session_id}",
                "upload": "/api/voice/upload",
            },
        }

    except Exception as e:
        logger.error(f"Voice health check failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "voice_service": {"status": "error"}
        }
