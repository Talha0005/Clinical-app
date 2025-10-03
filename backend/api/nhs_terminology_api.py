"""API endpoints for NHS Terminology Server integration."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
import logging

# Fix import path for Railway deployment
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from medical.nhs_terminology import NHSTerminologyServer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/terminology", tags=["NHS Terminology"])


class TerminologySearchRequest(BaseModel):
    """Request model for terminology search."""

    query: str
    system: str = "snomed"  # snomed, dmd, icd10
    limit: int = 10


class TerminologyValidateRequest(BaseModel):
    """Request model for code validation."""

    code: str
    system: str  # snomed, dmd, icd10


class TerminologyResponse(BaseModel):
    """Response model for terminology operations."""

    success: bool
    data: Optional[List[dict]] = None
    error: Optional[str] = None


@router.get("/health")
async def health_check():
    """Check NHS Terminology Server connection."""
    try:
        async with NHSTerminologyServer() as server:
            is_healthy = await server.health_check()
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "service": "NHS Terminology Server",
                "environment": server.environment,
                "fhir_url": server.fhir_base_url,
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/search")
async def search_terminology(request: TerminologySearchRequest):
    """Search for clinical terminology codes."""
    try:
        async with NHSTerminologyServer() as server:
            if request.system == "snomed":
                concepts = await server.search_snomed(request.query, request.limit)
            elif request.system == "dmd":
                concepts = await server.search_medications(request.query, request.limit)
            elif request.system == "icd10":
                concepts = await server.search_icd10(request.query, request.limit)
            else:
                raise HTTPException(
                    status_code=400, detail=f"Unknown system: {request.system}"
                )

            # Convert to dict format
            results = []
            for concept in concepts:
                results.append(
                    {
                        "code": concept.code,
                        "display": concept.display,
                        "system": concept.system,
                        "version": concept.version,
                    }
                )

            return TerminologyResponse(success=True, data=results)

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return TerminologyResponse(success=False, error=str(e))


@router.post("/validate")
async def validate_code(request: TerminologyValidateRequest):
    """Validate a clinical code."""
    try:
        async with NHSTerminologyServer() as server:
            system_urls = {
                "snomed": server.SYSTEMS["snomed_uk"],
                "dmd": server.SYSTEMS["dmd"],
                "icd10": server.SYSTEMS["icd10"],
            }

            system_url = system_urls.get(request.system.lower())
            if not system_url:
                raise HTTPException(
                    status_code=400, detail=f"Unknown system: {request.system}"
                )

            is_valid = await server.validate_code(request.code, system_url)

            # Try to get more details if valid
            details = None
            if is_valid:
                if request.system.lower() == "snomed":
                    concept = await server.get_snomed_concept(request.code)
                    if concept:
                        details = {
                            "display": concept.display,
                            "system": concept.system,
                            "active": True,
                        }

            return {
                "valid": is_valid,
                "code": request.code,
                "system": request.system,
                "details": details,
            }

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snomed/{code}")
async def get_snomed_concept(code: str):
    """Get full details of a SNOMED CT concept."""
    try:
        async with NHSTerminologyServer() as server:
            concept = await server.get_snomed_concept(code)

            if not concept:
                raise HTTPException(
                    status_code=404, detail=f"SNOMED concept {code} not found"
                )

            return {
                "code": concept.code,
                "display": concept.display,
                "system": concept.system,
                "version": concept.version,
                "designation": concept.designation,
                "property": concept.property,
                "browser_url": f"https://termbrowser.nhs.uk/?perspective=full&conceptId1={code}",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SNOMED lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/map/snomed-to-icd10")
async def map_snomed_to_icd10(
    snomed_code: str = Query(..., description="SNOMED CT code to map")
):
    """Map a SNOMED CT code to ICD-10."""
    try:
        async with NHSTerminologyServer() as server:
            mappings = await server.map_snomed_to_icd10(snomed_code)

            if not mappings:
                return {
                    "snomed_code": snomed_code,
                    "mappings": [],
                    "message": "No ICD-10 mappings found",
                }

            results = []
            for mapping in mappings:
                results.append(
                    {
                        "code": mapping.code,
                        "display": mapping.display,
                        "system": mapping.system,
                    }
                )

            return {
                "snomed_code": snomed_code,
                "mappings": results,
                "count": len(results),
            }

    except Exception as e:
        logger.error(f"Mapping failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
