"""Simple endpoints to ingest Synthea FHIR bundles during development."""

from pathlib import Path
from fastapi import APIRouter, HTTPException, Form, Depends

from auth import verify_token
from services.fhir_ingest import ingest_directory_to_mock_db


router = APIRouter(prefix="/api/synthea", tags=["Synthea Ingest (dev)"])


@router.post("/ingest")
async def ingest_directory(
    path: str = Form(...),
    token_data: dict = Depends(verify_token),
):
    """Ingest a directory of Synthea FHIR bundles into the mock DB.

    Body (form-data):
      - path: absolute or relative directory path containing *.json Bundle files
    """
    try:
        count = ingest_directory_to_mock_db(Path(path))
        resp = {"success": True, "patients": count, "db": "dat/patient-db.json"}
        return resp
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
