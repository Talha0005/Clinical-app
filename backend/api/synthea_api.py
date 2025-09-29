"""
Synthea API endpoints for DigiClinic.

Provides endpoints for generating synthetic patient data using Synthea
and integrating it with the DigiClinic system.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from auth import verify_token
from services.synthea_generator import (
    SyntheaGenerator, 
    SyntheaConfig,
    generate_uk_patient_cohort,
    generate_diabetes_cohort,
    generate_cardiac_cohort,
    generate_respiratory_cohort
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/synthea", tags=["synthea"])


# Request/Response Models
class SyntheaGenerationRequest(BaseModel):
    """Request model for Synthea patient generation."""
    
    population_size: int = Field(default=100, ge=1, le=1000, description="Number of patients to generate")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducible generation")
    state: str = Field(default="England", description="State/region for patient generation")
    city: str = Field(default="London", description="City for patient generation")
    cohort_name: Optional[str] = Field(default=None, description="Name for the generated cohort")
    
    # Clinical configuration
    enable_conditions: bool = Field(default=True, description="Include conditions in generation")
    enable_medications: bool = Field(default=True, description="Include medications in generation")
    enable_procedures: bool = Field(default=True, description="Include procedures in generation")
    enable_observations: bool = Field(default=True, description="Include observations in generation")
    enable_encounters: bool = Field(default=True, description="Include encounters in generation")
    
    # Disease prevalences
    diabetes_prevalence: float = Field(default=0.06, ge=0.0, le=1.0, description="Diabetes prevalence")
    hypertension_prevalence: float = Field(default=0.31, ge=0.0, le=1.0, description="Hypertension prevalence")
    asthma_prevalence: float = Field(default=0.12, ge=0.0, le=1.0, description="Asthma prevalence")
    
    # Output options
    ingest_to_digiclinic: bool = Field(default=True, description="Ingest generated data into DigiClinic")
    output_format: str = Field(default="fhir", description="Output format (fhir, csv, json)")


class SyntheaGenerationResponse(BaseModel):
    """Response model for Synthea patient generation."""
    
    success: bool
    message: str
    cohort_name: str
    population_size: int
    output_directory: str
    patients_generated: int
    patients_ingested: Optional[int] = None
    generation_time: float
    timestamp: str


class CohortGenerationRequest(BaseModel):
    """Request model for specific cohort generation."""
    
    cohort_type: str = Field(description="Type of cohort (diabetes, cardiac, respiratory, custom)")
    population_size: int = Field(default=50, ge=1, le=500, description="Number of patients to generate")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducible generation")
    custom_conditions: Optional[List[str]] = Field(default=None, description="Custom conditions for cohort")
    ingest_to_digiclinic: bool = Field(default=True, description="Ingest generated data into DigiClinic")


class SyntheaHealthResponse(BaseModel):
    """Response model for Synthea health check."""
    
    status: str
    synthea_available: bool
    synthea_path: str
    output_dir: str
    timestamp: str
    error: Optional[str] = None


class SyntheaConfigResponse(BaseModel):
    """Response model for available Synthea configurations."""
    
    states: List[str]
    cities: List[str]
    output_formats: List[str]
    fhir_versions: List[str]
    export_options: List[str]


# Dependency injection
def get_synthea_generator() -> SyntheaGenerator:
    """Get Synthea generator instance."""
    return SyntheaGenerator()


# API Endpoints
@router.get("/health", response_model=SyntheaHealthResponse)
async def synthea_health_check(
    generator: SyntheaGenerator = Depends(get_synthea_generator)
):
    """Check the health of the Synthea generator."""
    try:
        health_status = generator.health_check()
        return SyntheaHealthResponse(**health_status)
    except Exception as e:
        logger.error(f"Synthea health check failed: {e}")
        return SyntheaHealthResponse(
            status="unhealthy",
            synthea_available=False,
            synthea_path="",
            output_dir="",
            timestamp=datetime.utcnow().isoformat(),
            error=str(e)
        )


@router.get("/config", response_model=SyntheaConfigResponse)
async def get_synthea_configurations():
    """Get available Synthea configurations and options."""
    try:
        generator = SyntheaGenerator()
        configs = generator.get_available_configurations()
        return SyntheaConfigResponse(**configs)
    except Exception as e:
        logger.error(f"Failed to get Synthea configurations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get configurations: {e}")


@router.post("/generate", response_model=SyntheaGenerationResponse)
async def generate_patients(
    request: SyntheaGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(verify_token),
    generator: SyntheaGenerator = Depends(get_synthea_generator)
):
    """Generate synthetic patient data using Synthea."""
    try:
        start_time = datetime.utcnow()
        
        # Create configuration
        config = SyntheaConfig(
            population_size=request.population_size,
            seed=request.seed,
            state=request.state,
            city=request.city,
            output_format=request.output_format,
            fhir_version="R4",
            enable_conditions=request.enable_conditions,
            enable_medications=request.enable_medications,
            enable_procedures=request.enable_procedures,
            enable_observations=request.enable_observations,
            enable_encounters=request.enable_encounters,
            diabetes_prevalence=request.diabetes_prevalence,
            hypertension_prevalence=request.hypertension_prevalence,
            asthma_prevalence=request.asthma_prevalence
        )
        
        # Generate cohort name if not provided
        cohort_name = request.cohort_name or f"synthea-{request.population_size}-{start_time.strftime('%Y%m%d-%H%M%S')}"
        
        # Generate patients
        if request.ingest_to_digiclinic:
            # Generate and ingest in one operation
            patients_ingested = generator.generate_and_ingest(config)
            patients_generated = patients_ingested
        else:
            # Generate only
            data_dir = generator.generate_patients(config)
            patients_generated = request.population_size
            patients_ingested = None
        
        generation_time = (datetime.utcnow() - start_time).total_seconds()
        
        return SyntheaGenerationResponse(
            success=True,
            message=f"Successfully generated {patients_generated} patients",
            cohort_name=cohort_name,
            population_size=request.population_size,
            output_directory=str(generator.output_dir),
            patients_generated=patients_generated,
            patients_ingested=patients_ingested,
            generation_time=generation_time,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Patient generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Patient generation failed: {e}")


@router.post("/generate/cohort", response_model=SyntheaGenerationResponse)
async def generate_cohort(
    request: CohortGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(verify_token)
):
    """Generate a specific patient cohort."""
    try:
        start_time = datetime.utcnow()
        
        # Generate based on cohort type
        if request.cohort_type == "diabetes":
            patients_ingested = generate_diabetes_cohort(request.population_size)
        elif request.cohort_type == "cardiac":
            patients_ingested = generate_cardiac_cohort(request.population_size)
        elif request.cohort_type == "respiratory":
            patients_ingested = generate_respiratory_cohort(request.population_size)
        elif request.cohort_type == "custom" and request.custom_conditions:
            patients_ingested = generate_uk_patient_cohort(
                "custom",
                request.population_size,
                request.custom_conditions
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid cohort type: {request.cohort_type}"
            )
        
        generation_time = (datetime.utcnow() - start_time).total_seconds()
        
        return SyntheaGenerationResponse(
            success=True,
            message=f"Successfully generated {request.cohort_type} cohort",
            cohort_name=request.cohort_type,
            population_size=request.population_size,
            output_directory="data/synthea",
            patients_generated=patients_ingested,
            patients_ingested=patients_ingested if request.ingest_to_digiclinic else None,
            generation_time=generation_time,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Cohort generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cohort generation failed: {e}")


@router.post("/generate/uk", response_model=SyntheaGenerationResponse)
async def generate_uk_patients(
    population_size: int = 100,
    seed: Optional[int] = None,
    ingest_to_digiclinic: bool = True,
    current_user: str = Depends(verify_token),
    generator: SyntheaGenerator = Depends(get_synthea_generator)
):
    """Generate UK-specific patient data with NHS-compatible identifiers."""
    try:
        start_time = datetime.utcnow()
        
        # Generate UK patients
        data_dir = generator.generate_uk_patients(
            population_size=population_size,
            seed=seed
        )
        
        patients_ingested = 0
        if ingest_to_digiclinic:
            patients_ingested = generator.ingest_to_digiclinic(data_dir)
        
        generation_time = (datetime.utcnow() - start_time).total_seconds()
        
        return SyntheaGenerationResponse(
            success=True,
            message=f"Successfully generated {population_size} UK patients",
            cohort_name="uk-patients",
            population_size=population_size,
            output_directory=str(data_dir),
            patients_generated=population_size,
            patients_ingested=patients_ingested,
            generation_time=generation_time,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"UK patient generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"UK patient generation failed: {e}")


@router.get("/cohorts/available")
async def get_available_cohorts():
    """Get list of available pre-configured cohorts."""
    return {
        "cohorts": [
            {
                "name": "diabetes",
                "description": "Patients with Type 2 Diabetes, Hypertension, and Obesity",
                "conditions": ["Type 2 Diabetes", "Hypertension", "Obesity"],
                "default_size": 50
            },
            {
                "name": "cardiac",
                "description": "Patients with cardiac conditions",
                "conditions": ["Hypertension", "Coronary Artery Disease", "Atrial Fibrillation"],
                "default_size": 50
            },
            {
                "name": "respiratory",
                "description": "Patients with respiratory conditions",
                "conditions": ["Asthma", "COPD", "Bronchitis"],
                "default_size": 50
            }
        ]
    }


@router.get("/status")
async def get_generation_status():
    """Get status of recent patient generation activities."""
    try:
        # Check for recent generation activities
        synthea_dir = Path("data/synthea")
        if not synthea_dir.exists():
            return {"status": "no_activities", "recent_generations": []}
        
        recent_generations = []
        for item in synthea_dir.iterdir():
            if item.is_dir() and item.name.startswith(("synthea-", "cohort-")):
                # Get directory info
                stat = item.stat()
                recent_generations.append({
                    "name": item.name,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "size": sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                })
        
        # Sort by creation time (newest first)
        recent_generations.sort(key=lambda x: x["created"], reverse=True)
        
        return {
            "status": "active",
            "recent_generations": recent_generations[:10]  # Last 10 generations
        }
        
    except Exception as e:
        logger.error(f"Failed to get generation status: {e}")
        return {"status": "error", "error": str(e)}


@router.delete("/cleanup")
async def cleanup_old_generations(
    days_old: int = 7,
    current_user: str = Depends(verify_token)
):
    """Clean up old patient generation data."""
    try:
        synthea_dir = Path("data/synthea")
        if not synthea_dir.exists():
            return {"message": "No data to clean up", "cleaned": 0}
        
        cleaned_count = 0
        cutoff_time = datetime.utcnow().timestamp() - (days_old * 24 * 60 * 60)
        
        for item in synthea_dir.iterdir():
            if item.is_dir() and item.name.startswith(("synthea-", "cohort-")):
                if item.stat().st_ctime < cutoff_time:
                    # Remove old directory
                    import shutil
                    shutil.rmtree(item)
                    cleaned_count += 1
        
        return {
            "message": f"Cleaned up {cleaned_count} old generations",
            "cleaned": cleaned_count,
            "days_old": days_old
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {e}")
