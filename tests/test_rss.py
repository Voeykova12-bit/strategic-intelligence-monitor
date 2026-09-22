from app.collectors.rss import parse_rss_bytes

RSS = b'''<?xml version="1.0"?><rss version="2.0"><channel><item><title>Test news</title><link>https://example.com/a</link><pubDate>Tue, 22 Sep 2026 10:00:00 GMT</pubDate><description>Hello</description></item></channel></rss>'''


def test_parse_rss():
    items = parse_rss_bytes(RSS)
    assert len(items) == 1
    assert items[0].title == "Test news"
    assert items[0].url == "https://example.com/a"
    assert items[0].published_at is not None
