"""Editorial selection, conservative event identity, saved editions and evidence led trends."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
from hashlib import sha1
from difflib import SequenceMatcher
import json,re,html
from urllib.parse import urlsplit
from source_utils import parse_date,canonical_url,publisher
from archive_news import main as archive_news
ROOT=Path(__file__).resolve().parents[1]
MSK=timezone(timedelta(hours=3))
METHOD='editorial-v1'

def read(name,default):
    path=ROOT/name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def write(name,payload):
    path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

def stamp(value):
    parsed=parse_date(value)
    return datetime.fromisoformat(parsed) if parsed else None

RULES=[
 ('retail_media',r'ритейл[ -]?медиа|retail media|рекламн.{0,25}(платформ|модел|формат)|медийн.{0,15}реклам','MediaAdvertising','Сопоставить новые рекламные возможности с задачами охвата и продаж. Проверить доступный инвентарь, измерение и стоимость контакта.'),
 ('ad_market',r'реклам|медиарын|ad spend|advertis|marketing spend','MediaAdvertising','Проверить, меняет ли событие выбор каналов, медиабюджет или требования к измерению рекламного результата.'),
 ('loyalty',r'лояльност|персонали[зс]|кешбэк|кэшбэк|loyalty|personalization','BanksFintech','Сопоставить новую механику с ценностью для клиента: условия участия, частота использования и роль партнеров.'),
 ('brand_action',r'коллаборац|коллекци|ребренд|позиционирован|соавтор|совместн.{0,30}(проект|линейк)|brand partnership|rebrand','Fashion','Разобрать роль партнерства, аудиторию и новую ценность предложения. Результат для продаж требует отдельного подтверждения.'),
 ('ai_choice',r'агентн.{0,20}коммер|ии.{0,10}агент|agentic|product discovery|выбор.{0,15}(ии|нейросет)|ai.{0,15}(shopping|search)','TechnologyAI','Проверить, как продукт и данные бренда представлены в новых сценариях поиска и выбора. Прогноз не считать уже достигнутым масштабом.'),
 ('consumer',r'покупател|потребител|спрос|shopper|consumer','Consumer','Сопоставить результаты с аудиторией бренда и критериями выбора. Не переносить данные отдельной площадки на весь рынок.'),
 ('commerce',r'маркетплейс|онлайн.?торг|e.?commerce|онлайн.?продаж|доставк','DeliveryEcom','Проверить приоритет каналов продаж и доставки, ассортимент и экономику привлечения клиента в выбранной категории.'),
 ('mortgage',r'ипотек|новостро|жиль|квартир|housing|mortgage','RealEstate','Пересмотреть доступность предложения для целевой аудитории и аргументы покупки с учетом условий финансирования.'),
 ('rates',r'инфляц|ключев.{0,8}ставк|доходы насел|consumer spending','FinanceEconomy','Проверить предпосылки платежеспособного спроса и чувствительность аудитории к цене; учитывать период данных.'),
 ('auto',r'авторын|автомобил|автодилер|кроссовер|автопром|car sales|automaker','Automotive','Сопоставить изменение с конкурентным набором, доступностью покупки и аргументами выбора автомобиля.'),
 ('pharma',r'аптек|фарм|лекарств','Pharma','Проверить изменение структуры спроса, цен и каналов продаж; отделить рынок в целом от отдельного сегмента.'),
 ('retail',r'ритейл|дискаунтер|торгов.{0,5}сет|retail|grocery','Retail','Сопоставить формат и позиционирование игроков с покупательской миссией, ценой и доступностью предложения.'),
 ('telecom',r'телеком|оператор.{0,8}связ|5g|мобильн.{0,8}связ','Telecom','Проверить, какие новые сценарии сервиса становятся доступны аудитории и меняют конкурентное предложение.'),
 ('bank',r'банк|финтех|bank|fintech','BanksFintech','Проверить, меняются ли клиентский путь, условия продукта и конкурентное обещание для целевой аудитории.'),
]
NOISE=r'открылся.{0,30}форум|соберет представителей|соберёт представителей|представит.{0,65}конференц|приглаша[ею]|регистраци.{0,20}(открыт|на форум)|побед.{0,30}(преми|номинац)|преми.{0,30}(побед|номинац)|днем рождения|днём рождения|юбиле[йя]|розыгрыш|разыграем|гороскоп|дтп|пожар|ваканси|поддельн.{0,15}магазин|скидки до|вклад со ставкой|файлов в веб|java.платформ|госзакупк|бюджетное правило|национальной системы платежных карт'
ACTION=r'запус[кт]|запуст|внедри|автоматиз|созда[еёст]|обнови|измен[ия]|вырос|снизил|снизис|снизи|рост|сократ|достиг|расшир|замедл|переход|скоррект|утверд|откры|коллаборац|ребренд|launch|introduc|grow|declin|expan|shift|increase|rise|reach'
QUANT=r'\d+(?:[.,]\d+)?\s*(?:%|млрд|трлн|млн|billion|million)|год к году|по сравнению'
FOREIGN=r'\bсша\b|британи|узбекистан|казахстан|центральн.{0,5}ази|qazaqstan|алматы|google|макдоналдс|америк|китайск.{0,15}рын|в китае|в европе|япон|в индии|мировой экономик'

def classify_editorial(item,override=None):
    title=html.unescape(item.get('title',''));summary=html.unescape(item.get('summary',''));text=(title+' '+summary).lower()
    row=dict(item,title=title,summary=summary);row['editorial_version']=METHOD
    if re.search(FOREIGN,text,re.I) and not re.search(r'российск.{0,20}(рын|покуп|клиент)|в россии|рын.{0,8}рф',text):row['market_scope']='Global'
    rule=next((r for r in RULES if re.search(r[1],title,re.I)),None) or next((r for r in RULES if re.search(r[1],text,re.I)),None)
    noise=bool(re.search(NOISE,title,re.I));action=bool(re.search(ACTION,title,re.I));quant=bool(re.search(QUANT,text,re.I))
    noise=noise or bool(re.search(r'представит|расскажет|награ[дт]|приглаш|прямой эфир|собственные акции|чистая прибыль|приватизац|кворум|сервер|облачн|\bLTE\b|госдолг',title,re.I))
    noise=noise or bool(re.search(r'расширяет статистику|быструю доставку банковских карт|люксовых автомобилей|lamborghini|за \d+ год.{0,12}(расшир|вырос)|как подготовиться',title,re.I))
    if row.get('official_brand'):
        action=bool(re.search(r'запуст|впервые|старт.{0,12}(продаж|серийн)|теперь.{0,40}можно|появилась возможность|начали|стал первым|новый.{0,20}(сервис|продукт|формат)|объявляет.{0,15}старт',text,re.I))
        if not action:noise=True
    research=bool(re.search(r'исследован|опрос|по данным|аналитик|research|survey|report|study',text,re.I))
    # A regular digest or a how-to opinion is not a market change merely because it has numbers.
    if re.search(r'^динамика аптечного рынка на|^как |^почему |^топ.\d|^\d+% россиян в поездке',title,re.I):noise=True
    impact=32 if rule and action else 29 if rule and quant and research else 18 if rule else 5
    scale=18 if re.search(r'рынок|рынка|росси|потребител|покупател|маркетплейс|млрд|миллион|market|consumer|shopper',text,re.I) else 12
    novelty=18 if action else 15 if research and quant else 6
    utility=15 if rule and rule[0] in ('retail_media','ad_market','loyalty','brand_action','ai_choice','consumer','commerce') else 11 if rule else 2
    evidence=9 if quant and research else 7 if action else 3
    score=impact+scale+novelty+utility+evidence
    if noise:score=min(score,35)
    if not action and not (quant and research):score=min(score,65)
    if row.get('official_brand') and rule and rule[0] in ('brand_action','loyalty','retail_media') and action and not noise:score=max(score,80)
    categories=list(row.get('categories',[]))
    if rule:
        preferred=rule[2]
        if rule[0] in ('brand_action','loyalty','consumer'):preferred=categories[0] if categories else preferred
        categories=list(dict.fromkeys([preferred]+categories))
    row.update(categories=categories or ['Consumer'],primary_category=categories[0] if categories else 'Consumer',strategic_relevance_score=score,
       strategic_components={'impact':impact,'scale':scale,'novelty':novelty,'utility':utility,'evidence':evidence},eligible=score>=70 and not noise,
       exclusion_reason='Рутинное сообщение, анонс или недостаточно существенное изменение' if noise else 'Недостаточно конкретного нового изменения' if score<70 else '',
       strategic_theme=rule[0] if rule else 'other',interpretation=rule[3] if rule else 'Требуется содержательная оценка последствий для стратегии.',
       interpretation_basis='Редакционный вопрос по типу события',fact=(row.get('summary') or title)[:360])
    row['evidence_label']='Заявление бренда' if row.get('official_brand') else 'Первичные данные' if row.get('research_primary') else 'Публикация СМИ'
    row['independence']='brand' if row.get('official_brand') else 'unreviewed'
    if override:
        for k,v in override.items():
            if k not in ('url','reason'):row[k]=v
        row['editorial_reviewed']=True
        row['review_note']=override.get('reason','Проверено по первоисточнику')
    # The displayed total remains the sum of independently assessed dimensions.
    if override and 'strategic_components' in override:
        row['strategic_relevance_score']=sum(row['strategic_components'].values())
    return row

def normalized(title):return ' '.join(re.findall(r'[a-zа-яё0-9]+',title.lower()))

def same_event(a,b):
    if canonical_url(a['url'])==canonical_url(b['url']):return True
    if a.get('event_key') or b.get('event_key'):return bool(a.get('event_key') and a['event_key']==b.get('event_key'))
    if a['market_scope']!=b['market_scope'] or abs((stamp(a['published_at'])-stamp(b['published_at'])).total_seconds())>4*86400:return False
    ta,tb=normalized(a['title']),normalized(b['title'])
    if ta==tb:return True
    na=set(re.findall(r'\d+(?:[.,]\d+)?',ta));nb=set(re.findall(r'\d+(?:[.,]\d+)?',tb))
    if na and nb and na!=nb:return False
    brands_a=set(a.get('brands',[]));brands_b=set(b.get('brands',[]))
    if brands_a and brands_b and not brands_a&brands_b:return False
    if a.get('strategic_theme')!=b.get('strategic_theme'):return False
    overlap=len(set(ta.split())&set(tb.split()))/max(1,min(len(ta.split()),len(tb.split())))
    return SequenceMatcher(None,ta,tb).ratio()>.89 or (overlap>.78 and len(ta.split())>=5 and len(tb.split())>=5)

def event_groups(items,previous=None):
    old={alias:x['id'] for x in (previous or []) for alias in x.get('member_ids',[x['id']])}
    groups=[]
    for row in sorted(items,key=lambda x:(x.get('editorial_reviewed',False),x['strategic_relevance_score']),reverse=True):
        group=next((g for g in groups if same_event(g[0],row)),None)
        if group is None:groups.append([row])
        else:group.append(row)
    result=[]
    for members in groups:
        event=dict(members[0]);aliases=list(dict.fromkeys(x['id'] for x in members));event['member_ids']=aliases
        event['id']=next((old[k] for k in aliases if k in old),'event-'+sha1((event.get('event_key') or canonical_url(event['url'])).encode()).hexdigest()[:16])
        event['sources']=[{'id':x['id'],'url':x['url'],'source':x['source'],'platform':x.get('platform'),'publisher_id':x.get('publisher_id') or publisher(x['url']),'published_at':x['published_at']} for x in members]
        event['published_at']=min((x['published_at'] for x in members),key=stamp)
        event['last_signal_at']=max((x['published_at'] for x in members),key=stamp)
        event['platforms']=list(dict.fromkeys(x['platform'] for x in members if x.get('platform')))
        event['brands']=list(dict.fromkeys(b for x in members for b in x.get('brands',[])))
        event['categories']=list(dict.fromkeys(c for x in members for c in x.get('categories',[])))
        event['image_url']=next((x.get('image_url') for x in members if x.get('image_url')),'')
        event['videos']=list({v['url']:v for x in members for v in x.get('videos',[])}.values())
        result.append(event)
    return sorted(result,key=lambda x:(stamp(x['published_at']).date(),x['strategic_relevance_score']),reverse=True)

def last_due(now):
    local=now.astimezone(MSK);wed=(local-timedelta(days=(local.weekday()-2)%7)).replace(hour=9,minute=0,second=0,microsecond=0)
    if local<wed:wed-=timedelta(days=7)
    return wed

def edition_for(events,now):
    due=last_due(now);end=due.replace(hour=0);start=end-timedelta(days=7)
    qualified=[x for x in events if x['eligible'] and x['market_scope']=='Russia' and start<=stamp(x['published_at'])<end]
    days=7
    if len(qualified)<3:
        days=30;start=end-timedelta(days=days)
        qualified=[x for x in events if x['eligible'] and x['market_scope']=='Russia' and start<=stamp(x['published_at'])<end]
    ranked=sorted(qualified,key=lambda x:(x.get('lead_priority',0),x['strategic_relevance_score'],stamp(x['published_at'])),reverse=True)
    lead=[];cats={}
    for row in ranked:
        c=row['primary_category']
        if cats.get(c,0)>=2:continue
        lead.append(row);cats[c]=cats.get(c,0)+1
        if len(lead)==3:break
    for row in ranked:
        if len(lead)>=3:break
        if row not in lead:lead.append(row)
    return {'id':due.date().isoformat(),'scheduled_for':due.isoformat(),'generated_at':now.isoformat(),'window_start':start.isoformat(),'window_end':end.isoformat(),
        'window_days':days,'late':now>due+timedelta(hours=1),'events':qualified,'lead_ids':[x['id'] for x in lead],
        'insight':{'title':lead[0]['title'],'text':lead[0]['interpretation'],'kind':'Главное событие выпуска','event_ids':[lead[0]['id']]} if lead else None,'method_version':METHOD}

def save_due_editions(events,existing,now,insights=None,coverage=None):
    """Catch up missed Wednesdays, preserving every previously published edition."""
    result=list(existing);due=last_due(now)
    first=stamp(max(e['scheduled_for'] for e in result))+timedelta(days=7) if result else due
    while first<=due:
        current=edition_for(events,first)
        current['generated_at']=now.isoformat();current['late']=now>first+timedelta(hours=1)
        reviewed=(insights or {}).get(current['id'])
        if reviewed:
            refs=[x['id'] for x in current['events'] if x.get('event_key') in reviewed['event_keys']]
            if len(refs)==len(reviewed['event_keys']):current['insight']={**reviewed,'event_ids':refs}
        current['coverage']=coverage or {}
        result.append(current);first+=timedelta(days=7)
    return sorted(result,key=lambda x:x['id'],reverse=True)

def make_pulse(events,coverage,now):
    end=last_due(now).replace(hour=0);weeks=[]
    for offset in range(3,-1,-1):
        stop=end-timedelta(days=offset*7);start=stop-timedelta(days=7)
        selected=[x for x in events if x['eligible'] and x['market_scope']=='Russia' and start<=stamp(x['published_at'])<stop]
        dates={x['date'] for x in coverage if start.date().isoformat()<=x['date']<stop.date().isoformat() and x.get('complete') and x.get('method_version')==METHOD}
        weeks.append({'start':start.date().isoformat(),'end':stop.date().isoformat(),'events':selected,'covered_days':len(dates)})
    complete=all(w['covered_days']>=6 for w in weeks)
    cohorts=[set(day.get('sources',[])) for w in weeks for day in coverage if w['start']<=day['date']<w['end'] and day.get('complete') and day.get('method_version')==METHOD]
    cohort=set.intersection(*cohorts) if complete and len(cohorts)>=24 else set()
    if len(cohort)<10:cohort=set()
    counts={}
    for w in weeks:
        for x in w['events']:counts[x['primary_category']]=counts.get(x['primary_category'],0)+1
    categories=sorted(counts,key=counts.get,reverse=True)[:5] or ['Retail','BanksFintech','FMCG','Automotive','Fashion']
    cells=[]
    for w in weeks:
        selected=[x for x in w['events'] if not cohort or any(s['source'] in cohort for s in x['sources'])]
        cells.append({'start':w['start'],'end':w['end'],'total':len(selected),'covered_days':w['covered_days'],'comparable':bool(complete and cohort),
          'values':{c:{'count':sum(x['primary_category']==c for x in selected),'share':round(100*sum(x['primary_category']==c for x in selected)/len(selected),1) if selected else None,'event_ids':[x['id'] for x in selected if x['primary_category']==c]} for c in categories}})
    return {'method_version':METHOD,'categories':categories,'weeks':cells,'comparable':bool(complete and cohort),'cohort':sorted(cohort),
      'note':'Сопоставимый состав источников' if complete and cohort else 'Неполная история наблюдения. Числа — найденные события; сравнение недель недоступно.'}

def build_trends(events,definitions):
    lookup={canonical_url(s['url']):x for x in events for s in x['sources']};out=[]
    for definition in definitions:
        evidence=[]
        for e in definition.get('evidence',[]):
            event=lookup.get(canonical_url(e['url']))
            if event and event['market_scope']==definition['scope']:
                evidence.append({**e,'event_id':event['id'],'date':event['published_at'],'source':event['source'],'title':event['title']})
        if not evidence:continue
        chains={e['origin_id'] for e in evidence if e.get('supports_claim')}
        stage=definition.get('stage','emerging')
        if stage!='emerging' and (len(chains)<2 or not definition.get('editorial_reviewed')):stage='emerging'
        signals=[x for x in events if x['eligible'] and x['market_scope']==definition['scope'] and x.get('strategic_theme') in definition.get('themes',[])]
        # New thematic matches are discovery candidates, never independent proof or stage promotion.
        out.append({**definition,'stage':stage,'evidence':evidence,'independent_count':len(chains),'last_signal_at':max((e['date'] for e in evidence),key=stamp),
         'new_signal_ids':[x['id'] for x in signals if x['id'] not in {e['event_id'] for e in evidence}][:6]})
    return out

def main():
    now=datetime.now(timezone.utc);archive_news()
    news=read('data/news.json',{'items':[]});archive=read('data/archive.json',{'items':[]});social=read('data/social.json',{'accounts':[],'items':[]})
    enrich=read('data/enrichment.json',{});overrides={canonical_url(x['url']):x for x in read('config/editorial_overrides.json',[])}
    items=[]
    # Curated source records are retained alongside the rolling collection.
    raw_items={x['id']:x for x in read('config/backfill.json',{}).get('items',[])}
    raw_items.update({x['id']:x for x in archive['items']})
    for raw in raw_items.values():
        if not stamp(raw.get('published_at')) or stamp(raw['published_at'])>now:continue
        item=dict(raw);meta=enrich.get(canonical_url(item['url']),{})
        if meta.get('status')=='ok':
            if meta.get('title') and len(meta['title'])<240:item['title']=meta['title']
            if meta.get('summary') and not re.search(r'Новости Бизнес СМИ|Заказать исследование|Маркетинговое исследование',meta['summary'],re.I):item['summary']=meta['summary']
            elif re.search(r'Новости Бизнес СМИ',meta.get('summary','')):item['summary']=item['title']
            if meta.get('image_url'):item['image_url']=meta['image_url']
            if stamp(meta.get('published_at')) and stamp(meta['published_at'])<=now:item['published_at']=meta['published_at']
        item['verification_status']=meta.get('status','feed' if not item.get('official_brand') else 'official_post')
        items.append(classify_editorial(item,overrides.get(canonical_url(item['url']))))
    previous=read('data/intelligence.json',{});events=event_groups(items,previous.get('events'))
    editions=read('data/editions.json',{'editions':[]})
    editions['editions']=save_due_editions(events,editions['editions'],now,read('config/edition_insights.json',{}),{'source_errors':len(news.get('errors',[])),'note':'Часть источников недоступна' if news.get('errors') else 'Сбор завершен'})
    write('data/editions.json',editions)
    coverage=read('data/coverage.json',[]);today=now.astimezone(MSK).date().isoformat()
    ok={s['source'] for s in news.get('source_stats',[]) if s.get('status') in ('ok','no_dated_items') or s.get('added',0)>0}
    collected=stamp(news.get('updated_at'))
    if collected and collected.astimezone(MSK).date()==now.astimezone(MSK).date():
        coverage=[x for x in coverage if x['date']!=today]+[{'date':today,'sources':sorted(ok),'complete':len(ok)>=10,'method_version':METHOD}]
    write('data/coverage.json',coverage)
    trends=build_trends(events,read('config/trend_definitions.json',[]))
    payload={'version':4,'method_version':METHOD,'updated_at':now.isoformat(),'news_updated_at':news.get('updated_at'),'events':events,'archive_items':items,
      'editions':editions['editions'],'social_accounts':social['accounts'],'social_candidates':social.get('candidates',[]),'social_updated_at':social.get('updated_at'),
      'trends':trends,'pulse':make_pulse(events,coverage,now),'source_stats':news.get('source_stats',[]),'source_errors':news.get('errors',[])}
    write('data/intelligence.json',payload)
    print('Intelligence:',len(events),'events;',sum(x['eligible'] for x in events),'selected;',len(trends),'evidence-backed trend hypotheses')

if __name__=='__main__':main()
