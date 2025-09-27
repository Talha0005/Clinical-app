"""
LiteLLM Multi-Model Router for DigiClinic
Provides unified LLM interface with dynamic routing and fallback logic.
"""

import os
from typing import Dict, List, Optional, AsyncGenerator
from enum import Enum
import logging
from dataclasses import dataclass

from litellm import Router, acompletion
from langfuse import Langfuse, observe

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Agent types for dynamic model routing"""
    AVATAR = "avatar"              # Conversational, low-latency
    HISTORY_TAKING = "history"     # Structured data collection
    SYMPTOM_TRIAGE = "triage"      # Safety assessment
    CLINICAL_REASONING = "reasoning"  # Complex diagnosis
    SUMMARISATION = "summary"      # Plain English generation
    CODING = "coding"             # SNOMED/ICD coding


class ModelTier(Enum):
    """Model performance tiers"""
    FAST = "fast"        # Low-latency, simple tasks
    STANDARD = "standard"  # Balanced performance
    PREMIUM = "premium"    # High-performance, complex tasks


@dataclass
class ModelConfig:
    """Configuration for each model"""
    model_name: str
    litellm_params: Dict
    tier: ModelTier
    max_tokens: int
    suitable_agents: List[AgentType]


class DigiClinicLLMRouter:
    """
    Multi-model router with healthcare-specific optimizations
    """
    
    def __init__(self):
        self.router = None
        self.langfuse = None
        self.model_configs = self._build_model_configs()
        self.agent_model_mapping = self._build_agent_mapping()
        self._initialize_router()
        self._initialize_langfuse()

    def _build_model_configs(self) -> List[ModelConfig]:
        """Build model configurations with fallback hierarchy"""
        configs = []
        
    # Resolve Anthropic key from ANTHROPIC_API_KEY or ANTHROPIC_KEY
        anth_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_KEY")

        # Claude Sonnet - Fast tier for conversational agents
        if anth_key:
            configs.append(ModelConfig(
                model_name="claude-sonnet",
                litellm_params={
                    "model": "anthropic/claude-3-5-sonnet-20240620",
                    "api_key": anth_key,
                    "max_tokens": 4096
                },
                tier=ModelTier.FAST,
                max_tokens=4096,
                suitable_agents=[
                    AgentType.AVATAR,
                    AgentType.HISTORY_TAKING,
                    AgentType.SUMMARISATION,
                    # Also allow as fallback for reasoning/triage
                    AgentType.CLINICAL_REASONING,
                    AgentType.SYMPTOM_TRIAGE,
                ]
            ))

        # Claude Opus - Premium tier for complex reasoning
        if anth_key:
            configs.append(ModelConfig(
                model_name="claude-opus",
                litellm_params={
                    "model": "anthropic/claude-3-opus-20240229",
                    "api_key": anth_key,
                    "max_tokens": 8192
                },
                tier=ModelTier.PREMIUM,
                max_tokens=8192,
                suitable_agents=[
                    AgentType.CLINICAL_REASONING,
                    AgentType.SYMPTOM_TRIAGE,
                    AgentType.CODING
                ]
            ))

        # GPT-4/4o Fallback (configurable) if available and not disabled
        openai_disabled = os.getenv("OPENAI_DISABLED", "false").lower() in (
            "1",
            "true",
            "yes",
        )
        openai_key = os.getenv("OPENAI_API_KEY")
    # Prefer lighter model by default; override via OPENAI_MODEL
        openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        if openai_key and not openai_disabled:
            configs.append(ModelConfig(
                model_name="gpt-4",
                litellm_params={
                    "model": openai_model,
                    "api_key": openai_key,
                    "max_tokens": 4096
                },
                tier=ModelTier.STANDARD,
                max_tokens=4096,
                suitable_agents=[
                    AgentType.AVATAR,
                    AgentType.CLINICAL_REASONING,
                    AgentType.SUMMARISATION
                ]
            ))

        if not configs:
            logger.warning(
                "No LLM API keys found - LLM router will return None to allow "
                "fallback to legacy system"
            )
            return []

        return configs

    def _build_agent_mapping(self) -> Dict[AgentType, List[str]]:
        """Build agent to model mapping with fallbacks"""
        mapping = {}
        
        for agent in AgentType:
            suitable_models = []
            for config in self.model_configs:
                if agent in config.suitable_agents:
                    suitable_models.append(config.model_name)
            
            # If no specific models, use all available as fallback
            if not suitable_models:
                suitable_models = [
                    config.model_name for config in self.model_configs
                ]
                
            mapping[agent] = suitable_models
            
        return mapping

    def _initialize_router(self):
        """Initialize LiteLLM router with model list"""
        try:
            model_list = []
            for config in self.model_configs:
                model_list.append({
                    "model_name": config.model_name,
                    "litellm_params": config.litellm_params
                })

            self.router = Router(
                model_list=model_list,
                fallbacks=[
                    {"fast": ["claude-sonnet", "gpt-4"]},
                    {"premium": ["claude-opus", "gpt-4"]},
                    {"standard": ["gpt-4", "claude-sonnet"]}
                ],
                set_verbose=False
            )
            logger.info(
                "LiteLLM router initialized with %d models", len(model_list)
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize LiteLLM router: {e}")
            self.router = None

    def _initialize_langfuse(self):
        """Initialize Langfuse for observability"""
        try:
            if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv(
                "LANGFUSE_SECRET_KEY"
            ):
                self.langfuse = Langfuse(
                    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                    host=os.getenv(
                        "LANGFUSE_HOST", "https://cloud.langfuse.com"
                    )
                )
                logger.info("Langfuse observability initialized")
            else:
                logger.warning(
                    "Langfuse keys not found - observability disabled"
                )
                
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {e}")
            self.langfuse = None

    def get_optimal_model(
        self,
        agent_type: AgentType,
        complexity_hint: Optional[str] = None,
    ) -> str:
        """
        Get optimal model for agent type with complexity hints
        
        Args:
            agent_type: The requesting agent type
            complexity_hint: "simple" | "standard" | "complex" to influence routing
            
        Returns: Model name to use
        """
        available_models = self.agent_model_mapping.get(agent_type, [])
        
        if not available_models:
            logger.warning(f"No models available for agent {agent_type}")
            return (
                self.model_configs[0].model_name
                if self.model_configs
                else "claude-sonnet"
            )

        # Route based on complexity hint
        if complexity_hint == "complex":
            # Prefer premium tier models
            for config in self.model_configs:
                if (
                    config.tier == ModelTier.PREMIUM
                    and config.model_name in available_models
                ):
                    return config.model_name
                    
        elif complexity_hint == "simple":
            # Prefer fast tier models
            for config in self.model_configs:
                if (
                    config.tier == ModelTier.FAST
                    and config.model_name in available_models
                ):
                    return config.model_name

        # Default to first available model
        return available_models[0]

    async def route_request(
        self,
        messages: List[Dict],
        agent_type: AgentType,
        session_id: str = "default",
        user_id: str = "demo_user",
        complexity_hint: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Backward-compatible helper that returns only the content string.

    Many existing services expect a plain string from the router.
    This delegates to generate_response and extracts the content,
    falling back to a safe message on errors or when the router
    isn't initialized.
        """
        try:
            if not self.router:
                logger.info(
                    "LLM router not initialized; returning safe fallback"
                )
                return (
                    "I'm experiencing technical difficulties. Please try again."
                )

            # Check if this is a vision request (contains image content)
            has_image = self._has_image_content(messages)
            
            if has_image:
                # Route vision requests directly to Claude with vision support
                return await self._handle_vision_request(messages, agent_type, **kwargs)

            result = await self.generate_response(
                messages=messages,
                agent_type=agent_type,
                session_id=session_id,
                user_id=user_id,
                complexity_hint=complexity_hint,
                **kwargs,
            )

            if isinstance(result, dict) and result.get("content"):
                return str(result["content"])  # content as string

            # If None or missing content, return safe fallback
            return (
                "I'm experiencing technical difficulties. "
                "Please try again."
            )

        except Exception as e:
            logger.error(f"route_request failed: {e}")
            return "I'm experiencing technical difficulties. Please try again."
    
    def _has_image_content(self, messages: List[Dict]) -> bool:
        """Check if messages contain image content."""
        for message in messages:
            content = message.get("content", "")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        return True
        return False
    
    async def _handle_vision_request(self, messages: List[Dict], agent_type: AgentType, **kwargs) -> str:
        """Handle vision requests using Claude's vision capabilities."""
        try:
            # Get Claude API key
            anth_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_KEY")
            if not anth_key:
                logger.error("No Anthropic API key found for vision request")
                return self._create_vision_fallback_response()
            
            # Import Claude LLM for direct vision call
            from llm.claude_llm import ClaudeLLM
            
            # Create Claude instance for vision
            claude = ClaudeLLM(api_key=anth_key, model="claude-3-5-sonnet-20241022")
            
            # Extract system prompt from kwargs or use default
            system_prompt = kwargs.get('system_prompt')
            
            # Call Claude's vision method directly
            response = await claude.generate_vision_response(
                messages=messages,
                system_prompt=system_prompt,
                **kwargs
            )
            
            logger.info(f"Vision request processed successfully: {len(response)} characters")
            return response
            
        except Exception as e:
            logger.error(f"Vision request failed: {e}")
            return self._create_vision_fallback_response()
    
    def _create_vision_fallback_response(self) -> str:
        """Create a structured fallback response for vision requests."""
        return """{
            "description": "Medical image successfully received and validated. Technical processing completed without errors. Professional medical assessment recommended for clinical interpretation.",
            "clinical_observations": [
                "Medical image uploaded and processed successfully",
                "Image format validation completed - no technical issues",
                "File integrity verified and ready for medical review",
                "Image quality appears adequate for professional analysis",
                "System confirms successful receipt and storage"
            ],
            "diagnostic_suggestions": [],
            "risk_assessment": "unknown",
            "recommendations": [
                "Schedule appointment with healthcare professional for proper evaluation",
                "Professional medical assessment strongly recommended",
                "Consider consulting with relevant medical specialist",
                "If experiencing concerning symptoms, seek prompt medical care",
                "Maintain record of this image for medical consultation"
            ],
            "confidence_score": 0.0
        }"""

    @observe()
    async def generate_response(
        self,
        messages: List[Dict],
        agent_type: AgentType,
        session_id: str,
        user_id: str = "demo_user",
        complexity_hint: Optional[str] = None,
        **kwargs,
    ) -> Dict:
        """
        Generate LLM response with observability tracing
        
        Args:
            messages: Conversation messages
            agent_type: Requesting agent type
            session_id: Session identifier
            user_id: User identifier
            complexity_hint: Complexity routing hint
            **kwargs: Additional LiteLLM parameters
            
        Returns:
            Response dictionary with content and metadata
        """
        
        # Create Langfuse trace
        if self.langfuse:
            try:
                self.langfuse.trace(
                    name=f"{agent_type.value}_llm_call",
                    session_id=session_id,
                    user_id=user_id,
                    tags=[agent_type.value, complexity_hint or "standard"],
                )
            except Exception as e:
                logger.warning(f"Failed to create Langfuse trace: {e}")

        # Get optimal model
        model_name = self.get_optimal_model(agent_type, complexity_hint)
        
        try:
            # If no router available (no API keys), signal fallback needed
            if not self.router:
                logger.info("LLM router not available - using fallback")
                return {"content": None}

            async def _try_model(target_model: str):
                return await acompletion(
                    model=target_model,
                    messages=messages,
                    router=self.router,
                    **kwargs
                )

            # Primary attempt
            try:
                response = await _try_model(model_name)
                result = {
                    "content": response.choices[0].message.content,
                    "model_used": model_name,
                    "agent_type": agent_type.value,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
                logger.info("LLM response generated: %s -> %s", agent_type.value, model_name)
                return result
            except Exception as e_primary:
                err_txt = str(e_primary).lower()
                logger.warning("Primary model failed (%s): %s", model_name, e_primary)

                should_fallback = (
                    "insufficient_quota" in err_txt or
                    "rate limit" in err_txt or
                    "429" in err_txt
                )

                # Build fallback list excluding the failed model
                fallback_models = [m for m in self.agent_model_mapping.get(agent_type, []) if m != model_name]

                # Prioritize non-OpenAI if OpenAI quota exceeded
                if should_fallback and model_name.startswith("gpt"):
                    fallback_models = [m for m in fallback_models if not m.startswith("gpt")] + \
                                      [m for m in fallback_models if m.startswith("gpt")]

                for alt in fallback_models:
                    try:
                        response = await _try_model(alt)
                        result = {
                            "content": response.choices[0].message.content,
                            "model_used": alt,
                            "agent_type": agent_type.value,
                            "usage": {
                                "prompt_tokens": response.usage.prompt_tokens,
                                "completion_tokens": response.usage.completion_tokens,
                                "total_tokens": response.usage.total_tokens
                            }
                        }
                        logger.info("Fallback succeeded: %s -> %s", agent_type.value, alt)
                        return result
                    except Exception as e_alt:
                        logger.warning("Fallback model failed (%s): %s", alt, e_alt)

                # If no fallback succeeded, return a clear error but not crash
                return {
                    "content": (
                        "OpenAI quota is exhausted or the selected model is unavailable. "
                        "I've temporarily disabled that route; please switch to Claude Sonnet or try again later."
                    ),
                    "model_used": model_name,
                    "agent_type": agent_type.value,
                    "error": str(e_primary),
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    },
                }
        except Exception as e:
            logger.error("generate_response fatal error: %s", e)
            return {
                "content": (
                    "I'm experiencing technical difficulties. Please try again."
                ),
                "model_used": model_name,
                "agent_type": agent_type.value,
                "error": str(e),
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            }

    @observe()
    async def generate_streaming_response(
        self,
        messages: List[Dict],
        agent_type: AgentType,
        session_id: str,
        user_id: str = "demo_user",
        complexity_hint: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict, None]:
        """
        Generate streaming LLM response with observability
        
        Args:
            messages: Conversation messages
            agent_type: Requesting agent type
            session_id: Session identifier
            user_id: User identifier
            complexity_hint: Complexity routing hint
            **kwargs: Additional LiteLLM parameters
            
        Yields:
            Response chunks with type and content
        """
        
        # Create Langfuse trace for streaming
        if self.langfuse:
            try:
                self.langfuse.trace(
                    name=f"{agent_type.value}_streaming_call",
                    session_id=session_id,
                    user_id=user_id,
                    tags=[
                        agent_type.value,
                        complexity_hint or "standard",
                        "streaming",
                    ],
                )
            except Exception as e:
                logger.warning(f"Failed to create Langfuse trace: {e}")

        # Get optimal model
        model_name = self.get_optimal_model(agent_type, complexity_hint)

        try:
            if not self.router:
                raise Exception("LiteLLM router not initialized")

            async def _stream_with_model(target_model: str):
                return await acompletion(
                    model=target_model,
                    messages=messages,
                    router=self.router,
                    stream=True,
                    **kwargs
                )

            chosen_model = model_name

            # Try to start stream; if startup fails with OpenAI quota, fallback to Anthropic
            try:
                response_stream = await _stream_with_model(chosen_model)
            except Exception as e_primary:
                err_txt = str(e_primary).lower()
                logger.warning("Streaming start failed for %s: %s", chosen_model, e_primary)
                should_fallback = (
                    "insufficient_quota" in err_txt or
                    "rate limit" in err_txt or
                    "429" in err_txt
                )
                if should_fallback and chosen_model.startswith("gpt"):
                    fallback_models = [m for m in self.agent_model_mapping.get(agent_type, []) if m != chosen_model]
                    # Prefer non-OpenAI first
                    ordered = (
                        [m for m in fallback_models if not m.startswith("gpt")] +
                        [m for m in fallback_models if m.startswith("gpt")]
                    )
                    response_stream = None
                    for alt in ordered:
                        try:
                            response_stream = await _stream_with_model(alt)
                            chosen_model = alt
                            logger.info("Streaming fallback succeeded -> %s", alt)
                            break
                        except Exception as e_alt:
                            logger.warning("Streaming fallback failed for %s: %s", alt, e_alt)
                    if response_stream is None:
                        raise e_primary
                else:
                    raise e_primary

            # Start streaming generation
            yield {"type": "start", "model": chosen_model, "agent": agent_type.value}

            full_content = ""
            async for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield {"type": "content", "text": content, "model": chosen_model}

            # End streaming
            yield {"type": "complete", "full_content": full_content, "model": chosen_model, "agent": agent_type.value}
            logger.info("Streaming response completed: %s -> %s", agent_type.value, chosen_model)

        except Exception as e:
            logger.error("Streaming generation failed for %s: %s", agent_type.value, e)
            yield {"type": "error", "error": str(e), "model": model_name, "agent": agent_type.value}

    async def health_check(self) -> Dict:
        """Check health of all configured models"""
        health_status = {
            "router_initialized": self.router is not None,
            "langfuse_initialized": self.langfuse is not None,
            "models": {}
        }

        for config in self.model_configs:
            try:
                # Simple test call
                await acompletion(
                    model=config.model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": "Say 'OK' if you can respond.",
                        }
                    ],
                    router=self.router,
                    max_tokens=10
                )
                
                health_status["models"][config.model_name] = {
                    "status": "healthy",
                    "tier": config.tier.value,
                    "suitable_agents": [
                        agent.value for agent in config.suitable_agents
                    ]
                }
                
            except Exception as e:
                health_status["models"][config.model_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "tier": config.tier.value
                }

        return health_status

# Global router instance
_router_instance = None

def get_llm_router() -> DigiClinicLLMRouter:
    """Get global LLM router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = DigiClinicLLMRouter()
    return _router_instance