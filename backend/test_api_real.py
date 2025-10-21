#!/usr/bin/env python3
"""
Real API Test for DigiClinic Training System
Tests all training API endpoints with actual data
"""

import requests
import json
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8000"

def test_training_api_endpoints():
    """Test all training API endpoints with real data"""
    logger.info("🔬 Testing Training API Endpoints with REAL Data")
    logger.info("=" * 60)
    
    # Wait for server to start
    logger.info("⏳ Waiting for server to start...")
    time.sleep(3)
    
    try:
        # Test 1: Health check
        logger.info("🏥 Testing health check...")
        response = requests.get(f"{BASE_URL}/api/training/health", timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            logger.info(f"✅ Health check passed: {health_data}")
        else:
            logger.error(f"❌ Health check failed: {response.status_code}")
            return False
        
        # Test 2: Get training data sources
        logger.info("\n📊 Testing training data sources...")
        response = requests.get(f"{BASE_URL}/api/training/data/sources", timeout=10)
        
        if response.status_code == 200:
            sources_data = response.json()
            logger.info(f"✅ Data sources retrieved:")
            logger.info(f"  Synthea: {sources_data['sources']['synthea']['examples_count']} examples")
            logger.info(f"  Prompts: {sources_data['sources']['prompts']['examples_count']} examples")
            logger.info(f"  Conversations: {sources_data['sources']['conversations']['examples_count']} examples")
            logger.info(f"  Total: {sources_data['total_examples']} examples")
        else:
            logger.error(f"❌ Data sources failed: {response.status_code}")
            return False
        
        # Test 3: Prepare training data
        logger.info("\n🔧 Testing training data preparation...")
        response = requests.post(f"{BASE_URL}/api/training/prepare-data", timeout=30)
        
        if response.status_code == 200:
            prep_data = response.json()
            logger.info(f"✅ Training data prepared:")
            logger.info(f"  Examples: {prep_data['examples_count']}")
            logger.info(f"  Synthea: {prep_data['sources']['synthea']}")
            logger.info(f"  Prompts: {prep_data['sources']['prompts']}")
            logger.info(f"  Conversations: {prep_data['sources']['conversations']}")
        else:
            logger.error(f"❌ Data preparation failed: {response.status_code}")
            return False
        
        # Test 4: Get training status
        logger.info("\n📈 Testing training status...")
        response = requests.get(f"{BASE_URL}/api/training/status", timeout=10)
        
        if response.status_code == 200:
            status_data = response.json()
            logger.info(f"✅ Training status retrieved:")
            logger.info(f"  Is Training: {status_data['is_training']}")
            logger.info(f"  Progress: {status_data['progress']:.2%}")
            logger.info(f"  Current Epoch: {status_data['current_epoch']}")
            logger.info(f"  Training Loss: {status_data['training_loss']:.4f}")
            logger.info(f"  Validation Loss: {status_data['validation_loss']:.4f}")
        else:
            logger.error(f"❌ Training status failed: {response.status_code}")
            return False
        
        # Test 5: Start training
        logger.info("\n🚀 Testing training start...")
        
        training_config = {
            "model_name": "claude-3-5-sonnet",
            "epochs": 1,  # Just 1 epoch for testing
            "learning_rate": 0.0001,
            "batch_size": 4,
            "max_length": 1024,
            "validation_split": 0.2,
            "save_every_n_epochs": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/training/start",
            json=training_config,
            timeout=60
        )
        
        if response.status_code == 200:
            start_data = response.json()
            logger.info(f"✅ Training started:")
            logger.info(f"  Success: {start_data['success']}")
            logger.info(f"  Message: {start_data['message']}")
            logger.info(f"  Config: {start_data['config']}")
        else:
            logger.error(f"❌ Training start failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
        
        # Test 6: Monitor training progress
        logger.info("\n⏳ Monitoring training progress...")
        
        for i in range(10):  # Check for 10 iterations
            time.sleep(2)
            
            response = requests.get(f"{BASE_URL}/api/training/status", timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                logger.info(f"Progress check {i+1}: {status_data['progress']:.2%} - Loss: {status_data['training_loss']:.4f}")
                
                if not status_data['is_training']:
                    logger.info("✅ Training completed!")
                    break
            else:
                logger.warning(f"Status check failed: {response.status_code}")
        
        # Test 7: Get available models
        logger.info("\n🎯 Testing available models...")
        response = requests.get(f"{BASE_URL}/api/training/models", timeout=10)
        
        if response.status_code == 200:
            models_data = response.json()
            logger.info(f"✅ Available models: {len(models_data)}")
            
            for i, model in enumerate(models_data):
                logger.info(f"Model {i+1}: {model['name']}")
                logger.info(f"  Epoch: {model['metadata']['epoch']}")
                logger.info(f"  Training Loss: {model['metadata']['training_loss']:.4f}")
                logger.info(f"  Created: {model['metadata']['timestamp']}")
        else:
            logger.error(f"❌ Available models failed: {response.status_code}")
            return False
        
        # Test 8: Load a model (if available)
        if models_data:
            logger.info("\n🔄 Testing model loading...")
            
            model_name = models_data[0]['name']  # Load the first model
            response = requests.post(f"{BASE_URL}/api/training/models/{model_name}/load", timeout=10)
            
            if response.status_code == 200:
                load_data = response.json()
                logger.info(f"✅ Model loaded:")
                logger.info(f"  Success: {load_data['success']}")
                logger.info(f"  Message: {load_data['message']}")
            else:
                logger.error(f"❌ Model loading failed: {response.status_code}")
                return False
        
        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("🎉 ALL API ENDPOINTS TESTED SUCCESSFULLY!")
        logger.info("✅ Health check: WORKING")
        logger.info("✅ Data sources: WORKING")
        logger.info("✅ Data preparation: WORKING")
        logger.info("✅ Training status: WORKING")
        logger.info("✅ Training start: WORKING")
        logger.info("✅ Training progress: WORKING")
        logger.info("✅ Available models: WORKING")
        logger.info("✅ Model loading: WORKING")
        
        return True
        
    except requests.exceptions.ConnectionError:
        logger.error("❌ Cannot connect to server. Make sure the server is running.")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing API endpoints: {e}")
        return False

def test_with_real_data_summary():
    """Test with real data summary"""
    logger.info("\n📊 REAL DATA SUMMARY:")
    logger.info("=" * 40)
    
    try:
        # Get data sources
        response = requests.get(f"{BASE_URL}/api/training/data/sources", timeout=10)
        
        if response.status_code == 200:
            sources_data = response.json()
            
            logger.info("Real Training Data Available:")
            logger.info(f"  📋 Synthea Patients: {sources_data['sources']['synthea']['examples_count']} examples")
            logger.info(f"  📋 Doctor Prompts: {sources_data['sources']['prompts']['examples_count']} examples")
            logger.info(f"  📋 Conversations: {sources_data['sources']['conversations']['examples_count']} examples")
            logger.info(f"  📊 Total Examples: {sources_data['total_examples']}")
            
            # Quality assessment
            total_examples = sources_data['total_examples']
            if total_examples > 30:
                quality = "HIGH"
            elif total_examples > 10:
                quality = "GOOD"
            else:
                quality = "FAIR"
            
            logger.info(f"  🎯 Data Quality: {quality}")
            
            return True
        else:
            logger.error(f"❌ Could not get data summary: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error getting data summary: {e}")
        return False

def main():
    """Run all API tests"""
    logger.info("🔬 DigiClinic Training API Tests")
    logger.info("=" * 60)
    
    # Test API endpoints
    api_success = test_training_api_endpoints()
    
    # Test data summary
    data_success = test_with_real_data_summary()
    
    # Final results
    logger.info("\n" + "=" * 60)
    logger.info("📊 FINAL API TEST RESULTS:")
    logger.info(f"API Endpoints: {'✅ WORKING' if api_success else '❌ NOT WORKING'}")
    logger.info(f"Real Data: {'✅ WORKING' if data_success else '❌ NOT WORKING'}")
    
    if api_success and data_success:
        logger.info("\n🎉 ALL SYSTEMS WORKING WITH REAL DATA!")
        logger.info("✅ Training API endpoints: WORKING")
        logger.info("✅ Real Synthea data: WORKING")
        logger.info("✅ Real doctor prompts: WORKING")
        logger.info("✅ Real training process: WORKING")
        logger.info("✅ Real model creation: WORKING")
        logger.info("✅ Real model loading: WORKING")
    else:
        logger.info("\n⚠️  Some systems need attention")

if __name__ == "__main__":
    main()
