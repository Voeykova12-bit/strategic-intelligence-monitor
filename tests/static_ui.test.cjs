const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const root=path.join(__dirname,'..');
function app({fail=false,invalid=false}={}){
 const elements=new Map(),storage=new Map();
 function element(id){if(!elements.has(id))elements.set(id,{value:'',innerHTML:'',textContent:'',hidden:true,classList:{add(){},remove(){},toggle(){}},addEventListener(){}});return elements.get(id)}
 for(const id of ['#newsPeriod','#globalPeriod'])element(id).value='365';
 element('#newsSort').value='relevance';element('#newsPeriod option:checked').textContent='12 месяцев';
 const fixture={news:JSON.parse(fs.readFileSync(path.join(root,'docs/data/news.json'))),reports:JSON.parse(fs.readFileSync(path.join(root,'docs/data/reports.json'))),metrics:JSON.parse(fs.readFileSync(path.join(root,'docs/data/metrics.json')))};
 const ctx={console,Date,Intl,Set,Number,JSON,Math,Array,String,isFinite,AbortController,setTimeout,clearTimeout,
  localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
  document:{querySelector:element,querySelectorAll:()=>[]},
  window:{STRATEGY_RADAR_FALLBACK:fixture,scrollTo(){}},
  fetch:async url=>{if(fail)throw Error('offline');return{ok:true,json:async()=>invalid?{items:'broken'}:fixture[url.split('/')[1].split('.')[0]]}}
 };
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(root,'docs/app.js'),'utf8').replace(/load\(\);\s*$/,''),ctx);
 return{ctx,element,fixture};
}
test('offline and malformed responses show complete last-known-good data',async()=>{
 for(const options of [{fail:true},{invalid:true}]){
  const {ctx,element}=app(options);await ctx.load();
  assert(ctx.usingFallback);assert(ctx.DB.items.length>0);assert(ctx.REPORTDB.reports.length>0);assert(ctx.METRICDB.metrics.length>0);
  assert.equal(element('#offlineBanner').hidden,false);assert(element('#metricGrid').innerHTML.includes('metricValue'));
 }
});
test('combined category, source, geography and outlook filters',async()=>{
 const {ctx,element}=app();await ctx.load();
 const example=ctx.highQuality().find(x=>x.future_signal);
 assert(example);
 element('#newsCategory').value=example.categories[0];element('#newsSource').value=example.source;element('#newsScope').value=example.market_scope;element('#newsType').value='outlook';
 const result=ctx.filteredNews();assert(result.some(x=>x.id===example.id));assert(result.every(x=>x.future_signal&&x.source===example.source&&x.categories.includes(example.categories[0])));
 element('#search').value='NONEXISTENT_123456';assert.equal(ctx.filteredNews().length,0);
});
test('favorites persist using existing IDs',async()=>{
 const {ctx}=app();await ctx.load();const id=ctx.DB.items[0].id;ctx.saveStars([id]);assert.equal(ctx.starIds()[0],id);ctx.saveStars([]);assert.equal(ctx.starIds().length,0);
});
test('one publisher with two feed labels is not independent trend confirmation',()=>{
 const {ctx}=app();const base={title:'unique-topic',summary:'',topics:[],score:4,source_quality:4.5,market_scope:'Russia',published_at:new Date().toISOString(),publisher_id:'rbc.ru'};
 ctx.DB.items=[{...base,source:'РБК Тренды'},{...base,source:'РБК Недвижимость'}];
 assert.equal(ctx.trendEvidence({k:['unique-topic']},'Russia').confirmed,false);
});
