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
import threading
import queue

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
    # Prefer the new universal realtime model to avoid deprecation errors
    speech_model: str = "universal"


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

            # Build constructor kwargs dynamically to match SDK version
            ctor_kwargs: Dict[str, Any] = {}
            if sample_rate is None:
                sample_rate = self.config.sample_rate
            if on_data is not None:
                ctor_kwargs["on_data"] = on_data
            if on_error is not None:
                ctor_kwargs["on_error"] = on_error
            if on_open is not None:
                ctor_kwargs["on_open"] = on_open
            if on_close is not None:
                ctor_kwargs["on_close"] = on_close
            ctor_kwargs["sample_rate"] = sample_rate

            # Prefer the universal model when the constructor supports it
            try:
                sig = inspect.signature(aai.RealtimeTranscriber)
                if "transcription_model" in sig.parameters:
                    ctor_kwargs["transcription_model"] = "universal"
                elif "speech_model" in sig.parameters:
                    ctor_kwargs["speech_model"] = "universal"
                elif "model" in sig.parameters:
                    ctor_kwargs["model"] = "universal"
                if "encoding" in sig.parameters:
                    # AssemblyAI 0.44.3 expects an AudioEncoding enum.
                    # Prefer aai.types.AudioEncoding.pcm_s16le when available.
                    try:
                        aai_types = getattr(aai, "types", None)
                        audio_enc = (
                            getattr(aai_types, "AudioEncoding", None)
                            if aai_types is not None
                            else None
                        )
                        if (
                            audio_enc is not None
                            and hasattr(audio_enc, "pcm_s16le")
                        ):
                            ctor_kwargs["encoding"] = audio_enc.pcm_s16le
                        else:
                            # Fallback: let SDK default if enum unavailable
                            pass
                    except Exception:
                        pass
            except Exception:
                # If introspection fails, continue with minimal args
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
            # Prefer the new Streaming v3 API when available
            try:
                if not self.api_key:
                    raise RuntimeError("No API key for streaming v3")
                from assemblyai.streaming import v3 as aai_stream_v3

                result_queue: asyncio.Queue = asyncio.Queue()

                # Capture loop reference for thread-safe enqueues
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.get_event_loop()

                def _enqueue_threadsafe(item: Dict[str, Any]):
                    try:
                        loop.call_soon_threadsafe(
                            result_queue.put_nowait, item
                        )
                    except Exception as e:
                        try:
                            asyncio.run_coroutine_threadsafe(
                                result_queue.put(item), loop
                            )
                        except Exception:
                            logger.error(f"Failed to enqueue result: {e}")

                # Event handlers
                def on_begin(_client, event):
                    _enqueue_threadsafe(
                        {
                            "type": "status",
                            "status": VoiceServiceStatus.ACTIVE.value,
                            "message": (
                                "Session started: "
                                f"{getattr(event, 'id', '')}"
                            ),
                        }
                    )

                def on_turn(_client, event):
                    try:
                        transcript = getattr(event, "transcript", "")
                        end_of_turn = bool(
                            getattr(event, "end_of_turn", False)
                        )
                        result = {
                            "type": (
                                "final_transcript" if end_of_turn
                                else "partial_transcript"
                            ),
                            "text": transcript or "",
                            "confidence": getattr(
                                event, "end_of_turn_confidence", None
                            ),
                            "is_final": end_of_turn,
                            # Universal streaming doesn't expose
                            # audio_start/end; omit
                        }
                        _enqueue_threadsafe(result)
                    except Exception as e:
                        _enqueue_threadsafe({
                            "type": "error",
                            "error": f"Turn handling error: {e}",
                        })

                def on_terminated(_client, event):
                    _enqueue_threadsafe(
                        {
                            "type": "status",
                            "status": "completed",
                            "message": "Audio stream processing completed",
                        }
                    )

                def on_stream_error(_client, error):
                    _enqueue_threadsafe(
                        {
                            "type": "error",
                            "error": str(error),
                            "error_code": getattr(error, "code", None),
                        }
                    )

                # Initialize client
                client = aai_stream_v3.StreamingClient(
                    aai_stream_v3.StreamingClientOptions(
                        api_key=self.api_key,
                        api_host="streaming.assemblyai.com",
                    )
                )
                client.on(aai_stream_v3.StreamingEvents.Begin, on_begin)
                client.on(aai_stream_v3.StreamingEvents.Turn, on_turn)
                client.on(
                    aai_stream_v3.StreamingEvents.Termination, on_terminated
                )
                client.on(aai_stream_v3.StreamingEvents.Error, on_stream_error)

                # Update status: connecting
                self.status = VoiceServiceStatus.CONNECTING
                yield {
                    "type": "status",
                    "status": self.status.value,
                    "message": (
                        "Connecting to AssemblyAI transcription "
                        "service"
                    ),
                }

                # Connect with parameters (Universal Streaming)
                try:
                    client.connect(
                        aai_stream_v3.StreamingParameters(
                            sample_rate=self.config.sample_rate,
                            # For latency-sensitive voice agents,
                            # keep unformatted
                            # format_turns can be enabled if needed
                        )
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to connect StreamingClient (v3): {e}"
                    )
                    # Surface the real error to client and exit gracefully
                    yield {
                        "type": "error",
                        "error": (
                            "Realtime connect failed: "
                            f"{str(e)}. Check ASSEMBLYAI_API_KEY."
                        ),
                    }
                    return

                # Mark active
                self.status = VoiceServiceStatus.ACTIVE
                yield {
                    "type": "status",
                    "status": self.status.value,
                    "message": "Real-time transcription active",
                }

                # Bridge async audio generator -> blocking .stream()
                # via thread + Queue
                byte_queue: "queue.Queue[Optional[bytes]]" = queue.Queue(
                    maxsize=100
                )

                async def feed_audio():
                    try:
                        async for audio_chunk in audio_generator:
                            try:
                                byte_queue.put(audio_chunk, timeout=1.0)
                            except queue.Full:
                                logger.warning(
                                    "Audio queue full, dropping a chunk to"
                                    " keep up"
                                )
                    except Exception as e:
                        await result_queue.put({
                            "type": "error",
                            "error": f"Audio processing error: {e}",
                        })
                    finally:
                        # signal end of audio
                        try:
                            byte_queue.put(None, timeout=1.0)
                        except Exception:
                            pass

                def byte_iter():
                    while True:
                        item = byte_queue.get()
                        if item is None:
                            break
                        yield item

                # Start feeding audio
                audio_task = asyncio.create_task(feed_audio())

                # Start streaming in a background thread
                stream_exc: Dict[str, Any] = {}

                def _run_stream():
                    try:
                        client.stream(byte_iter())
                    except Exception as e:
                        stream_exc["error"] = e

                stream_thread = threading.Thread(
                    target=_run_stream, daemon=True
                )
                stream_thread.start()

                # Consume results until audio complete and stream thread ends
                while True:
                    try:
                        result = await asyncio.wait_for(
                            result_queue.get(), timeout=0.5
                        )
                        yield result
                        # If completed status emitted and stream thread
                        # finished, exit
                        if (
                            result.get("type") == "status"
                            and result.get("status") == "completed"
                        ):
                            break
                    except asyncio.TimeoutError:
                        if not stream_thread.is_alive() and (
                            audio_task.done() if audio_task else True
                        ):
                            break
                        continue

                # Ensure disconnect
                try:
                    client.disconnect(terminate=True)
                except Exception:
                    pass

                # Surface any streaming exception
                if "error" in stream_exc:
                    err = stream_exc["error"]
                    logger.error(f"Streaming v3 error: {err}")
                    yield {
                        "type": "error",
                        "error": f"Realtime streaming error: {err}",
                    }
                    return

                # End of processing for v3 path
                return
            except Exception as v3_err:
                # Fall back to legacy RealtimeTranscriber path only for
                # import-time errors (module missing). If it's an auth or
                # connection error, surface it and return.
                msg = str(v3_err)
                if any(k in msg.lower() for k in [
                    "unauthorized", "invalid api key", "forbidden"
                ]):
                    yield {
                        "type": "error",
                        "error": (
                            "AssemblyAI authorization failed. Please set a"
                            " valid ASSEMBLYAI_API_KEY in backend/.env and"
                            " restart the server."
                        ),
                    }
                    return
                logger.info(
                    "Streaming v3 import/path unavailable, falling back: %s",
                    v3_err,
                )

            # If we reach here, v3 is not usable and we won't use legacy
            yield {
                "type": "error",
                "error": (
                    "AssemblyAI streaming v3 is unavailable in this "
                    "environment. Please upgrade 'assemblyai' package to "
                    ">=0.43 and ensure ASSEMBLYAI_API_KEY is set."
                ),
            }
            return

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

            # Configure transcription with model compatibility across SDKs
            cfg_kwargs: Dict[str, Any] = {
                "language_code": self.config.language_code,
                "punctuate": self.config.punctuate,
                "format_text": self.config.format_text,
                "dual_channel": self.config.dual_channel,
                "speaker_labels": self.config.speaker_labels,
            }
            try:
                cfg_sig = inspect.signature(aai.TranscriptionConfig)
                params = set(cfg_sig.parameters.keys())
                model_value: Any = self.config.speech_model
                # Prefer using SpeechModel if available
                if hasattr(aai, "SpeechModel"):
                    try:
                        model_value = aai.SpeechModel(self.config.speech_model)
                    except Exception:
                        model_value = self.config.speech_model
                if "speech_model" in params:
                    cfg_kwargs["speech_model"] = model_value
                elif "model" in params:
                    cfg_kwargs["model"] = model_value
            except Exception:
                # Fallback: try common param names without introspection
                try:
                    cfg_kwargs["speech_model"] = getattr(
                        aai, "SpeechModel", lambda x: x
                    )(self.config.speech_model)
                except Exception:
                    cfg_kwargs["model"] = self.config.speech_model

            config = aai.TranscriptionConfig(**cfg_kwargs)

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
                "duration": (getattr(transcript, "audio_duration", 0) or 0)
                / 1000.0,
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
        # Determine realtime support: prefer Streaming v3 if available
        v3_supported = False
        try:
            from assemblyai.streaming import v3 as _aai_stream_v3  # type: ignore
            v3_supported = hasattr(_aai_stream_v3, "StreamingClient")
        except Exception:
            v3_supported = False

        health = {
            "service_status": self.status.value,
            "assemblyai_configured": bool(self.api_key),
            # Realtime supported if Streaming v3 is present or legacy transcriber exists
            "realtime_supported": bool(v3_supported or getattr(aai, "RealtimeTranscriber", None)),
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
