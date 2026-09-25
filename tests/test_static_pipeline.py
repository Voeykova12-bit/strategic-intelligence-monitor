import sys
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from bs4 import BeautifulSoup
from source_utils import parse_date,canonical_url,material_type,deduplicate,publication_meta,in_window,publisher,market_scope
from research_collector import allowed
from build_reports import unique_reports

def test_report_archive_does_not_duplicate_curated_pdf():
    curated={'id':'one','url':'https://example.com/report.pdf','landing_url':'https://example.com/report'}
    previous=dict(curated,local_path='reports/one.pdf')
    discovered={'id':'auto-two','url':'https://example.com/report?utm_source=feed'}
    assert len(unique_reports([curated,previous,discovered]))==1

def test_unknown_dates_never_become_today():
    assert parse_date(None) is None
    assert parse_date('yesterday') is None
    assert parse_date('31.02.2026') is None
    assert not in_window((datetime.now(timezone.utc)+timedelta(days=7)).isoformat())

def test_geography_is_not_publisher_location():
    assert market_scope('Зарубежные фармкомпании заключили сделки','RU')=='Global'
    assert market_scope('Российский рынок зарубежных автомобилей','RU')=='Russia'

def test_russian_dates():
    assert parse_date('21 сентября 2026')=='2026-09-21T00:00:00+00:00'

def test_url_identity_preserves_article_id():
    assert canonical_url('https://www.infoline.spb.ru/news/?news=22&utm_source=x&ysclid=y#z')=='https://infoline.spb.ru/news?news=22'
    assert publisher('https://trends.rbc.ru/trends/foo')==publisher('https://realty.rbc.ru/news/foo')

def test_dedup_across_collectors_keeps_original_id():
    now=datetime.now(timezone.utc).isoformat()
    base={'published_at':now,'title':'Рынок вырос на 10%','categories':['Retail'],'url':'https://example.com/news/1','source_quality':4.8,'id':'original'}
    duplicate=dict(base,id='new',url=base['url']+'/?utm_source=feed',source_quality=4.2,categories=['Consumer'])
    result=deduplicate([base,duplicate])
    assert len(result)==1 and result[0]['id']=='original'
    assert result[0]['categories']==['Retail','Consumer']

def test_content_type_separates_plans_forecasts_and_reports():
    assert material_type('Компания планирует открыть 100 магазинов по данным исследования')[0]=='company_plan'
    assert material_type('Прогноз рынка на 2027 год')[0]=='forecast'
    assert material_type('Исследование потребительских расходов')[0]=='research'
    assert material_type('Ежегодный отчет: исследование рынка и прогноз')[0]=='research'
    assert material_type('По данным компании продажи выросли')[0]=='news'

def test_consumer_filter_excludes_politics():
    assert allowed({'consumer_only':True},'Индекс потребительских настроений и сбережения')
    assert allowed({'consumer_only':True},'Выбор покупателей: потребительское поведение')
    assert not allowed({'consumer_only':True},'Выборы: экономические ожидания избирателей')

def test_publication_date_and_pdf_extraction():
    soup=BeautifulSoup('<article><h1>Report</h1><time datetime="2026-09-20T12:00:00Z"></time><a href="/report.pdf">PDF</a></article>','html.parser')
    assert publication_meta(soup,'https://example.com/news')[2:] == ('2026-09-20T12:00:00+00:00',['https://example.com/report.pdf'])

def test_related_article_date_is_not_publication_date():
    soup=BeautifulSoup('<main><h1>Report</h1><div class="news-item__date">21 сентября 2026</div></main>','html.parser')
    assert publication_meta(soup,'https://example.com/news')[2] is None
