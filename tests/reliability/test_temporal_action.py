"""
Test ActionEngine classification on temporal and version queries.
"""
from backend.services.action_engine import decide_action, classify_freshness

QUERIES = [
    ("what is FastAPI", False, "STABLE", "Static general knowledge"),
    ("what current fastapi version", True, "CURRENT", "Current version query"),
    ("what is the latest fastapi version", True, "CURRENT", "Latest version query"),
    ("latest Python version", True, "CURRENT", "Latest version query"),
    ("latest Node.js version", True, "CURRENT", "Latest version query"),
    ("latest Ollama version", True, "CURRENT", "Latest version query"),
    ("what happened in AI today", True, "CURRENT", "Time-sensitive today news"),
    ("good movies in 2026", True, "CURRENT", "Current year 2026 recommendation"),
    ("movies in 2025", False, "STABLE", "Past year 2025 movie query"),
    ("movies in 2027", True, "CURRENT", "Future year 2027 movie query"),
    ("special food in Vijayawada", True, "CURRENT", "Local culinary recommendation"),
    ("best places to visit in Vijayawada", True, "CURRENT", "Local tourism recommendation"),
    ("explain overfitting", False, "STABLE", "Static ML concept"),
    ("how are you Saki", False, "STABLE", "Casual chat")
]

def test_classifications():
    print("=" * 80)
    print("TESTING ACTION ENGINE CLASSIFICATIONS")
    print("=" * 80)
    all_passed = True
    for q, exp_web, exp_fresh, desc in QUERIES:
        act = decide_action(q)
        web_ok = (act.requires_world_access == exp_web)
        fresh_ok = (act.freshness_requirement == exp_fresh)
        passed = web_ok and fresh_ok
        if not passed:
            all_passed = False
        mark = "[PASS]" if passed else "[FAIL]"
        print(f"{mark} Query: '{q}' ({desc})")
        print(f"       -> Action: {act.action} | Web: {act.requires_world_access} (Exp: {exp_web}) | Freshness: {act.freshness_requirement} (Exp: {exp_fresh})")
        if not passed:
            print(f"       -> Reason: {act.reason}")
    print("\nOverall Result:", "ALL PASSED" if all_passed else "SOME FAILED")

if __name__ == "__main__":
    test_classifications()
