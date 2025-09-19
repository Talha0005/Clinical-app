"""Unit tests for base LLM classes and functionality."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Add backend directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from llm.base_llm import (
    ChatMessage, 
    ConversationHistory, 
    BaseLLM, 
    MockLLM, 
    LLMFactory
)


class TestChatMessage:
    """Test ChatMessage class functionality."""
    
    def test_chat_message_creation(self):
        """Test basic ChatMessage creation."""
        timestamp = datetime.now()
        message = ChatMessage(
            role="user",
            content="Hello, doctor",
            timestamp=timestamp,
            metadata={"test": "value"}
        )
        
        assert message.role == "user"
        assert message.content == "Hello, doctor"
        assert message.timestamp == timestamp
        assert message.metadata == {"test": "value"}
    
    def test_chat_message_to_dict(self):
        """Test ChatMessage dictionary conversion."""
        timestamp = datetime.now()
        message = ChatMessage(
            role="assistant",
            content="Hello, how can I help?",
            timestamp=timestamp
        )
        
        result = message.to_dict()
        
        assert result["role"] == "assistant"
        assert result["content"] == "Hello, how can I help?"
        assert result["timestamp"] == timestamp.isoformat()
        assert result["metadata"] == {}
    
    def test_chat_message_from_dict(self):
        """Test ChatMessage creation from dictionary."""
        timestamp = datetime.now()
        data = {
            "role": "system",
            "content": "You are a medical assistant",
            "timestamp": timestamp.isoformat(),
            "metadata": {"system": True}
        }
        
        message = ChatMessage.from_dict(data)
        
        assert message.role == "system"
        assert message.content == "You are a medical assistant"
        assert message.timestamp == timestamp
        assert message.metadata == {"system": True}
    
    def test_chat_message_roundtrip(self):
        """Test ChatMessage serialization roundtrip."""
        original = ChatMessage(
            role="user",
            content="Test message",
            timestamp=datetime.now(),
            metadata={"test": "data"}
        )
        
        # Convert to dict and back
        dict_data = original.to_dict()
        restored = ChatMessage.from_dict(dict_data)
        
        assert restored.role == original.role
        assert restored.content == original.content
        assert restored.metadata == original.metadata
        # Timestamps should be equal (accounting for microsecond precision)
        assert abs((restored.timestamp - original.timestamp).total_seconds()) < 1


class TestConversationHistory:
    """Test ConversationHistory class functionality."""
    
    def test_conversation_creation(self):
        """Test basic ConversationHistory creation."""
        created_at = datetime.now()
        conversation = ConversationHistory(
            messages=[],
            conversation_id="test-123",
            created_at=created_at,
            metadata={"patient": "john_doe"}
        )
        
        assert conversation.conversation_id == "test-123"
        assert conversation.created_at == created_at
        assert conversation.messages == []
        assert conversation.metadata == {"patient": "john_doe"}
    
    def test_add_message(self):
        """Test adding messages to conversation."""
        conversation = ConversationHistory(
            messages=[],
            conversation_id="test-123",
            created_at=datetime.now()
        )
        
        conversation.add_message("user", "Hello doctor", {"source": "web"})
        
        assert len(conversation.messages) == 1
        message = conversation.messages[0]
        assert message.role == "user"
        assert message.content == "Hello doctor"
        assert message.metadata == {"source": "web"}
        assert isinstance(message.timestamp, datetime)
    
    def test_to_dict(self):
        """Test ConversationHistory dictionary conversion."""
        created_at = datetime.now()
        conversation = ConversationHistory(
            messages=[],
            conversation_id="test-123",
            created_at=created_at,
            metadata={"test": True}
        )
        conversation.add_message("user", "Test message")
        
        result = conversation.to_dict()
        
        assert result["conversation_id"] == "test-123"
        assert result["created_at"] == created_at.isoformat()
        assert result["metadata"] == {"test": True}
        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == "Test message"
    
    def test_from_dict(self):
        """Test ConversationHistory creation from dictionary."""
        created_at = datetime.now()
        data = {
            "conversation_id": "test-456",
            "created_at": created_at.isoformat(),
            "metadata": {"restored": True},
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {}
                }
            ]
        }
        
        conversation = ConversationHistory.from_dict(data)
        
        assert conversation.conversation_id == "test-456"
        assert conversation.created_at == created_at
        assert conversation.metadata == {"restored": True}
        assert len(conversation.messages) == 1
        assert conversation.messages[0].content == "Hello"
    
    def test_get_messages_for_llm(self):
        """Test message formatting for LLM API."""
        conversation = ConversationHistory(
            messages=[],
            conversation_id="test-123",
            created_at=datetime.now()
        )
        
        conversation.add_message("system", "You are a doctor")
        conversation.add_message("user", "I have a headache")
        conversation.add_message("assistant", "Tell me more about your symptoms")
        
        messages = conversation.get_messages_for_llm()
        
        assert len(messages) == 3
        assert messages[0] == {"role": "system", "content": "You are a doctor"}
        assert messages[1] == {"role": "user", "content": "I have a headache"}
        assert messages[2] == {"role": "assistant", "content": "Tell me more about your symptoms"}
    
    def test_get_messages_for_llm_limit(self):
        """Test message history limiting."""
        conversation = ConversationHistory(
            messages=[],
            conversation_id="test-123",
            created_at=datetime.now()
        )
        
        # Add more messages than limit
        for i in range(10):
            conversation.add_message("user", f"Message {i}")
        
        messages = conversation.get_messages_for_llm(max_messages=5)
        
        assert len(messages) == 5
        # Should get the last 5 messages
        assert messages[0]["content"] == "Message 5"
        assert messages[4]["content"] == "Message 9"


class TestMockLLM:
    """Test MockLLM implementation."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a MockLLM instance for testing."""
        return MockLLM()
    
    @pytest.fixture
    def test_conversation(self):
        """Create a test conversation."""
        return ConversationHistory(
            messages=[],
            conversation_id="test-123",
            created_at=datetime.now()
        )
    
    def test_mock_llm_creation(self, mock_llm):
        """Test MockLLM initialization."""
        assert mock_llm.model_name == "mock-medical-llm"
        assert len(mock_llm.responses) > 0
        assert mock_llm.validate_config() is True
    
    @pytest.mark.asyncio
    async def test_generate_response(self, mock_llm, test_conversation):
        """Test MockLLM response generation."""
        initial_message_count = len(test_conversation.messages)
        
        response = await mock_llm.generate_response(
            test_conversation,
            "I have a headache"
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert response in mock_llm.responses
        # Should have added both user and assistant messages
        assert len(test_conversation.messages) == initial_message_count + 2
        assert test_conversation.messages[-2].role == "user"
        assert test_conversation.messages[-2].content == "I have a headache"
        assert test_conversation.messages[-1].role == "assistant"
        assert test_conversation.messages[-1].content == response
    
    @pytest.mark.asyncio
    async def test_generate_streaming_response(self, mock_llm, test_conversation):
        """Test MockLLM streaming response generation."""
        chunks = []
        async for chunk in mock_llm.generate_streaming_response(
            test_conversation,
            "I feel dizzy"
        ):
            chunks.append(chunk)
        
        # Should have content chunks and a stop signal
        content_chunks = [c for c in chunks if c.get("type") == "content"]
        stop_chunks = [c for c in chunks if c.get("type") == "stop"]
        
        assert len(content_chunks) > 0
        assert len(stop_chunks) == 1
        
        # Reconstruct the full response
        full_text = "".join(c.get("text", "") for c in content_chunks).strip()
        assert len(full_text) > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, mock_llm):
        """Test MockLLM health check."""
        health = await mock_llm.health_check()
        assert health is True
    
    def test_get_model_info(self, mock_llm):
        """Test MockLLM model information."""
        info = mock_llm.get_model_info()
        
        assert info["model_name"] == "mock-medical-llm"
        assert info["provider"] == "MockLLM"
        assert isinstance(info["config"], dict)


class TestLLMFactory:
    """Test LLMFactory functionality."""
    
    def test_create_mock_llm(self):
        """Test creating MockLLM via factory."""
        llm = LLMFactory.create_llm("mock")
        
        assert isinstance(llm, MockLLM)
        assert llm.model_name == "mock-medical-llm"
    
    def test_create_unknown_provider(self):
        """Test error handling for unknown provider."""
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            LLMFactory.create_llm("unknown_provider")
    
    def test_get_available_providers(self):
        """Test listing available providers."""
        providers = LLMFactory.get_available_providers()
        
        assert isinstance(providers, list)
        assert "mock" in providers
    
    def test_register_new_provider(self):
        """Test registering a new LLM provider."""
        class TestLLM(BaseLLM):
            async def generate_response(self, conversation, new_message, **kwargs):
                return "test response"
            
            async def generate_streaming_response(self, conversation, new_message, **kwargs):
                yield {"type": "content", "text": "test"}
                yield {"type": "stop"}
            
            def validate_config(self):
                return True
        
        # Register the new provider
        LLMFactory.register_provider("test", TestLLM)
        
        # Verify it's available
        assert "test" in LLMFactory.get_available_providers()
        
        # Test creating instance
        llm = LLMFactory.create_llm("test", model_name="test-model")
        assert isinstance(llm, TestLLM)
        assert llm.model_name == "test-model"
        
        # Clean up
        del LLMFactory._providers["test"]


class TestBaseLLMInterface:
    """Test BaseLLM abstract interface."""
    
    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseLLM cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseLLM("test-model")
    
    def test_get_model_info_filters_api_keys(self):
        """Test that get_model_info filters out API keys."""
        mock_llm = MockLLM(api_key="secret-key", other_config="value")
        
        info = mock_llm.get_model_info()
        
        # Should not contain api_key
        assert "api_key" not in str(info["config"])
        # Should contain other config
        assert info["config"].get("other_config") == "value"


@pytest.mark.asyncio
async def test_conversation_concurrent_access():
    """Test conversation thread safety with concurrent access."""
    conversation = ConversationHistory(
        messages=[],
        conversation_id="concurrent-test",
        created_at=datetime.now()
    )
    
    async def add_messages(prefix, count):
        for i in range(count):
            conversation.add_message("user", f"{prefix}-message-{i}")
            await asyncio.sleep(0.01)  # Small delay to encourage interleaving
    
    # Run concurrent tasks
    await asyncio.gather(
        add_messages("task1", 5),
        add_messages("task2", 5),
        add_messages("task3", 5)
    )
    
    # Should have all messages
    assert len(conversation.messages) == 15
    
    # Verify all messages are present (order may vary due to concurrency)
    contents = [msg.content for msg in conversation.messages]
    for i in range(5):
        assert f"task1-message-{i}" in contents
        assert f"task2-message-{i}" in contents
        assert f"task3-message-{i}" in contents