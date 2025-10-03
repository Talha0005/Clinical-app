import os
import json
from services.agents import ExtendedOrchestrator, AgentContext

example = (
    "I have chest pain and I also have diabetes. It gets worse when I "
    "climb stairs."
)

if __name__ == "__main__":
    orch = ExtendedOrchestrator()
    ctx = AgentContext(user_id="demo", region=os.environ.get("REGION", "GB"))

    out = orch.handle_turn(example, ctx=ctx, llm=None)

    print("=== Avatar text ===")
    print(out.text)
    print()

    print("=== Orchestrator data (keys) ===")
    print(list(out.data.keys()))
    print()

    print("=== Summary (patient + clinician) ===")
    summary = out.data.get("summary", {})
    print(json.dumps(summary, indent=2))
    print()

    print("=== Medical Record (FHIR + EHR) ===")
    medrec = out.data.get("medical_record", {})
    print(json.dumps(medrec, indent=2))
    print()

    print("=== Coding ===")
    coding = out.data.get("coding", {})
    print(json.dumps(coding, indent=2))
    print()

    print("=== Risk/HITL ===")
    risk = out.data.get("risk", {})
    hitl = out.data.get("hitl", {})
    print("risk:", json.dumps(risk, indent=2))
    print("hitl:", json.dumps(hitl, indent=2))
