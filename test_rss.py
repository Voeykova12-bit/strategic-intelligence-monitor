from app.services.prefilter import relevance_prefilter


def test_marketing_news_beats_noise():
    relevant = relevance_prefilter("Банк запустил новую рекламную кампанию и продукт")
    noise = relevance_prefilter("Прогноз погоды на завтра")
    assert relevant > noise
