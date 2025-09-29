from services.agents import ExtendedOrchestrator, AgentContext


def test_extended_pipeline_basic():
    orch = ExtendedOrchestrator()
    ctx = AgentContext(user_id="pytest", region="GB")

    text = (
        "I have chest pain and I also have diabetes. It gets worse when I "
        "climb stairs."
    )
    out = orch.handle_turn(text, ctx=ctx, llm=None)

    # Contract: required keys exist
    data = out.data
    for key in [
        "risk",
        "history",
        "triage",
        "support",
        "reasoning",
        "summary",
        "medical_record",
        "coding",
        "hitl",
    ]:
        assert key in data, f"missing {key}"

    # Summary contains patient-facing text
    assert data["summary"].get("patient_summary") is not None

    # Medical record includes FHIR and EHR stubs
    medrec = data["medical_record"]
    assert "ehr" in medrec and "fhir" in medrec
    assert medrec["fhir"].get("resourceType") == "Bundle"

    # Coding should include chest pain ICD or SNOMED when chest pain present
    codes = data["coding"]
    snomed = codes.get("snomed_ct", [])
    icd10 = codes.get("icd10", [])
    assert ("29857009" in snomed) or ("R07.9" in icd10)

    # HITL data contains decision
    assert data["hitl"].get("needs_review") in (True, False)
