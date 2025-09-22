"""
Multi-Modal Abstraction Layer for DigiClinic
Allows patients to choose and switch between different AI models dynamically
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from fastapi import HTTPException

# LiteLLM for unified interface
try:
    import litellm

    # Don't set langfuse callback to avoid version conflicts
    # litellm.success_callback = ["langfuse"]
    litellm.set_verbose = True
except ImportError:
    print("Warning: LiteLLM not installed. Install with: pip install litellm")

# Import existing services
from .medical_observability import MedicalObservabilityClient


class ModelProvider(Enum):
    """Available model providers for patient selection."""

    CLAUDE_OPUS = "anthropic/claude-3-opus-20240229"
    CLAUDE_SONNET = "anthropic/claude-3-5-sonnet-20241022"
    CLAUDE_HAIKU = "anthropic/claude-3-haiku-20240307"
    GPT4_TURBO = "gpt-4-turbo-preview"
    GPT4O = "gpt-4o"
    GPT35_TURBO = "gpt-3.5-turbo"
    GEMINI_PRO = "gemini/gemini-1.5-pro"
    GEMINI_FLASH = "gemini/gemini-1.5-flash"
    LLAMA3_70B = "together_ai/meta-llama/Llama-3-70b-chat-hf"
    MISTRAL_LARGE = "mistral-large-latest"
    MEDICAL_LLAMA = "ollama/medllama2"  # Specialized medical model
    LOCAL_LLAMA = "ollama/llama3"  # For privacy-conscious patients


@dataclass
class ModelCapabilities:
    """Capabilities and characteristics of each model."""

    name: str
    provider: str
    context_window: int
    supports_vision: bool
    supports_function_calling: bool
    supports_streaming: bool
    medical_specialized: bool
    privacy_level: str  # "cloud", "local", "encrypted"
    cost_per_1k_tokens: float
    speed_rating: int  # 1-5, 5 being fastest
    accuracy_rating: int  # 1-5, 5 being most accurate
    languages: List[str] = field(default_factory=list)
    specialties: List[str] = field(default_factory=list)


class ModelAbstractionLayer:
    """
    Multi-modal abstraction layer for seamless model switching.
    Provides unified interface regardless of underlying model.
    """

    logger = logging.getLogger(__name__)

    # Model capabilities registry
    MODEL_REGISTRY = {
        ModelProvider.CLAUDE_OPUS: ModelCapabilities(
            name="Claude Opus (Most Capable)",
            provider="anthropic",
            context_window=200000,
            supports_vision=True,
            supports_function_calling=True,
            supports_streaming=True,
            medical_specialized=False,
            privacy_level="cloud",
            cost_per_1k_tokens=0.015,
            speed_rating=3,
            accuracy_rating=5,
            languages=["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"],
            specialties=["complex_reasoning", "medical_diagnosis", "research"],
        ),
        ModelProvider.CLAUDE_SONNET: ModelCapabilities(
            name="Claude Sonnet (Balanced)",
            provider="anthropic",
            context_window=200000,
            supports_vision=True,
            supports_function_calling=True,
            supports_streaming=True,
            medical_specialized=False,
            privacy_level="cloud",
            cost_per_1k_tokens=0.003,
            speed_rating=4,
            accuracy_rating=4,
            languages=["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"],
            specialties=["general_consultation", "patient_communication"],
        ),
        ModelProvider.GPT4O: ModelCapabilities(
            name="GPT-4O (Multimodal)",
            provider="openai",
            context_window=128000,
            supports_vision=True,
            supports_function_calling=True,
            supports_streaming=True,
            medical_specialized=False,
            privacy_level="cloud",
            cost_per_1k_tokens=0.01,
            speed_rating=4,
            accuracy_rating=5,
            languages=["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"],
            specialties=["vision_analysis", "medical_imaging", "general_consultation"],
        ),
        ModelProvider.GEMINI_PRO: ModelCapabilities(
            name="Gemini Pro (Google)",
            provider="google",
            context_window=1000000,
            supports_vision=True,
            supports_function_calling=True,
            supports_streaming=True,
            medical_specialized=False,
            privacy_level="cloud",
            cost_per_1k_tokens=0.002,
            speed_rating=5,
            accuracy_rating=4,
            languages=["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"],
            specialties=["long_context", "research", "multimodal"],
        ),
        ModelProvider.MEDICAL_LLAMA: ModelCapabilities(
            name="Medical Llama (Specialized)",
            provider="local",
            context_window=32000,
            supports_vision=False,
            supports_function_calling=True,
            supports_streaming=True,
            medical_specialized=True,
            privacy_level="local",
            cost_per_1k_tokens=0.0,
            speed_rating=3,
            accuracy_rating=4,
            languages=["en"],
            specialties=[
                "medical_diagnosis",
                "clinical_guidelines",
                "drug_interactions",
            ],
        ),
    }

    def __init__(self):
        """Initialize the abstraction layer with all available models."""
        try:
            with open("backend/dat/current_model.json", "r") as f:
                data = json.load(f)
                self.current_model = ModelProvider(data["model"])
        except (FileNotFoundError, KeyError):
            self.current_model = ModelProvider.CLAUDE_SONNET

        # Memory management configuration
        self.MAX_CONVERSATIONS = 1000
        self.MAX_MESSAGES_PER_CONVERSATION = 100
        self.CONVERSATION_TTL_HOURS = 24

        # Initialize storage with metadata for memory management
        self.conversation_history = {}
        self.conversation_metadata = {}  # Stores last_accessed and created timestamps
        self.model_performance_metrics = {}

        # Initialize observability if credentials available
        self._init_observability()
        self._initialize_providers()

    def _init_observability(self):
        """Initialize observability client if credentials available."""
        langfuse_public = os.getenv("LANGFUSE_PUBLIC_KEY")
        langfuse_secret = os.getenv("LANGFUSE_SECRET_KEY")
        langfuse_host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        if langfuse_public and langfuse_secret:
            self.observability = MedicalObservabilityClient(
                langfuse_public_key=langfuse_public,
                langfuse_secret_key=langfuse_secret,
                langfuse_host=langfuse_host,
            )
            self.langfuse = self.observability.langfuse
        else:
            self.observability = None
            self.langfuse = None

    def _initialize_providers(self):
        """Initialize API keys for all providers."""
        # Anthropic
        self.anthropic_key = os.getenv("ANTHROPIC_KEY")

        # OpenAI (if available)
        self.openai_key = os.getenv("OPENAI_API_KEY")

        # Google (if available)
        self.google_key = os.getenv("GOOGLE_API_KEY")

        # Validate that we have at least one API key for model access
        if not any([self.anthropic_key, self.openai_key, self.google_key]):
            self.logger.warning(
                "No API keys found for any AI providers. Medical models may not work properly."
            )

        # Set up LiteLLM with available keys (don't expose keys directly)
        if self.anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = self.anthropic_key
            self.logger.info("✅ Anthropic API key configured")
        else:
            self.logger.warning(
                "❌ No Anthropic API key found - Claude models unavailable"
            )

        if self.openai_key:
            os.environ["OPENAI_API_KEY"] = self.openai_key
            self.logger.info("✅ OpenAI API key configured")
        else:
            self.logger.info("ℹ️ No OpenAI API key found - GPT models unavailable")

        if self.google_key:
            os.environ["GOOGLE_API_KEY"] = self.google_key
            self.logger.info("✅ Google API key configured")
        else:
            self.logger.info("ℹ️ No Google API key found - Gemini models unavailable")

    async def get_available_models(
        self, patient_preferences: Dict = None
    ) -> List[Dict]:
        """
        Get list of available models based on patient preferences.

        Args:
            patient_preferences: Dict with preferences like privacy_required,
                               budget_conscious, needs_vision, language, etc.
        """
        available = []

        for model_enum, capabilities in self.MODEL_REGISTRY.items():
            # Check if we have credentials for this provider
            if not self._has_credentials_for_provider(capabilities.provider):
                continue

            # Filter based on patient preferences
            if patient_preferences:
                if (
                    patient_preferences.get("privacy_required")
                    and capabilities.privacy_level != "local"
                ):
                    continue
                if (
                    patient_preferences.get("needs_vision")
                    and not capabilities.supports_vision
                ):
                    continue
                if (
                    patient_preferences.get("language")
                    and patient_preferences["language"] not in capabilities.languages
                ):
                    continue
                if (
                    patient_preferences.get("budget_conscious")
                    and capabilities.cost_per_1k_tokens > 0.005
                ):
                    continue

            available.append(
                {
                    "id": model_enum.value,
                    "name": capabilities.name,
                    "capabilities": capabilities.__dict__,
                    "recommended_for": capabilities.specialties,
                }
            )

        return available

    def _has_credentials_for_provider(self, provider: str) -> bool:
        """Check if we have credentials for a provider."""
        if provider == "anthropic":
            return bool(self.anthropic_key)
        elif provider == "openai":
            return bool(self.openai_key)
        elif provider == "google":
            return bool(self.google_key)
        elif provider == "local":
            return True  # Assume local models are available
        return False

    async def switch_model(
        self, model_id: str, conversation_id: str, reason: Optional[str] = None
    ) -> Dict:
        """
        Switch to a different model mid-conversation.

        Args:
            model_id: The model to switch to
            conversation_id: Current conversation ID
            reason: Optional reason for switching (for analytics)
        """
        try:
            new_model = ModelProvider(model_id)
            old_model = self.current_model

            # Log the switch with Langfuse
            if self.langfuse:
                self.langfuse.trace(
                    name="model_switch",
                    input={
                        "from_model": old_model.value,
                        "to_model": new_model.value,
                        "reason": reason,
                        "conversation_id": conversation_id,
                    },
                    metadata={"timestamp": datetime.now().isoformat()},
                )

            # Transfer conversation context
            context_summary = await self._summarize_context(conversation_id)

            self.current_model = new_model

            with open("backend/dat/current_model.json", "w") as f:
                json.dump({"model": new_model.value}, f)

            # Warm up the new model with context
            await self._warm_up_model(new_model, context_summary)

            return {
                "success": True,
                "previous_model": old_model.value,
                "current_model": new_model.value,
                "context_transferred": True,
                "message": f"Successfully switched to {self.MODEL_REGISTRY[new_model].name}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to switch model",
            }

    async def _summarize_context(self, conversation_id: str) -> str:
        """Summarize conversation context for model switching."""
        if conversation_id not in self.conversation_history:
            return ""

        history = self.conversation_history[conversation_id]

        # Use a fast model to summarize
        summary_prompt = f"""Summarize this medical consultation concisely:

        {json.dumps(history[-10:], indent=2)}  # Last 10 messages

        Include: patient symptoms, key findings, current diagnosis hypothesis."""

        response = await litellm.acompletion(
            model="claude-3-haiku-20240307",  # Fast model for summaries
            messages=[
                {"role": "system", "content": summary_prompt},
                {"role": "user", "content": "Summarize the above conversation."},
            ],
            max_tokens=500,
        )

        return response.choices[0].message.content

    async def _warm_up_model(self, model: ModelProvider, context: str):
        """Warm up a model with conversation context."""
        if not context:
            return

        warm_up_prompt = f"""You are continuing a medical consultation.
        Previous context: {context}

        Acknowledge you've reviewed the context and are ready to continue."""

        await self.process_message(
            message=warm_up_prompt,
            conversation_id="warmup",
            internal=True,  # Don't show to user
        )

    async def process_message(
        self,
        message: str,
        conversation_id: str,
        image: Optional[bytes] = None,
        audio: Optional[bytes] = None,
        model_override: Optional[str] = None,
        internal: bool = False,
        retry_count: int = 0,
    ) -> Dict:
        """
        Process a message with the current or specified model.

        Args:
            message: Text message
            conversation_id: Conversation ID
            image: Optional image bytes for vision models
            audio: Optional audio bytes for transcription
            model_override: Use specific model for this request
            internal: If True, don't store in history or show to user
        """
        model_to_use = (
            ModelProvider(model_override) if model_override else self.current_model
        )
        self.logger.info(f"Using model: {model_to_use.value}")
        capabilities = self.MODEL_REGISTRY[model_to_use]

        # Prepare the message
        messages = self._prepare_messages(conversation_id, message, not internal)

        # Handle multimodal inputs
        if image and capabilities.supports_vision:
            messages = self._add_image_to_messages(messages, image)

        if audio:
            # Transcribe audio first
            transcript = await self._transcribe_audio(audio)
            messages[-1]["content"] = f"{message}\n\n[Audio transcript: {transcript}]"

        # Select appropriate routing based on model
        model_string = self._get_litellm_model_string(model_to_use)

        # Make the API call with Langfuse tracking
        generation = (
            self.langfuse.generation(
                name=f"chat_{model_to_use.value}",
                input=messages,
                model=model_string,
                model_parameters={
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "stream": capabilities.supports_streaming,
                },
                metadata={
                    "conversation_id": conversation_id,
                    "has_image": bool(image),
                    "has_audio": bool(audio),
                },
            )
            if self.langfuse
            else None
        )

        try:
            # Stream or regular completion based on capabilities
            if capabilities.supports_streaming:
                response = await self._stream_completion(
                    model_string, messages, generation
                )
            else:
                response = await self._regular_completion(
                    model_string, messages, generation
                )

            # Track performance metrics
            self._track_performance(model_to_use, response)

            # Store in history if not internal
            if not internal:
                self._update_conversation_history(
                    conversation_id, message, response["content"]
                )

            return response

        except ConnectionError as e:
            # Network/connection specific error handling
            self.logger.error(f"Connection error in process_message: {e}")
            if not internal:  # Don't retry for internal calls (like comparisons)
                return {
                    "content": "I'm having trouble connecting to the AI service. Please check your internet connection and try again.",
                    "model": model_to_use.value,
                    "error": "connection_error",
                    "error_detail": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "conversation_id": conversation_id,
                }
            raise

        except ValueError as e:
            # Input validation errors
            self.logger.error(f"Input validation error in process_message: {e}")
            if not internal:
                return {
                    "content": "There seems to be an issue with your request format. Please try rephrasing your question.",
                    "model": model_to_use.value,
                    "error": "validation_error",
                    "error_detail": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "conversation_id": conversation_id,
                }
            raise

        except TimeoutError as e:
            # Timeout specific handling
            self.logger.error(f"Timeout error in process_message: {e}")
            if not internal:
                return {
                    "content": "The AI service is taking longer than expected to respond. Please try again.",
                    "model": model_to_use.value,
                    "error": "timeout_error",
                    "error_detail": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "conversation_id": conversation_id,
                }
            raise

        except Exception as e:
            # Fallback to a different model if current fails
            # Prevent infinite recursion with max retry limit
            MAX_RETRIES = 2
            if not model_override and retry_count < MAX_RETRIES and not internal:
                fallback_model = self._get_fallback_model(model_to_use)
                # Don't retry if fallback is the same as current model
                if fallback_model != model_to_use:
                    self.logger.warning(
                        f"Model {model_to_use.value} failed, falling back to {fallback_model.value}. Retry {retry_count + 1}/{MAX_RETRIES}"
                    )
                    return await self.process_message(
                        message=message,
                        conversation_id=conversation_id,
                        image=image,
                        audio=audio,
                        model_override=fallback_model.value,
                        internal=internal,
                        retry_count=retry_count + 1,
                    )

            # Log error and provide medical-appropriate fallback
            self.logger.error(
                f"All model fallbacks exhausted after {retry_count} retries. Final error: {str(e)}"
            )

            if not internal:
                # For medical safety, provide appropriate emergency guidance
                emergency_message = "I'm experiencing technical difficulties. If this is a medical emergency, please call 999 immediately or visit your nearest A&E department."
                return {
                    "content": emergency_message,
                    "model": model_to_use.value,
                    "error": "system_error",
                    "error_detail": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "conversation_id": conversation_id,
                }

            # For internal calls, re-raise the exception
            raise HTTPException(
                status_code=503,
                detail="AI service temporarily unavailable. Please try again later.",
            )

    def _get_litellm_model_string(self, model: ModelProvider) -> str:
        """Convert our model enum to LiteLLM model string."""
        return model.value

    async def _stream_completion(
        self, model: str, messages: List[Dict], generation
    ) -> Dict:
        """Handle streaming completion."""
        full_response = ""

        async for chunk in await litellm.acompletion(
            model=model,
            messages=messages,
            stream=True,
            temperature=0.7,
            max_tokens=2000,
        ):
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
                # Yield chunks for real-time display

        if generation:
            generation.end(output=full_response)

        return {"content": full_response, "model": model, "streamed": True}

    async def _regular_completion(
        self, model: str, messages: List[Dict], generation
    ) -> Dict:
        """Handle regular (non-streaming) completion."""
        response = await litellm.acompletion(
            model=model, messages=messages, temperature=0.7, max_tokens=2000
        )

        content = response.choices[0].message.content

        if generation:
            generation.end(output=content)

        return {"content": content, "model": model, "streamed": False}

    def _prepare_messages(
        self, conversation_id: str, message: str, include_history: bool
    ) -> List[Dict]:
        """Prepare messages for the model."""
        messages = []

        # System prompt based on current model
        system_prompt = self._get_system_prompt()
        messages.append({"role": "system", "content": system_prompt})

        # Add conversation history if needed
        if include_history and conversation_id in self.conversation_history:
            for msg in self.conversation_history[conversation_id][
                -10:
            ]:  # Last 10 messages
                messages.append(msg)

        # Add current message
        messages.append({"role": "user", "content": message})

        return messages

    def _get_system_prompt(self) -> str:
        """Get appropriate system prompt for current model."""
        base_prompt = """You are a medical AI assistant in the DigiClinic platform.
        You provide evidence-based medical guidance while being empathetic and clear.
        Always remind patients to seek immediate medical attention for emergencies."""

        # Add model-specific instructions
        capabilities = self.MODEL_REGISTRY[self.current_model]

        if capabilities.medical_specialized:
            base_prompt += "\nYou have specialized medical training. Use clinical terminology when appropriate."

        if capabilities.supports_vision:
            base_prompt += "\nYou can analyze medical images. Describe what you see clearly and note any concerning features."

        return base_prompt

    def _add_image_to_messages(self, messages: List[Dict], image: bytes) -> List[Dict]:
        """Add image to messages for vision models."""
        import base64

        # Encode image to base64
        image_base64 = base64.b64encode(image).decode("utf-8")

        # Add to last user message
        messages[-1]["content"] = [
            {"type": "text", "text": messages[-1]["content"]},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
            },
        ]

        return messages

    async def _transcribe_audio(self, audio: bytes) -> str:
        """Transcribe audio using AssemblyAI."""
        import assemblyai as aai

        aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        transcriber = aai.Transcriber()

        # Save audio temporarily
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio)
            tmp_path = tmp.name

        # Transcribe
        transcript = transcriber.transcribe(tmp_path)

        # Clean up
        os.unlink(tmp_path)

        return transcript.text if transcript else ""

    def _track_performance(self, model: ModelProvider, response: Dict):
        """Track model performance metrics."""
        if model not in self.model_performance_metrics:
            self.model_performance_metrics[model] = {
                "total_requests": 0,
                "total_tokens": 0,
                "errors": 0,
                "average_latency": 0,
            }

        metrics = self.model_performance_metrics[model]
        metrics["total_requests"] += 1
        # Add more metrics as needed

    def _update_conversation_history(
        self, conversation_id: str, user_message: str, assistant_message: str
    ):
        """Update conversation history with memory management."""
        # Clean up expired conversations before adding new ones
        self._cleanup_expired_conversations()

        current_time = time.time()

        # Initialize conversation if new
        if conversation_id not in self.conversation_history:
            # Check if we're at capacity
            if len(self.conversation_history) >= self.MAX_CONVERSATIONS:
                self._evict_oldest_conversation()

            self.conversation_history[conversation_id] = []
            self.conversation_metadata[conversation_id] = {
                "created": current_time,
                "last_accessed": current_time,
            }

        # Update last accessed time
        self.conversation_metadata[conversation_id]["last_accessed"] = current_time

        # Add messages
        conversation = self.conversation_history[conversation_id]
        conversation.append({"role": "user", "content": user_message})
        conversation.append({"role": "assistant", "content": assistant_message})

        # Enforce max messages per conversation (keep most recent)
        if len(conversation) > self.MAX_MESSAGES_PER_CONVERSATION:
            # Remove oldest messages but keep system messages
            messages_to_remove = len(conversation) - self.MAX_MESSAGES_PER_CONVERSATION
            self.conversation_history[conversation_id] = conversation[
                messages_to_remove:
            ]

    def _cleanup_expired_conversations(self):
        """Remove conversations older than TTL."""
        current_time = time.time()
        ttl_seconds = self.CONVERSATION_TTL_HOURS * 3600
        expired_conversations = []

        for conv_id, metadata in self.conversation_metadata.items():
            if current_time - metadata["last_accessed"] > ttl_seconds:
                expired_conversations.append(conv_id)

        for conv_id in expired_conversations:
            del self.conversation_history[conv_id]
            del self.conversation_metadata[conv_id]
            self.logger.debug(f"Expired conversation {conv_id}")

    def _evict_oldest_conversation(self):
        """Evict the least recently used conversation."""
        if not self.conversation_metadata:
            return

        # Find conversation with oldest last_accessed time
        oldest_conv_id = min(
            self.conversation_metadata.keys(),
            key=lambda x: self.conversation_metadata[x]["last_accessed"],
        )

        del self.conversation_history[oldest_conv_id]
        del self.conversation_metadata[oldest_conv_id]
        self.logger.debug(f"Evicted oldest conversation {oldest_conv_id}")

    def _get_fallback_model(self, failed_model: ModelProvider) -> ModelProvider:
        """Get fallback model if primary fails."""
        fallback_chain = {
            ModelProvider.CLAUDE_OPUS: ModelProvider.CLAUDE_SONNET,
            ModelProvider.CLAUDE_SONNET: ModelProvider.CLAUDE_HAIKU,
            ModelProvider.GPT4O: ModelProvider.GPT4_TURBO,
            ModelProvider.GPT4_TURBO: ModelProvider.GPT35_TURBO,
            ModelProvider.GEMINI_PRO: ModelProvider.GEMINI_FLASH,
        }

        return fallback_chain.get(failed_model, ModelProvider.CLAUDE_HAIKU)

    async def compare_models(
        self, message: str, models: List[str], conversation_id: str
    ) -> Dict:
        """
        Compare responses from multiple models side-by-side.
        Useful for patients to see different perspectives.
        """
        comparisons = {}

        # Run all models in parallel
        tasks = []
        for model_id in models:
            task = self.process_message(
                message=message,
                conversation_id=f"{conversation_id}_compare_{model_id}",
                model_override=model_id,
                internal=True,
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for model_id, response in zip(models, responses):
            if isinstance(response, Exception):
                comparisons[model_id] = {"error": str(response), "success": False}
            else:
                comparisons[model_id] = {
                    "response": response["content"],
                    "success": True,
                    "model_info": self.MODEL_REGISTRY[ModelProvider(model_id)].__dict__,
                }

        return comparisons

    async def get_model_recommendation(self, use_case: str, requirements: Dict) -> str:
        """
        Recommend the best model for a specific use case.

        Args:
            use_case: Type of consultation (e.g., "complex_diagnosis", "mental_health", "nutrition")
            requirements: Dict with requirements like needs_vision, privacy_required, etc.
        """
        recommendations = []

        for model_enum, capabilities in self.MODEL_REGISTRY.items():
            score = 0

            # Check if model is available
            if not self._has_credentials_for_provider(capabilities.provider):
                continue

            # Score based on use case
            if use_case in capabilities.specialties:
                score += 5

            # Score based on requirements
            if requirements.get("needs_vision") and capabilities.supports_vision:
                score += 3
            if (
                requirements.get("privacy_required")
                and capabilities.privacy_level == "local"
            ):
                score += 4
            if requirements.get("speed_priority") and capabilities.speed_rating >= 4:
                score += 2
            if (
                requirements.get("accuracy_priority")
                and capabilities.accuracy_rating >= 4
            ):
                score += 3
            if (
                requirements.get("budget_conscious")
                and capabilities.cost_per_1k_tokens < 0.005
            ):
                score += 2

            recommendations.append((model_enum, score))

        # Sort by score
        recommendations.sort(key=lambda x: x[1], reverse=True)

        if recommendations:
            return recommendations[0][0].value
        return ModelProvider.CLAUDE_SONNET.value  # Default

    def get_current_model(self) -> str:
        """Get the current model."""
        return self.current_model.value


# Singleton instance
_abstraction_layer = None


def get_model_abstraction_layer() -> ModelAbstractionLayer:
    """Get or create the model abstraction layer singleton."""
    global _abstraction_layer
    if _abstraction_layer is None:
        _abstraction_layer = ModelAbstractionLayer()
    return _abstraction_layer
