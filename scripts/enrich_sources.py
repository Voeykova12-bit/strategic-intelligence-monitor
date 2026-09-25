"""Bounded article verification. Store metadata and a short excerpt, never full pages."""
import json,re,concurrent.futures
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.request import Request,urlopen
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from source_utils import publication_meta,canonical_url
ROOT=Path(__file__).resolve().parents[1]

def inspect(item):
    url=item['url']; result={'url':url,'checked_at':datetime.now(timezone.utc).isoformat()}
    try:
        if urlsplit(url).path.lower().endswith('.pdf'):
            with urlopen(Request(url,headers={'User-Agent':'StrategyRadar/3.0'}),timeout=12) as r:valid=r.read(5)==b'%PDF-'
            if not valid:raise ValueError('Invalid PDF')
            result.update(status='ok',kind='pdf');return result
        with urlopen(Request(url,headers={'User-Agent':'StrategyRadar/3.0 (+public market research)'}),timeout=12) as r:
            soup=BeautifulSoup(r.read(3_000_000),'html.parser')
        title,desc,date,pdfs=publication_meta(soup,url)
        article=soup.find('article') or soup.find('main') or soup
        for el in article.select('nav,header,footer,script,style,aside'):el.decompose()
        paragraphs=[p.get_text(' ',strip=True) for p in article.select('p')]
        paragraphs=[p for p in paragraphs if len(p)>65 and not re.search(r'cookie|политик. конфиденц|подпис[ыи]в|©|все права|согласие на обработку',p,re.I)]
        body=' '.join(paragraphs[:12])
        image=soup.find('meta',property='og:image'); image=urljoin(url,image.get('content','')) if image else ''
        links=list(dict.fromkeys(canonical_url(urljoin(url,a['href'])) for a in article.select('a[href]') if a['href'].startswith(('http','/')) and urlsplit(urljoin(url,a['href'])).netloc!=urlsplit(url).netloc))[:30]
        if not title and not desc and not body:raise ValueError('No readable article')
        result.update(status='ok',title=title,summary=desc[:650],excerpt=body[:950],published_at=date,image_url=image if image.startswith('https://') else '',links=links,pdf_urls=pdfs)
    except Exception as e:result.update(status='error',reason=type(e).__name__)
    return result

def main():
    file=ROOT/'data/enrichment.json'; cache=json.loads(file.read_text(encoding='utf-8')) if file.exists() else {}
    news=json.loads((ROOT/'data/news.json').read_text(encoding='utf-8'))['items']
    now=datetime.now(timezone.utc)
    eligible=[]
    for item in news:
        old=cache.get(canonical_url(item['url']),{})
        if old.get('status')=='ok':continue
        if old.get('checked_at') and now-datetime.fromisoformat(old['checked_at'])<timedelta(hours=20):continue
        eligible.append(item)
    eligible.sort(key=lambda x:(bool(x.get('curated_backfill')),x.get('strategic_relevance_score',0),x['published_at']),reverse=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for result in pool.map(inspect,eligible[:100]):cache[canonical_url(result['url'])]=result
    file.write_text(json.dumps(cache,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Article checks:',len(cache),'readable:',sum(x['status']=='ok' for x in cache.values()),flush=True)

if __name__=='__main__':main()
