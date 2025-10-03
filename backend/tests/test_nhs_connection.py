#!/usr/bin/env python3
"""Test script to verify NHS Terminology Server connection."""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from medical.nhs_terminology import NHSTerminologyServer


async def test_nhs_connection():
    """Test NHS Terminology Server connection and basic operations."""

    print("=" * 60)
    print("NHS Terminology Server Connection Test")
    print("=" * 60)

    # Check credentials
    client_id = os.getenv("NHS_TERMINOLOGY_CLIENT_ID")
    client_secret = os.getenv("NHS_TERMINOLOGY_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("❌ ERROR: NHS credentials not found in environment variables")
        print(
            "   Please set NHS_TERMINOLOGY_CLIENT_ID and NHS_TERMINOLOGY_CLIENT_SECRET"
        )
        return False

    print("✅ Credentials found in environment")
    print(f"   Client ID: {client_id[:10]}..." if len(client_id) > 10 else client_id)
    print()

    try:
        async with NHSTerminologyServer() as server:
            print("Testing NHS Terminology Server connection...")
            print(f"Environment: {server.environment}")
            print(f"FHIR Base URL: {server.fhir_base_url}")
            print()

            # Test 1: Health check
            print("1. Health Check...")
            is_healthy = await server.health_check()
            if is_healthy:
                print("   ✅ Server is accessible")
            else:
                print("   ❌ Server health check failed")
                return False
            print()

            # Test 2: Get access token
            print("2. OAuth Authentication...")
            try:
                token = await server._get_access_token()
                print(f"   ✅ Access token obtained: {token[:20]}...")
            except Exception as e:
                print(f"   ❌ Authentication failed: {e}")
                return False
            print()

            # Test 3: Search SNOMED CT
            print("3. SNOMED CT Search Test...")
            print("   Searching for 'diabetes'...")
            concepts = await server.search_snomed("diabetes", limit=3)

            if concepts:
                print(f"   ✅ Found {len(concepts)} SNOMED concepts:")
                for concept in concepts:
                    print(f"      - {concept.display} ({concept.code})")
            else:
                print("   ⚠️  No SNOMED concepts found")
            print()

            # Test 4: Search medications
            print("4. dm+d Medication Search Test...")
            print("   Searching for 'paracetamol'...")
            medications = await server.search_medications("paracetamol", limit=3)

            if medications:
                print(f"   ✅ Found {len(medications)} medications:")
                for med in medications:
                    print(f"      - {med.display} ({med.code})")
            else:
                print("   ⚠️  No medications found")
            print()

            # Test 5: Validate a known SNOMED code
            print("5. Code Validation Test...")
            test_code = "73211009"  # Diabetes mellitus
            print(f"   Validating SNOMED code {test_code}...")
            is_valid = await server.validate_snomed_code(test_code)

            if is_valid:
                print(f"   ✅ Code {test_code} is valid")
                concept = await server.get_snomed_concept(test_code)
                if concept:
                    print(f"      Display: {concept.display}")
            else:
                print(f"   ❌ Code {test_code} validation failed")
            print()

            print("=" * 60)
            print("✅ NHS Terminology Server integration test completed!")
            print("=" * 60)
            return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv()

    # Run the test
    success = asyncio.run(test_nhs_connection())
    sys.exit(0 if success else 1)
