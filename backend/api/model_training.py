"""
Model Training API endpoints for DigiClinic
Provides endpoints for training models on Synthea data and doctor prompts
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from auth import verify_token
from services.model_training_service import training_service, TrainingConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/training", tags=["Model Training"])

class TrainingConfigRequest(BaseModel):
    """Training configuration request"""
    model_name: str = "claude-3-5-sonnet"
    epochs: int = 3
    learning_rate: float = 0.0001
    batch_size: int = 8
    max_length: int = 2048
    validation_split: float = 0.2
    save_every_n_epochs: int = 1

class TrainingStatusResponse(BaseModel):
    """Training status response"""
    is_training: bool
    progress: float
    current_epoch: int
    training_loss: float
    validation_loss: float
    models_dir: str

class ModelInfo(BaseModel):
    """Model information"""
    name: str
    path: str
    metadata: Dict[str, Any]

@router.post("/start")
async def start_training(
    config: TrainingConfigRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(verify_token)
):
    """Start model training on Synthea data and doctor prompts"""
    try:
        if training_service.is_training:
            raise HTTPException(
                status_code=400,
                detail="Training already in progress"
            )
        
        # Convert request to training config
        training_config = TrainingConfig(
            model_name=config.model_name,
            epochs=config.epochs,
            learning_rate=config.learning_rate,
            batch_size=config.batch_size,
            max_length=config.max_length,
            validation_split=config.validation_split,
            save_every_n_epochs=config.save_every_n_epochs
        )
        
        # Start training in background
        background_tasks.add_task(training_service.start_training, training_config)
        
        logger.info(f"Training started by user: {current_user}")
        
        return {
            "success": True,
            "message": "Training started successfully",
            "config": config.dict()
        }
        
    except Exception as e:
        logger.error(f"Error starting training: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start training: {str(e)}"
        )

@router.get("/status", response_model=TrainingStatusResponse)
async def get_training_status(current_user: str = Depends(verify_token)):
    """Get current training status"""
    try:
        status = training_service.get_training_status()
        return TrainingStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Error getting training status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get training status: {str(e)}"
        )

@router.get("/models", response_model=List[ModelInfo])
async def get_available_models(current_user: str = Depends(verify_token)):
    """Get list of available trained models"""
    try:
        models = training_service.get_available_models()
        return [ModelInfo(**model) for model in models]
        
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get available models: {str(e)}"
        )

@router.post("/models/{model_name}/load")
async def load_trained_model(
    model_name: str,
    current_user: str = Depends(verify_token)
):
    """Load a trained model for inference"""
    try:
        success = await training_service.load_trained_model(model_name)
        
        if success:
            logger.info(f"Model {model_name} loaded by user: {current_user}")
            return {
                "success": True,
                "message": f"Model {model_name} loaded successfully"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Model {model_name} not found or failed to load"
            )
        
    except Exception as e:
        logger.error(f"Error loading model {model_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load model: {str(e)}"
        )

@router.post("/prepare-data")
async def prepare_training_data(current_user: str = Depends(verify_token)):
    """Prepare training data from all sources"""
    try:
        examples = await training_service.prepare_all_training_data()
        
        logger.info(f"Training data prepared by user: {current_user}, {len(examples)} examples")
        
        return {
            "success": True,
            "message": f"Prepared {len(examples)} training examples",
            "examples_count": len(examples),
            "sources": {
                "synthea": len([e for e in examples if e.source == 'synthea']),
                "prompts": len([e for e in examples if e.source == 'prompt']),
                "conversations": len([e for e in examples if e.source == 'conversation'])
            }
        }
        
    except Exception as e:
        logger.error(f"Error preparing training data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to prepare training data: {str(e)}"
        )

@router.get("/data/sources")
async def get_training_data_sources(current_user: str = Depends(verify_token)):
    """Get information about available training data sources"""
    try:
        # Check Synthea data
        synthea_examples = await training_service.prepare_synthea_training_data()
        
        # Check prompt data
        prompt_examples = await training_service.prepare_prompt_training_data()
        
        # Check conversation data
        conversation_examples = await training_service.prepare_conversation_training_data()
        
        return {
            "sources": {
                "synthea": {
                    "available": len(synthea_examples) > 0,
                    "examples_count": len(synthea_examples),
                    "description": "Patient records and medical cases from Synthea"
                },
                "prompts": {
                    "available": len(prompt_examples) > 0,
                    "examples_count": len(prompt_examples),
                    "description": "Medical knowledge and best practices from doctor prompts"
                },
                "conversations": {
                    "available": len(conversation_examples) > 0,
                    "examples_count": len(conversation_examples),
                    "description": "Previous doctor-patient conversations"
                }
            },
            "total_examples": len(synthea_examples) + len(prompt_examples) + len(conversation_examples)
        }
        
    except Exception as e:
        logger.error(f"Error getting training data sources: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get training data sources: {str(e)}"
        )

@router.post("/stop")
async def stop_training(current_user: str = Depends(verify_token)):
    """Stop current training (if running)"""
    try:
        if not training_service.is_training:
            return {
                "success": True,
                "message": "No training in progress"
            }
        
        # Stop training (this would need to be implemented in the service)
        training_service.is_training = False
        
        logger.info(f"Training stopped by user: {current_user}")
        
        return {
            "success": True,
            "message": "Training stopped successfully"
        }
        
    except Exception as e:
        logger.error(f"Error stopping training: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop training: {str(e)}"
        )

@router.get("/health")
async def training_health_check():
    """Health check for training service"""
    try:
        status = training_service.get_training_status()
        models = training_service.get_available_models()
        
        return {
            "status": "healthy",
            "training_service": "active",
            "is_training": status["is_training"],
            "available_models": len(models),
            "models_dir": status["models_dir"]
        }
        
    except Exception as e:
        logger.error(f"Training service health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
