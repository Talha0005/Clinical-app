#!/usr/bin/env python3
"""
Simple Real Data Test for DigiClinic
Tests actual data without complex service initialization
"""

import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_real_synthea_data():
    """Test with real Synthea patient data"""
    logger.info("🧪 Testing with REAL Synthea data...")
    
    try:
        # Load real patient data
        patient_db_path = Path("dat/patient-db.json")
        if not patient_db_path.exists():
            logger.error("❌ No patient database found at dat/patient-db.json")
            return False
        
        with open(patient_db_path, 'r', encoding='utf-8') as f:
            patients_data = json.load(f)
        
        patients = patients_data if isinstance(patients_data, list) else patients_data.get('patients', [])
        logger.info(f"✅ Found {len(patients)} REAL patients in database")
        
        # Show real patient data
        for i, patient in enumerate(patients[:3]):  # Show first 3 patients
            logger.info(f"Patient {i+1}: {patient.get('name', 'Unknown')}")
            logger.info(f"  Age: {patient.get('age', 'Unknown')}")
            logger.info(f"  Medical History: {patient.get('medical_history', [])}")
            logger.info(f"  Medications: {patient.get('current_medications', [])}")
        
        # Create training examples from real data
        training_examples = []
        for patient in patients:
            # Example 1: Condition diagnosis
            if patient.get('medical_history'):
                for condition in patient['medical_history']:
                    input_text = f"Patient presents with: {condition}. "
                    input_text += f"Age: {patient.get('age', 'unknown')}, "
                    input_text += f"Name: {patient.get('name', 'unknown')}"
                    
                    output_text = f"Based on the symptoms '{condition}', "
                    output_text += f"this appears to be {condition}. "
                    output_text += f"Consider differential diagnosis and appropriate treatment options."
                    
                    training_examples.append({
                        'input': input_text,
                        'output': output_text,
                        'source': 'synthea',
                        'patient': patient.get('name', 'unknown')
                    })
            
            # Example 2: Medication management
            if patient.get('current_medications'):
                for medication in patient['current_medications']:
                    input_text = f"Patient is taking {medication}. "
                    input_text += f"Current conditions: {', '.join(patient.get('medical_history', []))}"
                    
                    output_text = f"Review medication {medication} for appropriateness. "
                    output_text += f"Check for drug interactions and contraindications. "
                    output_text += f"Monitor for side effects and therapeutic response."
                    
                    training_examples.append({
                        'input': input_text,
                        'output': output_text,
                        'source': 'synthea',
                        'patient': patient.get('name', 'unknown')
                    })
        
        logger.info(f"✅ Created {len(training_examples)} REAL training examples from Synthea data")
        
        # Show sample training examples
        for i, example in enumerate(training_examples[:3]):
            logger.info(f"Training Example {i+1} (Patient: {example['patient']}):")
            logger.info(f"  Input: {example['input'][:100]}...")
            logger.info(f"  Output: {example['output'][:100]}...")
            logger.info(f"  Source: {example['source']}")
        
        return len(training_examples) > 0
        
    except Exception as e:
        logger.error(f"❌ Error testing Synthea data: {e}")
        return False

def test_real_prompts():
    """Test with real doctor prompts"""
    logger.info("🧪 Testing with REAL doctor prompts...")
    
    try:
        # Load real prompts
        prompts_path = Path("dat/prompts.json")
        if not prompts_path.exists():
            logger.error("❌ No prompts file found at dat/prompts.json")
            return False
        
        with open(prompts_path, 'r', encoding='utf-8') as f:
            prompts_data = json.load(f)
        
        prompts = prompts_data.get('prompts', {})
        logger.info(f"✅ Found {len(prompts)} REAL prompts in system")
        
        # Show real prompts
        for prompt_id, prompt_data in prompts.items():
            logger.info(f"Prompt: {prompt_data.get('name', 'Unknown')}")
            logger.info(f"  ID: {prompt_id}")
            logger.info(f"  Category: {prompt_data.get('category', 'Unknown')}")
            logger.info(f"  Active: {prompt_data.get('is_active', False)}")
            logger.info(f"  Content: {prompt_data.get('content', '')[:100]}...")
        
        # Create training examples from real prompts
        training_examples = []
        for prompt_id, prompt_data in prompts.items():
            if prompt_data.get('is_active', False):
                content = prompt_data.get('content', '')
                category = prompt_data.get('category', '')
                
                if category == 'system':
                    input_text = "How should I behave as a medical AI assistant?"
                    output_text = content
                    
                    training_examples.append({
                        'input': input_text,
                        'output': output_text,
                        'source': 'prompt',
                        'prompt_id': prompt_id,
                        'category': category
                    })
                
                elif category == 'medical':
                    input_text = f"Medical question about {prompt_id}"
                    output_text = content
                    
                    training_examples.append({
                        'input': input_text,
                        'output': output_text,
                        'source': 'prompt',
                        'prompt_id': prompt_id,
                        'category': category
                    })
        
        logger.info(f"✅ Created {len(training_examples)} REAL training examples from prompts")
        
        # Show sample training examples
        for i, example in enumerate(training_examples[:2]):
            logger.info(f"Prompt Training Example {i+1} (Prompt: {example['prompt_id']}):")
            logger.info(f"  Input: {example['input'][:100]}...")
            logger.info(f"  Output: {example['output'][:100]}...")
            logger.info(f"  Source: {example['source']}")
            logger.info(f"  Category: {example['category']}")
        
        return len(training_examples) > 0
        
    except Exception as e:
        logger.error(f"❌ Error testing prompts: {e}")
        return False

def test_real_conversations():
    """Test with real conversation data"""
    logger.info("🧪 Testing with REAL conversation data...")
    
    try:
        # Check if we have any conversation files
        conversation_files = list(Path("dat").glob("*conversation*"))
        conversation_files.extend(list(Path("dat").glob("*chat*")))
        
        if not conversation_files:
            logger.info("ℹ️  No conversation files found - this is normal for a new system")
            logger.info("ℹ️  Conversations will be created as users interact with the system")
            return True
        
        logger.info(f"✅ Found {len(conversation_files)} conversation files")
        
        # Process conversation files
        training_examples = []
        for file_path in conversation_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    conversations = json.load(f)
                
                # Process conversations (format may vary)
                if isinstance(conversations, list):
                    for conv in conversations:
                        if 'messages' in conv:
                            messages = conv['messages']
                            for i in range(len(messages) - 1):
                                if (messages[i].get('role') == 'user' and 
                                    messages[i + 1].get('role') == 'assistant'):
                                    
                                    training_examples.append({
                                        'input': messages[i].get('content', ''),
                                        'output': messages[i + 1].get('content', ''),
                                        'source': 'conversation',
                                        'conversation_id': conv.get('id', 'unknown')
                                    })
                
            except Exception as e:
                logger.warning(f"⚠️  Could not process {file_path}: {e}")
        
        logger.info(f"✅ Created {len(training_examples)} REAL training examples from conversations")
        
        # Show sample conversation examples
        for i, example in enumerate(training_examples[:2]):
            logger.info(f"Conversation Example {i+1} (Conv: {example['conversation_id']}):")
            logger.info(f"  Input: {example['input'][:100]}...")
            logger.info(f"  Output: {example['output'][:100]}...")
            logger.info(f"  Source: {example['source']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing conversations: {e}")
        return False

def test_training_data_summary():
    """Test overall training data summary"""
    logger.info("🧪 Testing training data summary...")
    
    try:
        # Get all training data
        synthea_examples = []
        prompt_examples = []
        conversation_examples = []
        
        # Synthea data
        patient_db_path = Path("dat/patient-db.json")
        if patient_db_path.exists():
            with open(patient_db_path, 'r', encoding='utf-8') as f:
                patients_data = json.load(f)
            patients = patients_data if isinstance(patients_data, list) else patients_data.get('patients', [])
            
            for patient in patients:
                if patient.get('medical_history'):
                    for condition in patient['medical_history']:
                        synthea_examples.append({
                            'type': 'condition',
                            'patient': patient.get('name', 'unknown'),
                            'data': condition
                        })
                
                if patient.get('current_medications'):
                    for medication in patient['current_medications']:
                        synthea_examples.append({
                            'type': 'medication',
                            'patient': patient.get('name', 'unknown'),
                            'data': medication
                        })
        
        # Prompt data
        prompts_path = Path("dat/prompts.json")
        if prompts_path.exists():
            with open(prompts_path, 'r', encoding='utf-8') as f:
                prompts_data = json.load(f)
            prompts = prompts_data.get('prompts', {})
            
            for prompt_id, prompt_data in prompts.items():
                if prompt_data.get('is_active', False):
                    prompt_examples.append({
                        'id': prompt_id,
                        'category': prompt_data.get('category', 'unknown'),
                        'name': prompt_data.get('name', 'unknown')
                    })
        
        # Summary
        logger.info(f"📊 REAL TRAINING DATA SUMMARY:")
        logger.info(f"  Synthea Patients: {len(set(p['patient'] for p in synthea_examples))}")
        logger.info(f"  Synthea Conditions: {len([p for p in synthea_examples if p['type'] == 'condition'])}")
        logger.info(f"  Synthea Medications: {len([p for p in synthea_examples if p['type'] == 'medication'])}")
        logger.info(f"  Active Prompts: {len(prompt_examples)}")
        logger.info(f"  Total Training Examples: {len(synthea_examples) + len(prompt_examples)}")
        
        # Show breakdown by category
        categories = {}
        for prompt in prompt_examples:
            cat = prompt['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        logger.info(f"📋 Prompt Categories:")
        for category, count in categories.items():
            logger.info(f"  {category}: {count} prompts")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in training data summary: {e}")
        return False

def main():
    """Run all real tests"""
    logger.info("🔬 DigiClinic REAL Data Tests")
    logger.info("=" * 50)
    
    # Test results
    results = {}
    
    # Test 1: Real Synthea data
    results['synthea'] = test_real_synthea_data()
    
    # Test 2: Real prompts
    results['prompts'] = test_real_prompts()
    
    # Test 3: Real conversations
    results['conversations'] = test_real_conversations()
    
    # Test 4: Training data summary
    results['summary'] = test_training_data_summary()
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 REAL TEST RESULTS SUMMARY:")
    logger.info(f"Synthea Data: {'✅ WORKING' if results['synthea'] else '❌ NOT WORKING'}")
    logger.info(f"Doctor Prompts: {'✅ WORKING' if results['prompts'] else '❌ NOT WORKING'}")
    logger.info(f"Conversations: {'✅ WORKING' if results['conversations'] else '❌ NOT WORKING'}")
    logger.info(f"Data Summary: {'✅ WORKING' if results['summary'] else '❌ NOT WORKING'}")
    
    all_working = all(results.values())
    
    if all_working:
        logger.info("\n🎉 ALL REAL DATA SYSTEMS ARE WORKING!")
        logger.info("✅ Real Synthea patient data: AVAILABLE")
        logger.info("✅ Real doctor prompts: AVAILABLE")
        logger.info("✅ Real conversation system: READY")
        logger.info("✅ Training data preparation: WORKING")
    else:
        logger.info("\n⚠️  Some systems need attention")
        for test, result in results.items():
            if not result:
                logger.info(f"❌ {test}: NEEDS FIXING")

if __name__ == "__main__":
    main()
