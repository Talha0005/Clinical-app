"""Ad-hoc test script for manual patient database testing."""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.mock_patient_db import MockPatientDB
from mcp_server.tools.patient import handle_patient_db, handle_patient_list


# @pytest.mark.adhoc
async def test_patient_lookup_manual():
    """Manual test for patient lookup functionality."""
    print("🔍 Testing Patient Database Lookup...")
    
    # Test patient database operations
    try:
        db = MockPatientDB()
        
        print("\n📋 Loading all patients...")
        patients = db.load_patients()
        print(f"Found {len(patients)} patients in database")
        
        for patient in patients:
            print(f"  - {patient['name']} ({patient['national_insurance']})")
        
        print("\n🔍 Testing patient lookup...")
        if patients:
            first_patient = patients[0]
            name = first_patient['name']
            ni = first_patient['national_insurance']
            
            found_patient = db.find_patient(name, ni)
            if found_patient:
                print(f"✅ Successfully found: {found_patient['name']}")
            else:
                print("❌ Failed to find patient")
        
        print("\n🔧 Testing MCP tool handlers...")
        
        # Test patient-db tool
        if patients:
            first_patient = patients[0]
            arguments = {
                "patient_name": first_patient['name'],
                "national_insurance": first_patient['national_insurance']
            }
            
            result = await handle_patient_db(arguments)
            print(f"✅ Patient-db tool result: {len(result)} items")
            print(f"   Content preview: {result[0].text[:100]}...")
        
        # Test patient-list tool
        result = await handle_patient_list({})
        print(f"✅ Patient-list tool result: {len(result)} items")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Running ad-hoc patient database tests...")
    asyncio.run(test_patient_lookup_manual())