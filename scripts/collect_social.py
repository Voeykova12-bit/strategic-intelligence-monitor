"""Read verified official public accounts. Access failures never mean zero news."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha1
import json, os, re
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from source_utils import parse_date, canonical_url

ROOT = Path(__file__).resolve().parents[1]
UA = 'StrategyRadar/3.0 (+public brand news; bounded daily requests)'

def telegram(account):
    handle = urlsplit(account['url']).path.strip('/')
    url = 'https://t.me/s/' + handle
    with urlopen(Request(url, headers={'User-Agent': UA}), timeout=18) as r:
        soup = BeautifulSoup(r.read(3_000_000), 'html.parser')
    posts = soup.select('.tgme_widget_message[data-post]')
    if not posts:
        raise ValueError('Публичная лента недоступна или не содержит читаемых публикаций')
    rows = []
    for post in posts:
        body, stamp = post.select_one('.tgme_widget_message_text'), post.find('time')
        if not body or not stamp:
            continue
        text = body.get_text(' ', strip=True)
        date = parse_date(stamp.get('datetime'))
        if not date or datetime.fromisoformat(date) > datetime.now(timezone.utc):
            continue
        permalink = 'https://t.me/' + post['data-post']
        title = re.sub(r'^[^\w«]+', '', text).split('\n')[0]
        end = re.search(r'[.!?]\s', title)
        if end and end.start() > 40:
            title = title[:end.start()]
        if len(title) > 145:
            title = title[:145].rsplit(' ', 1)[0] + '…'
        image = ''
        photo = post.select_one('.tgme_widget_message_photo_wrap')
        if photo:
            m = re.search(r"url\(['\"]?(.*?)['\"]?\)", photo.get('style',''))
            if m and m[1].startswith('https://'):
                image = m[1]
        videos = []
        if post.select_one('video, .tgme_widget_message_video_player'):
            duration = post.select_one('.tgme_widget_message_video_duration')
            videos.append({'url':permalink,'title':title,'platform':'Telegram','duration':duration.get_text(strip=True) if duration else None,'description':'Видео в публикации бренда. Описание — по тексту поста.','description_basis':'post_text'})
        links = list(dict.fromkeys(a['href'] for a in body.select('a[href]') if a['href'].startswith('https://')))
        rows.append({'id':sha1(permalink.encode()).hexdigest()[:18], 'title':title, 'url':permalink,'summary':text[:650],
          'source':account['brand']+' · Telegram','publisher_id':account['publisher_id'],'published_at':date,
          'categories':account['categories'],'primary_category':account['categories'][0],'brands':[account['brand']],
          'market_scope':'Russia','platform':'telegram','account_id':account['id'],'official_brand':True,
          'source_quality':4.5,'image_url':image,'videos':videos,'primary_links':links,'content_type':'news',
          'source_relation':'brand_statement','collected_at':datetime.now(timezone.utc).isoformat()})
    return rows

def vk(account, token):
    def api(method, params):
        params.update({'access_token':token,'v':'5.199'})
        req=Request('https://api.vk.com/method/'+method,data=urlencode(params).encode(),headers={'User-Agent':UA})
        with urlopen(req, timeout=18) as response: result=json.load(response)
        if 'error' in result:
            raise ValueError('VK API: отказ в доступе, код '+str(result['error'].get('error_code','unknown')))
        return result['response']
    handle=urlsplit(account['url']).path.strip('/')
    resolved=api('utils.resolveScreenName',{'screen_name':handle})
    if not resolved or resolved.get('type') not in ('group','page'):
        raise ValueError('Не удалось определить официальное сообщество')
    owner=-abs(resolved['object_id'])
    posts=api('wall.get',{'owner_id':owner,'count':40,'filter':'owner'}).get('items',[])
    rows=[]
    for post in posts:
        text=post.get('text','').strip()
        if not text or post.get('copy_history'):continue
        url=f'https://vk.com/wall{owner}_{post["id"]}'
        videos=[]; image=''
        for att in post.get('attachments',[]):
            if att.get('type')=='photo':
                sizes=att['photo'].get('sizes',[])
                if sizes:image=max(sizes,key=lambda x:x.get('width',0)).get('url','')
            if att.get('type')=='video':
                v=att['video']; sec=v.get('duration'); videos.append({'url':f'https://vk.com/video{v["owner_id"]}_{v["id"]}','platform':'ВК Видео','title':v.get('title',text[:100]),'duration':f'{sec//60}:{sec%60:02}' if isinstance(sec,int) else None,'description':'Видео из официальной публикации.','description_basis':'post_text'})
        rows.append({'id':sha1(url.encode()).hexdigest()[:18],'title':text.split('\n')[0][:150],'url':url,'summary':text[:650],
          'source':account['brand']+' · ВК','publisher_id':account['publisher_id'],'published_at':datetime.fromtimestamp(post['date'],timezone.utc).isoformat(),
          'categories':account['categories'],'primary_category':account['categories'][0],'brands':[account['brand']],'market_scope':'Russia',
          'platform':'vk','account_id':account['id'],'official_brand':True,'source_quality':4.5,'image_url':image,'videos':videos,
          'content_type':'news','source_relation':'brand_statement','collected_at':datetime.now(timezone.utc).isoformat()})
    return rows

def run_account(account):
    status=dict(account);status['checked_at']=datetime.now(timezone.utc).isoformat()
    if not account.get('verified'):
        status.update(status='unverified',detail='Принадлежность аккаунта еще проверяется');return status,[]
    if account['platform']=='vk' and not os.environ.get('VK_ACCESS_TOKEN'):
        status.update(status='credentials_required',detail='Для автоматического сбора ВК требуется токен API с доступом к сообществу');return status,[]
    try:
        rows=telegram(account) if account['platform']=='telegram' else vk(account,os.environ['VK_ACCESS_TOKEN'])
        status.update(status='ok',count=len(rows),last_success_at=status['checked_at'],detail='Публичная лента; полнота истории и вложений не гарантируется' if account['platform']=='telegram' else 'Официальный API ВК')
        return status,rows
    except Exception as e:
        # Never include request objects or token-bearing API URLs in the published audit.
        status.update(status='error',detail=str(e)[:180] if isinstance(e,ValueError) else 'Источник недоступен: '+type(e).__name__)
        return status,[]

def main():
    config=json.loads((ROOT/'config/social_accounts.json').read_text(encoding='utf-8'))
    out=ROOT/'data/social.json'; previous=json.loads(out.read_text(encoding='utf-8')) if out.exists() else {}
    items={x['url']:x for x in previous.get('items',[])}; statuses=[]
    old={a['id']:a for a in previous.get('accounts',[])}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for status,rows in pool.map(run_account,config['accounts']):
            if not status.get('last_success_at'):status['last_success_at']=old.get(status['id'],{}).get('last_success_at')
            statuses.append(status)
            for row in rows:items[row['url']]=row
            print(status['brand'],status['platform'],status['status'],len(rows),flush=True)
    payload={'updated_at':datetime.now(timezone.utc).isoformat(),'accounts':statuses,'candidates':config.get('candidates',[]),'items':list(items.values())}
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
