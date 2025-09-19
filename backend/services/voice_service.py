"""
Voice Service for DigiClinic
Real-time voice processing with AssemblyAI integration
"""

import os
import asyncio
import logging
from typing import Optional, AsyncGenerator, Dict, Any
from dataclasses import dataclass
from enum import Enum

import assemblyai as aai
from langfuse import observe

logger = logging.getLogger(__name__)

class VoiceServiceStatus(Enum):
    """Voice service status states"""
    INACTIVE = "inactive"
    CONNECTING = "connecting" 
    ACTIVE = "active"
    ERROR = "error"

@dataclass
class VoiceConfig:
    """Voice processing configuration"""
    language_code: str = "en-US"
    sample_rate: int = 16000
    punctuate: bool = True
    format_text: bool = True
    dual_channel: bool = False
    speaker_labels: bool = False
    speech_model: str = "best"  # "nano", "best"

class DigiClinicVoiceService:
    """
    Real-time voice processing service for DigiClinic
    Integrates with AssemblyAI for speech-to-text transcription
    """

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        self.status = VoiceServiceStatus.INACTIVE
        self.transcriber = None
        self._initialize_assemblyai()

    def _initialize_assemblyai(self):
        """Initialize AssemblyAI client"""
        try:
            if not self.api_key:
                logger.warning("ASSEMBLYAI_API_KEY not found - voice service will use mock mode")
                return

            # Set API key for AssemblyAI
            aai.settings.api_key = self.api_key
            logger.info("AssemblyAI client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AssemblyAI: {e}")
            self.status = VoiceServiceStatus.ERROR

    @observe()
    async def create_real_time_transcriber(
        self,
        session_id: str,
        user_id: str = "demo_user"
    ) -> Optional[aai.RealtimeTranscriber]:
        """
        Create real-time transcriber with observability
        
        Args:
            session_id: Session identifier for tracing
            user_id: User identifier for tracing
            
        Returns:
            Configured RealtimeTranscriber or None if API key not available
        """
        
        try:
            if not self.api_key:
                logger.warning("No AssemblyAI API key - transcriber will be None")
                return None

            # Configure real-time transcription
            config = aai.RealtimeTranscriptionConfig(
                language_code=self.config.language_code,
                sample_rate=self.config.sample_rate,
                punctuate=self.config.punctuate,
                format_text=self.config.format_text,
                dual_channel=self.config.dual_channel,
                speaker_labels=self.config.speaker_labels,
                speech_model=aai.SpeechModel(self.config.speech_model)
            )

            # Create transcriber
            transcriber = aai.RealtimeTranscriber(config=config)
            
            logger.info(f"Real-time transcriber created for session {session_id}")
            return transcriber

        except Exception as e:
            logger.error(f"Failed to create real-time transcriber: {e}")
            self.status = VoiceServiceStatus.ERROR
            return None

    @observe()
    async def process_audio_stream(
        self,
        audio_generator: AsyncGenerator[bytes, None],
        session_id: str,
        user_id: str = "demo_user"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process streaming audio data and yield transcription results
        
        Args:
            audio_generator: Async generator yielding audio bytes
            session_id: Session identifier
            user_id: User identifier
            
        Yields:
            Transcription results and status updates
        """
        
        transcriber = None
        audio_task = None  # Initialize audio_task at function scope
        
        try:
            # Create transcriber
            transcriber = await self.create_real_time_transcriber(session_id, user_id)
            
            if not transcriber:
                # No API key mode for development
                yield {
                    "type": "status",
                    "status": "no_api_key",
                    "message": "Voice service requires ASSEMBLYAI_API_KEY environment variable"
                }
                return

            # Start real transcription
            self.status = VoiceServiceStatus.CONNECTING
            yield {
                "type": "status",
                "status": self.status.value,
                "message": "Connecting to AssemblyAI transcription service"
            }

            # Connect to AssemblyAI
            await transcriber.connect()
            
            self.status = VoiceServiceStatus.ACTIVE
            yield {
                "type": "status", 
                "status": self.status.value,
                "message": "Real-time transcription active"
            }

            # Create async queue for transcription results
            result_queue = asyncio.Queue()
            
            # Set up transcription event handlers that put results in queue
            def on_partial_transcript(transcript: aai.RealtimePartialTranscript):
                result = {
                    "type": "partial_transcript",
                    "text": transcript.text,
                    "confidence": transcript.confidence,
                    "is_final": False,
                    "audio_start": transcript.audio_start,
                    "audio_end": transcript.audio_end
                }
                # Put result in queue in a thread-safe way
                asyncio.create_task(result_queue.put(result))

            def on_final_transcript(transcript: aai.RealtimeFinalTranscript):
                result = {
                    "type": "final_transcript",
                    "text": transcript.text,
                    "confidence": transcript.confidence,
                    "is_final": True,
                    "audio_start": transcript.audio_start,
                    "audio_end": transcript.audio_end
                }
                # Put result in queue in a thread-safe way
                asyncio.create_task(result_queue.put(result))

            def on_error(error: aai.RealtimeError):
                logger.error(f"AssemblyAI transcription error: {error}")
                result = {
                    "type": "error",
                    "error": str(error),
                    "error_code": error.error_code if hasattr(error, 'error_code') else None
                }
                # Put result in queue in a thread-safe way
                asyncio.create_task(result_queue.put(result))

            # Set event handlers
            transcriber.on_partial_transcript = on_partial_transcript
            transcriber.on_final_transcript = on_final_transcript
            transcriber.on_error = on_error

            # Create tasks for concurrent audio processing and result handling
            
            async def process_audio():
                """Process audio stream in background"""
                try:
                    async for audio_chunk in audio_generator:
                        # Send audio to transcriber
                        transcriber.stream(audio_chunk)
                        # Small delay to allow processing
                        await asyncio.sleep(0.01)
                except Exception as e:
                    logger.error(f"Error processing audio chunk: {e}")
                    await result_queue.put({
                        "type": "error",
                        "error": f"Audio processing error: {str(e)}"
                    })
                finally:
                    # Signal end of audio processing
                    await result_queue.put({"type": "_audio_complete"})
            
            # Start audio processing in background
            audio_task = asyncio.create_task(process_audio())
            
            # Process results from queue
            audio_complete = False
            while not audio_complete:
                try:
                    # Wait for results with timeout
                    result = await asyncio.wait_for(result_queue.get(), timeout=1.0)
                    
                    if result.get("type") == "_audio_complete":
                        audio_complete = True
                        continue
                        
                    # Yield transcription results to client
                    yield result
                    
                except asyncio.TimeoutError:
                    # Check if audio task is done
                    if audio_task.done():
                        break
                    continue
                except Exception as e:
                    logger.error(f"Error processing result queue: {e}")
                    yield {
                        "type": "error",
                        "error": f"Result processing error: {str(e)}"
                    }

            # Signal end of audio stream
            await transcriber.close()
            
            yield {
                "type": "status",
                "status": "completed", 
                "message": "Audio stream processing completed"
            }

        except Exception as e:
            logger.error(f"Voice processing failed: {e}")
            self.status = VoiceServiceStatus.ERROR
            
            yield {
                "type": "error",
                "error": f"Voice processing failed: {str(e)}"
            }
            
        finally:
            # Clean up audio task and transcriber
            if audio_task and not audio_task.done():
                audio_task.cancel()
                try:
                    await audio_task
                except asyncio.CancelledError:
                    pass
                    
            if transcriber:
                try:
                    await transcriber.close()
                except:
                    pass
            
            self.status = VoiceServiceStatus.INACTIVE

    @observe()
    async def transcribe_audio_file(
        self,
        audio_file_path: str,
        session_id: str,
        user_id: str = "demo_user"
    ) -> Dict[str, Any]:
        """
        Transcribe uploaded audio file
        
        Args:
            audio_file_path: Path to audio file
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            Transcription result with text and metadata
        """
        
        try:
            if not self.api_key:
                return {
                    "text": "",
                    "confidence": 0.0,
                    "status": "no_api_key",
                    "error": "ASSEMBLYAI_API_KEY environment variable required",
                    "duration": 0.0
                }

            # Configure transcription
            config = aai.TranscriptionConfig(
                language_code=self.config.language_code,
                punctuate=self.config.punctuate,
                format_text=self.config.format_text,
                dual_channel=self.config.dual_channel,
                speaker_labels=self.config.speaker_labels,
                speech_model=aai.SpeechModel(self.config.speech_model)
            )

            # Create transcriber and process file
            transcriber = aai.Transcriber(config=config)
            transcript = transcriber.transcribe(audio_file_path)

            # Wait for completion
            while transcript.status not in [aai.TranscriptStatus.completed, aai.TranscriptStatus.error]:
                await asyncio.sleep(1)

            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"Transcription failed: {transcript.error}")

            result = {
                "text": transcript.text,
                "confidence": transcript.confidence,
                "status": "completed",
                "duration": transcript.audio_duration / 1000.0,  # Convert to seconds
                "words": len(transcript.words) if transcript.words else 0
            }

            logger.info(f"File transcription completed: {len(result['text'])} characters")
            return result

        except Exception as e:
            logger.error(f"File transcription failed: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "status": "error",
                "error": str(e),
                "duration": 0.0
            }

    async def health_check(self) -> Dict[str, Any]:
        """Check voice service health"""
        health = {
            "service_status": self.status.value,
            "assemblyai_configured": bool(self.api_key),
            "config": {
                "language_code": self.config.language_code,
                "sample_rate": self.config.sample_rate,
                "speech_model": self.config.speech_model
            }
        }

        # Test API connection if configured
        if self.api_key:
            try:
                # Set API key for AssemblyAI
                aai.settings.api_key = self.api_key
                health["api_connection"] = "configured"
                
            except Exception as e:
                health["api_connection"] = f"error: {str(e)}"
                
        else:
            health["api_connection"] = "not_configured"

        return health

# Global voice service instance
_voice_service_instance = None

def get_voice_service() -> DigiClinicVoiceService:
    """Get global voice service instance"""
    global _voice_service_instance
    if _voice_service_instance is None:
        _voice_service_instance = DigiClinicVoiceService()
    return _voice_service_instance