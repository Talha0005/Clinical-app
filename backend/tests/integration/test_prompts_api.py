"""
Integration tests for prompts management API endpoints
Tests the full API flow including authentication and data persistence
"""

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import tempfile
from pathlib import Path


# Mock the prompts service to use a temporary file
@pytest.fixture
def temp_prompts_service():
    """Create a temporary prompts service for testing"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        initial_data = {
            "prompts": {
                "test_system": {
                    "id": "test_system",
                    "name": "Test System Prompt",
                    "description": "System prompt for testing",
                    "category": "system",
                    "content": "You are a test assistant",
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
        temp_file = Path(f.name)

    # Patch the global prompts_service
    with patch("services.prompts_service.prompts_service") as mock_service:
        from services.prompts_service import PromptsService

        mock_service.__class__ = PromptsService
        test_service = PromptsService(prompts_file=str(temp_file))

        # Mock all the methods to use our test service
        mock_service.get_all_prompts = test_service.get_all_prompts
        mock_service.get_prompt = test_service.get_prompt
        mock_service.update_prompt = test_service.update_prompt
        mock_service.create_prompt = test_service.create_prompt
        mock_service.delete_prompt = test_service.delete_prompt
        mock_service.get_prompts_by_category = test_service.get_prompts_by_category

        yield mock_service


@pytest.fixture
def client():
    """Create test client"""
    from main import app

    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Get authentication headers for testing"""
    # Mock JWT token for testing - in real tests, you'd create a proper test token
    test_token = "test_jwt_token"

    with patch("main.verify_token") as mock_verify:
        mock_verify.return_value = "test_user"
        return {"Authorization": f"Bearer {test_token}"}


class TestPromptsAPI:
    """Test cases for prompts API endpoints"""

    def test_get_all_prompts_success(self, client, temp_prompts_service, auth_headers):
        """Test GET /api/prompts returns all prompts"""
        response = client.get("/api/prompts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "test_system"
        assert data[0]["name"] == "Test System Prompt"

    def test_get_all_prompts_unauthorized(self, client, temp_prompts_service):
        """Test GET /api/prompts without authentication"""
        response = client.get("/api/prompts")
        assert response.status_code == 401

    def test_get_prompt_by_id_success(self, client, temp_prompts_service, auth_headers):
        """Test GET /api/prompts/{id} returns specific prompt"""
        response = client.get("/api/prompts/test_system", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test_system"
        assert data["name"] == "Test System Prompt"
        assert data["category"] == "system"

    def test_get_prompt_by_id_not_found(
        self, client, temp_prompts_service, auth_headers
    ):
        """Test GET /api/prompts/{id} with non-existent prompt"""
        response = client.get("/api/prompts/non_existent", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_prompt_success(self, client, temp_prompts_service, auth_headers):
        """Test PUT /api/prompts/{id} updates prompt successfully"""
        update_data = {
            "name": "Updated System Prompt",
            "content": "You are an updated test assistant",
        }

        response = client.put(
            "/api/prompts/test_system", json=update_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated System Prompt"
        assert data["content"] == "You are an updated test assistant"
        assert data["version"] == 2  # Version should increment

    def test_update_prompt_not_found(self, client, temp_prompts_service, auth_headers):
        """Test PUT /api/prompts/{id} with non-existent prompt"""
        update_data = {"name": "Should Fail"}

        response = client.put(
            "/api/prompts/non_existent", json=update_data, headers=auth_headers
        )

        assert response.status_code == 404

    def test_create_prompt_success(self, client, temp_prompts_service, auth_headers):
        """Test POST /api/prompts creates new prompt"""
        new_prompt = {
            "id": "new_test_prompt",
            "name": "New Test Prompt",
            "description": "A new prompt for testing",
            "category": "custom",
            "content": "This is a new test prompt",
            "is_active": True,
        }

        response = client.post("/api/prompts", json=new_prompt, headers=auth_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "new_test_prompt"
        assert data["name"] == "New Test Prompt"
        assert data["version"] == 1

    def test_create_prompt_already_exists(
        self, client, temp_prompts_service, auth_headers
    ):
        """Test POST /api/prompts with existing prompt ID"""
        duplicate_prompt = {
            "id": "test_system",  # This already exists
            "name": "Duplicate",
            "description": "Should fail",
            "category": "system",
            "content": "Duplicate content",
        }

        response = client.post(
            "/api/prompts", json=duplicate_prompt, headers=auth_headers
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_delete_prompt_success(self, client, temp_prompts_service, auth_headers):
        """Test DELETE /api/prompts/{id} removes prompt"""
        # First create a prompt to delete
        new_prompt = {
            "id": "to_be_deleted",
            "name": "Delete Me",
            "description": "Will be deleted",
            "category": "custom",
            "content": "Delete this prompt",
        }
        client.post("/api/prompts", json=new_prompt, headers=auth_headers)

        # Now delete it
        response = client.delete("/api/prompts/to_be_deleted", headers=auth_headers)

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify it's gone
        get_response = client.get("/api/prompts/to_be_deleted", headers=auth_headers)
        assert get_response.status_code == 404

    def test_delete_prompt_not_found(self, client, temp_prompts_service, auth_headers):
        """Test DELETE /api/prompts/{id} with non-existent prompt"""
        response = client.delete("/api/prompts/non_existent", headers=auth_headers)
        assert response.status_code == 404

    def test_get_prompts_by_category(self, client, temp_prompts_service, auth_headers):
        """Test GET /api/prompts/category/{category} filters correctly"""
        # Create prompts in different categories
        medical_prompt = {
            "id": "medical_test",
            "name": "Medical Test",
            "description": "Medical prompt",
            "category": "medical",
            "content": "Medical content",
        }
        client.post("/api/prompts", json=medical_prompt, headers=auth_headers)

        # Test filtering by category
        response = client.get("/api/prompts/category/system", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert all(prompt["category"] == "system" for prompt in data)

        response = client.get("/api/prompts/category/medical", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert all(prompt["category"] == "medical" for prompt in data)

    def test_prompt_validation(self, client, temp_prompts_service, auth_headers):
        """Test that prompt creation validates required fields"""
        invalid_prompt = {
            "name": "Missing ID",
            "description": "No ID provided",
            # Missing required 'id' field
        }

        response = client.post(
            "/api/prompts", json=invalid_prompt, headers=auth_headers
        )
        assert response.status_code == 422  # Validation error

    def test_prompt_update_validation(self, client, temp_prompts_service, auth_headers):
        """Test that prompt updates validate data types"""
        invalid_update = {"is_active": "not_a_boolean"}  # Should be boolean

        response = client.put(
            "/api/prompts/test_system", json=invalid_update, headers=auth_headers
        )
        assert response.status_code == 422  # Validation error
