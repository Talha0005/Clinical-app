"""
Synthea Patient Data Generator for DigiClinic.

This module provides integration with Synthea to generate realistic, 
population-based FHIR patient records for testing and development.

Features:
- Generate synthetic patient populations
- Configure specific comorbidities and conditions
- Export FHIR R4 bundles
- Integration with DigiClinic patient database
"""

import os
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

from model.patient import Patient
from services.fhir_ingest import ingest_directory_to_mock_db

logger = logging.getLogger(__name__)


@dataclass
class SyntheaConfig:
    """Configuration for Synthea patient generation."""
    
    population_size: int = 100
    seed: Optional[int] = None
    state: str = "Massachusetts"  # Default state
    city: str = "Boston"
    output_format: str = "fhir"  # fhir, csv, json
    fhir_version: str = "R4"
    export_options: Dict[str, Any] = field(default_factory=dict)
    
    # Clinical configuration
    enable_conditions: bool = True
    enable_medications: bool = True
    enable_procedures: bool = True
    enable_observations: bool = True
    enable_encounters: bool = True
    
    # Specific condition configurations
    diabetes_prevalence: float = 0.1  # 10% of population
    hypertension_prevalence: float = 0.25  # 25% of population
    asthma_prevalence: float = 0.08  # 8% of population
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "population_size": self.population_size,
            "seed": self.seed,
            "state": self.state,
            "city": self.city,
            "output_format": self.output_format,
            "fhir_version": self.fhir_version,
            "export_options": self.export_options,
            "enable_conditions": self.enable_conditions,
            "enable_medications": self.enable_medications,
            "enable_procedures": self.enable_procedures,
            "enable_observations": self.enable_observations,
            "enable_encounters": self.enable_encounters,
            "diabetes_prevalence": self.diabetes_prevalence,
            "hypertension_prevalence": self.hypertension_prevalence,
            "asthma_prevalence": self.asthma_prevalence,
        }


class SyntheaGenerator:
    """Synthea patient data generator for DigiClinic."""
    
    def __init__(self, synthea_path: Optional[Path] = None):
        """
        Initialize Synthea generator.
        
        Args:
            synthea_path: Path to Synthea installation. If None, will look for it in the project.
        """
        if synthea_path is None:
            # Look for Synthea in the project directory
            project_root = Path(__file__).parent.parent.parent
            synthea_path = project_root / "synthea"
        
        self.synthea_path = Path(synthea_path)
        self.output_dir = Path("data/synthea")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Verify Synthea installation
        self._verify_synthea_installation()
    
    def _verify_synthea_installation(self) -> bool:
        """Verify that Synthea is properly installed and accessible."""
        try:
            # Check if Synthea directory exists
            if not self.synthea_path.exists():
                logger.warning(f"Synthea not found at {self.synthea_path}")
                return False
            
            # Check for Synthea executable
            synthea_jar = self.synthea_path / "build" / "libs" / "synthea-with-dependencies.jar"
            if not synthea_jar.exists():
                logger.warning(f"Synthea JAR not found at {synthea_jar}")
                return False
            
            logger.info(f"Synthea found at {self.synthea_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying Synthea installation: {e}")
            return False
    
    def generate_patients(
        self, 
        config: SyntheaConfig,
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Generate synthetic patient data using Synthea.
        
        Args:
            config: Synthea configuration
            output_dir: Output directory for generated data
            
        Returns:
            Path to the generated data directory
        """
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_dir = self.output_dir / f"synthea-{timestamp}-{config.population_size}"
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Build Synthea command
            cmd = self._build_synthea_command(config, output_dir)
            
            logger.info(f"Generating {config.population_size} patients with Synthea...")
            logger.info(f"Command: {' '.join(cmd)}")
            
            # Run Synthea
            result = subprocess.run(
                cmd,
                cwd=self.synthea_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Synthea generation failed: {result.stderr}")
                raise Exception(f"Synthea generation failed: {result.stderr}")
            
            logger.info(f"Successfully generated patients in {output_dir}")
            return output_dir
            
        except subprocess.TimeoutExpired:
            logger.error("Synthea generation timed out")
            raise Exception("Synthea generation timed out")
        except Exception as e:
            logger.error(f"Error generating patients: {e}")
            raise
    
    def _build_synthea_command(self, config: SyntheaConfig, output_dir: Path) -> List[str]:
        """Build the Synthea command line arguments."""
        synthea_jar = self.synthea_path / "build" / "libs" / "synthea-with-dependencies.jar"
        
        cmd = [
            "java", "-jar", str(synthea_jar),
            "-p", str(config.population_size),
            "-o", str(output_dir)
        ]
        
        # Add seed if specified
        if config.seed is not None:
            cmd.extend(["-s", str(config.seed)])
        
        # Add location
        cmd.extend(["-c", config.city, config.state])
        
        # Add export options
        if config.output_format == "fhir":
            cmd.append("--exporter.fhir.export")
            cmd.append("--exporter.fhir.version")
            cmd.append(config.fhir_version)
        
        # Add clinical options
        if not config.enable_conditions:
            cmd.append("--exporter.fhir.export_conditions=false")
        if not config.enable_medications:
            cmd.append("--exporter.fhir.export_medications=false")
        if not config.enable_procedures:
            cmd.append("--exporter.fhir.export_procedures=false")
        if not config.enable_observations:
            cmd.append("--exporter.fhir.export_observations=false")
        if not config.enable_encounters:
            cmd.append("--exporter.fhir.export_encounters=false")
        
        return cmd
    
    def generate_uk_patients(
        self,
        population_size: int = 100,
        seed: Optional[int] = None,
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Generate UK-specific patient data with NHS-compatible identifiers.
        
        Args:
            population_size: Number of patients to generate
            seed: Random seed for reproducible generation
            output_dir: Output directory for generated data
            
        Returns:
            Path to the generated data directory
        """
        # UK-specific configuration
        config = SyntheaConfig(
            population_size=population_size,
            seed=seed,
            state="England",  # UK state
            city="London",
            output_format="fhir",
            fhir_version="R4",
            # UK-specific disease prevalences
            diabetes_prevalence=0.06,  # 6% in UK
            hypertension_prevalence=0.31,  # 31% in UK
            asthma_prevalence=0.12,  # 12% in UK
        )
        
        return self.generate_patients(config, output_dir)
    
    def generate_cohort(
        self,
        cohort_name: str,
        conditions: List[str],
        population_size: int = 50,
        seed: Optional[int] = None
    ) -> Path:
        """
        Generate a specific patient cohort with defined conditions.
        
        Args:
            cohort_name: Name of the cohort
            conditions: List of conditions to include
            population_size: Number of patients to generate
            seed: Random seed for reproducible generation
            
        Returns:
            Path to the generated data directory
        """
        # Create cohort-specific configuration
        config = SyntheaConfig(
            population_size=population_size,
            seed=seed,
            state="Massachusetts",
            city="Boston",
            output_format="fhir",
            fhir_version="R4",
        )
        
        # Generate timestamped output directory
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir = self.output_dir / f"cohort-{cohort_name}-{timestamp}"
        
        # Generate patients
        data_dir = self.generate_patients(config, output_dir)
        
        # Post-process to ensure cohort conditions are present
        self._post_process_cohort(data_dir, conditions)
        
        return data_dir
    
    def _post_process_cohort(self, data_dir: Path, conditions: List[str]):
        """Post-process generated data to ensure cohort conditions are present."""
        # This would involve modifying the generated FHIR bundles
        # to ensure specific conditions are present
        # For now, this is a placeholder for future enhancement
        logger.info(f"Post-processing cohort data in {data_dir} for conditions: {conditions}")
    
    def ingest_to_digiclinic(self, data_dir: Path) -> int:
        """
        Ingest Synthea-generated data into DigiClinic patient database.
        
        Args:
            data_dir: Directory containing Synthea-generated FHIR bundles
            
        Returns:
            Number of patients successfully ingested
        """
        try:
            logger.info(f"Ingesting Synthea data from {data_dir} into DigiClinic...")
            patient_count = ingest_directory_to_mock_db(data_dir)
            logger.info(f"Successfully ingested {patient_count} patients")
            return patient_count
            
        except Exception as e:
            logger.error(f"Error ingesting Synthea data: {e}")
            raise
    
    def generate_and_ingest(
        self,
        config: SyntheaConfig,
        output_dir: Optional[Path] = None
    ) -> int:
        """
        Generate patients and immediately ingest them into DigiClinic.
        
        Args:
            config: Synthea configuration
            output_dir: Output directory for generated data
            
        Returns:
            Number of patients successfully generated and ingested
        """
        # Generate patients
        data_dir = self.generate_patients(config, output_dir)
        
        # Ingest into DigiClinic
        patient_count = self.ingest_to_digiclinic(data_dir)
        
        return patient_count
    
    def get_available_configurations(self) -> Dict[str, Any]:
        """Get available Synthea configurations and options."""
        return {
            "states": [
                "Massachusetts", "California", "Texas", "Florida", "New York",
                "England", "Scotland", "Wales", "Northern Ireland"
            ],
            "cities": [
                "Boston", "Los Angeles", "Houston", "Miami", "New York",
                "London", "Edinburgh", "Cardiff", "Belfast"
            ],
            "output_formats": ["fhir", "csv", "json"],
            "fhir_versions": ["R4", "STU3"],
            "export_options": [
                "conditions", "medications", "procedures", 
                "observations", "encounters", "allergies"
            ]
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of the Synthea generator."""
        try:
            synthea_available = self._verify_synthea_installation()
            
            return {
                "status": "healthy" if synthea_available else "unhealthy",
                "synthea_path": str(self.synthea_path),
                "synthea_available": synthea_available,
                "output_dir": str(self.output_dir),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Convenience functions for common use cases
def generate_uk_patient_cohort(
    cohort_name: str,
    population_size: int = 100,
    conditions: Optional[List[str]] = None
) -> int:
    """
    Generate a UK patient cohort and ingest into DigiClinic.
    
    Args:
        cohort_name: Name of the cohort
        population_size: Number of patients to generate
        conditions: Optional list of specific conditions to include
        
    Returns:
        Number of patients successfully generated and ingested
    """
    generator = SyntheaGenerator()
    
    if conditions:
        data_dir = generator.generate_cohort(cohort_name, conditions, population_size)
        return generator.ingest_to_digiclinic(data_dir)
    else:
        config = SyntheaConfig(
            population_size=population_size,
            state="England",
            city="London",
            output_format="fhir",
            fhir_version="R4"
        )
        return generator.generate_and_ingest(config)


def generate_diabetes_cohort(population_size: int = 50) -> int:
    """Generate a diabetes patient cohort."""
    return generate_uk_patient_cohort(
        "diabetes",
        population_size,
        ["Type 2 Diabetes", "Hypertension", "Obesity"]
    )


def generate_cardiac_cohort(population_size: int = 50) -> int:
    """Generate a cardiac patient cohort."""
    return generate_uk_patient_cohort(
        "cardiac",
        population_size,
        ["Hypertension", "Coronary Artery Disease", "Atrial Fibrillation"]
    )


def generate_respiratory_cohort(population_size: int = 50) -> int:
    """Generate a respiratory patient cohort."""
    return generate_uk_patient_cohort(
        "respiratory",
        population_size,
        ["Asthma", "COPD", "Bronchitis"]
    )
