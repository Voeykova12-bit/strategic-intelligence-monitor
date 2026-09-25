from __future__ import annotations

import hashlib, html, json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlsplit
from email.utils import parsedate_to_datetime

from concurrent.futures import ThreadPoolExecutor
from source_utils import parse_date, material_type, deduplicate, in_window
from research_collector import collect, allowed

import feedparser
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"news.json"
BACKFILL=ROOT/"config"/"backfill.json"
UA="StrategyRadar/1.0 (+market intelligence dashboard)"

SOURCES=[
 {"name":"Банк России — новости","kind":"rss","url":"https://www.cbr.ru/rss/eventrss","country":"RU","hint":"FinanceEconomy","quality":5.0},
 {"name":"Банк России — пресс-релизы","kind":"rss","url":"https://www.cbr.ru/rss/RssPress","country":"RU","hint":"BanksFintech","quality":5.0},
 {"name":"Marketing Dive","kind":"rss","url":"https://www.marketingdive.com/feeds/news/","country":"US","hint":"MediaAdvertising","quality":4.5},
 {"name":"Retail Dive","kind":"rss","url":"https://www.retaildive.com/feeds/news/","country":"US","hint":"Retail","quality":4.5},
 {"name":"TechCrunch","kind":"rss","url":"https://techcrunch.com/feed/","country":"US","hint":"TechnologyAI","quality":4.3},
 {"name":"Modern Retail","kind":"rss","url":"https://www.modernretail.co/feed/","country":"US","hint":"Retail","quality":4.3},
 {"name":"РОМИР — аналитика","kind":"html","url":"https://romir.ru/feed/analytics","country":"RU","hint":"Consumer","quality":4.8},
 {"name":"Росстат — новости статистики","kind":"html","url":"https://rosstat.gov.ru/central-news","country":"RU","hint":"FinanceEconomy","quality":5.0},
 {"name":"AdIndex — реклама и медиа","kind":"html","url":"https://adindex.ru/news/","country":"RU","hint":"MediaAdvertising","quality":4.5,"path_contains":["/news/"]},
 {"name":"АКАР — рынок рекламы","kind":"html","url":"https://akarussia.ru/volumes/","country":"RU","hint":"MediaAdvertising","quality":4.9,"path_contains":["/news/","/volumes/"]},
 {"name":"Data Insight — исследования","kind":"html","url":"https://datainsight.ru/news","country":"RU","hint":"DeliveryEcom","quality":4.8,"research_primary":True,"path_contains":["/DI_","/trend","/agentic","/ecosystem","/egrocery","/top-100","/onlineimport","/whoiswho"]},
 {"name":"New Retail — отраслевые новости","kind":"html","url":"https://new-retail.ru/novosti/","country":"RU","hint":"Retail","quality":4.2,"path_contains":["/novosti/"]},
 {"name":"Минэкономразвития — новости","kind":"html","url":"https://economy.gov.ru/material/news/","country":"RU","hint":"FinanceEconomy","quality":5.0,"path_contains":["/material/news/"]},
 {"name":"ФАС России — новости","kind":"html","url":"https://fas.gov.ru/news","country":"RU","hint":"FinanceEconomy","quality":5.0,"path_contains":["/news/"]},
 {"name":"Mediascope — исследования","kind":"html","url":"https://mediascope.net/news/","country":"RU","hint":"MediaAdvertising","quality":4.8,"path_contains":["/news/"]},
]

KEY={
 "Pharma":["фарм","аптек","лекарств"],
 "Fashion":["fashion","одежд","обув","текстиль","модной индустр"],
 "Retail":["ритейл","рознич","магазин","дискаунтер","retail","store","grocery","shopper","private label"],
 "DeliveryEcom":["e-commerce","ecommerce","маркетплейс","доставка","delivery","marketplace","commerce"],
 "BanksFintech":["банк","кредит","ипотек","финтех","bank","banking","fintech","lending","mortgage","payments"],
 "FinanceEconomy":["инфляц","ввп","ключевая ставка","экономик","финансов","inflation","economy","gdp","interest rate","consumer spending"],
 "FMCG":["fmcg","напит","продукт","consumer goods","beverage","food brand"],
 "Automotive":["авторынок","автомобил","car sales","automotive","automaker","dealer"],
 "RealEstate":["недвижим","жиль","девелоп","real estate","housing","property","developer"],
 "Telecom":["телеком","оператор связи","мобильн связь","сотов","5g","4g","мтс","мегафон","билайн","t2","telecom","mobile operator"],
 "TechnologyAI":["искусственн интеллект","нейросет","ии ","generative ai","artificial intelligence","machine learning","ai ","martech","adtech","technology","software","platform"],
 "Consumer":["потребител","покупател","домохозяйств","потребительск спрос","потребительск настро","consumer","shopper","spending","consumer confidence"],
 "MediaAdvertising":["реклам","маркетинг","retail media","advertising","marketing","ad spend","creator","influencer","media"]
}
TOPICS={
 "Рынок и продажи":["рынок","продаж","выруч","оборот","market","sales","revenue","growth"],
 "Потребитель":["потребител","покупател","спрос","consumer","shopper","demand","spending"],
 "Цены и промо":["цена","скидк","инфляц","price","discount","promotion","affordability"],
 "Форматы и экспансия":["открыт","расшир","экспан","store opening","expansion","format"],
 "Ассортимент и СТМ":["стм","ассортимент","private label","assortment"],
 "Маркетинг и медиа":["реклам","маркетинг","retail media","advertising","marketing","campaign","creator","influencer","media"],
 "Лояльность и CRM":["лояльност","персонализац","loyalty","personalization","first-party data"],
 "Digital и технологии":["искусственн","нейросет","ии ","ai ","technology","automation","generative","martech","adtech"],
 "M&A и инвестиции":["инвести","слияни","сделк","investment","acquisition","merger","funding"],
 "Исследования и прогнозы":["исследован","опрос","прогноз","research","survey","report","forecast","study"]
}
NOISE=["погода","гороскоп","рецепт","дтп","пожар","celebrity","football","match result"]

def clean(s):
    s=html.unescape(s or "")
    s=re.sub(r"<[^>]+>"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def parse_dt(v):
    return parse_date(v)

def date_from_title(title):
    return parse_date(title)

def classify(text,hint):
    low=" "+text.lower()+" "
    cats=[c for c,ks in KEY.items() if any(k in low for k in ks)]
    if hint:
        cats = [hint] + [c for c in cats if c != hint]
    tops=[t for t,ks in TOPICS.items() if any(k in low for k in ks)]
    return cats[:4],tops[:6] or ["Бизнес-изменения"]

def metric_type(ctx):
    low=ctx.lower()
    for name,ks in [
      ("Выручка / оборот",["выруч","оборот","revenue","gmv"]),
      ("Продажи",["продаж","sales","sold"]),
      ("Доля рынка",["доля рынка","market share"]),
      ("Кредитование",["кредит","ипотек","mortgage","lending"]),
      ("Цены",["цена","price","inflation"]),
      ("Инвестиции",["инвести","investment","funding"]),
      ("Спрос",["спрос","demand","consumer spending"])
    ]:
        if any(k in low for k in ks):return name
    return "Рыночная метрика"

def extract_metrics(text):
    out=[];seen=set()
    for pat in [
      r"\b\d+(?:[.,]\d+)?\s*%",
      r"\b\d+(?:[.,]\d+)?\s*(?:трлн|млрд|млн)\s*(?:₽|руб(?:\.|лей|ля)?|\$|долл(?:\.|аров)?)"
    ]:
        for m in re.finditer(pat,text,re.I):
            v=re.sub(r"\s+"," ",m.group(0)).strip()
            if v.lower() in seen:continue
            seen.add(v.lower())
            s=max(0,m.start()-90);e=min(len(text),m.end()+110);ctx=clean(text[s:e])
            out.append({"type":metric_type(ctx),"value":v,"context":ctx[:190]})
            if len(out)>=5:return out
    return out

def image_from_entry(e,raw=""):
    for k in ("media_thumbnail","media_content"):
        for x in e.get(k,[]) or []:
            if isinstance(x,dict) and x.get("url"):return x["url"]
    for x in e.get("links",[]) or []:
        if isinstance(x,dict) and str(x.get("type","")).startswith("image/") and x.get("href"):return x["href"]
    m=re.search(r'<img[^>]+src=["\']([^"\']+)',raw or "",re.I)
    return m.group(1) if m else ""

FUTURE_WORDS=["прогноз","ожида","планирует","намерен","будет ","к 2027","к 2028","к 2029","к 2030","forecast","outlook","plans to","will ","expected to","by 2027","by 2028","by 2029","by 2030"]

def content_type(text,tops):
    return material_type(text)

def make(src,title,url,summary,published,image=""):
    if not in_window(published): return None
    if not allowed(src, title, summary): return None
    text=f"{title}. {summary}"; low=text.lower()
    if any(n in low for n in NOISE):return None
    cats,tops=classify(text,src["hint"])
    if not cats:return None
    strategic=sum(k in low for k in ["рынк","продаж","спрос","потребител","реклам","маркетинг","инвести","выруч","оборот","исследован","прогноз","производств","цифров","market","sales","consumer","advertising","marketing","revenue","growth","report"])
    if not strategic: return None
    score=min(5,2.5+min(1.3,strategic*.25)+(0.4 if re.search(r"\d",text) else 0)+(src["quality"]-4)*.35+len(tops)*.08)
    if src.get("research_primary") and strategic: score=min(5,score+.5)
    if score<3.2:return None
    scope="Russia" if src["country"]=="RU" else "Global"
    uid=hashlib.sha1((url+"|"+title.lower()).encode()).hexdigest()[:18]
    why="Международный сигнал, который может повлиять на маркетинг, потребление или бизнес-модели и быть релевантен российскому рынку." if scope=="Global" else "Сигнал влияет на рыночный, потребительский или коммуникационный контекст и может быть полезен для стратегической работы."
    if "Исследования и прогнозы" in tops:why+=" Есть исследовательская или прогнозная база."
    ctype,future_signal=content_type(text,tops)
    return {"id":uid,"title":clean(title),"url":url,"source":src["name"],"published_at":published,"summary":clean(summary)[:420],"categories":cats,"primary_category":cats[0],"topics":tops,"brands":[],"score":round(score,1),"strategic_relevance_score":int(round(score*20)),"why_it_matters":why,"market_scope":scope,"metrics":extract_metrics(text),"image_url":image,"source_quality":src["quality"],"content_type":ctype,"future_signal":future_signal,"future_horizon":["future"] if future_signal else []}

def rss(src):
    raw=urlopen(Request(src["url"],headers={"User-Agent":UA}),timeout=25).read()
    f=feedparser.parse(raw);out=[]
    for e in f.entries[:70]:
        title=clean(e.get("title",""));url=e.get("link","");r=e.get("summary") or e.get("description") or ""
        if not title or not url:continue
        item=make(src,title,url,clean(r),parse_dt(e.get("published") or e.get("updated")),image_from_entry(e,r))
        if item:out.append(item)
    return out

def html_items(src):
    return collect(src, make)

def source_result(src):
    try:
        rows = rss(src) if src["kind"] == "rss" else html_items(src)
        return src, rows, None
    except Exception as exc:
        return src, [], str(exc)[:220]

def main():
    payload=json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"items":[]}
    cutoff=datetime.now(timezone.utc)-timedelta(days=365)
    by={}
    for x in payload.get("items",[]):
        try:d=datetime.fromisoformat(x.get("published_at","").replace("Z","+00:00"))
        except Exception:continue
        if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
        if d>=cutoff:by[x["id"]]=x
    if BACKFILL.exists():
        try:
            seeded=json.loads(BACKFILL.read_text(encoding="utf-8")).get("items",[])
        except Exception:
            seeded=[]
        for x in seeded:
            try:d=datetime.fromisoformat(x.get("published_at","").replace("Z","+00:00"))
            except Exception:continue
            if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
            if d>=cutoff and (x.get("url") or "").startswith("http") and int(x.get("strategic_relevance_score",0) or 0)>=80:
                x["curated_backfill"]=True
                by.setdefault(x["id"],x)
    stats=list(payload.get("source_stats",[]));errors=list(payload.get("errors",[]))
    configured = json.loads((ROOT/'config/research_sources.json').read_text(encoding='utf-8'))['sources']
    research = {"name":"Банк России — исследования","url":"https://cbr.ru/ec_research/","hint":"FinanceEconomy","quality":5.0,"research_primary":True,"path_contains":["/ec_research/"]}
    sources = SOURCES + configured + [research]
    for src in sources:
        src.setdefault('kind', 'html')
        src.setdefault('country', 'RU')
    with ThreadPoolExecutor(max_workers=6) as pool:
        for src, rows, error in pool.map(source_result, sources):
            for x in rows:
                by[x['id']] = x
            stats.append({'source':src['name'], 'added':len(rows), 'status':'error' if error else 'ok' if rows else 'no_dated_items'})
            if error:
                errors.append({'source':src['name'], 'error':error})
            print(src['name'], len(rows), error or '', flush=True)
    items=deduplicate(list(by.values()))
    for x in items:
        txt=f"{x.get('title','')}. {x.get('summary','')}"
        config = next((s for s in sources if s['name'] == x.get('source')), None)
        if config:
            x['categories'], x['topics'] = classify(txt, config['hint'])
            x['primary_category'] = x['categories'][0]
        tops=x.get("topics") or []
        ctype,future_signal=content_type(txt,tops)
        x["content_type"]=ctype
        x["future_signal"]=future_signal or bool(x.get("future_horizon"))
        if x["future_signal"] and not x.get("future_horizon"):x["future_horizon"]=["future"]
        sc=float(x.get("score",0) or 0)
        x["strategic_relevance_score"]=int(round(sc*20))
        if "source_quality" not in x:x["source_quality"]=4.2
    items.sort(key=lambda x:(float(x.get("score",0)),x.get("published_at","")),reverse=True)
    payload["items"]=items[:5000]
    payload["configured_source_count"]=len(sources)+12
    payload["item_count"]=len(payload["items"])
    payload["source_count"]=len(set([x.get("source","") for x in payload["items"]]))
    payload["updated_at"]=datetime.now(timezone.utc).isoformat()
    payload["source_stats"]=stats[-80:]
    payload["errors"]=errors[-40:]
    DATA.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Augmented Strategy Radar:",payload["item_count"],"items")

if __name__=="__main__":
    main()
