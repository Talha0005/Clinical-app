"""Manual server testing script."""

import sys
import asyncio
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests


# @pytest.mark.adhoc
def test_server_endpoints_manual():
    """Manual test for server endpoints."""
    base_url = "http://127.0.0.1:8000"
    
    print("🌐 Testing DigiCare MCP Server endpoints...")
    print(f"Base URL: {base_url}")
    
    # Test root endpoint
    try:
        print("\n🏠 Testing root endpoint...")
        response = requests.get(f"{base_url}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
    
    # Test health endpoint
    try:
        print("\n❤️ Testing health endpoint...")
        response = requests.get(f"{base_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
    
    # Test tools list
    try:
        print("\n🔧 Testing tools list endpoint...")
        response = requests.get(f"{base_url}/tools")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Found {len(data.get('tools', []))} tools:")
        for tool in data.get('tools', []):
            print(f"  - {tool['name']}: {tool['description']}")
    except Exception as e:
        print(f"❌ Tools list error: {e}")
    
    # Test patient-list tool
    try:
        print("\n👥 Testing patient-list tool...")
        response = requests.post(f"{base_url}/tools/patient-list", json={})
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Patient list result:")
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"❌ Patient-list tool error: {e}")
    
    # Test patient-db tool (if we have sample data)
    try:
        print("\n🔍 Testing patient-db tool...")
        test_args = {
            "patient_name": "John Smith", 
            "national_insurance": "AB123456C"
        }
        response = requests.post(f"{base_url}/tools/patient-db", json=test_args)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Patient lookup result:")
            print(json.dumps(data, indent=2))
        else:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Patient-db tool error: {e}")


def test_server_availability():
    """Check if server is running."""
    base_url = "http://127.0.0.1:8000"
    
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and healthy")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running")
        print("💡 Start the server with: cd backend/mcp_server && python server.py")
        return False
    except Exception as e:
        print(f"❌ Error checking server: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Running manual server tests...")
    
    if test_server_availability():
        test_server_endpoints_manual()
    else:
        print("\n⚠️ Server is not available. Please start it first.")