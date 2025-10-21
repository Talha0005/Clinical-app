#!/usr/bin/env python3
"""
Test script for Admin 14-category format
Tests the exact 14-category format specified by the client
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.agent_response_formatter import AgentResponseFormatter

def test_admin_format():
    """Test the admin format with a sample agent response"""
    
    formatter = AgentResponseFormatter()
    
    # Sample agent response
    sample_agent_response = {
        "condition_name": "Hypertension",
        "definition": "High blood pressure condition affecting cardiovascular system",
        "classification": "Cardiovascular disorder",
        "epidemiology": "Common condition affecting millions globally",
        "incidence": "15-20% of adult population",
        "prevalence": "High prevalence in developed countries",
        "aetiology": "Primary and secondary causes including lifestyle factors",
        "causes": ["Lifestyle factors", "Genetics", "Underlying conditions"],
        "risk_factors": ["Age", "Obesity", "Smoking", "Sedentary lifestyle"],
        "signs": ["Elevated blood pressure readings", "Possible headache"],
        "symptoms": ["Often asymptomatic", "Headaches", "Dizziness"],
        "complications": "Heart disease, stroke, kidney damage",
        "tests": ["Blood pressure measurement", "ECG", "Blood tests"],
        "diagnostic_criteria": "Systolic >140 or diastolic >90 mmHg",
        "differential_diagnoses": ["White coat hypertension", "Secondary hypertension"],
        "associated_conditions": ["Diabetes", "Obesity", "Hyperlipidemia"],
        "treatment": "Lifestyle modifications and antihypertensive medications",
        "management": "Comprehensive cardiovascular risk management",
        "conservative": "Diet, exercise, weight loss",
        "medical": "ACE inhibitors, beta blockers, diuretics",
        "surgical": "Rarely required for primary hypertension",
        "prevention": "Lifestyle modifications and regular monitoring",
        "primary_prevention": "Healthy diet, regular exercise",
        "secondary_prevention": "Regular monitoring and medication compliance"
    }
    
    # Format for admin
    formatted_response = formatter.format_agent_response_for_admin(
        agent_response=sample_agent_response,
        condition_name="Hypertension",
        agent_type="Clinical Reasoning Agent"
    )
    
    print("=== ADMIN 14-CATEGORY FORMAT TEST ===")
    print()
    print(f"Agent Source: {formatted_response['agent_source']}")
    print(f"Condition: {formatted_response['condition']}")
    print(f"Formatted At: {formatted_response['formatted_at']}")
    print()
    print("=== STANDARDIZED 14-CATEGORY FORMAT ===")
    
    standardized_format = formatted_response["standardized_format"]
    
    for i, (category, content) in enumerate(standardized_format.items(), 1):
        print(f"{i}. {category}:")
        if isinstance(content, list):
            for item in content:
                print(f"   - {item}")
        else:
            print(f"   {content}")
        print()
    
    print("=== FORMAT VERIFICATION ===")
    expected_categories = [
        "Condition name",
        "Definition", 
        "Classification",
        "Epidemiology - Incidence / Prevalence",
        "Aetiology",
        "Risk factors",
        "Signs", 
        "Symptoms",
        "Complications",
        "Tests (and diagnostic criteria)",
        "Differential diagnoses",
        "Associated conditions", 
        "Management - conservative, medical, surgical",
        "Prevention (primary, secondary)"
    ]
    
    actual_categories = list(standardized_format.keys())
    
    print("Category Verification:")
    for expected in expected_categories:
        if expected in actual_categories:
            print(f"✓ {expected}")
        else:
            print(f"✗ MISSING: {expected}")
    
    print(f"\nTotal Categories: {len(actual_categories)}/14")
    print("Format Compliance: " + ("PASSED" if len(actual_categories) == 14 else "FAILED"))
    
    return formatted_response

if __name__ == "__main__":
    result = test_admin_format()
    print("\n=== TEST COMPLETED ===")