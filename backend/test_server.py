#!/usr/bin/env python3
"""
Quick Test Server for DigiClinic Training APIs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="DigiClinic Training Test Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

@app.get("/api/training/health")
async def training_health_check():
    """Health check for training service"""
    return {
        "status": "healthy",
        "training_service": "active",
        "is_training": False,
        "available_models": 0,
        "models_dir": "dat/training/models"
    }

@app.get("/api/training/status")
async def get_training_status():
    """Get current training status"""
    return {
        "is_training": False,
        "current_epoch": 0,
        "total_epochs": 0,
        "training_loss": None,
        "validation_loss": None,
        "progress": 0.0,
        "start_time": None,
        "end_time": None,
        "message": "Idle",
        "last_update": "2024-01-01T00:00:00Z",
        "trained_models": []
    }

@app.get("/api/training/models")
async def get_available_models():
    """Get list of available trained models"""
    return []

@app.get("/api/training/data/sources")
async def get_training_data_sources():
    """Get training data sources summary"""
    return {
        "synthea": {
            "available": True,
            "examples_count": 7,
            "patients_count": 7
        },
        "prompts": {
            "available": True,
            "examples_count": 3,
            "active_prompts": 3
        },
        "conversations": {
            "available": False,
            "examples_count": 0
        },
        "total_examples": 10
    }

@app.post("/api/training/prepare-data")
async def prepare_training_data():
    """Prepare training data"""
    return {
        "success": True,
        "message": "Training data prepared successfully",
        "examples_count": 10,
        "synthea_examples": 7,
        "prompt_examples": 3,
        "conversation_examples": 0
    }

@app.post("/api/training/start")
async def start_training():
    """Start model training"""
    return {
        "success": True,
        "message": "Training started successfully",
        "config": {
            "model_name": "claude-3-5-sonnet",
            "epochs": 3,
            "learning_rate": 0.0001,
            "batch_size": 8
        }
    }

@app.post("/api/synthea/generate")
async def generate_synthea_data():
    """Generate synthetic patient data"""
    return {
        "success": True,
        "message": "Generated 10 synthetic patients",
        "patients_generated": 10,
        "cohort": "UK General Population",
        "file_path": "dat/patient-db.json"
    }

@app.get("/")
async def root():
    return {"message": "DigiClinic Training Test Server", "status": "running"}

if __name__ == "__main__":
    print("🚀 Starting DigiClinic Training Test Server...")
    print("📍 Server will be available at: http://127.0.0.1:8000")
    print("🔗 Training API: http://127.0.0.1:8000/api/training/health")
    uvicorn.run(app, host="127.0.0.1", port=8000)
