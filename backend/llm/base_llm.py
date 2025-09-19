"""
Base LLM wrapper for DigiClinic - Generic interface for swapping LLM providers
Feature 2: LLM Wrapper Component
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class ChatMessage:
    """Represents a single message in a conversation"""
    role: str  # "system", "user", "assistant"
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create from dictionary"""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata")
        )


@dataclass
class ConversationHistory:
    """Manages conversation history that travels between browser and server"""
    messages: List[ChatMessage]
    conversation_id: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a new message to the conversation"""
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata
        )
        self.messages.append(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization to browser"""
        return {
            "conversation_id": self.conversation_id,
            "created_at": self.created_at.isoformat(),
            "messages": [msg.to_dict() for msg in self.messages],
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationHistory':
        """Create from dictionary sent from browser"""
        return cls(
            conversation_id=data["conversation_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            messages=[ChatMessage.from_dict(msg) for msg in data["messages"]],
            metadata=data.get("metadata")
        )

    def get_messages_for_llm(self, max_messages: int = 50) -> List[Dict[str, str]]:
        """Get messages formatted for LLM API calls with history limits"""
        # Keep only the most recent messages to prevent memory/API issues
        recent_messages = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        return [
            {"role": msg.role, "content": msg.content}
            for msg in recent_messages
        ]


class BaseLLM(ABC):
    """
    Abstract base class for LLM implementations
    This allows us to swap out different LLM providers easily
    """

    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.config = kwargs

    @abstractmethod
    async def generate_response(
        self, 
        conversation: ConversationHistory,
        new_message: str,
        **kwargs
    ) -> str:
        """
        Generate a response given conversation history and new message
        
        Args:
            conversation: Current conversation history
            new_message: New user message
            **kwargs: Additional parameters for this LLM
            
        Returns:
            Generated response string
        """
        pass

    @abstractmethod
    async def generate_streaming_response(
        self, 
        conversation: ConversationHistory,
        new_message: str,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Generate a streaming response for real-time chat
        
        Args:
            conversation: Current conversation history
            new_message: New user message
            **kwargs: Additional parameters for this LLM
            
        Yields:
            Chunks of the response as they're generated
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate that this LLM is properly configured"""
        pass

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about this LLM model"""
        return {
            "model_name": self.model_name,
            "provider": self.__class__.__name__,
            "config": {k: v for k, v in self.config.items() if not k.startswith('api_key')}
        }


class MockLLM(BaseLLM):
    """
    Mock LLM implementation for testing and development
    Returns random medical-themed responses
    """

    def __init__(self, **kwargs):
        super().__init__("mock-medical-llm", **kwargs)
        self.responses = [
            "Thank you for sharing that information. Can you tell me more about when these symptoms started?",
            "Based on what you've described, I'd like to ask a few follow-up questions to better understand your condition.",
            "I understand your concern. This type of symptom can have several potential causes. Have you experienced anything similar before?",
            "For your safety, if you're experiencing severe symptoms, please consider contacting your GP or emergency services immediately.",
            "Let me help you understand this better. Can you describe the intensity of what you're experiencing on a scale of 1-10?",
            "That's helpful information. Are you currently taking any medications or have any known allergies I should be aware of?",
            "Based on our conversation, I'd recommend discussing this with your healthcare provider for a proper examination.",
        ]

    async def generate_response(
        self, 
        conversation: ConversationHistory,
        new_message: str,
        **kwargs
    ) -> str:
        """Generate a mock medical response"""
        import random
        
        # Add user message to conversation
        conversation.add_message("user", new_message)
        
        # Simulate processing delay
        import asyncio
        await asyncio.sleep(1)
        
        # Choose a contextual response
        response = random.choice(self.responses)
        
        # Add assistant message to conversation
        conversation.add_message("assistant", response)
        
        return response

    async def generate_streaming_response(
        self, 
        conversation: ConversationHistory,
        new_message: str,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """Generate a streaming mock response"""
        import asyncio
        
        # Don't add user message here - generate_response will handle it
        response = await self.generate_response(conversation, new_message)
        
        # Simulate streaming by yielding word by word with proper format
        words = response.split()
        for word in words:
            yield {"type": "content", "text": f"{word} "}
            await asyncio.sleep(0.1)
            
        # Signal completion
        yield {"type": "stop"}

    def validate_config(self) -> bool:
        """Mock LLM is always valid"""
        return True
    
    async def health_check(self) -> bool:
        """Mock LLM health check - always healthy"""
        return True


class LLMFactory:
    """Factory for creating LLM instances"""
    
    _providers = {
        "mock": MockLLM,
        # We'll add Claude, OpenAI, etc. in future features
    }

    @classmethod
    def create_llm(cls, provider: str, **kwargs) -> BaseLLM:
        """
        Create an LLM instance
        
        Args:
            provider: LLM provider name ("mock", "claude", "openai", etc.)
            **kwargs: Configuration for the LLM
            
        Returns:
            Configured LLM instance
        """
        if provider not in cls._providers:
            raise ValueError(f"Unknown LLM provider: {provider}. Available: {list(cls._providers.keys())}")
        
        llm_class = cls._providers[provider]
        return llm_class(**kwargs)

    @classmethod
    def register_provider(cls, name: str, llm_class: type):
        """Register a new LLM provider"""
        cls._providers[name] = llm_class

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available LLM providers"""
        return list(cls._providers.keys())