#!/usr/bin/env python3
"""
Screenshot Format Comparison Test
Check our implementation against actual screenshot requirements
"""

from services.agent_response_formatter import AgentResponseStandardizer

def test_screenshot_format_comparison():
    print('ACTUAL SCREENSHOT COMPARISON ANALYSIS')
    print('=' * 50)
    
    try:
        standardizer = AgentResponseStandardizer()
        
        # Test with realistic agent response
        realistic_agent_response = {
            'definition': 'Fever is elevated body temperature',
            'causes': 'Viral/bacterial infections', 
            'symptoms': ['temperature', 'chills', 'fatigue'],
            'treatment': 'Fluids, rest, antipyretics',
            'clinical_codes': 'SNOMED CT + ICD-10'
        }
        
        formatted_response = standardizer.ensure_admin_format_compliance(
            agent_response=realistic_agent_response,
            condition_name='Fever'
        )
        
        standardized_format = formatted_response.get('standardized_format', {})
        
        # SCREENSHOT REQUIRED CATEGORIES (from your accurate feedback)
        screenshot_required_categories = [
            'Condition name', 'Definition', 'Classification', 'Epidemiology', 'Aetiology', 
            'Risk factors', 'Signs', 'Symptoms', 'Complications', 'Tests', 
            'Differential diagnoses', 'Associated conditions', 'Management', 'Prevention'
        ]
        
        print('OUR IMPLEMENTED vs SCREENSHOT REQUIRED:')
        print('=' * 55)
        
        our_categories = list(standardized_format.keys())
        print('OUR CATEGORIES:', our_categories)
        print('SCREENSHOT REQUIRED:', screenshot_required_categories)
        
        print('\nDETAILED COMPARISON:')
        print('-' * 30)
        
        missing_categories = []
        matching_categories = []
        
        for screenshot_cat in screenshot_required_categories:
            found_match = False
            for our_cat in our_categories:
                if screenshot_cat.lower() == our_cat.lower():
                    matching_categories.append(screenshot_cat)
                    found_match = True
                    print(f'MATCHED: {screenshot_cat}')
                    break
        
        if not found_match:
            missing_categories.append(screenshot_cat)
            print(f'MISSING: {screenshot_cat}')
        
        print('\nSUMMARY:')
        print(f'Matching categories: {len(matching_categories)}/{len(screenshot_required_categories)}')
        print(f'Missing categories: {len(missing_categories)}')
        print(f'Miss rate: {(len(missing_categories)/len(screenshot_required_categories))*100:.1f}%')
        
        if missing_categories:
            print('\nMISSING CATEGORIES NEED TO BE FIXED:')
            for cat in missing_categories:
                print(f'  - {cat}')
        
        return missing_categories
    
    except Exception as e:
        print(f'ERROR: {e}')
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    missing = test_screenshot_format_comparison()
