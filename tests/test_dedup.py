from app.services.dedup import canonicalize_url, normalize_title, title_similarity, likely_same_story


def test_canonicalize_url_removes_tracking():
    assert canonicalize_url("https://Example.com/news/1/?utm_source=x&b=2&a=1#x") == "https://example.com/news/1?a=1&b=2"


def test_title_normalization():
    assert normalize_title("Ёлка: Новый бренд!") == "елка новый бренд"


def test_same_story():
    a = "Сбер запустил новый рекламный продукт для бизнеса"
    b = "Сбер запустил новый рекламный продукт для малого бизнеса"
    assert title_similarity(a, b) > 0.75
    assert likely_same_story(a, b)
