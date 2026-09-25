"""Bounded public-page collection; missing dates are skipped, never fabricated."""
import re
from urllib.request import Request, urlopen
from urllib.parse import urlsplit, urljoin
from bs4 import BeautifulSoup
from source_utils import canonical_url, publication_meta, in_window, parse_date

CONSUMER = ['потребител','покуп','расход','доход','сбережен','экономическ','материальн','финансов','инфляц','цен','кредит','занятост','рынок труда','работ','досуг','интернет','медиа','образ жизни']
POLITICAL = ['выбор','президент','партии','партий','военн','спецоперац','сво','одобрение деятельности','доверие полит','политическ','украин','санкци']

def allowed(src, text, summary=''):
    low = text.lower()
    return not src.get('consumer_only') or (any(w in (low+' '+summary.lower()) for w in CONSUMER) and not any(w in low for w in POLITICAL))

def page(url):
    with urlopen(Request(url, headers={'User-Agent':'StrategyRadar/2.0 (+public market research)', 'Accept':'text/html,*/*'}), timeout=10) as response:
        return BeautifulSoup(response.read(3_000_000), 'html.parser')

def collect(src, make):
    soup = page(src['url'])
    rows, seen, failures = [], set(), 0
    if src.get('kind') == 'telegram':
        for post in soup.select('.tgme_widget_message'):
            body, link, time = post.select_one('.tgme_widget_message_text'), post.select_one('.tgme_widget_message_date'), post.find('time')
            if not body or not link or not time:
                continue
            text = body.get_text(' ', strip=True)
            date = parse_date(time.get('datetime'))
            if not in_window(date):
                continue
            item = make(src, text[:170], link['href'], text[:420], date)
            if item:
                item['supplementary'] = True
                rows.append(item)
        return rows
    candidates = []
    for a in soup.find_all('a', href=True):
        url = urljoin(src['url'], a['href'])
        p = urlsplit(url)
        if p.scheme not in {'https','http'} or p.netloc.removeprefix('www.') != urlsplit(src['url']).netloc.removeprefix('www.'):
            continue
        key = canonical_url(url)
        title = a.get_text(' ', strip=True)
        if len(title) < 28 or key in seen or key == canonical_url(src['url']):
            continue
        if any(w in p.path.lower() for w in ['/tag/','/category/','/author/','/about','/contacts','/privacy','/subscription']):
            continue
        patterns = src.get('path_contains', [])
        if patterns and not any(re.search(w, p.path) if src.get('path_regex') else w in p.path for w in patterns):
            continue
        seen.add(key)
        if allowed(src, title):
            candidates.append((url, title, parse_date(title)))
        if len(candidates) >= 20:
            break
    for url, title, listing_date in candidates:
        try:
            detail = page(url)
            detail_title, summary, published, pdfs = publication_meta(detail, url)
            published = published or listing_date
            title = detail_title or title
            if not in_window(published) or not allowed(src, title, summary):
                continue
            item = make(src, title, url, summary, published)
            if item:
                item['pdf_urls'] = pdfs
                item['research_primary'] = bool(src.get('research_primary'))
                rows.append(item)
            if len(rows) >= 10:
                break
        except Exception:
            failures += 1
    if candidates and failures == len(candidates):
        raise RuntimeError('Article pages unavailable; existing archive retained')
    return rows
