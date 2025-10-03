import os
import sys
import json
from typing import List, Dict
import requests

BASE = os.environ.get("DIGICLINIC_BASE_URL", "http://127.0.0.1:8000")
USER = os.environ.get("DIGICLINIC_USER", "doctor")
PASS = os.environ.get("DIGICLINIC_PASS", "doctor")


def auth_headers() -> Dict[str, str]:
    r = requests.post(
        f"{BASE}/api/auth/login",
        json={"username": USER, "password": PASS},
        timeout=20,
    )
    r.raise_for_status()
    tok = r.json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def get_available(headers) -> List[str]:
    r = requests.get(
        f"{BASE}/api/models/available", headers=headers, timeout=20
    )
    r.raise_for_status()
    data = r.json()
    models = [m["id"] for m in data.get("models", [])]
    return models


def agent_health(headers) -> dict:
    r = requests.get(
        f"{BASE}/api/models/agent/health", headers=headers, timeout=15
    )
    r.raise_for_status()
    return r.json()


def switch_to(headers, model_id: str, conv_id: str) -> dict:
    r = requests.post(
        f"{BASE}/api/models/switch",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "model_id": model_id,
            "conversation_id": conv_id,
            "reason": "verification",
        },
        timeout=40,
    )
    r.raise_for_status()
    return r.json()


def compare_two(headers, models: List[str], conv_id: str) -> dict:
    assert len(models) == 2
    r = requests.post(
        f"{BASE}/api/models/compare",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "message": (
                "Short medical triage test. Patient reports mild fever "
                "and sore throat."
            ),
            "models": models,
            "conversation_id": conv_id,
        },
        timeout=90,
    )
    r.raise_for_status()
    return r.json()


def stream_smoke(headers, conv_id: str, model_id: str) -> bool:
    # Only meaningful if AGENTS_ENABLED=false (backend will stream via model layer)
    try:
        import sseclient  # type: ignore
    except Exception:
        sseclient = None

    with requests.post(
        f"{BASE}/api/models/chat/stream",
        headers=headers,
        json={
            "message": "stream test",
            "conversation_id": conv_id,
            "model_id": model_id,
        },
        stream=True,
        timeout=90,
    ) as resp:
        resp.raise_for_status()
        seen_content = False
        if sseclient is not None:
            client = sseclient.SSEClient(resp)
            for event in client.events():
                try:
                    data = json.loads(event.data)
                except Exception:
                    continue
                if data.get("type") == "content" and data.get("text"):
                    seen_content = True
                    break
        else:
            # Fallback: iterate raw lines for 'data:'
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                try:
                    data = json.loads(line[len("data:"):].strip())
                except Exception:
                    continue
                if data.get("type") == "content" and data.get("text"):
                    seen_content = True
                    break
        return seen_content


def performance(headers) -> dict:
    r = requests.get(
        f"{BASE}/api/models/performance", headers=headers, timeout=20
    )
    r.raise_for_status()
    return r.json()


def main() -> int:
    headers = auth_headers()

    # Agent flag
    ah = agent_health(headers)
    agents_enabled = bool(ah.get("agents_enabled"))
    print("agents_enabled:", agents_enabled, "raw=", ah.get("env_value"))

    # Available models
    models = get_available(headers)
    print("available models (", len(models), "):")
    for m in models:
        print(" -", m)
    if not models:
        print("No models available. Check API keys and flags.")
        return 2

    # Switch to each model
    conv_switch = "verify-switch"
    results = {}
    for m in models:
        try:
            res = switch_to(headers, m, conv_switch)
            results[m] = {
                "switch": "ok" if res.get("success") else f"fail: {res}"
            }
        except Exception as e:
            results[m] = {"switch": f"error: {e}"}
    print("\nSwitch results:")
    for k, v in results.items():
        print(f" - {k}: {v['switch']}")

    # Compare in pairs to exercise generation
    print("\nCompare tests:")
    pairs = []
    for i in range(0, len(models), 2):
        if i + 1 < len(models):
            pairs.append((models[i], models[i + 1]))
        else:
            # If odd count, compare last with first
            pairs.append((models[i], models[0]))
    comp_summary = []
    for a, b in pairs:
        try:
            data = compare_two(
                headers, [a, b], conv_id=f"verify-compare-{a[:6]}-{b[:6]}"
            )
            comps = data.get("comparisons", {})
            ok_a = bool(comps.get(a, {}).get("response"))
            ok_b = bool(comps.get(b, {}).get("response"))
            comp_summary.append((a, b, ok_a, ok_b))
            print(
                f" - {a} vs {b}: A={'OK' if ok_a else 'FAIL'}, "
                f"B={'OK' if ok_b else 'FAIL'}"
            )
        except Exception as e:
            comp_summary.append((a, b, False, False))
            print(f" - {a} vs {b}: ERROR {e}")

    # Optional stream smoke if agents disabled
    if not agents_enabled:
        baseline = models[0]
        try:
            ok = stream_smoke(
                headers, conv_id="verify-stream", model_id=baseline
            )
            print(f"\nStreaming test on {baseline}: {'OK' if ok else 'FAIL'}")
        except Exception as e:
            print(f"\nStreaming test error: {e}")
    else:
        print("\nStreaming test skipped (agents enabled)")

    # Performance snapshot
    try:
        perf = performance(headers)
        print("\nPerformance snapshot:")
        print(json.dumps(perf, indent=2))
    except Exception as e:
        print("\nPerformance fetch error:", e)

    # Exit code indicates if any compare failed
    any_fail = any(not a_ok or not b_ok for _, _, a_ok, b_ok in comp_summary)
    return 0 if not any_fail else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except requests.HTTPError as e:
        print("HTTP error:", e)
        if e.response is not None:
            print("Body:", e.response.text)
        raise
