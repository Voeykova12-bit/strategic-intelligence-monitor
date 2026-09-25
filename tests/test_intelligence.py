import copy,json,sys
from pathlib import Path
from datetime import datetime,timedelta,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from intelligence import classify_editorial,same_event,event_groups,edition_for,last_due,save_due_editions,make_pulse,build_trends,METHOD

def event(id='a',date='2026-09-21T10:00:00+00:00',**kw):
    return dict(id=id,title='Маркетплейс запустил новый рекламный формат',url='https://example.com/'+id,summary='Новая медийная реклама',source='Издание',source_quality=4.5,published_at=date,categories=['MediaAdvertising'],primary_category='MediaAdvertising',market_scope='Russia',eligible=True,strategic_relevance_score=85,strategic_theme='ad_market',interpretation='Проверить формат',sources=[{'source':'Издание','url':'https://example.com/'+id}],**kw)

def test_reliability_does_not_promote_routine_or_change_relevance():
    a=event();a['title']='Регистрация на форум открыта';a['source_quality']=5
    assert not classify_editorial(a)['eligible']
    a=event();b={**a,'source_quality':1}
    assert classify_editorial(a)['strategic_relevance_score']==classify_editorial(b)['strategic_relevance_score']

def test_brand_promotion_and_invitation_are_not_market_events():
    a=event(official_brand=True);a['title']='Меняем сервисы банка вместе';a['summary']='Расскажите, что хочется изменить в сервисах банка'
    assert not classify_editorial(a)['eligible']
    a['title']='Geely запустит прямой эфир';assert not classify_editorial(a)['eligible']

def test_same_theme_is_not_event_identity_and_numbers_must_agree():
    a=event();b=event('b');b['title']='Маркетплейс снизил комиссию продавцам'
    assert not same_event(a,b)
    a['title']='Продажи косметики выросли на 42%';b['title']='Продажи косметики выросли на 15%'
    assert not same_event(a,b)

def test_cross_platform_group_preserves_old_favorite_ids_and_sources():
    a=event(event_key='launch');b=event('social',platform='telegram',event_key='launch',official_brand=True)
    g=event_groups([a,b]);assert len(g)==1;assert set(g[0]['member_ids'])=={'a','social'};assert len(g[0]['sources'])==2
    again=event_groups([b,a],g);assert again[0]['id']==g[0]['id']

def test_canonical_same_url_groups_even_if_only_one_row_is_reviewed():
    a=event(event_key='review');b=event('b');b['url']=a['url']+'?utm_source=test'
    assert same_event(a,b)

def test_wednesday_moscow_cutoff_and_sparse_window():
    assert last_due(datetime.fromisoformat('2026-09-23T05:59:00+00:00')).day==16
    now=datetime.fromisoformat('2026-09-23T06:00:00+00:00')
    rows=[event(str(i),'2026-09-22T20:59:00+00:00') for i in range(3)]
    rows+=[event('too-new','2026-09-22T21:00:00+00:00')]
    e=edition_for(rows,now);assert e['window_days']==7;assert len(e['events'])==3
    e=edition_for(rows[:1]+[event('old','2026-09-01T00:00:00+00:00')],now)
    assert e['window_days']==30;assert len(e['events'])==2
    assert edition_for([],now)['events']==[]

def test_saved_editions_are_immutable_and_missing_weeks_recovered():
    saved=[edition_for([event()],datetime.fromisoformat('2026-09-23T06:00:00+00:00'))];before=copy.deepcopy(saved)
    result=save_due_editions([],saved,datetime.fromisoformat('2026-10-09T10:00:00+00:00'))
    assert [e['id'] for e in result]==['2026-10-07','2026-09-30','2026-09-23']
    assert result[-1]==before[0];assert result[0]['late']
    assert save_due_editions([],result,datetime.fromisoformat('2026-10-09T10:00:00+00:00'))==result

def test_partial_coverage_never_pretends_market_growth_or_comparable_share():
    now=datetime.fromisoformat('2026-09-25T10:00:00+00:00')
    p=make_pulse([event()],[],now);assert not p['comparable'];assert p['weeks'][-1]['total']==1
    stable=['Издание']+[str(i) for i in range(9)]
    days=[{'date':(datetime(2026,8,26)+timedelta(days=i)).date().isoformat(),'complete':True,'sources':stable+(['Переменный'] if i%2 else []),'method_version':METHOD} for i in range(28)]
    p=make_pulse([event()],days,now);assert p['comparable'];assert p['cohort']==sorted(stable)

def test_trend_reprints_do_not_create_independent_confirmation():
    a=event();b=event('b');defs=[dict(id='t',scope='Russia',themes=['ad_market'],stage='developing',editorial_reviewed=True,evidence=[dict(url=x['url'],origin_id='same-research',supports_claim=True) for x in [a,b]])]
    t=build_trends([a,b],defs)[0];assert t['independent_count']==1;assert t['stage']=='emerging'
    assert len(t['evidence'])==2

def test_real_editorial_examples_and_official_registry():
    root=Path(__file__).resolve().parents[1]
    p=json.loads((root/'data/intelligence.json').read_text(encoding='utf-8'))
    beauty=[x for x in p['events'] if x.get('event_key')=='easycommerce-beauty-h12026'];assert len(beauty)==1;assert len(beauty[0]['sources'])>=3
    assert not any(x['eligible'] for x in p['events'] if 'Открылся' in x['title'] and 'форум' in x['title'])
    assert all(a['proof_url'].startswith('https://') for a in p['social_accounts'])
    assert len({a['url'].rstrip('/') for a in p['social_accounts']})==len(p['social_accounts'])
    assert all(x['market_scope']=='Global' for x in p['events'] if 'nielseniq.com' in x['url'])

def test_failed_social_collection_keeps_history_without_claiming_success(tmp_path,monkeypatch):
    import collect_social
    monkeypatch.setattr(collect_social,'ROOT',tmp_path);monkeypatch.delenv('VK_ACCESS_TOKEN',raising=False)
    (tmp_path/'config').mkdir();(tmp_path/'data').mkdir()
    account=dict(id='brand-tg',brand='Brand',platform='telegram',verified=True)
    (tmp_path/'config/social_accounts.json').write_text(json.dumps({'accounts':[account,{**account,'id':'brand-vk','platform':'vk'}]}))
    previous={'items':[{'id':'old','url':'https://t.me/brand/1'}],'accounts':[{**account,'last_success_at':'2026-09-20T10:00:00+00:00'}]}
    (tmp_path/'data/social.json').write_text(json.dumps(previous))
    def fail(a):raise TimeoutError('Unavailable')
    monkeypatch.setattr(collect_social,'telegram',fail);collect_social.main()
    data=json.loads((tmp_path/'data/social.json').read_text(encoding='utf-8'))
    assert data['items']==previous['items'];assert data['accounts'][0]['status']=='error'
    assert data['accounts'][0]['last_success_at']==previous['accounts'][0]['last_success_at']
    assert data['accounts'][1]['status']=='credentials_required'
