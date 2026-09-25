const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const root=path.join(__dirname,'..');
function app({fail=false,invalid=false}={}){
 const elements=new Map(),storage=new Map(),handlers={};
 function element(id){if(!elements.has(id))elements.set(id,{value:'',innerHTML:'',textContent:'',hidden:true,dataset:{},classList:{add(){},remove(){},toggle(){}},setAttribute(){},querySelectorAll:()=>[],addEventListener(){},showModal(){this.open=true},close(){this.open=false}});return elements.get(id)}
 const fixture={};for(const name of ['news','reports','metrics','intelligence'])fixture[name]=JSON.parse(fs.readFileSync(path.join(root,'docs/data',name+'.json')));
 const ctx={console,Date,Intl,Set,Number,JSON,Math,Array,String,isFinite,AbortController,setTimeout,clearTimeout,
  localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
  document:{querySelector:element,querySelectorAll:()=>[],addEventListener:(name,fn)=>handlers[name]=fn},
  window:{STRATEGY_RADAR_FALLBACK:fixture,scrollTo(){},scrollY:0,location:{hash:'#home'},history:{replaceState(){}},addEventListener(){}},
  fetch:async url=>{if(fail)throw Error('offline');return{ok:true,json:async()=>invalid?{items:'broken'}:fixture[url.split('/')[1].split('.')[0]]}}
 };vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(root,'docs/radar.js'),'utf8').replace(/load\(\);\s*$/,''),ctx);
 return{ctx,element,fixture,handlers};
}
test('offline and malformed responses retain all four datasets and show snapshot date',async()=>{
 for(const options of [{fail:true},{invalid:true}]){const {ctx,element}=app(options);await ctx.load();assert(ctx.usingFallback);assert(ctx.INTEL.events.length>0);assert(ctx.INTEL.editions.length>0);assert(ctx.REPORTDB.reports.length>0);assert.equal(element('#offlineBanner').hidden,false);assert.equal((element('#metricGrid').innerHTML.match(/class="metric/g)||[]).length,12)}
});
test('current-year news are Russia only, search combines with categories, newest date first',async()=>{
 const {ctx,element}=app();await ctx.load();ctx.newsMode='year';let rows=ctx.filteredNews();assert(rows.length);assert(rows.every(x=>x.market_scope==='Russia'&&ctx.localYear(x.published_at)===ctx.localYear(Date.now())));
 assert(rows.every((x,i)=>i===0||new Date(rows[i-1].published_at)>=new Date(x.published_at)));
 const example=rows[0];ctx.newsCategory=example.categories[0];element('#search').value=example.title;rows=ctx.filteredNews();assert(rows.some(x=>x.id===example.id));assert(rows.every(x=>x.categories.includes(ctx.newsCategory)));
 element('#search').value='NO_SUCH_NEWS_987';assert.equal(ctx.filteredNews().length,0);ctx.renderNews();assert(element('#newsList').innerHTML.includes('empty'));
});
test('weekly edition and yearly feed do not overwrite each other',async()=>{
 const {ctx}=app();await ctx.load();const edition=JSON.stringify(ctx.currentEdition());ctx.newsMode='year';ctx.filteredNews();ctx.newsCategory='Retail';ctx.newsMode='edition';ctx.filteredNews();assert.equal(JSON.stringify(ctx.currentEdition()),edition);
});
test('legacy bookmark survives regrouping, reload and removal',async()=>{
 const {ctx,handlers}=app();await ctx.load();const x=ctx.INTEL.events.find(x=>x.member_ids.length>1);assert(x);ctx.saveStars([x.member_ids[0]]);assert(ctx.saved(x));await ctx.load();assert(ctx.saved(ctx.getEvent(x.member_ids[0])));
 handlers.click({target:{closest:()=>({dataset:{star:x.id}})}});assert.equal(ctx.starIds().length,0);
});
test('VK is not populated with Telegram results; video links and missing durations stay truthful',async()=>{
 const {ctx,element}=app();await ctx.load();ctx.socialPlatform='vk';assert(ctx.socialEvents().every(x=>x.platforms.includes('vk')));ctx.renderSocial();
 if(!ctx.socialEvents().length)assert(element('#socialFeature').innerHTML.includes('Сбор ВК еще не подключен'));
 ctx.socialPlatform='telegram';assert(ctx.socialEvents().length);assert(ctx.videos().every(v=>v.url.startsWith('https://')));
 const v=ctx.videos().find(v=>!v.duration);if(v)assert(!ctx.videoTile(v).includes('undefined'));
});
test('every report remains accessible with the original destination',async()=>{
 const {ctx}=app();await ctx.load();for(const r of ctx.REPORTDB.reports){assert(ctx.reportCard(r).includes(ctx.url(r.kind==='local_pdf'?r.local_path||r.url:r.url)))}
 assert.equal(ctx.REPORTDB.reports.length,JSON.parse(fs.readFileSync(path.join(root,'data/reports.json'))).reports.length);
});
test('world trends and unknown favorites have explicit states; HTML content is escaped',async()=>{
 const {ctx,element}=app();await ctx.load();ctx.trendScope='Global';ctx.renderTrends();assert(element('#trendCards').innerHTML.includes('trendCard'));ctx.saveStars(['legacy-unavailable']);ctx.renderFavorites();assert(element('#favoritesList').innerHTML.includes('Закладка сохранена'));
 assert.equal(ctx.url('javascript:alert(1)'),'#');assert.equal(ctx.esc('<img onerror="bad">'),'&lt;img onerror=&quot;bad&quot;&gt;');
});
