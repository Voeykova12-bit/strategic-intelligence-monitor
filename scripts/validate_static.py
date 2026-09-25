"""Publication gate: data invariants and static asset consistency."""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from source_utils import canonical_url, in_window, parse_date

ROOT=Path(__file__).resolve().parents[1]

def validate():
    for name, key in [('news','items'),('reports','reports'),('metrics','metrics')]:
        raw=(ROOT/'data'/f'{name}.json').read_bytes()
        payload=json.loads(raw)
        assert payload.get(key), f'Empty {name}'
        assert raw==(ROOT/'docs/data'/f'{name}.json').read_bytes(), f'Unsynchronized {name}'
    news=json.loads((ROOT/'data/news.json').read_text(encoding='utf-8'))
    urls=[canonical_url(x['url']) for x in news['items']]
    assert len(urls)==len(set(urls)), 'Duplicate canonical URLs'
    assert len({x['id'] for x in news['items']})==len(news['items']), 'Duplicate IDs'
    assert all(parse_date(x.get('published_at')) and datetime.fromisoformat(parse_date(x['published_at'])) <= datetime.now(timezone.utc)+timedelta(hours=2) for x in news['items']), 'Invalid publication dates'
    if '--fresh' in sys.argv:
        assert all(in_window(x['published_at']) for x in news['items']), 'Outside retention window'
    assert all(x['categories'] for x in news['items']), 'Missing category'
    for name in ['index.html','app.js','styles.css','premium.css']:
        assert (ROOT/'site'/name).read_bytes()==(ROOT/'docs'/name).read_bytes(), f'Unsynchronized UI: {name}'
    for r in json.loads((ROOT/'data/reports.json').read_text(encoding='utf-8'))['reports']:
        if r.get('kind')=='local_pdf':
            p=(ROOT/'docs'/r['local_path']).resolve()
            assert p.is_relative_to(ROOT/'docs/reports') and p.read_bytes().startswith(b'%PDF'), f'Invalid PDF: {r["id"]}'
    print(f'Publication checks passed: {len(urls)} unique dated materials')

if __name__=='__main__':validate()
