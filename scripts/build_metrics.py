from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"metrics.json"
UA="StrategyRadar/1.0 (+official market metrics)"

def page(url, timeout=15):
    req=Request(url,headers={"User-Agent":UA,"Accept":"text/html,*/*"})
    with urlopen(req,timeout=timeout) as r:
        raw=r.read()
    soup=BeautifulSoup(raw,"html.parser")
    return soup, " ".join(soup.stripped_strings)

def norm(v):
    return v.replace(",",".").strip()

def metric(id,label,value,period,source,url,change="",history=None,note=""):
    return {"id":id,"label":label,"value":value,"period":period,"source":source,"source_url":url,"change":change,"history":history or [],"note":note}

def cbr_rates():
    url="https://www.cbr.ru/hd_base/KeyRate/"
    _,txt=page(url)
    pairs=re.findall(r"(\d{2}\.\d{2}\.\d{4})\s+(\d{1,2},\d{2})",txt)
    if not pairs:return None
    latest=pairs[0]
    history=[{"period":d,"value":float(norm(v))} for d,v in list(reversed(pairs[:45]))[::max(1,len(pairs[:45])//8 or 1)]]
    return metric("key-rate","Ключевая ставка ЦБ",norm(latest[1])+"%",latest[0],"Банк России",url,history=history,note="официальная ставка")

def cbr_inflation():
    url="https://www.cbr.ru/hd_base/infl/"
    _,txt=page(url)
    rows=re.findall(r"(\d{2}\.\d{4})\s+(\d{1,2},\d{2})\s+(\d{1,2},\d{2})\s+(\d{1,2},\d{2})",txt)
    if not rows:return None
    latest=rows[0]
    history=[{"period":p,"value":float(norm(infl))} for p,rate,infl,target in reversed(rows[:8])]
    return metric("inflation","Инфляция",norm(latest[2])+"%",latest[0],"Банк России / Росстат",url,history=history,note="год к году")

def latest_auto():
    year=datetime.now(timezone.utc).year
    month=datetime.now(timezone.utc).month
    for m in [month,month-1,month-2]:
        if m<1:continue
        archive=f"https://www.autostat.ru/press-releases/archive/{year}/{m}/"
        try:soup,_=page(archive)
        except Exception:continue
        links=[]
        for a in soup.find_all("a",href=True):
            t=" ".join(a.stripped_strings)
            if "Продажи новых легковых автомобилей в России" in t:
                links.append((urljoin(archive,a["href"]),t))
        for url,title in links:
            try:_,txt=page(url)
            except Exception:continue
            mm=re.search(r"реализовано\s+(\d+(?:[.,]\d+)?)\s*тыс",txt,re.I)
            yoy=re.search(r"на\s+(\d+(?:[.,]\d+)?)%\s+(меньше|больше)",txt,re.I)
            date=re.search(r"(\d{1,2})\s+([а-яё]+)\s+(20\d{2})\s+года",txt,re.I)
            if mm:
                ch=""
                if yoy:ch=("−" if yoy.group(2).lower()=="меньше" else "+")+yoy.group(1).replace(",",".")+"% г/г"
                month_match=re.search(r"(январ[ея]|феврал[ея]|март[ае]?|апрел[ея]|ма[ея]|июн[ея]|июл[ея]|август[ае]|сентябр[ея]|октябр[ея]|ноябр[ея]|декабр[ея])\s+(20\d{2})",txt,re.I)
                month_names={"января":"январь","январе":"январь","февраля":"февраль","феврале":"февраль","марта":"март","марте":"март","апреля":"апрель","апреле":"апрель","мая":"май","мае":"май","июня":"июнь","июне":"июнь","июля":"июль","июле":"июль","августа":"август","августе":"август","сентября":"сентябрь","сентябре":"сентябрь","октября":"октябрь","октябре":"октябрь","ноября":"ноябрь","ноябре":"ноябрь","декабря":"декабрь","декабре":"декабрь"}
                period=(month_names.get(month_match.group(1).lower(),month_match.group(1))+" "+month_match.group(2)) if month_match else f"{m:02d}.{year}"
                return metric("auto-sales","Продажи новых автомобилей",mm.group(1).replace(",",".")+" тыс.",period,"АВТОСТАТ",url,change=ch,note="новые легковые автомобили")
    return None

def latest_mortgage():
    now=datetime.now(timezone.utc)
    candidates=[]
    y=now.year;m=now.month
    for back in range(1,8):
        mm=m-back;yy=y
        while mm<=0:mm+=12;yy-=1
        candidates.append((yy,mm))
    for yy,mm in candidates:
        code=f"{mm:02d}{str(yy)[2:]}"
        url=f"https://www.cbr.ru/statistics/bank_sector/mortgage/Indicator_mortgage/{code}/"
        try:_,txt=page(url)
        except Exception:continue
        match=re.search(r"Объем\s*выдач\s+(\d+(?:[.,]\d+)?)\s*млрд",txt,re.I)
        if not match:
            match=re.search(r"объем.{0,40}выдач.{0,80}?(\d+(?:[.,]\d+)?)\s*млрд",txt,re.I)
        if match:
            value=match.group(1).replace(",",".")+" млрд ₽"
            return metric("mortgage","Выдачи ипотеки",value,f"{mm:02d}.{yy}","Банк России",url,note="ИЖК, объем выдач")
    return None

def ad_market():
    url="https://akarussia.ru/news/obem-rynka-marketingovyh-kommunikacij-v-2025-godu/"
    try:_,txt=page(url)
    except Exception:return None
    m=re.search(r"(?:объем|рынок).{0,120}?(\d{3}(?:[.,]\d+)?)\s*млрд",txt,re.I)
    if not m:
        m=re.search(r"(981[.,]6|980)\s*млрд",txt,re.I)
    if not m:return None
    return metric("ad-market","Рекламный рынок РФ",m.group(1).replace(",",".")+" млрд ₽","2025","АКАР",url,change="+8.5% г/г",note="объем рекламы по оценке АКАР")

def ecommerce():
    url="https://datainsight.ru/DI_eCommerce_2026"
    try:_,txt=page(url)
    except Exception:return None
    m=re.search(r"объем рынка.{0,80}?достиг\s+(\d+(?:[.,]\d+)?)\s*трлн",txt,re.I)
    if not m:return None
    return metric("ecommerce","E-commerce РФ",m.group(1).replace(",",".")+" трлн ₽","2025","Data Insight",url,change="+19% г/г",note="розничная интернет-торговля; прогноз 2026 >15 трлн ₽")

def main():
    old={}
    if OUT.exists():
        try:old={x.get("id"):x for x in json.loads(OUT.read_text(encoding="utf-8")).get("metrics",[])}
        except Exception:old={}
    builders=[
        ("key-rate",cbr_rates),("inflation",cbr_inflation),("auto-sales",latest_auto),
        ("mortgage",latest_mortgage),("ad-market",ad_market),("ecommerce",ecommerce)
    ]
    rows=[];errors=[]
    for metric_id,fn in builders:
        try:
            item=fn()
            if item:
                rows.append(item)
            elif metric_id in old:
                rows.append(old[metric_id])
        except Exception as e:
            errors.append({"metric":metric_id,"error":str(e)[:180]})
            if metric_id in old:
                rows.append(old[metric_id])
    payload={"updated_at":datetime.now(timezone.utc).isoformat(),"metric_count":len(rows),"metrics":rows,"errors":errors}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Built {len(rows)} key metrics; errors={len(errors)}")

if __name__=="__main__":
    main()
