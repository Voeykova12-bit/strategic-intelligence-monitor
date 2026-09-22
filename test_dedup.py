from app.services.scoring import final_strategic_score


def test_score_is_bounded():
    assert 1 <= final_strategic_score(llm_score=9, source_quality=9, novelty=9, corroborating_sources=50, client_relevance=9) <= 5


def test_high_signal_scores_higher():
    low = final_strategic_score(llm_score=2, source_quality=2, novelty=2)
    high = final_strategic_score(llm_score=5, source_quality=5, novelty=5, corroborating_sources=4, client_relevance=5)
    assert high > low
