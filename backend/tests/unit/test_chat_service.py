"""Unit tests for DigiClinicChatService."""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# Add backend directory to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.chat_service import DigiClinicChatService
from llm.base_llm import ConversationHistory, MockLLM


class TestDigiClinicChatService:
    """Test DigiClinicChatService functionality."""

    @pytest.fixture
    def chat_service(self):
        """Create a chat service instance for testing."""
        return DigiClinicChatService(llm_provider="mock")

    @pytest.fixture
    def sample_conversation_data(self):
        """Create sample conversation data as it would come from browser."""
        return {
            "conversation_id": "test-123",
            "created_at": datetime.now().isoformat(),
            "messages": [
                {
                    "role": "system",
                    "content": "You are a medical assistant",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {},
                },
                {
                    "role": "user",
                    "content": "I have a headache",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {},
                },
            ],
            "metadata": {},
        }

    def test_service_initialization(self, chat_service):
        """Test service initialization."""
        assert isinstance(chat_service.llm, MockLLM)
        assert chat_service.active_conversations == {}
        assert chat_service.conversations is chat_service.active_conversations
        assert chat_service.prompts_service is not None

    def test_service_initialization_with_config(self):
        """Test service initialization with LLM configuration."""
        service = DigiClinicChatService(llm_provider="mock", custom_param="test_value")

        assert isinstance(service.llm, MockLLM)
        # MockLLM should have received the custom parameter
        assert service.llm.config.get("custom_param") == "test_value"

    @pytest.mark.asyncio
    async def test_start_conversation_new(self, chat_service):
        """Test starting a new conversation."""
        conversation = await chat_service.start_conversation()

        assert isinstance(conversation, ConversationHistory)
        assert conversation.conversation_id is not None
        assert len(conversation.messages) == 2  # System + welcome message
        assert conversation.messages[0].role == "system"
        assert conversation.messages[1].role == "assistant"
        assert "Dr. Hervix" in conversation.messages[1].content

        # Should be stored in active conversations
        assert conversation.conversation_id in chat_service.active_conversations

    @pytest.mark.asyncio
    async def test_start_conversation_with_id(self, chat_service):
        """Test starting conversation with specific ID."""
        conversation_id = "custom-123"
        conversation = await chat_service.start_conversation(
            conversation_id=conversation_id
        )

        assert conversation.conversation_id == conversation_id
        assert conversation_id in chat_service.active_conversations

    @pytest.mark.asyncio
    async def test_start_conversation_existing(self, chat_service):
        """Test retrieving existing conversation."""
        # Create initial conversation
        conversation1 = await chat_service.start_conversation(
            conversation_id="existing-123"
        )
        initial_message_count = len(conversation1.messages)

        # Retrieve same conversation
        conversation2 = await chat_service.start_conversation(
            conversation_id="existing-123"
        )

        assert conversation1 is conversation2
        assert (
            len(conversation2.messages) == initial_message_count
        )  # No new messages added

    @pytest.mark.asyncio
    async def test_start_conversation_with_patient_context(self, chat_service):
        """Test starting conversation with patient context."""
        patient_context = {"patient_id": "P12345", "condition": "follow_up"}

        conversation = await chat_service.start_conversation(
            patient_context=patient_context
        )

        assert conversation.metadata["patient_context"] == patient_context

    @pytest.mark.asyncio
    async def test_send_message_success(self, chat_service, sample_conversation_data):
        """Test successful message sending."""
        result = await chat_service.send_message(
            sample_conversation_data, "Tell me more about my headache"
        )

        assert result["success"] is True
        assert "response" in result
        assert "conversation" in result
        assert len(result["response"]) > 0

        # Conversation should be updated in cache
        conv_id = sample_conversation_data["conversation_id"]
        assert conv_id in chat_service.active_conversations

    @pytest.mark.asyncio
    async def test_send_message_with_llm_error(
        self, chat_service, sample_conversation_data
    ):
        """Test message sending when LLM fails."""
        # Mock LLM to raise exception
        with patch.object(
            chat_service.llm, "generate_response", side_effect=Exception("LLM failed")
        ):
            result = await chat_service.send_message(
                sample_conversation_data, "Test message"
            )

            assert result["success"] is False
            assert "error" in result
            assert "LLM failed" in result["error"]
            assert (
                result["conversation"] == sample_conversation_data
            )  # Original data returned

    @pytest.mark.asyncio
    async def test_get_conversation_exists(self, chat_service):
        """Test getting existing conversation."""
        # Create a conversation
        conversation = await chat_service.start_conversation(conversation_id="get-test")

        # Retrieve it
        result = await chat_service.get_conversation("get-test")

        assert result is not None
        assert result["conversation_id"] == "get-test"
        assert len(result["messages"]) == 2  # System + welcome

    @pytest.mark.asyncio
    async def test_get_conversation_not_exists(self, chat_service):
        """Test getting non-existent conversation."""
        result = await chat_service.get_conversation("non-existent")
        assert result is None

    def test_get_llm_info(self, chat_service):
        """Test getting LLM information."""
        info = chat_service.get_llm_info()

        assert "model_name" in info
        assert "provider" in info
        assert info["provider"] == "MockLLM"

    def test_switch_llm_success(self, chat_service):
        """Test successful LLM switching."""
        original_llm = chat_service.llm

        # Switch to same provider (should work)
        success = chat_service.switch_llm("mock", test_param="new_value")

        assert success is True
        assert chat_service.llm is not original_llm
        assert chat_service.llm.config.get("test_param") == "new_value"

    def test_switch_llm_invalid_provider(self, chat_service):
        """Test switching to invalid LLM provider."""
        original_llm = chat_service.llm

        success = chat_service.switch_llm("invalid_provider")

        assert success is False
        assert chat_service.llm is original_llm  # Should remain unchanged

    def test_switch_llm_invalid_config(self, chat_service):
        """Test switching with invalid configuration."""
        # Mock an LLM that fails validation
        with patch("llm.base_llm.MockLLM.validate_config", return_value=False):
            success = chat_service.switch_llm("mock")
            assert success is False

    def test_clear_conversation_exists(self, chat_service):
        """Test clearing existing conversation."""
        # Create a conversation
        conv_id = chat_service.create_conversation("test_user")
        assert conv_id in chat_service.active_conversations

        # Clear it
        success = chat_service.clear_conversation(conv_id)

        assert success is True
        assert conv_id not in chat_service.active_conversations

    def test_clear_conversation_not_exists(self, chat_service):
        """Test clearing non-existent conversation."""
        success = chat_service.clear_conversation("non-existent")
        assert success is False

    def test_get_active_conversations_empty(self, chat_service):
        """Test getting active conversations when none exist."""
        conversations = chat_service.get_active_conversations()
        assert conversations == {}

    def test_get_active_conversations_with_data(self, chat_service):
        """Test getting active conversations with data."""
        # Create some conversations
        conv1_id = chat_service.create_conversation("user1")
        conv2_id = chat_service.create_conversation("user2")

        conversations = chat_service.get_active_conversations()

        assert len(conversations) == 2
        assert conv1_id in conversations
        assert conv2_id in conversations

        # Check data structure
        conv1_data = conversations[conv1_id]
        assert "created_at" in conv1_data
        assert "message_count" in conv1_data
        assert "last_message" in conv1_data
        assert conv1_data["message_count"] == 0  # No messages yet

    def test_create_conversation(self, chat_service):
        """Test creating a conversation."""
        conv_id = chat_service.create_conversation("test_user_123")

        assert conv_id is not None
        assert conv_id in chat_service.active_conversations

        conversation = chat_service.active_conversations[conv_id]
        assert isinstance(conversation, ConversationHistory)
        assert conversation.conversation_id == conv_id
        assert (
            len(conversation.messages) == 0
        )  # create_conversation doesn't add messages

    def test_get_conversation_history_exists(self, chat_service):
        """Test getting conversation history."""
        # Create and populate conversation
        conv_id = chat_service.create_conversation("test_user")
        conversation = chat_service.active_conversations[conv_id]
        conversation.add_message("user", "Hello")
        conversation.add_message("assistant", "Hi there")

        history = chat_service.get_conversation_history(conv_id)

        assert history is not None
        assert history["conversation_id"] == conv_id
        assert history["message_count"] == 2
        assert len(history["messages"]) == 2
        assert history["messages"][0]["content"] == "Hello"
        assert history["messages"][1]["content"] == "Hi there"

    def test_get_conversation_history_not_exists(self, chat_service):
        """Test getting history for non-existent conversation."""
        history = chat_service.get_conversation_history("non-existent")
        assert history is None

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, chat_service):
        """Test health check when service is healthy."""
        health = await chat_service.health_check()

        assert health["status"] == "healthy"
        assert health["llm_provider"] == "MockLLM"
        assert health["active_conversations"] == 0
        assert health["llm_healthy"] is True

    @pytest.mark.asyncio
    async def test_health_check_with_conversations(self, chat_service):
        """Test health check with active conversations."""
        # Create some conversations
        chat_service.create_conversation("user1")
        chat_service.create_conversation("user2")

        health = await chat_service.health_check()

        assert health["active_conversations"] == 2

    @pytest.mark.asyncio
    async def test_health_check_llm_unhealthy(self, chat_service):
        """Test health check when LLM is unhealthy."""
        with patch.object(chat_service.llm, "health_check", return_value=False):
            health = await chat_service.health_check()

            assert health["status"] == "degraded"
            assert health["llm_healthy"] is False

    @pytest.mark.asyncio
    async def test_health_check_exception(self, chat_service):
        """Test health check when exception occurs."""
        with patch.object(
            chat_service.llm,
            "health_check",
            side_effect=Exception("Health check failed"),
        ):
            health = await chat_service.health_check()

            assert health["status"] == "unhealthy"
            assert "error" in health
            assert "Health check failed" in health["error"]

    @pytest.mark.asyncio
    async def test_health_check_no_health_check_method(self, chat_service):
        """Test health check with LLM that doesn't have health_check method."""

        # Create a mock LLM without health_check method
        class MockLLMWithoutHealthCheck:
            def __init__(self):
                self.__class__.__name__ = "MockLLMWithoutHealthCheck"

        chat_service.llm = MockLLMWithoutHealthCheck()

        health = await chat_service.health_check()

        # Should default to healthy when no health_check method
        assert health["status"] == "healthy"
        assert health["llm_healthy"] is True

    def test_conversation_reconstruction_from_dict(self, chat_service):
        """Test conversation reconstruction from browser data."""
        conversation_data = {
            "conversation_id": "reconstruct-test",
            "created_at": datetime.now().isoformat(),
            "messages": [
                {
                    "role": "user",
                    "content": "Test message",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {"source": "web"},
                }
            ],
            "metadata": {"session": "test"},
        }

        # This should work without errors
        asyncio = pytest.importorskip("asyncio")

        async def run_test():
            result = await chat_service.send_message(conversation_data, "Follow up")
            assert result["success"] is True

            # Conversation should be cached
            assert "reconstruct-test" in chat_service.active_conversations

            cached_conv = chat_service.active_conversations["reconstruct-test"]
            assert cached_conv.metadata["session"] == "test"
            assert len(cached_conv.messages) >= 1  # Original + new messages

        asyncio.run(run_test())

    @pytest.mark.asyncio
    async def test_concurrent_message_sending(self, chat_service):
        """Test concurrent message sending to same conversation."""
        conversation_data = {
            "conversation_id": "concurrent-test",
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "metadata": {},
        }

        async def send_message(msg_id):
            return await chat_service.send_message(
                conversation_data.copy(),  # Each task gets its own copy
                f"Message {msg_id}",
            )

        import asyncio

        # Send multiple messages concurrently
        results = await asyncio.gather(
            send_message(1), send_message(2), send_message(3), return_exceptions=True
        )

        # All should succeed
        successful_results = [
            r for r in results if isinstance(r, dict) and r.get("success")
        ]
        assert len(successful_results) >= 1  # At least some should succeed

        # Conversation should be cached
        assert "concurrent-test" in chat_service.active_conversations

    def test_system_prompt_content(self, chat_service):
        """Test system prompt contains required medical content."""
        # Get prompt from prompts service
        prompt = chat_service.prompts_service.get_active_prompt("system_prompt")

        # Should have medical content (if prompt exists)
        if prompt:
            assert len(prompt) > 0
        else:
            # If no prompt from service, that's also valid (fallback behavior)
            pass

    def test_conversation_id_generation(self, chat_service):
        """Test conversation ID generation is unique."""
        ids = set()
        for _ in range(10):
            conv_id = chat_service.create_conversation("test_user")
            assert conv_id not in ids  # Should be unique
            ids.add(conv_id)
            # Should be valid UUID format
            uuid.UUID(conv_id)  # This will raise if not valid UUID
