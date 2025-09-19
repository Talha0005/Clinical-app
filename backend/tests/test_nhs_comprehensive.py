#!/usr/bin/env python3
"""Comprehensive test script for NHS Terminology Server integration."""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from medical.nhs_terminology import NHSTerminologyServer


async def test_comprehensive_nhs():
    """Comprehensive test of NHS Terminology Server functionality."""
    
    print("=" * 80)
    print("NHS TERMINOLOGY SERVER - COMPREHENSIVE TEST")
    print("=" * 80)
    
    async with NHSTerminologyServer() as server:
        
        # Test 1: Authentication & Server Info
        print("\n🔐 AUTHENTICATION & SERVER INFO")
        print("-" * 50)
        try:
            token = await server._get_access_token()
            print(f"✅ Authentication successful")
            print(f"   Environment: {server.environment}")
            print(f"   FHIR Base: {server.fhir_base_url}")
            print(f"   Token: {token[:30]}...")
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return
        
        # Test 2: SNOMED CT Searches
        print("\n🏥 SNOMED CT SEARCHES")
        print("-" * 50)
        
        test_terms = ["diabetes", "heart attack", "pneumonia", "hypertension", "asthma"]
        
        for term in test_terms:
            print(f"\nSearching SNOMED for '{term}':")
            try:
                concepts = await server.search_snomed(term, limit=5)
                if concepts:
                    print(f"   ✅ Found {len(concepts)} concepts:")
                    for i, concept in enumerate(concepts[:3], 1):
                        print(f"      {i}. {concept.display} ({concept.code})")
                else:
                    print(f"   ⚠️  No concepts found")
            except Exception as e:
                print(f"   ❌ Search failed: {e}")
        
        # Test 3: SNOMED Code Validation
        print("\n✅ SNOMED CODE VALIDATION")
        print("-" * 50)
        
        test_codes = [
            ("73211009", "Diabetes mellitus"),
            ("22298006", "Myocardial infarction"),
            ("233604007", "Pneumonia"),
            ("38341003", "Hypertension"),
            ("195967001", "Asthma"),
            ("123456789", "Invalid code")
        ]
        
        for code, description in test_codes:
            print(f"\nValidating {code} ({description}):")
            try:
                is_valid = await server.validate_snomed_code(code)
                if is_valid:
                    print(f"   ✅ Valid SNOMED code")
                    # Get full details
                    concept = await server.get_snomed_concept(code)
                    if concept:
                        print(f"      Display: {concept.display}")
                        print(f"      System: {concept.system}")
                else:
                    print(f"   ❌ Invalid or inactive code")
            except Exception as e:
                print(f"   ❌ Validation failed: {e}")
        
        # Test 4: Medication Searches (dm+d) - Enhanced with fallback testing
        print("\n💊 MEDICATION SEARCHES (dm+d)")
        print("-" * 50)
        
        medications = ["paracetamol", "aspirin", "ibuprofen", "amoxicillin", "metformin"]
        
        for med in medications:
            print(f"\nSearching dm+d for '{med}' (testing multiple URL patterns):")
            try:
                results = await server.search_medications(med, limit=3)
                if results:
                    print(f"   ✅ Found {len(results)} medications:")
                    for i, med_concept in enumerate(results, 1):
                        print(f"      {i}. {med_concept.display} ({med_concept.code})")
                else:
                    print(f"   ⚠️  No medications found with any URL pattern")
            except Exception as e:
                print(f"   ❌ Search failed: {e}")
        
        # Test 5: ICD-10 Searches - Enhanced with multiple methods
        print("\n📋 ICD-10 DIAGNOSTIC CODES")
        print("-" * 50)
        
        icd_terms = ["diabetes", "heart disease", "pneumonia", "depression", "cancer"]
        
        for term in icd_terms:
            print(f"\nSearching ICD-10 for '{term}' (testing multiple methods):")
            try:
                results = await server.search_icd10(term, limit=3)
                if results:
                    print(f"   ✅ Found {len(results)} codes:")
                    for i, concept in enumerate(results, 1):
                        print(f"      {i}. {concept.display} ({concept.code})")
                else:
                    print(f"   ⚠️  No ICD-10 codes found with any method")
            except Exception as e:
                print(f"   ❌ Search failed: {e}")
        
        # Test 5b: OPCS-4 Procedure Searches - NEW
        print("\n🔧 OPCS-4 PROCEDURE CODES")
        print("-" * 50)
        
        procedure_terms = ["appendectomy", "knee replacement", "cataract surgery", "bypass", "biopsy"]
        
        for term in procedure_terms:
            print(f"\nSearching OPCS-4 for '{term}':")
            try:
                results = await server.search_opcs4(term, limit=3)
                if results:
                    print(f"   ✅ Found {len(results)} procedures:")
                    for i, concept in enumerate(results, 1):
                        print(f"      {i}. {concept.display} ({concept.code})")
                else:
                    print(f"   ⚠️  No OPCS-4 procedures found")
            except Exception as e:
                print(f"   ❌ Search failed: {e}")
        
        # Test 6: Code Mapping (SNOMED to ICD-10)
        print("\n🔄 CODE MAPPING (SNOMED → ICD-10)")
        print("-" * 50)
        
        snomed_codes = [
            ("73211009", "Diabetes mellitus"),
            ("22298006", "Myocardial infarction"),
            ("233604007", "Pneumonia")
        ]
        
        for snomed_code, description in snomed_codes:
            print(f"\nMapping SNOMED {snomed_code} ({description}) to ICD-10:")
            try:
                mappings = await server.map_snomed_to_icd10(snomed_code)
                if mappings:
                    print(f"   ✅ Found {len(mappings)} ICD-10 mappings:")
                    for i, mapping in enumerate(mappings, 1):
                        print(f"      {i}. {mapping.display} ({mapping.code})")
                else:
                    print(f"   ⚠️  No mappings found")
            except Exception as e:
                print(f"   ❌ Mapping failed: {e}")
        
        # Test 7: Text-to-Code Conversion - Enhanced for all systems
        print("\n🔤 TEXT-TO-CODE CONVERSION")
        print("-" * 50)
        
        test_cases = [
            ("chest pain", "snomed"),
            ("paracetamol", "dmd"),
            ("diabetes", "icd10"),
            ("surgery", "opcs4")
        ]
        
        for text, system in test_cases:
            print(f"\nConverting '{text}' to {system.upper()} codes:")
            try:
                concepts = await server.text_to_code(text, system, limit=3)
                if concepts:
                    print(f"   ✅ Found {len(concepts)} matches:")
                    for i, concept in enumerate(concepts, 1):
                        print(f"      {i}. {concept.display} ({concept.code})")
                else:
                    print(f"   ⚠️  No matches found")
            except Exception as e:
                print(f"   ❌ Conversion failed: {e}")
        
        # Test 8: ValueSet Operations
        print("\n📚 VALUESET OPERATIONS")
        print("-" * 50)
        
        print("\nTesting ValueSet expansion for clinical findings:")
        try:
            # Try expanding a clinical findings subset
            clinical_findings_url = "http://snomed.info/sct?fhir_vs=ecl/<<404684003"
            valueset = await server.expand_valueset(clinical_findings_url, filter="diabetes")
            if valueset:
                print(f"   ✅ Expanded ValueSet: {valueset.title}")
                print(f"      Total concepts: {valueset.total}")
                print(f"      Returned: {len(valueset.contains)} concepts")
                for i, concept in enumerate(valueset.contains[:3], 1):
                    print(f"         {i}. {concept.display} ({concept.code})")
            else:
                print(f"   ⚠️  ValueSet not found or empty")
        except Exception as e:
            print(f"   ❌ ValueSet expansion failed: {e}")
        
        # Test 9: Code System Information - Enhanced with all systems
        print("\n🏗️ CODE SYSTEM INFORMATION")
        print("-" * 50)
        
        systems = [
            ("snomed", "SNOMED CT", "73211009"),      # Diabetes
            ("dmd", "dm+d", None),                    # Will skip validation
            ("icd10", "ICD-10", "E11"),              # Type 2 diabetes
            ("opcs4", "OPCS-4", "Z94.1")             # Knee replacement (example)
        ]
        
        for system_key, system_name, test_code in systems:
            print(f"\nTesting {system_name} system:")
            try:
                system_url = server.SYSTEMS.get(system_key)
                if system_url:
                    print(f"   ✅ System URL: {system_url}")
                    
                    # Test validation with a known good code if available
                    if test_code:
                        is_valid = await server.validate_code(test_code, system_key)
                        print(f"      Validation test ({test_code}): {'✅ Valid' if is_valid else '❌ Invalid'}")
                    else:
                        print(f"      Validation test: Skipped (no test code)")
                    
                    # Show ValueSet patterns for this system
                    patterns = [k for k in server.VALUESET_PATTERNS.keys() if k.startswith(system_key)]
                    if patterns:
                        print(f"      Available patterns: {', '.join(patterns)}")
                    
                else:
                    print(f"   ❌ System URL not configured")
            except Exception as e:
                print(f"   ❌ System test failed: {e}")
        
        print("\n" + "=" * 80)
        print("🎉 COMPREHENSIVE NHS TERMINOLOGY TEST COMPLETED!")
        print("=" * 80)


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the comprehensive test
    asyncio.run(test_comprehensive_nhs())