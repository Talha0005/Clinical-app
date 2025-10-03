#!/usr/bin/env python3
"""
NHS API Connection Test Script
Run this to verify your NHS API credentials are working
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent  # Go up to backend/
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_nhs_api():
    """Test NHS API connection"""
    print("🏥 NHS API Connection Test")
    print("=" * 50)

    # Check environment variables
    client_id = os.getenv("NHS_CLIENT_ID")
    client_secret = os.getenv("NHS_CLIENT_SECRET")
    environment = os.getenv("NHS_ENVIRONMENT", "sandbox")

    print(f"Environment: {environment}")
    print(f"Client ID: {client_id[:8]}..." if client_id else "❌ Not set")
    print(f"Client Secret: {'✅ Set' if client_secret else '❌ Not set'}")
    print()

    if not client_id or not client_secret:
        print("❌ NHS credentials not configured!")
        print("Please set NHS_CLIENT_ID and NHS_CLIENT_SECRET in your .env file")
        return False

    try:
        # Import OAuth client
        from api.nhs_oauth import NHSOAuthClient

        print("🔐 Testing OAuth authentication...")

        # Create OAuth client
        oauth_client = NHSOAuthClient(
            client_id=client_id, client_secret=client_secret, environment=environment
        )

        # Test authentication
        async with oauth_client as client:
            success, message = await client.test_connection()

            if success:
                print("✅ OAuth authentication successful!")
                print(f"   {message}")

                # Test getting a token
                token = await client.get_access_token()
                print(f"   Token type: {token.token_type}")
                print(f"   Expires at: {token.expires_at}")
                print(f"   Token: {token.access_token[:20]}...")

                return True
            else:
                print(f"❌ OAuth authentication failed: {message}")
                return False

    except Exception as e:
        print(f"❌ Error testing NHS API: {e}")
        return False


async def test_service_search():
    """Test NHS Service Search API"""
    print("\n🔍 Testing NHS Service Search API...")

    try:
        from api.nhs_service_search import NHSServiceSearch

        async with NHSServiceSearch() as search_client:
            # Test searching for services in London
            print("   Searching for GP services near SW1A 1AA (Westminster)...")

            services = await search_client.search_by_postcode(
                postcode="SW1A1AA", service_types=["GP"], radius_miles=5, limit=3
            )

            if services:
                print(f"✅ Found {len(services)} GP services:")
                for service in services[:2]:  # Show first 2
                    print(f"   • {service.name} - {service.postcode}")
                return True
            else:
                print("⚠️  No services found (this might be normal for test data)")
                return True

    except Exception as e:
        print(f"❌ Service search failed: {e}")
        return False


async def main():
    """Main test function"""
    print("DigiClinic NHS API Test Suite")
    print("Testing your NHS Digital credentials and API access\n")

    # Test OAuth
    oauth_success = await test_nhs_api()

    if oauth_success:
        # Test Service Search
        search_success = await test_service_search()

        if search_success:
            print(
                "\n🎉 All tests passed! Your NHS API integration is working correctly."
            )
        else:
            print("\n⚠️  OAuth works but service search failed. Check API permissions.")
    else:
        print("\n❌ OAuth failed. Please check your credentials.")

    print("\nNext steps:")
    print("1. Replace 'your-client-id-here' and 'your-client-secret-here' in .env")
    print("2. Run the backend server: cd backend && python main.py")
    print(
        "3. Test the connection endpoint: http://localhost:8000/api/nhs/test-connection"
    )


if __name__ == "__main__":
    asyncio.run(main())
