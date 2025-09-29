"""Patients API endpoints for synthetic database management.

Endpoints:
- POST /api/patients/init
    Initialize DB and optionally seed from dat/patient-db.json
- POST /api/patients/import/json
    Import patients from uploaded JSON array
- GET  /api/patients/search
    Filters: name, min_age, max_age, gender, condition, medication
- GET  /api/patients/{id}
- PUT  /api/patients/{id}
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Callable, cast
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)

from auth import verify_token
from services.patient_db import (
    init_db,
    stats,
    search_patients,
    get_patient,
    update_patient,
    upsert_patient,
)
from pathlib import Path

try:
    from services.audit import log_audit
except Exception:

    def log_audit(
        *,
        actor: str,
        event_type: str,
        target: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        return None


router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.post("/init")
async def patients_init(
    seed: bool = True,
    current_user: str = Depends(cast(Callable[..., str], verify_token)),
):
    try:
        init_db()
        seeded = False
        if seed:
            # Load bundled sample JSON if exists
            backend_dir = Path(__file__).resolve().parent.parent
            sample_path = backend_dir / "dat" / "patient-db.json"
            if sample_path.exists():
                try:
                    # Skip if patients already exist to avoid duplicating seeds
                    try:
                        from services.patient_db import stats as _stats

                        if _stats().get("patients", 0) > 0:
                            return {
                                "ok": True,
                                "seeded": False,
                                "stats": stats(),
                                "note": "DB not empty; skipped seed",
                            }
                    except Exception:
                        pass
                    data = json.loads(sample_path.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        for idx, p in enumerate(data):
                            # Build stable external_id to prevent duplicates
                            ni = p.get("national_insurance") or ""
                            raw_name = p.get("name") or ""
                            norm = raw_name.strip().lower().replace(" ", "-")
                            ext_id = ni or (norm and f"demo-{norm}") or f"demo-{idx}"
                            upsert_patient(
                                external_id=ext_id,
                                name=p.get("name"),
                                age=p.get("age"),
                                gender=p.get("gender"),
                                ni_number=p.get("national_insurance"),
                                demographics={"source": "seed"},
                                conditions_list=[
                                    {"display": c} for c in p.get("medical_history", [])
                                ],
                                medications_list=[
                                    {"display": m}
                                    for m in p.get("current_medications", [])
                                ],
                            )
                        seeded = True
                except Exception:
                    seeded = False
        return {"ok": True, "seeded": seeded, "stats": stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/json")
async def import_patients_json(
    file: UploadFile = File(...),
    current_user: str = Depends(cast(Callable[..., str], verify_token)),
):
    try:
        payload = await file.read()
        arr = json.loads(payload.decode("utf-8"))
        if not isinstance(arr, list):
            raise HTTPException(status_code=400, detail="Expected a JSON array")
        count = 0
        for idx, p in enumerate(arr):
            upsert_patient(
                external_id=(p.get("external_id") or p.get("id") or f"import-{idx}"),
                name=p.get("name"),
                age=p.get("age"),
                gender=p.get("gender"),
                ni_number=(p.get("ni_number") or p.get("national_insurance")),
                demographics=p.get("demographics"),
                conditions_list=p.get("conditions"),
                medications_list=p.get("medications"),
            )
            count += 1
        return {"ok": True, "imported": count, "stats": stats()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def patients_search(
    name: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None, ge=0),
    max_age: Optional[int] = Query(None, ge=0),
    gender: Optional[str] = Query(None),
    condition: Optional[str] = Query(None),
    medication: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: str = Depends(cast(Callable[..., str], verify_token)),
):
    try:
        rows = search_patients(
            name=name,
            min_age=min_age,
            max_age=max_age,
            gender=gender,
            condition=condition,
            medication=medication,
            limit=limit,
            offset=offset,
        )
        return {"results": rows, "count": len(rows), "stats": stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{patient_id}")
async def patients_get(
    patient_id: int,
    current_user: str = Depends(cast(Callable[..., str], verify_token)),
):
    p = get_patient(patient_id)
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    return p


@router.put("/{patient_id}")
async def patients_update(
    patient_id: int,
    body: Dict[str, Any],
    current_user: str = Depends(cast(Callable[..., str], verify_token)),
):
    ok = update_patient(patient_id, body)
    if not ok:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    # Audit trail: who edited patient and what fields
    try:
        changed = list(body.keys())
        log_audit(
            actor=current_user,
            event_type="patient_update",
            target=str(patient_id),
            details={"fields": changed},
        )
    except Exception:
        pass
    return {"ok": True}
