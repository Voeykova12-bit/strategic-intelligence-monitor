var DB={items:[],updated_at:null,source_count:0};var currentView="home";var currentReport="Ритейл";
var CAT={Retail:"Ритейл",DeliveryEcom:"E-commerce",BanksFintech:"Банки",FinanceEconomy:"Финансы",FMCG:"FMCG",Automotive:"Авто",RealEstate:"Недвижимость",TelecomTech:"Технологии",MediaAdvertising:"Реклама и медиа"};
var REPORTS={
"Ритейл":[
{t:"Retail Media и рекламные платформы ритейлеров",s:"AdIndex / Retail.ru",d:"актуальная аналитика",u:"https://adindex.ru/"},
{t:"Потребительское поведение и FMCG",s:"РОМИР",d:"исследования потребителей",u:"https://romir.ru/feed/analytics"},
{t:"Оборот розничной торговли",s:"Росстат",d:"официальная статистика",u:"https://rosstat.gov.ru/"}],
"Авто":[
{t:"Рынок новых легковых автомобилей",s:"АВТОСТАТ",d:"ежемесячные данные",u:"https://www.autostat.ru/press-releases/"},
{t:"Автомобильный рынок России",s:"АВТОСТАТ",d:"аналитика и пресс-релизы",u:"https://www.autostat.ru/"},
{t:"Потребительские исследования по авто",s:"РОМИР",d:"исследования",u:"https://romir.ru/feed/publications"}],
"Недвижимость":[
{t:"Ипотечное кредитование",s:"Банк России",d:"официальные данные",u:"https://www.cbr.ru/statistics/bank_sector/mortgage/"},
{t:"Рынок недвижимости",s:"РБК Недвижимость",d:"аналитика рынка",u:"https://realty.rbc.ru/"},
{t:"Строительство и жилье",s:"Росстат",d:"официальная статистика",u:"https://rosstat.gov.ru/"}],
"Банки":[
{t:"Обзор банковского сектора",s:"Банк России",d:"официальные обзоры",u:"https://www.cbr.ru/analytics/bank_sector/"},
{t:"Денежно-кредитная политика",s:"Банк России",d:"доклады и прогнозы",u:"https://www.cbr.ru/dkp/"},
{t:"Банковский рынок и продукты",s:"Банки.ру",d:"отраслевые исследования",u:"https://www.banki.ru/"}],
"Финансы":[
{t:"Макроэкономическая статистика",s:"Росстат",d:"официальные публикации",u:"https://rosstat.gov.ru/"},
{t:"Ключевая ставка и инфляция",s:"Банк России",d:"официальные данные",u:"https://www.cbr.ru/hd_base/KeyRate/"},
{t:"Экономика и рынки",s:"РБК / Коммерсантъ",d:"деловая аналитика",u:"https://www.rbc.ru/economics/"}]
};
var TREND={
ru:[
{n:"Рост retail media",k:["retail media","ритейл-медиа","рекламн платформ"],i:"▥",d:"Ритейлеры и маркетплейсы развивают собственные рекламные экосистемы; важно для медиамикса и shopper marketing."},
{n:"Развитие жестких дискаунтеров",k:["дискаунтер","чижик","низкоцен"],i:"🛒",d:"Расширение дискаунтеров усиливает ценовую конкуренцию и меняет структуру FMCG-ритейла."},
{n:"Сдвиг к ценностному потреблению",k:["экономят","ценностн","цена и качество","промо","стм"],i:"♙",d:"Покупатели внимательнее относятся к цене, промо и СТМ; это влияет на позиционирование и ценностное предложение."},
{n:"Фокус на локальных брендах",k:["российск брен","локальн брен","отечественн брен","импортозамещ"],i:"◇",d:"Локальные бренды расширяют присутствие и конкурируют за доверие, полку и медийную заметность."}],
global:[
{n:"AI в маркетинге",k:["generative ai","artificial intelligence","ai marketing","gen ai"],i:"◎",d:"Генеративный AI встраивается в креатив, аналитику, медиапланирование и персонализацию."},
{n:"Creator commerce",k:["creator commerce","creator economy","influencer commerce","social commerce"],i:"♧",d:"Контент и продажи сходятся: авторы становятся полноценным каналом commerce."},
{n:"Рост retail media networks",k:["retail media network","retail media","commerce media"],i:"⌘",d:"Ритейлеры масштабируют рекламные экосистемы и first-party data-продукты."},
{n:"Генеративная персонализация",k:["personalization","personalisation","first-party data","dynamic creative","personalized"],i:"⚙",d:"AI и собственные данные позволяют персонализировать коммуникацию и предложения в реальном времени."}]
};
function $(s){return document.querySelector(s)}function $$(s){return Array.prototype.slice.call(document.querySelectorAll(s))}
function esc(s){return (s==null?"":String(s)).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
function age(x){var t=new Date(x.published_at).getTime();return isFinite(t)?(Date.now()-t)/86400000:9999}
function fmt(d){try{return new Intl.DateTimeFormat("ru-RU",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"}).format(new Date(d))}catch(e){return""}}
function shortSource(s){s=s||"";return s.split("—")[0].trim().replace("РОМИР","Ромир").slice(0,18)}
function sourceClass(s){s=(s||"").toLowerCase();if(s.indexOf("рбк")>=0)return"rbc";if(s.indexOf("adindex")>=0)return"adindex";if(s.indexOf("sostav")>=0)return"sostav";if(s.indexOf("romir")>=0||s.indexOf("ромир")>=0)return"romir";if(s.indexOf("retail")>=0)return"retail";if(s.indexOf("росстат")>=0)return"rosstat";return""}
function importance(x){return (Number(x.score)||3)*1.25+(Number(x.source_quality)||4)*.7+Math.max(0,3-Math.min(age(x),3))*.4+((x.metrics||[]).length?.45:0)+(x.image_url?.15:0)}
function highQuality(){return (DB.items||[]).filter(function(x){return (Number(x.score)||0)>=3.8&&(Number(x.source_quality)||4)>=4.2})}
function topNews(){var list=highQuality().filter(function(x){return age(x)<=10}).sort(function(a,b){return importance(b)-importance(a)}),out=[],seen={};list.forEach(function(x){var k=shortSource(x.source);if(out.length<6&&(seen[k]||0)<1){out.push(x);seen[k]=(seen[k]||0)+1}});if(out.length<6)list.forEach(function(x){if(out.length<6&&out.indexOf(x)<0)out.push(x)});return out}
function bars(seed,red){var a=[3,4,3,5,6,5,7,8];if(seed%2)a=[2,3,4,3,5,6,7,9];return '<div class="spark '+(red?'red':'')+'">'+a.map(function(v){return'<i style="height:'+(v*3+4)+'px"></i>'}).join("")+"</div>"}
function metricPool(cat,keys){var arr=[];highQuality().filter(function(x){return age(x)<=180&&(x.categories||[]).indexOf(cat)>=0}).forEach(function(x){var txt=(x.title+" "+x.summary+" "+JSON.stringify(x.metrics||[])).toLowerCase();if(!keys.length||keys.some(function(k){return txt.indexOf(k)>=0})){(x.metrics||[]).forEach(function(m){if(m&&m.value)arr.push({x:x,m:m})})}});arr.sort(function(a,b){return new Date(b.x.published_at)-new Date(a.x.published_at)});return arr}
function firstMetric(cat,keys){var a=metricPool(cat,keys);return a[0]}
function metricData(){var defs=[
{l:"Оборот розничной торговли",c:"Retail",k:["оборот","выручк","retail"],i:"🛒"},
{l:"Продажи автомобилей",c:"Automotive",k:["продаж","рынок"],i:"▣"},
{l:"Ипотечные кредиты",c:"RealEstate",k:["ипотек","кредит"],i:"⌂"},
{l:"Ключевая ставка ЦБ",c:"FinanceEconomy",k:["ключев","ставк"],i:"%"},
{l:"Digital / рекламный рынок",c:"MediaAdvertising",k:["реклам","digital","медиа"],i:"▤"}];
return defs.map(function(d,idx){var r=firstMetric(d.c,d.k);if(!r&&d.l.indexOf("Ипотеч")===0)r=firstMetric("BanksFintech",["ипотек","кредит"]);return{l:d.l,i:d.i,v:r?r.m.value:"—",n:r?shortSource(r.x.source)+" · "+fmt(r.x.published_at):"нет свежей подтвержденной цифры",red:idx===2}})}
function renderMetrics(){$("#metricGrid").innerHTML=metricData().map(function(m,i){return'<div class="metric"><div class="metricIcon">'+m.i+'</div><div><div class="metricLabel">'+esc(m.l)+'</div><div class="metricValue">'+esc(m.v)+'</div><div class="metricNote">'+esc(m.n)+'</div></div>'+bars(i,m.red)+'</div>'}).join("")}
function starIds(){try{return JSON.parse(localStorage.getItem("sr_favorites")||"[]")}catch(e){return[]}}function saveStars(v){localStorage.setItem("sr_favorites",JSON.stringify(v))}
function card(x){var im=x.image_url?'<img src="'+esc(x.image_url)+'" loading="lazy" alt="" onerror="this.remove()">':"";var why=(x.why_it_matters||x.summary||"Важный сигнал для понимания рынка и конкурентного контекста.");return'<article class="newsCard"><div class="sourceLine"><span class="source '+sourceClass(x.source)+'">'+esc(shortSource(x.source))+'</span><span class="time">'+fmt(x.published_at)+'</span></div><div class="thumb">'+im+'</div><h3>'+esc(x.title||"Без заголовка")+'</h3><div class="meaningLabel">Что это значит:</div><div class="meaning">'+esc(why.slice(0,160))+(why.length>160?"…":"")+'</div><button class="star '+(starIds().indexOf(x.id)>=0?"on":"")+'" data-star="'+esc(x.id)+'">'+(starIds().indexOf(x.id)>=0?"★":"☆")+'</button><a class="openCard" href="'+esc(x.url)+'" target="_blank" rel="noopener">Открыть</a></article>'}
function bindStars(){$$("[data-star]").forEach(function(b){b.onclick=function(e){e.preventDefault();e.stopPropagation();var id=b.getAttribute("data-star"),f=starIds();f=f.indexOf(id)>=0?f.filter(function(x){return x!==id}):f.concat([id]);saveStars(f);renderTop();renderFavorites()}})}
function renderTop(){$("#topNews").innerHTML=topNews().map(card).join("")||'<div class="empty">Нет свежих материалов, отвечающих фильтру качества.</div>';bindStars()}
function trendEvidence(def,scope){var items=highQuality().filter(function(x){return age(x)<=90&&(scope==="Global"?x.market_scope==="Global":x.market_scope!=="Global")});var hits=items.filter(function(x){var t=(x.title+" "+x.summary+" "+(x.topics||[]).join(" ")).toLowerCase();return def.k.some(function(k){return t.indexOf(k)>=0})});var src=[];hits.forEach(function(x){var s=shortSource(x.source);if(src.indexOf(s)<0)src.push(s)});return{hits:hits,src:src}}
function trendRows(scope){var defs=scope==="Global"?TREND.global:TREND.ru;return defs.map(function(d){var e=trendEvidence(d,scope),trusted=e.src.length>=2||e.hits.some(function(x){return(Number(x.source_quality)||0)>=4.8}),label=trusted?"Подтверждено: "+Math.max(e.src.length,1)+" источник"+(e.src.length===1?"":"а"):"Недостаточно подтверждений";return'<div class="trendRow"><div class="trendIco">'+d.i+'</div><div><div class="trendName">'+esc(d.n)+'</div><div class="evidence">'+esc(label)+'</div></div><div class="trendDesc">'+esc(d.d)+'</div><div class="chev">›</div></div>'}).join("")}
function renderTrends(){["#ruTrends","#ruTrendsFull"].forEach(function(s){$(s).innerHTML=trendRows("Russia")});["#globalTrends","#globalTrendsFull"].forEach(function(s){$(s).innerHTML=trendRows("Global")})}
function reportTabs(){var t=Object.keys(REPORTS),html=t.map(function(x){return'<button class="'+(x===currentReport?"active":"")+'" data-report="'+x+'">'+x+"</button>"}).join("");$("#previewTabs").innerHTML=html;$("#reportTabs").innerHTML=html;$$("[data-report]").forEach(function(b){b.onclick=function(){currentReport=b.getAttribute("data-report");renderReports()}})}
function reportCard(r,big){if(big)return'<a class="reportBig" href="'+esc(r.u)+'" target="_blank" rel="noopener"><div class="pdf">PDF</div><div><h3>'+esc(r.t)+'</h3><p>'+esc(r.s)+" · "+esc(r.d)+'</p><small>Открыть исследование / источник ↗</small></div></a>';return'<a class="reportCard" href="'+esc(r.u)+'" target="_blank" rel="noopener"><div class="pdf">PDF</div><div><strong>'+esc(r.t)+'</strong><small>'+esc(r.s)+" · "+esc(r.d)+'</small></div><div class="downIcon">↓</div></a>'}
function renderReports(){reportTabs();$("#previewReports").innerHTML=REPORTS[currentReport].map(function(r){return reportCard(r,false)}).join("");$("#reportLibrary").innerHTML=REPORTS[currentReport].map(function(r){return reportCard(r,true)}).join("")}
function filteredNews(){var q=($("#search").value||"").trim().toLowerCase(),cat=$("#newsCategory")?$("#newsCategory").value:"",days=Number($("#newsPeriod")?$("#newsPeriod").value:30);return highQuality().filter(function(x){var txt=(x.title+" "+x.summary+" "+x.source+" "+(x.topics||[]).join(" ")).toLowerCase();return age(x)<=days&&(!cat||(x.categories||[]).indexOf(cat)>=0)&&(!q||txt.indexOf(q)>=0)}).sort(function(a,b){return importance(b)-importance(a)})}
function article(x){return'<a class="article" href="'+esc(x.url)+'" target="_blank" rel="noopener"><div class="articleCat">'+esc(CAT[x.primary_category]||x.primary_category||"Рынок")+'</div><div><h3>'+esc(x.title)+'</h3><p>'+esc((x.why_it_matters||x.summary||"").slice(0,230))+'</p></div><div class="articleMeta">'+esc(shortSource(x.source))+"<br>"+fmt(x.published_at)+"<br>score "+(Number(x.score)||0).toFixed(1)+"</div></a>"}
function renderNews(){var a=filteredNews();$("#newsList").innerHTML=a.slice(0,120).map(article).join("")||'<div class="empty">Нет материалов по выбранным фильтрам.</div>'}
function renderMarkets(){var keys=Object.keys(CAT);$("#marketGrid").innerHTML=keys.map(function(c){var a=highQuality().filter(function(x){return(x.categories||[]).indexOf(c)>=0&&age(x)<=30});return'<div class="marketCard"><h3>'+esc(CAT[c])+'</h3><p>Качественных материалов за 30 дней</p><div class="count">'+a.length+'</div><p>'+(a[0]?esc(a[0].title.slice(0,110)):"Нет свежих значимых сигналов")+"</p></div>"}).join("")}
function renderFavorites(){var ids=starIds(),a=(DB.items||[]).filter(function(x){return ids.indexOf(x.id)>=0});$("#favoritesList").innerHTML=a.length?a.map(article).join(""):'<div class="empty">Здесь будут материалы, которые вы отметите звездочкой.</div>'}
function fillCats(){var c=[];(DB.items||[]).forEach(function(x){(x.categories||[]).forEach(function(z){if(c.indexOf(z)<0)c.push(z)})});c.sort();$("#newsCategory").innerHTML='<option value="">Все рынки</option>'+c.map(function(x){return'<option value="'+esc(x)+'">'+esc(CAT[x]||x)+"</option>"}).join("")}
function setView(v){currentView=v;$$(".view").forEach(function(x){x.classList.remove("active")});$("#view-"+v).classList.add("active");$$("#nav button").forEach(function(x){x.classList.toggle("active",x.getAttribute("data-view")===v)});var t={home:["Панель мониторинга рынков","Актуальные новости, тренды и исследования для стратегических решений"],news:["Новости","Только значимые материалы из проверенных источников"],trends:["Тренды","Сигналы, подтвержденные качественными источниками"],markets:["Рынки","Быстрый обзор активности по ключевым категориям"],reports:["Отчеты","Исследования и отраслевые материалы по рынкам"],favorites:["Избранное","Сохраненные материалы для дальнейшей работы"]};$("#pageTitle").textContent=t[v][0];$("#pageSubtitle").textContent=t[v][1];if(v==="news")renderNews();if(v==="markets")renderMarkets();if(v==="favorites")renderFavorites();window.scrollTo({top:0,behavior:"smooth"})}
$$("#nav button").forEach(function(b){b.onclick=function(){setView(b.getAttribute("data-view"))}});$$("[data-go]").forEach(function(b){b.onclick=function(){setView(b.getAttribute("data-go"))}});
$("#search").addEventListener("input",function(){if(currentView!=="news"&&$("#search").value.trim())setView("news");else if(currentView==="news")renderNews()});$("#newsCategory").addEventListener("change",renderNews);$("#newsPeriod").addEventListener("change",renderNews);
async function load(){try{var r=await fetch("data/news.json?ts="+Date.now(),{cache:"no-store"});if(!r.ok)throw new Error("HTTP "+r.status);DB=await r.json();var u=DB.updated_at||DB.generated_at||DB.last_updated;$("#fresh").textContent=u?"Обновлено "+fmt(u)+" · "+(DB.source_count||new Set(DB.items.map(function(x){return x.source})).size)+" источников":"Загружено "+DB.items.length+" материалов";fillCats();renderMetrics();renderTop();renderTrends();renderReports();renderNews();renderMarkets();renderFavorites()}catch(e){$("#fresh").textContent="Не удалось загрузить данные";DB={items:[]};renderMetrics();renderTop();renderTrends();renderReports();renderNews();renderMarkets();renderFavorites()}}
load();