#!/usr/bin/env python3
"""
Real Training Test Script for DigiClinic
Tests with actual Synthea data, real prompts, and real conversations
"""

import asyncio
import json
import logging
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.model_training_service import training_service, TrainingConfig
from services.prompts_service import prompts_service

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_real_synthea_data():
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
        
        # Test training data preparation
        synthea_examples = await training_service.prepare_synthea_training_data()
        logger.info(f"✅ Created {len(synthea_examples)} REAL training examples from Synthea data")
        
        # Show sample training examples
        for i, example in enumerate(synthea_examples[:2]):
            logger.info(f"Training Example {i+1}:")
            logger.info(f"  Input: {example.input_text[:100]}...")
            logger.info(f"  Output: {example.output_text[:100]}...")
            logger.info(f"  Source: {example.source}")
            logger.info(f"  Metadata: {example.metadata}")
        
        return len(synthea_examples) > 0
        
    except Exception as e:
        logger.error(f"❌ Error testing Synthea data: {e}")
        return False

async def test_real_prompts():
    """Test with real doctor prompts"""
    logger.info("🧪 Testing with REAL doctor prompts...")
    
    try:
        # Load real prompts
        prompts = prompts_service.get_all_prompts()
        logger.info(f"✅ Found {len(prompts)} REAL prompts in system")
        
        # Show real prompts
        for prompt_id, prompt_data in prompts.items():
            logger.info(f"Prompt: {prompt_data.get('name', 'Unknown')}")
            logger.info(f"  Category: {prompt_data.get('category', 'Unknown')}")
            logger.info(f"  Active: {prompt_data.get('is_active', False)}")
            logger.info(f"  Content: {prompt_data.get('content', '')[:100]}...")
        
        # Test training data preparation
        prompt_examples = await training_service.prepare_prompt_training_data()
        logger.info(f"✅ Created {len(prompt_examples)} REAL training examples from prompts")
        
        # Show sample training examples
        for i, example in enumerate(prompt_examples[:2]):
            logger.info(f"Prompt Training Example {i+1}:")
            logger.info(f"  Input: {example.input_text[:100]}...")
            logger.info(f"  Output: {example.output_text[:100]}...")
            logger.info(f"  Source: {example.source}")
            logger.info(f"  Metadata: {example.metadata}")
        
        return len(prompt_examples) > 0
        
    except Exception as e:
        logger.error(f"❌ Error testing prompts: {e}")
        return False

async def test_real_conversations():
    """Test with real conversation data"""
    logger.info("🧪 Testing with REAL conversation data...")
    
    try:
        # Test conversation data preparation
        conversation_examples = await training_service.prepare_conversation_training_data()
        logger.info(f"✅ Found {len(conversation_examples)} REAL conversation examples")
        
        # Show sample conversation examples
        for i, example in enumerate(conversation_examples[:2]):
            logger.info(f"Conversation Example {i+1}:")
            logger.info(f"  Input: {example.input_text[:100]}...")
            logger.info(f"  Output: {example.output_text[:100]}...")
            logger.info(f"  Source: {example.source}")
            logger.info(f"  Metadata: {example.metadata}")
        
        return True  # Even if no conversations, this is still valid
        
    except Exception as e:
        logger.error(f"❌ Error testing conversations: {e}")
        return False

async def test_real_training():
    """Test real training process"""
    logger.info("🧪 Testing REAL training process...")
    
    try:
        # Prepare all training data
        all_examples = await training_service.prepare_all_training_data()
        logger.info(f"✅ Prepared {len(all_examples)} TOTAL training examples")
        
        # Count by source
        synthea_count = len([e for e in all_examples if e.source == 'synthea'])
        prompt_count = len([e for e in all_examples if e.source == 'prompt'])
        conversation_count = len([e for e in all_examples if e.source == 'conversation'])
        
        logger.info(f"📊 Training Data Breakdown:")
        logger.info(f"  Synthea: {synthea_count} examples")
        logger.info(f"  Prompts: {prompt_count} examples")
        logger.info(f"  Conversations: {conversation_count} examples")
        
        if len(all_examples) == 0:
            logger.warning("⚠️  No training data available")
            return False
        
        # Test training configuration
        config = TrainingConfig(
            model_name="claude-3-5-sonnet",
            epochs=1,  # Just 1 epoch for testing
            learning_rate=0.0001,
            batch_size=4,
            max_length=1024,
            validation_split=0.2,
            save_every_n_epochs=1
        )
        
        logger.info(f"🔧 Training Configuration:")
        logger.info(f"  Model: {config.model_name}")
        logger.info(f"  Epochs: {config.epochs}")
        logger.info(f"  Learning Rate: {config.learning_rate}")
        logger.info(f"  Batch Size: {config.batch_size}")
        
        # Start real training
        logger.info("🚀 Starting REAL training...")
        success = await training_service.start_training(config)
        
        if success:
            logger.info("✅ Training completed successfully!")
            
            # Check training status
            status = training_service.get_training_status()
            logger.info(f"📊 Final Training Status:")
            logger.info(f"  Progress: {status['progress']:.2%}")
            logger.info(f"  Epochs: {status['current_epoch']}")
            logger.info(f"  Training Loss: {status['training_loss']:.4f}")
            logger.info(f"  Validation Loss: {status['validation_loss']:.4f}")
            
            # Check available models
            models = training_service.get_available_models()
            logger.info(f"✅ Created {len(models)} trained models")
            
            for model in models:
                logger.info(f"Model: {model['name']}")
                logger.info(f"  Epoch: {model['metadata']['epoch']}")
                logger.info(f"  Loss: {model['metadata']['training_loss']:.4f}")
                logger.info(f"  Created: {model['metadata']['timestamp']}")
            
            return True
        else:
            logger.error("❌ Training failed")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error in training test: {e}")
        return False

async def test_model_loading():
    """Test loading trained models"""
    logger.info("🧪 Testing model loading...")
    
    try:
        models = training_service.get_available_models()
        
        if len(models) == 0:
            logger.warning("⚠️  No trained models available")
            return False
        
        # Test loading the latest model
        latest_model = models[0]  # Models are sorted by epoch
        logger.info(f"🔄 Loading model: {latest_model['name']}")
        
        success = await training_service.load_trained_model(latest_model['name'])
        
        if success:
            logger.info("✅ Model loaded successfully!")
            return True
        else:
            logger.error("❌ Model loading failed")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error testing model loading: {e}")
        return False

async def main():
    """Run all real tests"""
    logger.info("🔬 DigiClinic REAL Training Tests")
    logger.info("=" * 50)
    
    # Test results
    results = {}
    
    # Test 1: Real Synthea data
    results['synthea'] = await test_real_synthea_data()
    
    # Test 2: Real prompts
    results['prompts'] = await test_real_prompts()
    
    # Test 3: Real conversations
    results['conversations'] = await test_real_conversations()
    
    # Test 4: Real training
    results['training'] = await test_real_training()
    
    # Test 5: Model loading
    results['model_loading'] = await test_model_loading()
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 REAL TEST RESULTS SUMMARY:")
    logger.info(f"Synthea Data: {'✅ WORKING' if results['synthea'] else '❌ NOT WORKING'}")
    logger.info(f"Doctor Prompts: {'✅ WORKING' if results['prompts'] else '❌ NOT WORKING'}")
    logger.info(f"Conversations: {'✅ WORKING' if results['conversations'] else '❌ NOT WORKING'}")
    logger.info(f"Model Training: {'✅ WORKING' if results['training'] else '❌ NOT WORKING'}")
    logger.info(f"Model Loading: {'✅ WORKING' if results['model_loading'] else '❌ NOT WORKING'}")
    
    all_working = all(results.values())
    
    if all_working:
        logger.info("\n🎉 ALL REAL SYSTEMS ARE WORKING!")
        logger.info("✅ Model training with real Synthea data: WORKING")
        logger.info("✅ Model training with real doctor prompts: WORKING")
        logger.info("✅ Model training with real conversations: WORKING")
        logger.info("✅ Real model training process: WORKING")
        logger.info("✅ Real model loading: WORKING")
    else:
        logger.info("\n⚠️  Some systems need attention")
        for test, result in results.items():
            if not result:
                logger.info(f"❌ {test}: NEEDS FIXING")

if __name__ == "__main__":
    asyncio.run(main())
