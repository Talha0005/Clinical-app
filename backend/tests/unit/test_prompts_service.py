"""
Unit tests for PromptsService
Tests prompt management functionality including CRUD operations and error handling
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import pytest

from services.prompts_service import PromptsService


class TestPromptsService:
    """Test cases for PromptsService class"""

    @pytest.fixture
    def temp_prompts_file(self):
        """Create a temporary prompts file for testing"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            initial_data = {
                "prompts": {
                    "test_prompt": {
                        "id": "test_prompt",
                        "name": "Test Prompt",
                        "description": "A test prompt",
                        "category": "test",
                        "content": "This is a test prompt",
                        "version": 1,
                        "created_at": "2025-01-12T00:00:00Z",
                        "updated_at": "2025-01-12T00:00:00Z",
                        "is_active": True,
                    }
                },
                "metadata": {
                    "version": 1,
                    "last_updated": "2025-01-12T00:00:00Z",
                    "total_prompts": 1,
                },
            }
            json.dump(initial_data, f)
            return Path(f.name)

    @pytest.fixture
    def prompts_service(self, temp_prompts_file):
        """Create PromptsService instance with temporary file"""
        return PromptsService(prompts_file=str(temp_prompts_file))

    def test_load_prompts_success(self, prompts_service):
        """Test successful loading of prompts from file"""
        prompts = prompts_service.get_all_prompts()
        assert "test_prompt" in prompts
        assert prompts["test_prompt"]["name"] == "Test Prompt"

    def test_get_prompt_exists(self, prompts_service):
        """Test getting an existing prompt"""
        prompt = prompts_service.get_prompt("test_prompt")
        assert prompt is not None
        assert prompt["name"] == "Test Prompt"

    def test_get_prompt_not_exists(self, prompts_service):
        """Test getting a non-existent prompt"""
        prompt = prompts_service.get_prompt("non_existent")
        assert prompt is None

    def test_get_active_prompt(self, prompts_service):
        """Test getting active prompt content"""
        content = prompts_service.get_active_prompt("test_prompt")
        assert content == "This is a test prompt"

    def test_get_inactive_prompt(self, prompts_service):
        """Test getting inactive prompt returns None"""
        # Update prompt to inactive
        prompts_service.update_prompt("test_prompt", {"is_active": False})
        content = prompts_service.get_active_prompt("test_prompt")
        assert content is None

    def test_update_prompt_success(self, prompts_service):
        """Test successful prompt update"""
        updates = {"name": "Updated Test Prompt", "content": "Updated content"}
        success = prompts_service.update_prompt(
            "test_prompt", updates, user_id="test_user"
        )
        assert success is True

        # Verify changes
        prompt = prompts_service.get_prompt("test_prompt")
        assert prompt["name"] == "Updated Test Prompt"
        assert prompt["content"] == "Updated content"
        assert prompt["version"] == 2

    def test_update_prompt_not_found(self, prompts_service):
        """Test updating non-existent prompt"""
        success = prompts_service.update_prompt("non_existent", {"name": "New Name"})
        assert success is False

    def test_create_prompt_success(self, prompts_service):
        """Test successful prompt creation"""
        new_prompt_data = {
            "id": "new_prompt",
            "name": "New Prompt",
            "description": "A new prompt",
            "category": "custom",
            "content": "New prompt content",
            "is_active": True,
        }
        success = prompts_service.create_prompt(new_prompt_data)
        assert success is True

        # Verify creation
        prompt = prompts_service.get_prompt("new_prompt")
        assert prompt is not None
        assert prompt["name"] == "New Prompt"

    def test_create_prompt_already_exists(self, prompts_service):
        """Test creating prompt with existing ID"""
        duplicate_data = {
            "id": "test_prompt",  # This ID already exists
            "name": "Duplicate",
            "description": "Should fail",
            "content": "Duplicate content",
        }
        success = prompts_service.create_prompt(duplicate_data)
        assert success is False

    def test_delete_prompt_success(self, prompts_service):
        """Test successful prompt deletion"""
        success = prompts_service.delete_prompt("test_prompt")
        assert success is True

        # Verify deletion
        prompt = prompts_service.get_prompt("test_prompt")
        assert prompt is None

    def test_delete_prompt_not_found(self, prompts_service):
        """Test deleting non-existent prompt"""
        success = prompts_service.delete_prompt("non_existent")
        assert success is False

    def test_get_prompts_by_category(self, prompts_service):
        """Test filtering prompts by category"""
        # Add another prompt with different category
        new_prompt = {
            "id": "medical_prompt",
            "name": "Medical Prompt",
            "description": "Medical test",
            "category": "medical",
            "content": "Medical content",
            "is_active": True,
        }
        prompts_service.create_prompt(new_prompt)

        # Test filtering
        test_prompts = prompts_service.get_prompts_by_category("test")
        medical_prompts = prompts_service.get_prompts_by_category("medical")

        assert len(test_prompts) == 1
        assert len(medical_prompts) == 1
        assert "test_prompt" in test_prompts
        assert "medical_prompt" in medical_prompts

    def test_load_prompts_invalid_json(self):
        """Test loading prompts with invalid JSON"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            invalid_file = Path(f.name)

        service = PromptsService(prompts_file=str(invalid_file))
        # Should create default prompts when JSON is invalid
        prompts = service.get_all_prompts()
        assert len(prompts) >= 1  # Should have at least default prompt

    def test_load_prompts_file_not_found(self):
        """Test loading prompts when file doesn't exist"""
        non_existent_file = "/non/existent/path/prompts.json"
        service = PromptsService(prompts_file=non_existent_file)

        # Should create default prompts when file doesn't exist
        prompts = service.get_all_prompts()
        assert len(prompts) >= 1  # Should have at least default prompt

    @patch("services.prompts_service.logger")
    def test_audit_logging_on_update(self, mock_logger, prompts_service):
        """Test that audit logging occurs on prompt updates"""
        updates = {"content": "Updated medical content"}
        prompts_service.update_prompt("test_prompt", updates, user_id="test_doctor")

        # Verify audit logging was called
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        assert "AUDIT" in call_args
        assert "test_doctor" in call_args
        assert "test_prompt" in call_args

    def test_save_prompts_atomic_operation(self, temp_prompts_file):
        """Test that prompts are saved atomically"""
        service = PromptsService(prompts_file=str(temp_prompts_file))

        # Mock a failure during JSON serialization to test atomic behavior
        with patch("json.dump", side_effect=json.JSONDecodeError("Test error", "", 0)):
            success = service.save_prompts()
            assert success is False

        # Original file should still be intact
        assert temp_prompts_file.exists()
        with open(temp_prompts_file, "r") as f:
            data = json.load(f)
            assert "test_prompt" in data["prompts"]

    def test_medical_prompt_audit_logging(self, prompts_service):
        """Test special audit logging for medical prompts"""
        # Create a medical prompt
        medical_prompt = {
            "id": "medical_test",
            "name": "Medical Test",
            "description": "Medical prompt",
            "category": "medical",
            "content": "Original medical content",
            "is_active": True,
        }
        prompts_service.create_prompt(medical_prompt)

        with patch("services.prompts_service.logger") as mock_logger:
            # Update medical prompt content
            updates = {"content": "Updated medical content"}
            prompts_service.update_prompt("medical_test", updates, user_id="doctor123")

            # Verify medical audit logging
            mock_logger.warning.assert_called()
            call_args = mock_logger.warning.call_args[0][0]
            assert "MEDICAL_AUDIT" in call_args
            assert "doctor123" in call_args
