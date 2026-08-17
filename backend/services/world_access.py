from __future__ import annotations

import re
import time
from typing import List
from urllib.parse import urlparse

import httpx

from backend.core.config import settings
from backend.models.world_access import (
    DataClass,
    EvidenceItem,
    PrivacyDecision,
    WorldAccessAction,
    WorldAccessRequest,
    WorldAccessResult,
)


SECRET_PATTERNS = [
    r"(?i)\bsk-[a-z0-9_-]{20,}\b",
    r"(?i)\b(api[_ -]?key|secret|password|passwd|token|bearer|private[_ -]?key)\s*[:=]\s*\S+",
    r"(?i)\b(authorization|cookie)\s*[:=]\s*\S+",
]

PERSONAL_PATTERNS = [
    r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",
    r"\b(?:\+?\d[\d ()-]{8,}\d)\b",
]


class WorldAccessManager:
    """Native Saki boundary between local cognition and external web access."""

    def _classify(self, text: str) -> DataClass:
        if any(re.search(pattern, text or "") for pattern in SECRET_PATTERNS):
            return DataClass.SECRET
        if any(re.search(pattern, text or "") for pattern in PERSONAL_PATTERNS):
            return DataClass.PERSONAL
        return DataClass.PUBLIC

    def sanitize_query(self, query: str) -> PrivacyDecision:
        original = (query or "").strip()
        data_class = self._classify(original)
        mode = str(settings.PRIVACY_MODE).upper()

        if not original:
            return PrivacyDecision(allowed=False, mode=mode, data_class=data_class, blocked_reasons=["empty_query"])

        if data_class == DataClass.SECRET:
            return PrivacyDecision(
                allowed=False,
                mode=mode,
                data_class=data_class,
                blocked_reasons=["secret_or_credential_detected"],
            )

        sanitized = original
        for pattern in SECRET_PATTERNS + PERSONAL_PATTERNS:
            sanitized = re.sub(pattern, "", sanitized).strip()

        sanitized = re.sub(r"\s+", " ", sanitized).strip(" ,.;:-")
        if not sanitized:
            return PrivacyDecision(
                allowed=False,
                mode=mode,
                data_class=data_class,
                blocked_reasons=["query_empty_after_privacy_filter"],
            )

        if mode == "HIGH" and data_class != DataClass.PUBLIC:
            return PrivacyDecision(
                allowed=False,
                mode=mode,
                data_class=data_class,
                blocked_reasons=["privacy_mode_high_blocks_non_public_context"],
            )

        return PrivacyDecision(
            allowed=True,
            mode=mode,
            data_class=data_class,
            sanitized_query=sanitized,
        )

    def search(self, request: WorldAccessRequest) -> WorldAccessResult:
        now = time.time()
        decision = self.sanitize_query(request.query or "")
        if not decision.allowed:
            return WorldAccessResult(
                action=WorldAccessAction.SEARCH,
                query=request.query,
                allowed=False,
                privacy=decision,
                retrieved_at=now,
            )

        endpoint = settings.SEARXNG_URL.rstrip("/") + "/search"
        try:
            response = httpx.get(
                endpoint,
                params={
                    "q": decision.sanitized_query,
                    "format": "json",
                    "categories": "general",
                },
                timeout=settings.WORLD_ACCESS_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            return WorldAccessResult(
                action=WorldAccessAction.SEARCH,
                query=decision.sanitized_query,
                allowed=True,
                privacy=decision,
                error=f"World search unavailable: {exc}",
                retrieved_at=now,
            )

        evidence: List[EvidenceItem] = []
        for item in (payload.get("results") or [])[: request.max_results]:
            evidence.append(
                EvidenceItem(
                    title=str(item.get("title") or ""),
                    url=str(item.get("url") or ""),
                    snippet=str(item.get("content") or item.get("snippet") or ""),
                    source=str(item.get("engine") or "searxng"),
                    retrieved_at=now,
                    freshness="unknown",
                    metadata={"category": item.get("category")},
                )
            )

        return WorldAccessResult(
            action=WorldAccessAction.SEARCH,
            query=decision.sanitized_query,
            allowed=True,
            evidence=evidence,
            privacy=decision,
            retrieved_at=now,
        )

    def fetch_public_url(self, url: str) -> str:
        """Fetch only an explicitly supplied public URL; no cookies or auth headers are forwarded."""
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Only valid HTTP(S) URLs are allowed")
        response = httpx.get(
            url,
            timeout=settings.WORLD_ACCESS_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": settings.WORLD_ACCESS_USER_AGENT},
        )
        response.raise_for_status()
        return response.text


world_access = WorldAccessManager()
