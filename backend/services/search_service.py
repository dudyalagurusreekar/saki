from backend.core.config import settings
from backend.core.privacy import (
    make_safe_query, 
    expand_query, 
    PrivacyPolicyEngine, 
    OutboundRequest, 
    PrivacyAuditLogger,
    DECISION_BLOCK,
    DECISION_REQUIRE_CONFIRMATION
)
from backend.services.search import multi_search

def safe_search(user_input: str) -> list[str]:
    """
    Executes outbound web search only after passing PrivacyPolicyEngine enforcement.
    Fails closed on secrets, PII, or STRICT privacy mode.
    """
    req = OutboundRequest(
        query=user_input, 
        action="WEB_SEARCH",
        destination="PUBLIC_SEARCH",
        privacy_mode=settings.PRIVACY_MODE
    )
    decision = PrivacyPolicyEngine.evaluate_request(req)
    PrivacyAuditLogger.log_decision(decision, action="WEB_SEARCH", destination="PUBLIC_SEARCH")

    if decision.decision in [DECISION_BLOCK, DECISION_REQUIRE_CONFIRMATION] or not decision.sanitized_request:
        return []

    safe_query = decision.sanitized_request


    if not safe_query:
        return []

    queries = expand_query(safe_query)

    if not queries:
        queries = [safe_query]

    results = []

    for q in queries:
        try:
            res = multi_search(q)

            if isinstance(res, list):
                results.extend(res)
            elif isinstance(res, str):
                results.append(res)

        except Exception:
            continue

    clean_results = []
    seen = set()

    for r in results:
        r = r.strip()
        if r and r not in seen:
            seen.add(r)
            clean_results.append(r)

    return clean_results