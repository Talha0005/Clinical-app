"""
LiteLLM Multi-Model Router for DigiClinic
Provides unified LLM interface with dynamic routing and fallback logic.
"""

import os
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
from enum import Enum
import logging
from dataclasses import dataclass

from litellm import Router, completion, acompletion
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
        
        # Claude Sonnet - Fast tier for conversational agents
        if os.getenv("ANTHROPIC_API_KEY"):
            configs.append(ModelConfig(
                model_name="claude-sonnet",
                litellm_params={
                    "model": "anthropic/claude-3-5-sonnet-20240620",
                    "api_key": os.getenv("ANTHROPIC_API_KEY"),
                    "max_tokens": 4096
                },
                tier=ModelTier.FAST,
                max_tokens=4096,
                suitable_agents=[
                    AgentType.AVATAR, 
                    AgentType.HISTORY_TAKING,
                    AgentType.SUMMARISATION
                ]
            ))

        # Claude Opus - Premium tier for complex reasoning
        if os.getenv("ANTHROPIC_API_KEY"):
            configs.append(ModelConfig(
                model_name="claude-opus",
                litellm_params={
                    "model": "anthropic/claude-3-opus-20240229", 
                    "api_key": os.getenv("ANTHROPIC_API_KEY"),
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

        # GPT-4 Fallback (if available)
        if os.getenv("OPENAI_API_KEY"):
            configs.append(ModelConfig(
                model_name="gpt-4",
                litellm_params={
                    "model": "gpt-4-turbo-preview",
                    "api_key": os.getenv("OPENAI_API_KEY"),
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
            logger.warning("No LLM API keys found - LLM router will return None to allow fallback to legacy system")
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
                suitable_models = [config.model_name for config in self.model_configs]
                
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
                set_verbose=True
            )
            logger.info(f"LiteLLM router initialized with {len(model_list)} models")
            
        except Exception as e:
            logger.error(f"Failed to initialize LiteLLM router: {e}")
            self.router = None

    def _initialize_langfuse(self):
        """Initialize Langfuse for observability"""
        try:
            if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
                self.langfuse = Langfuse(
                    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
                )
                logger.info("Langfuse observability initialized")
            else:
                logger.warning("Langfuse keys not found - observability disabled")
                
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {e}")
            self.langfuse = None

    def get_optimal_model(self, agent_type: AgentType, complexity_hint: Optional[str] = None) -> str:
        """
        Get optimal model for agent type with complexity hints
        
        Args:
            agent_type: The requesting agent type
            complexity_hint: "simple", "standard", "complex" to influence routing
            
        Returns:
            Model name to use
        """
        available_models = self.agent_model_mapping.get(agent_type, [])
        
        if not available_models:
            logger.warning(f"No models available for agent {agent_type}")
            return self.model_configs[0].model_name if self.model_configs else "claude-sonnet"

        # Route based on complexity hint
        if complexity_hint == "complex":
            # Prefer premium tier models
            for config in self.model_configs:
                if config.tier == ModelTier.PREMIUM and config.model_name in available_models:
                    return config.model_name
                    
        elif complexity_hint == "simple":
            # Prefer fast tier models
            for config in self.model_configs:
                if config.tier == ModelTier.FAST and config.model_name in available_models:
                    return config.model_name

        # Default to first available model
        return available_models[0]

    @observe()
    async def generate_response(
        self, 
        messages: List[Dict], 
        agent_type: AgentType,
        session_id: str,
        user_id: str = "demo_user",
        complexity_hint: Optional[str] = None,
        **kwargs
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
        trace = None
        if self.langfuse:
            try:
                trace = self.langfuse.trace(
                    name=f"{agent_type.value}_llm_call",
                    session_id=session_id,
                    user_id=user_id,
                    tags=[agent_type.value, complexity_hint or "standard"]
                )
            except Exception as e:
                logger.warning(f"Failed to create Langfuse trace: {e}")

        # Get optimal model
        model_name = self.get_optimal_model(agent_type, complexity_hint)
        
        try:
            # If no router available (no API keys), return None to signal fallback needed
            if not self.router:
                logger.info(f"LLM router not available - returning None to trigger fallback")
                return None

            # Make LLM call through router
            response = await acompletion(
                model=model_name,
                messages=messages,
                router=self.router,
                **kwargs
            )

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

            logger.info(f"LLM response generated: {agent_type.value} -> {model_name}")
            return result

        except Exception as e:
            logger.error(f"LLM generation failed for {agent_type.value}: {e}")
            
            # Return error response
            return {
                "content": f"I apologize, but I'm experiencing technical difficulties. Please try again.",
                "model_used": model_name,
                "agent_type": agent_type.value,
                "error": str(e),
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
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
        trace = None
        if self.langfuse:
            try:
                trace = self.langfuse.trace(
                    name=f"{agent_type.value}_streaming_call",
                    session_id=session_id,
                    user_id=user_id,
                    tags=[agent_type.value, complexity_hint or "standard", "streaming"]
                )
            except Exception as e:
                logger.warning(f"Failed to create Langfuse trace: {e}")

        # Get optimal model
        model_name = self.get_optimal_model(agent_type, complexity_hint)

        try:
            if not self.router:
                raise Exception("LiteLLM router not initialized")

            # Start streaming generation
            yield {"type": "start", "model": model_name, "agent": agent_type.value}

            response_stream = await acompletion(
                model=model_name,
                messages=messages,
                router=self.router,
                stream=True,
                **kwargs
            )

            full_content = ""
            async for chunk in response_stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield {
                        "type": "content", 
                        "text": content,
                        "model": model_name
                    }

            # End streaming
            yield {
                "type": "complete",
                "full_content": full_content,
                "model": model_name,
                "agent": agent_type.value
            }

            logger.info(f"Streaming response completed: {agent_type.value} -> {model_name}")

        except Exception as e:
            logger.error(f"Streaming generation failed for {agent_type.value}: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "model": model_name,
                "agent": agent_type.value
            }

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
                test_response = await acompletion(
                    model=config.model_name,
                    messages=[{"role": "user", "content": "Say 'OK' if you can respond."}],
                    router=self.router,
                    max_tokens=10
                )
                
                health_status["models"][config.model_name] = {
                    "status": "healthy",
                    "tier": config.tier.value,
                    "suitable_agents": [agent.value for agent in config.suitable_agents]
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