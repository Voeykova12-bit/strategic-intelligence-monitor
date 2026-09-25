"""Shared, conservative parsing and identity rules for the static collectors."""
import json
import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, urljoin

MONTHS = dict(zip('января февраля марта апреля мая июня июля августа сентября октября ноября декабря'.split(), range(1, 13)))

def parse_date(value):
    if not value:
        return None
    value = str(value).strip()
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (ValueError, TypeError):
            m = re.search(r'\b(\d{1,2})\s+(' + '|'.join(MONTHS) + r')\s+(20\d{2})\b', value.lower())
            n = re.search(r'\b(\d{2})[./](\d{2})[./](20\d{2})\b', value)
            try:
                if m:
                    dt = datetime(int(m[3]), MONTHS[m[2]], int(m[1]))
                elif n:
                    dt = datetime(int(n[3]), int(n[2]), int(n[1]))
                else:
                    return None
            except ValueError:
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

def in_window(value, now=None):
    parsed = parse_date(value)
    if not parsed:
        return False
    now = now or datetime.now(timezone.utc)
    return now - timedelta(days=365) <= datetime.fromisoformat(parsed) <= now + timedelta(hours=2)

def canonical_url(url):
    p = urlsplit(url.strip())
    q = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith('utm_') and k.lower() not in {'ysclid','yclid','gclid','fbclid','from','ref'}]
    return urlunsplit(('https', p.netloc.lower().removeprefix('www.'), p.path.rstrip('/') or '/', urlencode(sorted(q)), ''))

def publisher(url):
    host = urlsplit(url).netloc.lower().removeprefix('www.')
    if host.endswith('.rbc.ru'):
        return 'rbc.ru'
    return host

def market_scope(text, country='RU'):
    low = text.lower()
    if any(w in low for w in ['в россии','российск','рынок рф','рынка рф']):
        return 'Russia'
    if country != 'RU' or any(w in low for w in ['зарубежн','западные','западных','мировой рынок','мирового рынка','глобальн','в сша','в китае','в европе','великобритани']):
        return 'Global'
    return 'Russia'

def deduplicate(items):
    result, urls, titles = [], {}, {}
    for item in sorted(items, key=lambda x: (bool(x.get('curated_backfill')), float(x.get('source_quality', 0))), reverse=True):
        if not in_window(item.get('published_at')):
            continue
        url = canonical_url(item.get('url', ''))
        if not urlsplit(url).netloc:
            continue
        title = re.sub(r'[^\w]+', ' ', item.get('title', '').casefold()).strip()
        old = urls.get(url) or titles.get(title)
        if old is not None:
            old['categories'] = list(dict.fromkeys(old.get('categories', []) + item.get('categories', [])))
            if item.get('pdf_urls'):
                old['pdf_urls'] = list(dict.fromkeys(old.get('pdf_urls', []) + item['pdf_urls']))
            continue
        item['url'] = url
        item['publisher_id'] = publisher(url)
        urls[url] = titles[title] = item
        result.append(item)
    return result

def publication_meta(soup, url):
    title = soup.find('meta', property='og:title')
    heading = soup.find('h1')
    title = title.get('content', '') if title else heading.get_text(' ', strip=True) if heading else ''
    desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', property='og:description')
    desc = desc.get('content', '') if desc else ''
    dates = []
    for attrs in ({'property':'article:published_time'}, {'name':'article:published_time'}, {'itemprop':'datePublished'}, {'name':'date'}):
        tag = soup.find(attrs=attrs)
        if tag:
            dates.append(tag.get('content') or tag.get('datetime') or tag.get_text(' ', strip=True))
    def walk(obj):
        if isinstance(obj, dict):
            if obj.get('datePublished'):
                dates.append(obj['datePublished'])
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            walk(json.loads(script.string or script.get_text()))
        except (ValueError, TypeError):
            pass
    article = soup.find('article') or soup.find('main') or soup
    for tag in article.find_all('time')[:2]:
        if tag.get('itemprop') != 'dateModified' and 'updated' not in tag.get('class', []):
            dates.append(tag.get('datetime') or tag.get_text(' ', strip=True))
    # Only explicit date elements, never arbitrary numbers in the page footer.
    for tag in article.select('[class*="date"], [class*="Date"]')[:5]:
        if any(x in ' '.join(tag.get('class', [])) for x in ['news-item', 'update', 'modif', 'validate']):
            continue
        dates.append(tag.get_text(' ', strip=True))
    published = next((d for raw in dates if (d := parse_date(raw))), None)
    pdfs = [urljoin(url, a['href']) for a in article.find_all('a', href=True) if urlsplit(a['href']).path.lower().endswith('.pdf')]
    return title, desc, published, list(dict.fromkeys(pdfs))[:5]

def material_type(text):
    low = text.lower()
    plan = any(w in low for w in ['планирует','планируют','намерен','запустит','откроет','расширит','инвестирует','plans to','will launch','will open','will invest'])
    forecast = any(w in low for w in ['прогноз','forecast','outlook','ожидается','expected to'])
    research = any(w in low for w in ['исследован','отчет','отчёт','доклад','обзор рынка','динамика аптечного рынка','survey','research','report','study'])
    return ('company_plan' if plan else 'forecast' if forecast else 'research' if research else 'news'), (plan or forecast)
