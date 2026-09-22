from __future__ import annotations


def final_strategic_score(
    *, llm_score: float, source_quality: float, novelty: float, corroborating_sources: int = 1, client_relevance: float = 0.0
) -> float:
    source = max(1.0, min(5.0, source_quality))
    novelty = max(1.0, min(5.0, novelty))
    corroboration = min(5.0, 1.0 + max(0, corroborating_sources - 1) * 0.7)
    client = max(1.0, min(5.0, client_relevance if client_relevance else 1.0))
    raw = llm_score * 0.52 + source * 0.16 + novelty * 0.14 + corroboration * 0.08 + client * 0.10
    return round(max(1.0, min(5.0, raw)), 1)
