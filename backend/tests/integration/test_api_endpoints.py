"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from mcp_server.server import create_app


@pytest.mark.integration
class TestAPIEndpoints:
    """Integration tests for API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns server info."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "DigiCare MCP Server"
        assert data["version"] == "0.1.0"
        assert "mcp_endpoint" in data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    def test_list_tools_endpoint(self, client):
        """Test tools list endpoint."""
        response = client.get("/tools")
        assert response.status_code == 200
        
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) >= 2
        
        tool_names = [tool["name"] for tool in data["tools"]]
        assert "patient-db" in tool_names
        assert "patient-list" in tool_names
    
    def test_oauth_discovery_endpoints(self, client):
        """Test OAuth discovery endpoints."""
        # Test authorization server discovery
        response = client.get("/.well-known/oauth-authorization-server")
        assert response.status_code == 200
        
        data = response.json()
        assert "authorization_endpoint" in data
        assert "token_endpoint" in data
        assert "response_types_supported" in data
        
        # Test protected resource discovery
        response = client.get("/.well-known/oauth-protected-resource")
        assert response.status_code == 200
        
        data = response.json()
        assert "resource_server" in data
        assert "authorization_servers" in data
    
    def test_oauth_register_endpoint(self, client):
        """Test OAuth client registration."""
        response = client.post("/register")
        assert response.status_code == 200
        
        data = response.json()
        assert "client_id" in data
        assert "client_secret" in data
        assert "registration_access_token" in data
    
    def test_oauth_token_endpoint(self, client):
        """Test OAuth token endpoint."""
        response = client.post("/oauth/token")
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
    
    def test_create_patient_endpoint(self, client):
        """Test create patient endpoint."""
        import random
        import string
        # Generate valid UK National Insurance format: AA123456A
        letters = ''.join(random.choices(string.ascii_uppercase, k=2))
        numbers = ''.join(random.choices(string.digits, k=6))
        suffix = random.choice(string.ascii_uppercase)
        ni_number = f"{letters}{numbers}{suffix}"
        
        new_patient = {
            "name": f"Integration Test Patient {letters}",
            "national_insurance": ni_number,
            "age": 35,
            "medical_history": ["Test condition"],
            "current_medications": ["Test medication"]
        }
        
        response = client.post("/tools/create-patient", json=new_patient)
        assert response.status_code == 200
        
        data = response.json()
        assert "result" in data
        assert "Successfully created patient" in data["result"][0]["text"]
        
        # Verify patient can be found
        lookup_response = client.post("/tools/patient-db", json={
            "patient_name": new_patient["name"],
            "national_insurance": new_patient["national_insurance"]
        })
        assert lookup_response.status_code == 200
        lookup_data = lookup_response.json()
        assert new_patient["name"] in lookup_data["result"][0]["text"]
    
    def test_create_patient_duplicate_fails(self, client):
        """Test creating duplicate patient fails."""
        # Try to create patient with existing National Insurance
        duplicate_patient = {
            "name": "Duplicate Test",
            "national_insurance": "AB123456C",  # Should already exist
            "age": 30
        }
        
        response = client.post("/tools/create-patient", json=duplicate_patient)
        assert response.status_code == 200  # Tool returns 200 but with error message
        data = response.json()
        assert "result" in data
        assert "already exists" in data["result"][0]["text"]