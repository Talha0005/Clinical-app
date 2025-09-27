"""
Voice Service for DigiClinic
Real-time voice processing with AssemblyAI integration
"""

import os
import asyncio
import logging
import inspect
from typing import Optional, AsyncGenerator, Dict, Any, Callable
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
        self.last_error_message: Optional[str] = None
        self._initialize_assemblyai()

    def _initialize_assemblyai(self):
        """Initialize AssemblyAI client"""
        try:
            if not self.api_key:
                logger.warning(
                    "ASSEMBLYAI_API_KEY not found - voice service will use "
                    "mock mode",
                )
                return

            # Set API key for AssemblyAI
            aai.settings.api_key = self.api_key
            logger.info("AssemblyAI client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize AssemblyAI: {e}")
            self.last_error_message = (
                f"Failed to initialize AssemblyAI: {e}"
            )
            self.status = VoiceServiceStatus.ERROR

    @observe()
    async def create_real_time_transcriber(
        self,
        session_id: str,
        user_id: str = "demo_user",
        *,
        on_data: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Any], None]] = None,
        on_open: Optional[Callable[[Any], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        sample_rate: Optional[int] = None,
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
                logger.warning(
                    "No AssemblyAI API key - transcriber will be None"
                )
                return None

            # Create transcriber (handle multiple SDK shapes)
            if not hasattr(aai, "RealtimeTranscriber"):
                msg = (
                    "Installed assemblyai SDK lacks RealtimeTranscriber. "
                    "Please upgrade the 'assemblyai' package."
                )
                logger.error(msg)
                self.last_error_message = msg
                self.status = VoiceServiceStatus.ERROR
                return None

            transcriber = None

            # Prefer config-based construction when available
            config_cls = None
            config = None
            if hasattr(aai, "RealtimeTranscriberConfig"):
                config_cls = getattr(aai, "RealtimeTranscriberConfig")
            elif hasattr(aai, "RealtimeTranscriptionConfig"):
                config_cls = getattr(aai, "RealtimeTranscriptionConfig")

            if config_cls is not None:
                try:
                    speech_model = None
                    if hasattr(aai, "SpeechModel"):
                        try:
                            speech_model = aai.SpeechModel(
                                self.config.speech_model
                            )
                        except Exception:
                            speech_model = getattr(
                                aai.SpeechModel,
                                self.config.speech_model,
                                None,
                            )

                    extra_kwargs = (
                        {"speech_model": speech_model}
                        if speech_model is not None
                        else {}
                    )
                    config = config_cls(
                        language_code=self.config.language_code,
                        sample_rate=self.config.sample_rate,
                        punctuate=self.config.punctuate,
                        format_text=self.config.format_text,
                        dual_channel=self.config.dual_channel,
                        speaker_labels=self.config.speaker_labels,
                        **extra_kwargs,
                    )
                except TypeError:
                    # Minimal config for older SDKs
                    config = config_cls(
                        language_code=self.config.language_code,
                        sample_rate=self.config.sample_rate,
                    )

            # Instantiate transcriber using best available API
            try:
                if config is not None:
                    # Older SDKs: pass config object
                    transcriber = aai.RealtimeTranscriber(config=config)
                else:
                    # Newer SDKs (e.g., 0.44.3) require handlers +
                    # sample_rate in constructor
                    ctor_kwargs: Dict[str, Any] = {}
                    if sample_rate is None:
                        sample_rate = self.config.sample_rate
                    # Only include keys if provided (on_open/on_close optional)
                    if on_data is not None:
                        ctor_kwargs["on_data"] = on_data
                    if on_error is not None:
                        ctor_kwargs["on_error"] = on_error
                    if on_open is not None:
                        ctor_kwargs["on_open"] = on_open
                    if on_close is not None:
                        ctor_kwargs["on_close"] = on_close
                    ctor_kwargs["sample_rate"] = sample_rate
                    # Explicitly set PCM16 encoding when available
                    try:
                        if hasattr(aai, "AudioEncoding"):
                            ctor_kwargs["encoding"] = aai.AudioEncoding.pcm16
                    except Exception:
                        pass

                    try:
                        transcriber = aai.RealtimeTranscriber(**ctor_kwargs)
                    except TypeError:
                        # Fallbacks for odd SDKs: try minimal required args
                        transcriber = aai.RealtimeTranscriber(
                            on_data=on_data or (lambda *_: None),
                            on_error=on_error or (lambda *_: None),
                            sample_rate=sample_rate,
                        )
            except Exception as e:
                logger.error(
                    f"Failed to instantiate RealtimeTranscriber: {e}"
                )
                self.last_error_message = (
                    f"Failed to instantiate RealtimeTranscriber: {e}"
                )
                self.status = VoiceServiceStatus.ERROR
                return None

            logger.info(
                f"Real-time transcriber created for session {session_id}"
            )
            return transcriber

        except Exception as e:
            logger.error(f"Failed to create real-time transcriber: {e}")
            self.last_error_message = (
                f"Failed to create real-time transcriber: {e}"
            )
            self.status = VoiceServiceStatus.ERROR
            return None

    @observe()
    async def process_audio_stream(
        self,
        audio_generator: AsyncGenerator[bytes, None],
        session_id: str,
        user_id: str = "demo_user",
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
            # Prepare event handlers and dynamic connect kwargs
            # Create async queue for transcription results
            result_queue: asyncio.Queue = asyncio.Queue()

            # Helper to extract event fields safely across SDK variants
            def _extract_attr(obj: Any, name: str, default: Any = None):
                if hasattr(obj, name):
                    try:
                        return getattr(obj, name)
                    except Exception:
                        return default
                if isinstance(obj, dict):
                    return obj.get(name, default)
                return default

            def on_partial_transcript(transcript: Any):
                result = {
                    "type": "partial_transcript",
                    "text": _extract_attr(transcript, "text", ""),
                    "confidence": _extract_attr(
                        transcript, "confidence", None
                    ),
                    "is_final": False,
                    "audio_start": _extract_attr(
                        transcript, "audio_start", None
                    ),
                    "audio_end": _extract_attr(
                        transcript, "audio_end", None
                    ),
                }
                asyncio.create_task(result_queue.put(result))

            def on_final_transcript(transcript: Any):
                result = {
                    "type": "final_transcript",
                    "text": _extract_attr(transcript, "text", ""),
                    "confidence": _extract_attr(
                        transcript, "confidence", None
                    ),
                    "is_final": True,
                    "audio_start": _extract_attr(
                        transcript, "audio_start", None
                    ),
                    "audio_end": _extract_attr(
                        transcript, "audio_end", None
                    ),
                }
                asyncio.create_task(result_queue.put(result))

            def on_error(error: Any):
                logger.error(f"AssemblyAI transcription error: {error}")
                err_code = _extract_attr(error, "error_code", None)
                result = {
                    "type": "error",
                    "error": str(error),
                    "error_code": err_code,
                }
                asyncio.create_task(result_queue.put(result))

            # Build unified on_data that dispatches to partial/final
            def unified_on_data(event: Any):
                try:
                    cls_name = (
                        event.__class__.__name__
                        if hasattr(event, "__class__")
                        else ""
                    )
                    if isinstance(event, dict):
                        msg_type = (
                            event.get("type")
                            or event.get("message_type")
                            or ""
                        )
                        if "partial" in str(msg_type).lower():
                            on_partial_transcript(event)
                        else:
                            on_final_transcript(event)
                    elif cls_name.lower().find("partial") != -1:
                        on_partial_transcript(event)
                    else:
                        on_final_transcript(event)
                except Exception as e:  # Ensure errors surface
                    on_error(e)

            # Create transcriber (handlers passed for SDKs that require them)
            transcriber = await self.create_real_time_transcriber(
                session_id,
                user_id,
                on_data=unified_on_data,
                on_error=on_error,
                sample_rate=self.config.sample_rate,
            )

            if not transcriber:
                # Could be missing API key or unsupported SDK version
                message = (
                    self.last_error_message
                    or (
                        "Voice service requires ASSEMBLYAI_API_KEY "
                        "environment variable"
                    )
                )
                status = "error" if self.last_error_message else "no_api_key"
                yield {
                    "type": "status",
                    "status": status,
                    "message": message,
                }
                return

            # Start real transcription
            self.status = VoiceServiceStatus.CONNECTING
            yield {
                "type": "status",
                "status": self.status.value,
                "message": "Connecting to AssemblyAI transcription "
                "service",
            }

            # Connect to AssemblyAI: handle sync vs async connect
            try:
                connect_method = getattr(transcriber, "connect")
                if inspect.iscoroutinefunction(connect_method):
                    await connect_method()
                else:
                    connect_method()
            except Exception as e:
                logger.error(f"Failed to connect RealtimeTranscriber: {e}")
                raise

            self.status = VoiceServiceStatus.ACTIVE
            yield {
                "type": "status",
                "status": self.status.value,
                "message": "Real-time transcription active",
            }

            # Create tasks for concurrent audio processing and result handling

            async def process_audio():
                """Process audio stream in background"""
                try:
                    async for audio_chunk in audio_generator:
                        # Resolve best available streaming method
                        stream_method: Optional[Callable] = None
                        for name in (
                            "stream",
                            "send_audio",
                            "send",
                            "send_pcm",
                        ):
                            if hasattr(transcriber, name):
                                stream_method = getattr(transcriber, name)
                                break
                        if stream_method is None:
                            raise RuntimeError(
                                "AssemblyAI SDK missing audio streaming "
                                "method"
                            )

                        try:
                            if inspect.iscoroutinefunction(stream_method):
                                await stream_method(audio_chunk)
                            else:
                                stream_method(audio_chunk)
                        except TypeError:
                            # Some SDKs expect (bytes, sample_rate)
                            if inspect.iscoroutinefunction(stream_method):
                                await stream_method(
                                    audio_chunk, self.config.sample_rate
                                )
                            else:
                                stream_method(
                                    audio_chunk, self.config.sample_rate
                                )
                        # Small delay to allow processing
                        await asyncio.sleep(0.01)
                except Exception as e:
                    logger.error(f"Error processing audio chunk: {e}")
                    await result_queue.put(
                        {
                            "type": "error",
                            "error": f"Audio processing error: {str(e)}",
                        }
                    )
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
                    result = await asyncio.wait_for(
                        result_queue.get(), timeout=1.0
                    )

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
                    logger.error(
                        f"Error processing result queue: {e}"
                    )
                    yield {
                        "type": "error",
                        "error": (
                            f"Result processing error: {str(e)}"
                        ),
                    }

            # Attempt to flush any remaining partials into a final transcript
            try:
                # Prefer an explicit flush/end if the SDK supports it
                if hasattr(transcriber, "flush"):
                    flush_fn = getattr(transcriber, "flush")
                    if inspect.iscoroutinefunction(flush_fn):
                        await flush_fn()
                    else:
                        flush_fn()
                elif hasattr(transcriber, "end"):
                    end_fn = getattr(transcriber, "end")
                    if inspect.iscoroutinefunction(end_fn):
                        await end_fn()
                    else:
                        end_fn()
            except Exception:
                # Non-fatal if flush not supported
                pass

            # Drain results emitted by flush/end for a short window
            try:
                loop = asyncio.get_event_loop()
                deadline = loop.time() + 1.0
                while loop.time() < deadline:
                    try:
                        extra = await asyncio.wait_for(
                            result_queue.get(), timeout=0.2
                        )
                        if extra.get("type") != "_audio_complete":
                            yield extra
                    except asyncio.TimeoutError:
                        break
            except Exception:
                pass

            # Signal end of audio stream and close transcriber
            try:
                if hasattr(transcriber, "close"):
                    if inspect.iscoroutinefunction(transcriber.close):
                        await transcriber.close()
                    else:
                        transcriber.close()
            except Exception:
                pass

            yield {
                "type": "status",
                "status": "completed",
                "message": "Audio stream processing completed",
            }

        except Exception as e:
            logger.error(f"Voice processing failed: {e}")
            self.status = VoiceServiceStatus.ERROR

            yield {
                "type": "error",
                "error": f"Voice processing failed: {str(e)}",
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
                    if hasattr(transcriber, "close"):
                        close_method = getattr(transcriber, "close")
                        if inspect.iscoroutinefunction(close_method):
                            await close_method()
                        else:
                            close_method()
                except Exception:
                    pass

            self.status = VoiceServiceStatus.INACTIVE

    @observe()
    async def transcribe_audio_file(
        self,
        audio_file_path: str,
        session_id: str,
        user_id: str = "demo_user",
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
                    "error": (
                        "ASSEMBLYAI_API_KEY environment variable required"
                    ),
                    "duration": 0.0,
                }

            # Configure transcription
            config = aai.TranscriptionConfig(
                language_code=self.config.language_code,
                punctuate=self.config.punctuate,
                format_text=self.config.format_text,
                dual_channel=self.config.dual_channel,
                speaker_labels=self.config.speaker_labels,
                speech_model=aai.SpeechModel(self.config.speech_model),
            )

            # Create transcriber and process file
            transcriber = aai.Transcriber(config=config)
            transcript = transcriber.transcribe(audio_file_path)

            # Wait for completion
            while transcript.status not in [
                aai.TranscriptStatus.completed,
                aai.TranscriptStatus.error,
            ]:
                await asyncio.sleep(1)

            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(
                    f"Transcription failed: {transcript.error}"
                )

            result = {
                "text": transcript.text,
                "confidence": transcript.confidence,
                "status": "completed",
                # Convert to seconds
                "duration": transcript.audio_duration / 1000.0,
                "words": len(transcript.words) if transcript.words else 0,
            }

            logger.info(
                "File transcription completed: %d characters",
                len(result["text"]),
            )
            return result

        except Exception as e:
            logger.error(f"File transcription failed: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "status": "error",
                "error": str(e),
                "duration": 0.0,
            }

    async def health_check(self) -> Dict[str, Any]:
        """Check voice service health"""
        health = {
            "service_status": self.status.value,
            "assemblyai_configured": bool(self.api_key),
            # Consider realtime supported if RealtimeTranscriber exists,
            # even when config classes are absent
            "realtime_supported": bool(
                getattr(aai, "RealtimeTranscriber", None)
            ),
            "assemblyai_version": getattr(aai, "__version__", "unknown"),
            "config": {
                "language_code": self.config.language_code,
                "sample_rate": self.config.sample_rate,
                "speech_model": self.config.speech_model,
            },
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
