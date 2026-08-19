"""
Sprint 1 Exit Gate Test via FastAPI TestClient
Tests all 10 queries:
1. "special food in Vijayawada"
2. "good movies in 2026"
3. "latest FastAPI version"
4. "latest Python version"
5. "what happened in AI today"
6. "best places to visit in Vijayawada"
7. "what is FastAPI"
8. "explain overfitting"
9. "how are you Saki"
10. "tell me about an obscure local place"
"""

from fastapi.testclient import TestClient
from backend.main import app
import json
import traceback

client = TestClient(app)

QUERIES = [
    "special food in Vijayawada",
    "good movies in 2026",
    "latest FastAPI version",
    "latest Python version",
    "what happened in AI today",
    "best places to visit in Vijayawada",
    "what is FastAPI",
    "explain overfitting",
    "how are you Saki",
    "tell me about an obscure local place"
]

def run_exit_gate():
    results = []
    print("=" * 80)
    print("SPRINT 1 EXIT GATE RUNNER")
    print("=" * 80)
    
    for idx, query in enumerate(QUERIES, start=1):
        print(f"\n[{idx}/10] Testing POST /api/chat with query: '{query}'")
        try:
            res = client.post("/api/chat", json={"message": query, "conversation_id": f"exitgate-{idx}"})
            print(f"      HTTP Status: {res.status_code}")
            if res.status_code == 200:
                data = res.json()
                print(f"      Selected Model: {data.get('routing', {}).get('selected_model')}")
                print(f"      Action Decision: {data.get('action_decision', {}).get('action')}")
                print(f"      Web Required: {data.get('action_decision', {}).get('requires_world_access')}")
                print(f"      Evidence Count: {len(data.get('world_access_evidence') or [])}")
                safe_snippet = data.get('response', '').encode('ascii', 'replace').decode('ascii')[:100]
                print(f"      Response snippet: {safe_snippet}...")
                results.append({
                    "query": query,
                    "status_code": res.status_code,
                    "model": data.get('routing', {}).get('selected_model'),
                    "action": data.get('action_decision', {}).get('action'),
                    "web_required": data.get('action_decision', {}).get('requires_world_access'),
                    "evidence_count": len(data.get('world_access_evidence') or []),
                    "response": data.get('response', ''),
                    "error": None
                })
            else:
                print(f"      ERROR BODY: {res.text}")
                results.append({
                    "query": query,
                    "status_code": res.status_code,
                    "error": res.text
                })
        except Exception as e:
            tb = traceback.format_exc()
            print(f"      EXCEPTION: {e}\n{tb}")
            results.append({
                "query": query,
                "status_code": 500,
                "error": str(e),
                "traceback": tb
            })
            
    with open("tests/reliability/sprint1_exit_gate_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nResults written to tests/reliability/sprint1_exit_gate_results.json")

if __name__ == "__main__":
    run_exit_gate()
