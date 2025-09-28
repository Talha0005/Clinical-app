"""
Chat service that integrates LLM wrapper with DigiClinic MCP server
Feature 2: LLM Wrapper Component - Service Layer
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.base_llm import LLMFactory, ConversationHistory, BaseLLM
from llm.claude_llm import ClaudeLLM
from .prompts_service import prompts_service
from medical.nhs_terminology import NHSTerminologyServer
from .llm_router import get_llm_router, AgentType
from .direct_llm_service import direct_llm_service


class DigiClinicChatService:
    """
    Chat service that manages conversations with LLM integration
    Handles conversation history that travels between browser and server
    """

    def __init__(self, llm_provider: str = "router", **llm_config):
        # Use LLM router for enhanced multi-model capabilities
        if llm_provider == "router":
            try:
                self.llm_router = get_llm_router()
                # Always create fallback LLM for when router has no API keys
                self.llm = LLMFactory.create_llm("mock", **llm_config)
                self.logger = logging.getLogger(__name__)
                self.logger.info("Chat service initialized with LLM router and fallback LLM")
            except Exception as e:
                self.logger = logging.getLogger(__name__)
                self.logger.error(f"LLM router initialization failed, falling back to legacy LLM: {e}")
                self.llm = LLMFactory.create_llm("mock", **llm_config)
                self.llm_router = None
        else:
            # Legacy single LLM mode
            self.llm: BaseLLM = LLMFactory.create_llm(llm_provider, **llm_config)
            self.llm_router = None
            self.logger = logging.getLogger(__name__)
            
        # NOTE: In-memory storage for prototype. Production systems should use 
        # persistent storage (Redis/PostgreSQL) for conversation scalability
        self.active_conversations: Dict[str, ConversationHistory] = {}
        self.conversations = self.active_conversations  # Alias for compatibility
        
        # Load system prompt from prompts service
        self.prompts_service = prompts_service
        
        # NHS Terminology Server for clinical context
        self.nhs_terminology = None  # Will be initialized when needed

    async def start_conversation(
        self, 
        conversation_id: Optional[str] = None,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> ConversationHistory:
        """
        Start a new conversation or retrieve existing one
        
        Args:
            conversation_id: Optional existing conversation ID
            patient_context: Optional patient information for context
            
        Returns:
            ConversationHistory object
        """
        if conversation_id and conversation_id in self.active_conversations:
            return self.active_conversations[conversation_id]

        # Create new conversation
        new_id = conversation_id or str(uuid.uuid4())
        conversation = ConversationHistory(
            conversation_id=new_id,
            created_at=datetime.now(),
            messages=[],
            metadata={"patient_context": patient_context} if patient_context else None
        )

        # Add system prompt from prompts service
        system_prompt = self.prompts_service.get_active_prompt("system_prompt")
        if system_prompt:
            conversation.add_message("system", system_prompt)

        # Add welcome message from prompts service
        welcome_msg = self.prompts_service.get_active_prompt("welcome_message")
        if welcome_msg:
            conversation.add_message("assistant", welcome_msg)

        self.active_conversations[new_id] = conversation
        self.logger.info(f"Started new conversation: {new_id}")
        
        return conversation

    async def send_message(
        self, 
        conversation_data: Dict[str, Any],
        new_message: str
    ) -> Dict[str, Any]:
        """
        Send a message and get LLM response with NHS terminology context
        
        Args:
            conversation_data: Conversation history from browser
            new_message: New user message
            
        Returns:
            Updated conversation data with LLM response
        """
        try:
            # Reconstruct conversation from browser data
            conversation = ConversationHistory.from_dict(conversation_data)
            
            # Update our active conversations cache
            self.active_conversations[conversation.conversation_id] = conversation

            self.logger.info(f"Processing message in conversation {conversation.conversation_id}")

            # Generate LLM response using direct AI service for real responses
            messages = []
            for msg in conversation.messages:
                messages.append({"role": msg.role, "content": msg.content})
            messages.append({"role": "user", "content": new_message})
            
            # Use direct LLM service for real AI responses
            self.logger.info("Using direct LLM service for real AI responses")
            try:
                direct_response = await direct_llm_service.generate_response(
                    messages=messages,
                    model_preference="anthropic"
                )
                if direct_response and direct_response.get("content"):
                    response = direct_response["content"]
                    self.logger.info(f"Direct AI response: {direct_response.get('model_used')} -> {response[:100]}...")
                else:
                    self.logger.info("Direct AI failed - falling back to mock LLM")
                    response = await self.llm.generate_response(conversation, new_message)
            except Exception as e:
                self.logger.warning(f"Direct AI service failed: {e} - falling back to mock LLM")
                response = await self.llm.generate_response(conversation, new_message)

            self.logger.info(f"Generated response: {response[:100]}...")

            # Add the new user message and assistant response to conversation history
            conversation.add_message("user", new_message)
            conversation.add_message("assistant", response)
            
            # Update the active conversations cache with the updated conversation
            self.active_conversations[conversation.conversation_id] = conversation

            # Return updated conversation data for browser
            return {
                "success": True,
                "conversation": conversation.to_dict(),
                "response": response
            }

        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "conversation": conversation_data  # Return original data
            }

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation data for browser"""
        if conversation_id in self.active_conversations:
            conversation = self.active_conversations[conversation_id]
            return conversation.to_dict()
        return None

    def get_llm_info(self) -> Dict[str, Any]:
        """Get information about current LLM"""
        return self.llm.get_model_info()

    def switch_llm(self, provider: str, **config) -> bool:
        """
        Switch to a different LLM provider
        
        Args:
            provider: New LLM provider name
            **config: Configuration for new LLM
            
        Returns:
            True if successful, False if failed
        """
        try:
            new_llm = LLMFactory.create_llm(provider, **config)
            if new_llm.validate_config():
                self.llm = new_llm
                self.logger.info(f"Switched to LLM provider: {provider}")
                return True
            else:
                self.logger.error(f"Invalid configuration for LLM provider: {provider}")
                return False
        except Exception as e:
            self.logger.error(f"Error switching LLM provider: {e}")
            return False

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation from memory"""
        if conversation_id in self.active_conversations:
            del self.active_conversations[conversation_id]
            self.logger.info(f"Cleared conversation: {conversation_id}")
            return True
        return False

    def get_active_conversations(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all active conversations"""
        return {
            conv_id: {
                "created_at": conv.created_at.isoformat(),
                "message_count": len(conv.messages),
                "last_message": conv.messages[-1].timestamp.isoformat() if conv.messages else None
            }
            for conv_id, conv in self.active_conversations.items()
        }

    def create_conversation(self, user_id: str) -> str:
        """Create a new conversation and return its ID"""
        conversation_id = str(uuid.uuid4())
        conversation = ConversationHistory(
            messages=[],
            conversation_id=conversation_id,
            created_at=datetime.now()
        )
        self.active_conversations[conversation_id] = conversation
        self.logger.info(f"Created new conversation: {conversation_id} for user: {user_id}")
        return conversation_id

    def get_conversation_history(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation history for API response"""
        if conversation_id in self.active_conversations:
            conversation = self.active_conversations[conversation_id]
            return {
                "conversation_id": conversation_id,
                "messages": [msg.to_dict() for msg in conversation.messages],
                "created_at": conversation.created_at.isoformat(),
                "message_count": len(conversation.messages)
            }
        return None

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        try:
            llm_healthy = await self.llm.health_check() if hasattr(self.llm, 'health_check') else True
            return {
                "status": "healthy" if llm_healthy else "degraded",
                "llm_provider": self.llm.__class__.__name__,
                "active_conversations": len(self.active_conversations),
                "llm_healthy": llm_healthy
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "active_conversations": len(self.active_conversations)
            }