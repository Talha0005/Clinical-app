#!/usr/bin/env python3
"""
Real Training Test with Actual Data Processing
Tests the complete training pipeline with real Synthea data and prompts
"""

import asyncio
import json
import logging
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_real_training_pipeline():
    """Test the complete real training pipeline"""
    logger.info("🚀 Testing REAL Training Pipeline with Actual Data")
    logger.info("=" * 60)
    
    try:
        # Import training service
        from services.model_training_service import training_service, TrainingConfig
        
        # Step 1: Prepare real training data
        logger.info("📊 Step 1: Preparing REAL training data...")
        
        # Test Synthea data preparation
        synthea_examples = await training_service.prepare_synthea_training_data()
        logger.info(f"✅ Synthea: {len(synthea_examples)} training examples")
        
        # Test prompt data preparation
        prompt_examples = await training_service.prepare_prompt_training_data()
        logger.info(f"✅ Prompts: {len(prompt_examples)} training examples")
        
        # Test conversation data preparation
        conversation_examples = await training_service.prepare_conversation_training_data()
        logger.info(f"✅ Conversations: {len(conversation_examples)} training examples")
        
        total_examples = len(synthea_examples) + len(prompt_examples) + len(conversation_examples)
        logger.info(f"📈 Total training examples: {total_examples}")
        
        if total_examples == 0:
            logger.error("❌ No training data available")
            return False
        
        # Step 2: Configure real training
        logger.info("\n🔧 Step 2: Configuring REAL training...")
        
        config = TrainingConfig(
            model_name="claude-3-5-sonnet",
            epochs=2,  # Real epochs for testing
            learning_rate=0.0001,
            batch_size=4,
            max_length=1024,
            validation_split=0.2,
            save_every_n_epochs=1
        )
        
        logger.info(f"Training Configuration:")
        logger.info(f"  Model: {config.model_name}")
        logger.info(f"  Epochs: {config.epochs}")
        logger.info(f"  Learning Rate: {config.learning_rate}")
        logger.info(f"  Batch Size: {config.batch_size}")
        logger.info(f"  Validation Split: {config.validation_split}")
        
        # Step 3: Start real training
        logger.info("\n🚀 Step 3: Starting REAL training...")
        
        # Check initial status
        initial_status = training_service.get_training_status()
        logger.info(f"Initial Status: {initial_status}")
        
        # Start training
        success = await training_service.start_training(config)
        
        if not success:
            logger.error("❌ Training failed")
            return False
        
        # Step 4: Check training results
        logger.info("\n📊 Step 4: Analyzing REAL training results...")
        
        final_status = training_service.get_training_status()
        logger.info(f"Final Training Status:")
        logger.info(f"  Progress: {final_status['progress']:.2%}")
        logger.info(f"  Epochs Completed: {final_status['current_epoch']}")
        logger.info(f"  Training Loss: {final_status['training_loss']:.4f}")
        logger.info(f"  Validation Loss: {final_status['validation_loss']:.4f}")
        
        # Step 5: Check created models
        logger.info("\n🎯 Step 5: Checking REAL trained models...")
        
        models = training_service.get_available_models()
        logger.info(f"Created {len(models)} trained models:")
        
        for i, model in enumerate(models):
            logger.info(f"Model {i+1}: {model['name']}")
            logger.info(f"  Epoch: {model['metadata']['epoch']}")
            logger.info(f"  Training Loss: {model['metadata']['training_loss']:.4f}")
            logger.info(f"  Validation Loss: {model['metadata']['validation_loss']:.4f}")
            logger.info(f"  Created: {model['metadata']['timestamp']}")
        
        # Step 6: Test model loading
        logger.info("\n🔄 Step 6: Testing REAL model loading...")
        
        if models:
            latest_model = models[0]  # Most recent model
            logger.info(f"Loading model: {latest_model['name']}")
            
            load_success = await training_service.load_trained_model(latest_model['name'])
            
            if load_success:
                logger.info("✅ Model loaded successfully!")
            else:
                logger.error("❌ Model loading failed")
                return False
        
        # Step 7: Analyze training data quality
        logger.info("\n🔍 Step 7: Analyzing REAL training data quality...")
        
        # Analyze Synthea data quality
        synthea_quality_score = 0
        for example in synthea_examples[:5]:  # Sample first 5
            input_len = len(example.input_text)
            output_len = len(example.output_text)
            
            # Quality metrics
            detail_score = min(output_len / max(input_len, 1), 3.0)
            medical_keywords = ['patient', 'diagnosis', 'treatment', 'medication', 'symptoms']
            medical_score = sum(1 for kw in medical_keywords if kw.lower() in example.output_text.lower())
            
            example_quality = detail_score + medical_score * 0.5
            synthea_quality_score += example_quality
            
            logger.info(f"Synthea Example Quality: {example_quality:.2f}")
            logger.info(f"  Input: {example.input_text[:50]}...")
            logger.info(f"  Output: {example.output_text[:50]}...")
        
        avg_synthea_quality = synthea_quality_score / min(len(synthea_examples), 5)
        logger.info(f"Average Synthea Quality Score: {avg_synthea_quality:.2f}")
        
        # Analyze prompt data quality
        prompt_quality_score = 0
        for example in prompt_examples:
            input_len = len(example.input_text)
            output_len = len(example.output_text)
            
            detail_score = min(output_len / max(input_len, 1), 3.0)
            medical_score = sum(1 for kw in medical_keywords if kw.lower() in example.output_text.lower())
            
            example_quality = detail_score + medical_score * 0.5
            prompt_quality_score += example_quality
        
        avg_prompt_quality = prompt_quality_score / max(len(prompt_examples), 1)
        logger.info(f"Average Prompt Quality Score: {avg_prompt_quality:.2f}")
        
        # Overall quality assessment
        overall_quality = (avg_synthea_quality + avg_prompt_quality) / 2
        logger.info(f"Overall Training Data Quality: {overall_quality:.2f}")
        
        if overall_quality > 2.0:
            logger.info("✅ High quality training data")
        elif overall_quality > 1.0:
            logger.info("✅ Good quality training data")
        else:
            logger.info("⚠️  Training data quality could be improved")
        
        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("🎉 REAL TRAINING PIPELINE TEST COMPLETED!")
        logger.info(f"✅ Training Data: {total_examples} examples")
        logger.info(f"✅ Training Process: {'SUCCESS' if success else 'FAILED'}")
        logger.info(f"✅ Models Created: {len(models)}")
        logger.info(f"✅ Data Quality: {overall_quality:.2f}/5.0")
        logger.info(f"✅ Final Loss: {final_status['training_loss']:.4f}")
        
        return success and len(models) > 0
        
    except Exception as e:
        logger.error(f"❌ Error in real training pipeline test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_training_data_sources():
    """Test individual training data sources"""
    logger.info("🔍 Testing Individual Training Data Sources")
    logger.info("=" * 50)
    
    try:
        from services.model_training_service import training_service
        
        # Test each data source individually
        sources = {
            'Synthea': await training_service.prepare_synthea_training_data(),
            'Prompts': await training_service.prepare_prompt_training_data(),
            'Conversations': await training_service.prepare_conversation_training_data()
        }
        
        for source_name, examples in sources.items():
            logger.info(f"\n📊 {source_name} Data Source:")
            logger.info(f"  Examples: {len(examples)}")
            
            if examples:
                # Show sample
                sample = examples[0]
                logger.info(f"  Sample Input: {sample.input_text[:80]}...")
                logger.info(f"  Sample Output: {sample.output_text[:80]}...")
                logger.info(f"  Source: {sample.source}")
                
                # Quality analysis
                total_length = sum(len(ex.input_text) + len(ex.output_text) for ex in examples)
                avg_length = total_length / len(examples)
                logger.info(f"  Average Length: {avg_length:.0f} characters")
                
                # Medical content analysis
                medical_keywords = ['patient', 'diagnosis', 'treatment', 'medication', 'symptoms', 'medical']
                medical_count = sum(
                    sum(1 for kw in medical_keywords if kw.lower() in ex.output_text.lower())
                    for ex in examples
                )
                logger.info(f"  Medical Keywords: {medical_count}")
            else:
                logger.info(f"  No examples found")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing data sources: {e}")
        return False

async def main():
    """Run all real training tests"""
    logger.info("🔬 DigiClinic REAL Training Tests")
    logger.info("=" * 60)
    
    # Test 1: Individual data sources
    data_sources_ok = await test_training_data_sources()
    
    # Test 2: Complete training pipeline
    training_pipeline_ok = await test_real_training_pipeline()
    
    # Final results
    logger.info("\n" + "=" * 60)
    logger.info("📊 FINAL REAL TEST RESULTS:")
    logger.info(f"Data Sources: {'✅ WORKING' if data_sources_ok else '❌ NOT WORKING'}")
    logger.info(f"Training Pipeline: {'✅ WORKING' if training_pipeline_ok else '❌ NOT WORKING'}")
    
    if data_sources_ok and training_pipeline_ok:
        logger.info("\n🎉 ALL REAL TRAINING SYSTEMS ARE WORKING!")
        logger.info("✅ Real Synthea data processing: WORKING")
        logger.info("✅ Real doctor prompt processing: WORKING")
        logger.info("✅ Real training pipeline: WORKING")
        logger.info("✅ Real model creation: WORKING")
        logger.info("✅ Real model loading: WORKING")
    else:
        logger.info("\n⚠️  Some systems need attention")

if __name__ == "__main__":
    asyncio.run(main())
