from __future__ import annotations

import hashlib
import html
import json
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

import feedparser
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "news.json"
SOURCES_PATH = ROOT / "config" / "sources.yaml"
CLIENTS_PATH = ROOT / "config" / "clients.yaml"
USER_AGENT = "StrategicIntelligenceMonitor/3.0 (+agency strategy research)"
MAX_ITEMS = 5000
RETENTION_DAYS = 550

CATEGORY_LABELS = {
    "Retail": "Ритейл",
    "DeliveryEcom": "E-commerce & доставка",
    "BanksFintech": "Банки & финтех",
    "FinanceEconomy": "Финансы & экономика",
    "FMCG": "FMCG",
    "Automotive": "Авто",
    "RealEstate": "Недвижимость",
    "TelecomTech": "Телеком & технологии",
    "MediaAdvertising": "Медиа & реклама",
}

CATEGORY_KEYWORDS = {
    "Retail": ["ритейл","рознич","магазин","торговая сеть","супермаркет","гипермаркет","дискаунтер","x5","пятёроч","пятероч","перекрёст","перекрест","чижик","магнит","лента","вкусвилл","fix price","metro","ашан","окей","o'key"],
    "DeliveryEcom": ["маркетплейс","e-commerce","ecommerce","онлайн-торгов","доставка","e-grocery","пвз","курьер","даркстор","dark store","last mile","последняя миля","самовывоз","ozon","wildberries","самокат","купер","яндекс лавка","яндекс маркет"],
    "BanksFintech": ["банк","банков","кредит","вклад","депозит","ипотек","карта","эквайр","кэшбэк","кешбэк","финтех","платеж","платёж","рассроч","bnpl","альфа-банк","альфа банк","сбер","втб","т-банк","тинькофф","газпромбанк","совкомбанк","псб","мкб","озон банк","яндекс банк"],
    "FinanceEconomy": ["финансовый рынок","финансовые рынки","финансовый сектор","финансовая система","центробанк","центральный банк","ключевая ставка","инфляц","рубл","валют","курс доллара","бирж","облигац","финрын","дивиденд","денежно-кредит","ввп","макроэконом","доходы населения","потребительские расходы"],
    "FMCG": ["fmcg","товары повседнев","производитель продуктов","производитель напит","продуктовый бренд","молочн","мясн","напитк","кофе","чай","снек","кондитер","бакале","заморож","косметик","бытовая хим","готовая еда","private label","собственная торговая марка","стм","pepsico","nestle","unilever","mars","mondelez","черкизово","мираторг","русагро","эфко"],
    "Automotive": ["авторынок","автомобил","автобизнес","автодилер","дилерская сеть","легковых автомобил","кроссовер","автокредит","автолизинг","автопроизвод","lada","haval","chery","geely","changan","jetour","tank","tenet","москвич","автоваз","exeed","omoda","gac"],
    "RealEstate": ["недвижим","новострой","жиль","квартир","девелоп","застройщик","ипотек","офисная недвиж","коммерческая недвиж","складская недвиж","арендные ставки","строительств жилья","жилой комплекс"],
    "TelecomTech": ["телеком","оператор связи","мобильная связь","интернет-провайдер","мтс","мегафон","билайн","t2","ростелеком","цифровизац","искусственн","нейросет"," ии "," ai ","adtech","martech","облачн","дата-центр","software","saas"],
    "MediaAdvertising": ["рекламный рынок","рынок рекламы","медиарынок","рекламные бюджеты","медиаинвести","наружная реклама","digital-реклама","интернет-реклама","телевизионная реклама","рекламное агентство","медиагруппа","рекламная платформа","programmatic","retail media","ритейл медиа","ритейл-медиа"],
}

TOPIC_KEYWORDS = {
    "Рынок и продажи": ["рынок","продаж","доля рынка","оборот","выручк","темп роста","динамика рынка","снижение рынка"],
    "Потребитель": ["потребител","покупател","спрос","поведен","предпочт","частота покуп","средний чек","трафик","лояльност","аудитор"],
    "Цены и промо": ["цена","цены","подорож","дешев","скидк","тариф","инфляц","промо"],
    "Доставка": ["доставка","e-grocery","экспресс-достав","last mile","последняя миля","курьер","даркстор","dark store","самовывоз"],
    "Форматы и экспансия": ["открыл","открыла","открытие","расшир","новые магазины","новые точки","новый формат","география сети","дилерская сеть"],
    "Ассортимент и СТМ": ["ассортимент","стм","собственная торговая марка","private label","готовая еда","категорийный"],
    "Маркетинг и медиа": ["реклам","кампан","медиаразмещ","маркетинг","бренд","ребрендинг","позиционирован","спонсор","коллаборац"],
    "Лояльность и CRM": ["лояльност","программа лояльности","кэшбэк","кешбэк","crm","персонализац"],
    "Digital и технологии": ["искусственн","нейросет"," ии "," ai ","технолог","автоматизац","цифровизац","приложен","финтех"],
    "Регулирование": ["закон","регулирован","цб ","фас ","минфин","маркировк","налог","требован"],
    "M&A и инвестиции": ["слияни","поглощ","приобрел","приобрёл","сделк","инвести","раунд","капвлож"],
    "Финрезультаты": ["выручк","прибыл","ebitda","оборот","финансовые результаты","рентабельност"],
    "Запуск продукта/сервиса": ["запустил","запускает","запуск","новый продукт","новый сервис","представил"],
    "Исследования и прогнозы": ["исследован","опрос","аналитик","по данным","прогноз","ожидает рынок","оценил рынок"],
}

STRATEGIC_TERMS = ["рынок","доля рынка","продаж","выручк","прибыл","ebitda","оборот","инвести","сделк","слияни","поглощ","стратег","развити","расшир","формат","открыт","закрыт","доставка","e-grocery","логист","маркетплейс","онлайн-торг","средний чек","трафик","спрос","потребител","покупател","предпочт","лояльност","ассортимент","стм","private label","цена","инфляц","ключевая ставка","кредит","вклад","платеж","рассроч","регулирован","закон","маркировк","реклам","маркетинг","бренд","ребренд","позиционирован","медиа","кампан","партнер","партнёр","спонсор","исследован","опрос","прогноз","новый сервис","новый продукт","цифровизац","автоматизац","искусственн","нейросет","дилер","ипотек","девелоп","арендн","ввод жилья","производств"]

NOISE_TERMS = ["кишечн","отравлен","сальмонел","ботулиз","бактери","инфекц","санитарн","малина","клубника","арбуз","дыня","рецепт","как приготовить","польза продукта","вред продукта","врач рассказал","диетолог","нутрициолог","калорий","похуден","здоровье","симптом","лечение","дтп","авария","пожар","ограб","краж","задержан","уголовн","гороскоп","погода","ваканс"]
BUSINESS_OVERRIDE_TERMS = ["отзыв продук","приостанов","штраф","иск","репутац","продаж","выручк","закрыт","сеть","бренд","фас","суд","регулирован","массов","рынок","производитель","ритейлер"]
MAJOR_PLAYERS = ["x5","пятёрочка","пятерочка","перекрёсток","перекресток","чижик","магнит","лента","вкусвилл","ozon","wildberries","fix price","metro","ашан","окей","самокат","купер","яндекс лавка","яндекс маркет","альфа-банк","альфа банк","сбер","втб","т-банк","газпромбанк","совкомбанк","псб","мкб","haval","chery","geely","changan","jetour","tank","tenet","лада","автоваз","москвич","пик","самолет","самолёт","лср","эталон","а101","donstroy","sminex","мтс","мегафон","билайн","t2","ростелеком","pepsico","nestle","unilever","mars","mondelez","черкизово","мираторг","русагро","эфко"]
KNOWN_BRANDS = ["X5","Пятёрочка","Пятерочка","Перекрёсток","Перекресток","Чижик","Магнит","Лента","ВкусВилл","Ozon","Wildberries","Fix Price","METRO","Ашан","О'КЕЙ","Самокат","Купер","Яндекс Лавка","Яндекс Маркет","Альфа-Банк","Сбер","ВТБ","Т-Банк","Газпромбанк","Совкомбанк","ПСБ","МКБ","Haval","Chery","Geely","Changan","Jetour","TANK","TENET","LADA","АвтоВАЗ","Москвич","ПИК","Самолет","Самолёт","ЛСР","Эталон","А101","Donstroy","Sminex","МТС","МегаФон","Билайн","T2","Ростелеком","PepsiCo","Nestle","Unilever","Mars","Mondelez","Черкизово","Мираторг","Русагро","ЭФКО","Черноголовка"]

FOREIGN_MARKERS = ["сша","америк","евросоюз","европ","китай","китайск","индия","турц","оаэ","британи","германи","франци","итал","испан","япони","коре","global","worldwide","международн"]
RUSSIA_MARKERS = ["россия","россий"," рф ","москв","петербург","рубл","цб росс","x5","пятёроч","чижик","альфа-банк"]
FUTURE_RE = re.compile(r"\b(2027|2028|2029|2030|2031|2032|2033|2034|2035)\b")
FUTURE_WORDS = ["планирует","планируют","планируется","намерен","намерена","к 2027","до 2030","в следующем году","прогнозирует","прогноз"]

def canonicalize(url):
    try:
        parts=urlsplit(url.strip()); q=[(k,v) for k,v in parse_qsl(parts.query,keep_blank_values=True) if not k.lower().startswith("utm_") and k.lower() not in {"gclid","yclid","fbclid","from","ref"}]
        return urlunsplit((parts.scheme.lower() or "https",parts.netloc.lower(),parts.path.rstrip("/") or "/",urlencode(sorted(q)),""))
    except Exception: return url

def clean_text(value):
    value=html.unescape(value or ""); value=re.sub(r"<[^>]+>"," ",value); return re.sub(r"\s+"," ",value).strip()

def compact_summary(value,limit=360):
    text=clean_text(value)
    if len(text)<=limit: return text
    cut=text[:limit]; pos=max(cut.rfind(". "),cut.rfind("! "),cut.rfind("? "))
    return (cut[:pos+1] if pos>150 else cut.rstrip())+"…"

def parse_date_value(raw):
    if not raw: return datetime.now(timezone.utc).isoformat()
    try: dt=parsedate_to_datetime(raw)
    except Exception:
        try: dt=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
        except Exception: return datetime.now(timezone.utc).isoformat()
    if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

def contains_term(low, term):
    term=str(term).lower()
    if re.fullmatch(r"[a-zа-яё0-9-]+", term) and (len(term) <= 4 or term in {"x5","t2","ai","ии","vk"}):
        return bool(re.search(r"(?<![a-zа-яё0-9])"+re.escape(term)+r"(?![a-zа-яё0-9])", low))
    return term in low

def classify(text,hint=None):
    low=f" {text.lower()} "; cats=[k for k,words in CATEGORY_KEYWORDS.items() if any(contains_term(low,w) for w in words)]
    if hint and hint not in cats: cats.insert(0,hint)
    topics=[k for k,words in TOPIC_KEYWORDS.items() if any(contains_term(low,w) for w in words)]
    brands=[b for b in KNOWN_BRANDS if contains_term(low,b)]
    return cats[:4],(topics or ["Бизнес-изменения"])[:6],list(dict.fromkeys(brands))[:12]

def detect_scope(text):
    low=f" {text.lower()} "; ru=sum(1 for m in RUSSIA_MARKERS if m in low); foreign=sum(1 for m in FOREIGN_MARKERS if m in low)
    return "Global" if foreign>ru else "Russia"

def planning_horizon(text):
    low=text.lower(); years=FUTURE_RE.findall(text)
    return list(dict.fromkeys(years)) or (["future"] if any(x in low for x in FUTURE_WORDS) else [])

def load_clients():
    return (yaml.safe_load(CLIENTS_PATH.read_text(encoding="utf-8")) or {}).get("clients",[])

def client_matches(text,clients):
    low=text.lower(); out={}
    for c in clients:
        matched=[term for term in c.get("brands",[]) if contains_term(low,term)]
        if matched: out[c["slug"]]={"name":c["name"],"score":round(min(5.0,3.0+len(matched)*0.4),1),"matches":matched[:6]}
    return out

def strategic_filter(text,categories,topics,brands,client_hits,future):
    low=f" {text.lower()} "; strategic_hits=sum(1 for t in STRATEGIC_TERMS if contains_term(low,t)); major_hits=sum(1 for t in MAJOR_PLAYERS if contains_term(low,t))
    noise=[t for t in NOISE_TERMS if t in low]; override=any(t in low for t in BUSINESS_OVERRIDE_TERMS)
    has_number=bool(re.search(r"\b\d+(?:[.,]\d+)?\s*(?:%|млн|млрд|трлн|руб|₽|долл|магазин|точк|клиент|автомоб|квартир)",low))
    high={"Рынок и продажи","Потребитель","Доставка","Финрезультаты","M&A и инвестиции","Регулирование","Маркетинг и медиа","Форматы и экспансия","Исследования и прогнозы","Лояльность и CRM","Цены и промо"}
    value=min(3.0,strategic_hits*0.42)+min(1.25,major_hits*0.38)+min(0.9,len(set(topics)&high)*0.24)+(0.55 if has_number else 0)+(1.0 if client_hits else 0)+(0.4 if future else 0)+(0.2 if len(categories)>1 else 0)
    if noise and not override: value-=3.2
    elif noise: value-=0.8
    reasons=[]
    if "Рынок и продажи" in topics or "Финрезультаты" in topics: reasons.append("рынок / бизнес")
    if "Потребитель" in topics: reasons.append("потребитель")
    if "Доставка" in topics: reasons.append("доставка")
    if "Маркетинг и медиа" in topics: reasons.append("маркетинг")
    if "Регулирование" in topics: reasons.append("регулирование")
    if "M&A и инвестиции" in topics: reasons.append("инвестиции / M&A")
    if client_hits: reasons.append("клиент")
    if major_hits: reasons.append("крупный игрок")
    if future: reasons.append("будущий горизонт")
    if has_number: reasons.append("есть данные")
    high_count=len(set(topics)&high)
    passes_value=client_hits or (major_hits and high_count>=1) or strategic_hits>=2 or high_count>=2 or (future and strategic_hits>=1) or (has_number and strategic_hits>=1 and high_count>=1)
    relevant=bool(categories) and bool(passes_value) and not (noise and not override)
    return relevant,round(max(0,min(5,value)),1),list(dict.fromkeys(reasons))[:5]

def metric_type_for(context):
    low=context.lower()
    rules=[
      ("Доля рынка",["доля рынка","доля продаж","занимает около","занимает более"]),
      ("Выручка / оборот",["выручк","оборот","gmv","доход"]),
      ("Продажи",["продаж","продано","реализ","реализац","регистрац"]),
      ("Спрос",["спрос","потреблен","покупател","потребител"]),
      ("Средний чек",["средний чек","чек вырос","чек сниз"]),
      ("Цены",["цена","цены","подорож","удешев","инфляц"]),
      ("Трафик",["трафик","посещаем","визит"]),
      ("Клиенты",["клиент","пользовател","аудитор"]),
      ("Сеть / точки",["магазин","торговых точ","точек","пвз","отделени","офис"]),
      ("Кредитование",["кредит","ипотек","портфель","выдач"]),
      ("Инвестиции",["инвести","капвлож","влож"]),
    ]
    for label,words in rules:
        if any(w in low for w in words):
            return label
    return "Рыночная метрика"

def extract_metrics(text):
    clean=clean_text(text)
    patterns=[
      re.compile(r"\b\d+(?:[.,]\d+)?\s*%",re.I),
      re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:трлн|млрд|млн)\s*(?:₽|руб(?:\.|лей|ля)?|долл(?:\.|аров)?|\$)",re.I),
      re.compile(r"\b\d[\d\s]*(?:[.,]\d+)?\s*(?:автомобил(?:ей|я)?|машин(?:ы|а)?|магазин(?:ов|а)?|точ(?:ек|ки)|заказ(?:ов|а)?|клиент(?:ов|а)?|квартир(?:ы)?|м²|кв\.?\s*м)",re.I),
    ]
    found=[]
    seen=set()
    for pat in patterns:
        for m in pat.finditer(clean):
            value=re.sub(r"\s+"," ",m.group(0)).strip()
            key=value.lower()
            if key in seen:
                continue
            start=max(0,m.start()-100); end=min(len(clean),m.end()+120)
            context=clean[start:end]
            sent_start=max(clean.rfind(".",0,m.start()),clean.rfind("!",0,m.start()),clean.rfind("?",0,m.start()))
            sent_end=min([x for x in [clean.find(".",m.end()),clean.find("!",m.end()),clean.find("?",m.end())] if x!=-1] or [min(len(clean),m.end()+140)])
            snippet=clean[sent_start+1:sent_end+1].strip()
            if len(snippet)>190:
                snippet=snippet[:187].rstrip()+"…"
            found.append({"type":metric_type_for(context),"value":value,"context":snippet})
            seen.add(key)
            if len(found)>=6:
                return found
    return found

def why_it_matters(categories,brands,future,reasons):
    cat=categories[0] if categories else ""
    base={
      "Retail":"Показывает изменение в бизнесе ритейла: формате, продажах, ценах, ассортименте или конкурентной динамике.",
      "DeliveryEcom":"Помогает отслеживать рынок e-commerce и доставки: модели сервиса, игроков, логистику и поведение покупателей.",
      "BanksFintech":"Может менять банковские офферы, финтех-сервисы, клиентское поведение и коммуникационную конкуренцию.",
      "FinanceEconomy":"Задает макроконтекст для спроса, потребительских расходов и бизнес-планирования.",
      "FMCG":"Показывает сдвиги в спросе, портфелях брендов, ценах, дистрибуции и потребительских привычках.",
      "Automotive":"Важен для понимания продаж, цен, модельного ряда, дилерской сети и конкурентной динамики авторынка.",
      "RealEstate":"Отражает динамику спроса, цен, ипотеки, девелопмента и коммерческой недвижимости.",
      "TelecomTech":"Показывает изменения в цифровых сервисах, телеком-рынке и технологиях, влияющих на потребителей и маркетинг.",
      "MediaAdvertising":"Помогает видеть изменения рекламного и медиарынка, бюджетов, каналов и рекламных технологий."
    }.get(cat,"Материал влияет на рыночный или конкурентный контекст.")
    if brands: base+=f" В фокусе: {', '.join(brands[:3])}."
    if future: base+=f" Горизонт: {', '.join(future)}."
    if reasons: base+=f" Отобрано как: {', '.join(reasons[:3])}."
    return base

def title_key(title):
    return " ".join(re.sub(r"[^a-zа-яё0-9 ]+"," ",title.lower()).split())[:180]

def make_items(raw_items,src,clients):
    out=[]; hint=src.get("category_hint")
    for title,url,summary,published in raw_items:
        combined=f"{title}. {summary}"; cats,topics,brands=classify(combined,hint)
        if not cats: continue
        future=planning_horizon(combined); cm=client_matches(combined,clients); relevant,value,reasons=strategic_filter(combined,cats,topics,brands,cm,future)
        if not relevant: continue
        bonus=max(0,min(.7,(float(src.get("reliability_score",3))-3)*.25))+max(0,min(.5,(int(src.get("priority",3))-3)*.2))
        score=round(min(5,value+bonus),1); uid=hashlib.sha1(f"{url}|{title_key(title)}".encode("utf-8")).hexdigest()[:18]
        metrics=extract_metrics(combined)\n        out.append({"id":uid,"title":title,"url":url,"source":src.get("name","Source"),"published_at":published,"summary":summary,"categories":cats,"primary_category":cats[0],"topics":topics,"brands":brands,"score":score,"relevance_reasons":reasons,"why_it_matters":why_it_matters(cats,brands,future,reasons),"client_matches":cm,"market_scope":detect_scope(combined),"future_horizon":future,"metrics":metrics})
    return out

def fetch_rss(src,clients):
    req=Request(src["url"],headers={"User-Agent":USER_AGENT,"Accept":"application/rss+xml, application/xml, text/xml, */*"})
    with urlopen(req,timeout=30) as r: raw=r.read()
    feed=feedparser.parse(raw); rows=[]
    for e in feed.entries[:100]:
        title=clean_text(e.get("title")); url=canonicalize(e.get("link","")); summary=compact_summary(e.get("summary") or e.get("description") or "")
        if title and url: rows.append((title,url,summary,parse_date_value(e.get("published") or e.get("updated"))))
    return make_items(rows,src,clients)

def detail_meta(url):
    req=Request(url,headers={"User-Agent":USER_AGENT,"Accept":"text/html,*/*"})
    with urlopen(req,timeout=20) as r: page=r.read()
    soup=BeautifulSoup(page,"html.parser"); desc=""; published=""
    for attrs in ({"property":"og:description"},{"name":"description"}):
        tag=soup.find("meta",attrs=attrs)
        if tag and tag.get("content"): desc=clean_text(tag.get("content")); break
    for attrs in ({"property":"article:published_time"},{"name":"article:published_time"}):
        tag=soup.find("meta",attrs=attrs)
        if tag and tag.get("content"): published=tag.get("content"); break
    return compact_summary(desc),parse_date_value(published)

def fetch_html(src,clients):
    req=Request(src["url"],headers={"User-Agent":USER_AGENT,"Accept":"text/html,*/*"})
    with urlopen(req,timeout=30) as r: page=r.read()
    soup=BeautifulSoup(page,"html.parser"); domain=urlsplit(src["url"]).netloc.lower(); seen=set(); rows=[]
    for a in soup.find_all("a",href=True):
        heading=a.find(["h1","h2","h3","h4"])
        title=clean_text(heading.get_text(" ",strip=True) if heading else a.get_text(" ",strip=True))
        href=urljoin(src["url"],a.get("href")); p=urlsplit(href)
        if domain.endswith("autostat.ru"):
            title=re.sub(r"^(?:сегодня|вчера|\\d{1,2}\\s+[а-яё]+)\\s*,?\\s*\\d{1,2}:\\d{2}\\s*","",title,flags=re.I)
        if len(title)>190:
            cut=title[:190]; pos=cut.rfind(". "); title=(cut[:pos] if pos>60 else cut).strip()
        if p.netloc.lower()!=domain or len(title)<28 or href in seen: continue
        if domain.endswith("autostat.ru") and "/news/" not in p.path: continue
        if domain.endswith("rbc.ru") and "/news/" not in p.path: continue
        seen.add(href)
        try: summary,published=detail_meta(href)
        except Exception: summary,published="",datetime.now(timezone.utc).isoformat()
        rows.append((title,canonicalize(href),summary,published))
        if len(rows)>=28: break
        time.sleep(.05)
    return make_items(rows,src,clients)

def requalify(item,clients,active_sources,cutoff):
    try:
        dt=datetime.fromisoformat((item.get("published_at") or "").replace("Z","+00:00"))
        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
    except Exception: return None
    if dt<cutoff or item.get("source") not in active_sources: return None
    combined=f"{item.get('title','')}. {item.get('summary','')}"; cats,topics,brands=classify(combined)
    future=planning_horizon(combined); cm=client_matches(combined,clients); relevant,value,reasons=strategic_filter(combined,cats,topics,brands,cm,future)
    if not relevant: return None
    metrics=extract_metrics(combined)\n    item.update({"categories":cats,"primary_category":cats[0],"topics":topics,"brands":brands,"score":round(min(5,max(float(item.get("score",0) or 0),value)),1),"relevance_reasons":reasons,"why_it_matters":why_it_matters(cats,brands,future,reasons),"client_matches":cm,"future_horizon":future,"metrics":metrics})
    return item

def main():
    sources=(yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8")) or {}).get("sources",[])
    sources=[s for s in sources if s.get("accessible_without_vpn_ru",False)]
    clients=load_clients(); active={s["name"] for s in sources}; cutoff=datetime.now(timezone.utc)-timedelta(days=RETENTION_DAYS)
    try: previous=json.loads(DATA_PATH.read_text(encoding="utf-8")).get("items",[]) if DATA_PATH.exists() else []
    except Exception: previous=[]
    by_id={}; title_seen={}
    for raw in previous:
        item=requalify(raw,clients,active,cutoff)
        if item: by_id[item["id"]]=item; title_seen[title_key(item.get("title",""))]=item["id"]
    errors=[]; stats=[]
    for src in sources:
        added=0
        try:
            items=fetch_rss(src,clients) if src.get("type")=="rss" else fetch_html(src,clients)
            for item in items:
                key=title_key(item["title"]); old_id=title_seen.get(key)
                if old_id and old_id in by_id:
                    if item["score"]<=float(by_id[old_id].get("score",0) or 0): continue
                    by_id.pop(old_id,None)
                by_id[item["id"]]=item; title_seen[key]=item["id"]; added+=1
        except Exception as exc: errors.append({"source":src.get("name"),"error":str(exc)[:240]})
        stats.append({"source":src.get("name"),"added":added}); time.sleep(.12)
    items=list(by_id.values()); items.sort(key=lambda x:(float(x.get("score",0) or 0),x.get("published_at") or ""),reverse=True); items=items[:MAX_ITEMS]
    payload={"updated_at":datetime.now(timezone.utc).isoformat(),"source_count":len(sources),"item_count":len(items),"retention_days":RETENTION_DAYS,"categories":[{"id":k,"label":v} for k,v in CATEGORY_LABELS.items()],"clients":[{"slug":c["slug"],"name":c["name"]} for c in clients],"source_stats":stats,"errors":errors,"items":items}
    DATA_PATH.parent.mkdir(parents=True,exist_ok=True); DATA_PATH.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Updated {len(items)} strategically relevant items from {len(sources)} sources; errors={len(errors)}")

if __name__=="__main__": main()
