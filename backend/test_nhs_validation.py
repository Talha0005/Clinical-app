#!/usr/bin/env python3
"""
NHS Validation Test for Model Training
Tests NHS validation before model training
"""

import asyncio
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_nhs_validation():
    """Test NHS validation before model training"""
    logger.info("🏥 Testing NHS Validation for Model Training")
    logger.info("=" * 60)
    
    try:
        # Import NHS validation service
        from services.nhs_validation_service import nhs_validator
        
        # Load real patient data
        patient_db_path = Path("dat/patient-db.json")
        if not patient_db_path.exists():
            logger.error("❌ No patient database found")
            return False
        
        with open(patient_db_path, 'r', encoding='utf-8') as f:
            patients_data = json.load(f)
        
        patients = patients_data if isinstance(patients_data, list) else patients_data.get('patients', [])
        logger.info(f"📊 Found {len(patients)} patients for NHS validation")
        
        # Load real prompts data
        prompts_path = Path("dat/prompts.json")
        if not prompts_path.exists():
            logger.error("❌ No prompts file found")
            return False
        
        with open(prompts_path, 'r', encoding='utf-8') as f:
            prompts_data = json.load(f)
        
        prompts = prompts_data.get('prompts', {})
        logger.info(f"📋 Found {len(prompts)} prompts for NHS validation")
        
        # Test 1: Validate Synthea data
        logger.info("\n🏥 Test 1: Validating Synthea data against NHS terminology...")
        
        synthea_result = await nhs_validator.validate_synthea_data(patients)
        
        logger.info(f"✅ Synthea Validation Results:")
        logger.info(f"  Is Valid: {synthea_result.is_valid}")
        logger.info(f"  Validation Score: {synthea_result.validation_score:.1f}%")
        logger.info(f"  Validated Codes: {len(synthea_result.validated_codes)}")
        logger.info(f"  Invalid Items: {len(synthea_result.invalid_items)}")
        
        # Show validated codes
        logger.info(f"\n📋 Validated Medical Codes:")
        for code in synthea_result.validated_codes[:5]:  # Show first 5
            logger.info(f"  {code['type'].upper()}: {code['original']}")
            logger.info(f"    Code: {code.get('snomed_code', code.get('dm_d_code', 'N/A'))}")
            logger.info(f"    Description: {code.get('description', 'N/A')}")
            logger.info(f"    Patient: {code.get('patient', 'N/A')}")
        
        # Show invalid items
        if synthea_result.invalid_items:
            logger.info(f"\n❌ Invalid Items:")
            for item in synthea_result.invalid_items[:3]:  # Show first 3
                logger.info(f"  {item['type'].upper()}: {item['original']}")
                logger.info(f"    Reason: {item.get('reason', 'N/A')}")
                logger.info(f"    Patient: {item.get('patient', 'N/A')}")
        
        # Test 2: Validate prompts
        logger.info("\n📋 Test 2: Validating doctor prompts against NHS guidelines...")
        
        prompts_result = await nhs_validator.validate_prompts(prompts_data)
        
        logger.info(f"✅ Prompts Validation Results:")
        logger.info(f"  Is Valid: {prompts_result.is_valid}")
        logger.info(f"  Validation Score: {prompts_result.validation_score:.1f}%")
        logger.info(f"  Validated Codes: {len(prompts_result.validated_codes)}")
        logger.info(f"  Invalid Items: {len(prompts_result.invalid_items)}")
        
        # Show validated prompts
        logger.info(f"\n📋 Validated Prompts:")
        for prompt in prompts_result.validated_codes:
            logger.info(f"  Prompt: {prompt['prompt_id']}")
            logger.info(f"    Compliance Score: {prompt['compliance_score']:.1f}%")
            logger.info(f"    NHS Keywords: {prompt['nhs_keywords_found']}")
            logger.info(f"    Category: {prompt['category']}")
        
        # Test 3: Generate comprehensive report
        logger.info("\n📊 Test 3: Generating comprehensive NHS validation report...")
        
        validation_report = nhs_validator.get_validation_report(synthea_result, prompts_result)
        
        logger.info(f"✅ Overall NHS Validation Report:")
        logger.info(f"  Overall Valid: {validation_report['overall_validation']['is_valid']}")
        logger.info(f"  Overall Score: {validation_report['overall_validation']['validation_score']:.1f}%")
        logger.info(f"  Total Items: {validation_report['overall_validation']['total_items']}")
        logger.info(f"  Valid Items: {validation_report['overall_validation']['valid_items']}")
        logger.info(f"  Invalid Items: {validation_report['overall_validation']['invalid_items']}")
        
        # Show recommendations
        logger.info(f"\n💡 NHS Validation Recommendations:")
        for i, recommendation in enumerate(validation_report['recommendations'], 1):
            logger.info(f"  {i}. {recommendation}")
        
        # Test 4: Check if training can proceed
        logger.info(f"\n🚀 Test 4: Can model training proceed?")
        
        can_proceed = validation_report['overall_validation']['is_valid']
        
        if can_proceed:
            logger.info("✅ YES - Model training can proceed with NHS validation approval")
            logger.info(f"   NHS Validation Score: {validation_report['overall_validation']['validation_score']:.1f}%")
            logger.info("   All data meets NHS standards")
        else:
            logger.info("❌ NO - Model training cannot proceed")
            logger.info(f"   NHS Validation Score: {validation_report['overall_validation']['validation_score']:.1f}%")
            logger.info("   Data does not meet NHS standards")
        
        # Save validation report
        report_file = Path("dat/training/nhs_validation_test_report.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n📄 NHS validation report saved to: {report_file}")
        
        return can_proceed
        
    except Exception as e:
        logger.error(f"❌ Error in NHS validation test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_training_with_nhs_validation():
    """Test complete training process with NHS validation"""
    logger.info("\n🔬 Testing Complete Training Process with NHS Validation")
    logger.info("=" * 60)
    
    try:
        # Import training service
        from services.model_training_service import training_service, TrainingConfig
        
        # Test training with NHS validation
        logger.info("🚀 Starting training with NHS validation...")
        
        config = TrainingConfig(
            model_name="claude-3-5-sonnet",
            epochs=1,  # Just 1 epoch for testing
            learning_rate=0.0001,
            batch_size=4,
            max_length=1024,
            validation_split=0.2,
            save_every_n_epochs=1
        )
        
        # Start training (this will include NHS validation)
        success = await training_service.start_training(config)
        
        if success:
            logger.info("✅ Training completed successfully with NHS validation!")
            
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
            
            return True
        else:
            logger.error("❌ Training failed")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error in training with NHS validation test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all NHS validation tests"""
    logger.info("🔬 DigiClinic NHS Validation Tests")
    logger.info("=" * 60)
    
    # Test 1: NHS validation
    validation_success = await test_nhs_validation()
    
    # Test 2: Training with NHS validation
    training_success = await test_training_with_nhs_validation()
    
    # Final results
    logger.info("\n" + "=" * 60)
    logger.info("📊 FINAL NHS VALIDATION TEST RESULTS:")
    logger.info(f"NHS Validation: {'✅ WORKING' if validation_success else '❌ NOT WORKING'}")
    logger.info(f"Training with NHS Validation: {'✅ WORKING' if training_success else '❌ NOT WORKING'}")
    
    if validation_success and training_success:
        logger.info("\n🎉 ALL NHS VALIDATION SYSTEMS ARE WORKING!")
        logger.info("✅ NHS terminology validation: WORKING")
        logger.info("✅ NHS guidelines validation: WORKING")
        logger.info("✅ Model training with NHS validation: WORKING")
        logger.info("✅ NHS compliance checking: WORKING")
    else:
        logger.info("\n⚠️  Some NHS validation systems need attention")

if __name__ == "__main__":
    asyncio.run(main())
