"""
Simple test endpoint for voice-to-text-to-LLM workflow
This bypasses audio processing and directly tests transcript-to-LLM functionality
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
import json
import logging
from auth import verify_token

# Import the LLM router functionality
try:
    from api.chat import llm_router
    from llm.base_llm import LLMFactory
except ImportError as e:
    print(f"Warning: Could not import LLM functionality: {e}")
    llm_router = None

router = APIRouter(prefix="/api/test", tags=["test"])
logger = logging.getLogger(__name__)

@router.websocket("/voice-text/{session_id}")
async def test_voice_text_websocket(websocket: WebSocket, session_id: str, token: str = None):
    """
    Test WebSocket endpoint that accepts text transcripts and returns LLM responses
    This is for testing the voice-to-LLM pipeline without audio processing
    """
    await websocket.accept()
    authenticated = False
    user_id = None
    
    try:
        logger.info(f"Test voice-text WebSocket connected: {session_id}")
        
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle authentication
                if message.get("type") == "auth":
                    try:
                        # Verify token (simplified - normally we'd use the dependency)
                        from jose import jwt
                        from auth import SECRET_KEY, ALGORITHM
                        
                        payload = jwt.decode(message["token"], SECRET_KEY, algorithms=[ALGORITHM])
                        user_id = payload.get("sub")
                        authenticated = True
                        
                        await websocket.send_json({
                            "type": "status",
                            "status": "authenticated",
                            "message": f"Authenticated as {user_id}"
                        })
                        continue
                        
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "error": f"Authentication failed: {str(e)}"
                        })
                        continue
                
                # Handle text transcript
                elif message.get("type") == "transcript":
                    if not authenticated:
                        await websocket.send_json({
                            "type": "error", 
                            "error": "Must authenticate first"
                        })
                        continue
                    
                    transcript_text = message.get("text", "").strip()
                    is_final = message.get("is_final", False)
                    
                    # Echo the transcript back
                    await websocket.send_json({
                        "type": "transcript",
                        "text": transcript_text,
                        "is_final": is_final
                    })
                    
                    # If final transcript, generate LLM response
                    if is_final and transcript_text and llm_router:
                        try:
                            logger.info(f"Generating LLM response for: {transcript_text}")
                            
                            # Prepare messages for LLM
                            messages = [
                                {"role": "user", "content": transcript_text}
                            ]
                            
                            # Generate response using LLM router
                            response = await llm_router.generate_response(
                                messages=messages,
                                model_id="anthropic/claude-3-5-sonnet-20240620",
                                user_id=user_id,
                                conversation_id=session_id
                            )
                            
                            # Send LLM response
                            await websocket.send_json({
                                "type": "llm_response",
                                "response": response.content,
                                "model": "claude-3-5-sonnet"
                            })
                            
                            logger.info("LLM response sent successfully")
                            
                        except Exception as e:
                            logger.error(f"LLM response error: {e}")
                            await websocket.send_json({
                                "type": "error",
                                "error": f"Failed to generate response: {str(e)}"
                            })
                
                elif message.get("type") == "close":
                    logger.info(f"Test WebSocket close requested: {session_id}")
                    break
                    
                else:
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Unknown message type: {message.get('type')}"
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json({
                    "type": "error", 
                    "error": f"Processing error: {str(e)}"
                })
                
    except WebSocketDisconnect:
        logger.info(f"Test WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Test WebSocket error: {e}")
    finally:
        logger.info(f"Test WebSocket connection closed: {session_id}")