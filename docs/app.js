var DB={items:[],updated_at:null,source_count:0},REPORTDB={reports:[],updated_at:null},METRICDB={metrics:[],updated_at:null};
var currentView="home",currentReport="Ритейл",currentMarket="Retail",lang=localStorage.getItem("sr_lang")||"ru",usingFallback=false;

var CAT={
  Retail:"Ритейл",DeliveryEcom:"E-commerce / Delivery",MediaAdvertising:"Advertising & Media",FMCG:"FMCG",
  BanksFintech:"Banks",FinanceEconomy:"Finance / Economy",Automotive:"Automotive",RealEstate:"Real Estate",
  TechnologyAI:"Technology / AI",Telecom:"Telecom",Consumer:"Consumer",
  TelecomTech:"Technology / Telecom"
};
var MARKET_ORDER=["Retail","DeliveryEcom","MediaAdvertising","FMCG","BanksFintech","FinanceEconomy","Automotive","RealEstate","TechnologyAI","Telecom","Consumer"];
var MARKET_ICON={Retail:"🛒",DeliveryEcom:"◫",MediaAdvertising:"◉",FMCG:"◇",BanksFintech:"▦",FinanceEconomy:"₽",Automotive:"▣",RealEstate:"⌂",TechnologyAI:"◎",Telecom:"◌",Consumer:"♙"};

var TXT={
ru:{navHome:"Главная",navNews:"Новости",navTrends:"Тренды",navMarkets:"Рынки",navReports:"Отчеты",navFav:"Избранное",
homeTitle:"Панель мониторинга рынков",homeSub:"Актуальные новости, тренды и исследования для стратегических решений",
newsTitle:"Новости",newsSub:"Только значимые материалы из проверенных источников",
trendsTitle:"Тренды",trendsSub:"Сигналы рынка, подтвержденные данными и качественными источниками",
marketsTitle:"Рынки",marketsSub:"Новости, цифры, тренды, прогнозы и исследования по каждой категории",
reportsTitle:"Отчеты",reportsSub:"Конкретные исследования и отраслевые материалы 2025–2026",
favTitle:"Избранное",favSub:"Сохраненные материалы для дальнейшей работы"},
en:{navHome:"Home",navNews:"News",navTrends:"Trends",navMarkets:"Markets",navReports:"Reports",navFav:"Saved",
homeTitle:"Market Intelligence Dashboard",homeSub:"Current news, trends and research for strategic decisions",
newsTitle:"News",newsSub:"Only material signals from trusted sources",
trendsTitle:"Trends",trendsSub:"Market signals supported by data and credible sources",
marketsTitle:"Markets",marketsSub:"News, figures, trends, outlooks and research by category",
reportsTitle:"Reports",reportsSub:"Specific research and industry reports for 2025–2026",
favTitle:"Saved",favSub:"Saved materials for later work"}
};

var FALLBACK_BUNDLE=window.STRATEGY_RADAR_FALLBACK||{news:{items:[]},reports:{reports:[]},metrics:{metrics:[]}};
var TREND={
ru:[
{n:"Рост retail media",k:["retail media","ритейл-медиа","retail-media"],i:"▥",d:"Ритейлеры и маркетплейсы превращают собственные данные и инвентарь в самостоятельный рекламный канал.",why:"Меняет медиамикс FMCG и retail-брендов и усиливает связку медиа с продажами."},
{n:"Развитие жестких дискаунтеров",k:["дискаунтер","чижик","жестк"],i:"🛒",d:"Дискаунтеры продолжают расширять географию и усиливать конкуренцию в массовом сегменте.",why:"Повышает роль цены, СТМ и простого value proposition."},
{n:"Сдвиг к ценностному потреблению",k:["ценностн","экономят","цена и качество","промо","стм","потребительск стратег"],i:"♙",d:"Покупатели внимательнее сопоставляют цену, качество и необходимость покупки.",why:"Требует более доказательной коммуникации ценности и промо-механик."},
{n:"AI и агентная коммерция",k:["агентн коммерц","ии-агент","ai-агент","искусственн интеллект","нейросет"],i:"◎",d:"AI начинает участвовать не только в поиске, но и в выборе и покупке товаров.",why:"Бренду важно быть понятным не только человеку, но и рекомендательным AI-системам."},
{n:"Замедление роста eCommerce при росте масштаба",k:["ecommerce","e-commerce","интернет-торгов","онлайн-торгов"],i:"◫",d:"Онлайн-рынок продолжает расти, но переходит к более зрелой динамике.",why:"Фокус смещается с простого захвата роста на эффективность, удержание и экономику заказа."},
{n:"Локализация автомобильного рынка",k:["локальн сбор","локализац","собранн в рф"],i:"▣",d:"Доля локально собранных автомобилей в продажах растет.",why:"Меняется конкурентный набор брендов и аргументация вокруг доступности, сервиса и происхождения."}
],
global:[
{n:"AI становится каналом product discovery",k:["ai for product discovery","ai product discovery","artificial intelligence","generative ai","ai-powered"],i:"◎",d:"Покупатели все чаще используют AI для исследования и выбора товаров.",why:"Видимость бренда в AI-ответах становится новой частью digital shelf и upper funnel."},
{n:"Retail media становится глобальной инфраструктурой",k:["retail media","commerce media","retail media network"],i:"▥",d:"Ритейлеры масштабируют рекламные сети на базе first-party данных.",why:"Бюджеты смещаются ближе к транзакции, а измеримость становится ключевым преимуществом."},
{n:"Social и creator commerce сближают контент и покупку",k:["creator commerce","social commerce","creator economy","influencer"],i:"♧",d:"Контентные платформы и авторы все чаще становятся полноценным каналом продаж.",why:"Коммуникация, consideration и конверсия все чаще происходят в одной среде."},
{n:"Персонализация переходит к AI-оркестрации",k:["personalization","personalisation","dynamic creative","first-party data"],i:"⚙",d:"AI и собственные данные ускоряют персонализацию предложений и контента.",why:"Стратегия CRM и media должна учитывать real-time сигналы и качество собственных данных."}
]};

function $(s){return document.querySelector(s)}function $$(s){return Array.prototype.slice.call(document.querySelectorAll(s))}
function esc(s){return(s==null?"":String(s)).replace(/[&<>"']/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
function t(k){return TXT[lang][k]||TXT.ru[k]||k}
function age(x){var ms=new Date(x.published_at).getTime();return isFinite(ms)?Math.max(0,(Date.now()-ms)/86400000):9999}
function fmt(d,onlyDate){try{return new Intl.DateTimeFormat(lang==="en"?"en-GB":"ru-RU",onlyDate?{day:"2-digit",month:"short",year:"numeric"}:{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"}).format(new Date(d))}catch(e){return""}}
function shortSource(s){s=s||"";return s.split("—")[0].trim().replace("РОМИР","Ромир").slice(0,24)}
function sourceClass(s){s=(s||"").toLowerCase();if(s.indexOf("рбк")>=0)return"rbc";if(s.indexOf("adindex")>=0)return"adindex";if(s.indexOf("sostav")>=0)return"sostav";if(s.indexOf("romir")>=0||s.indexOf("ромир")>=0)return"romir";if(s.indexOf("retail")>=0)return"retail";if(s.indexOf("росстат")>=0)return"rosstat";return""}
function strategicScore(x){return Number(x.strategic_relevance_score)||Math.round((Number(x.score)||0)*20)}
function importance(x){return strategicScore(x)+Math.min(8,(Number(x.source_quality)||4)*1.5)+Math.max(0,8-Math.min(age(x),8))+(x.metrics||[]).length*1.5+(x.future_signal?1:0)}
function highQuality(){return(DB.items||[]).filter(function(x){return strategicScore(x)>=70&&(Number(x.source_quality)||4)>=4.1&&age(x)<=365})}
function uniqSources(items,max){var out=[],seen={};items.forEach(function(x){var k=shortSource(x.source);if(out.length<(max||items.length)&&(seen[k]||0)<1){out.push(x);seen[k]=1}});return out}
function topNews(){
 var all=highQuality().sort(function(a,b){return importance(b)-importance(a)}),wins=[1,3,7,30],chosen=[];
 for(var w of wins){chosen=uniqSources(all.filter(function(x){return age(x)<=w}),6);if(chosen.length>=6){$("#topWindowLabel").textContent=w===1?"Значимое за последние 24 часа":"Свежие значимые события за "+w+" дней";return chosen.slice(0,6)}}
 chosen=uniqSources(all,6);$("#topWindowLabel").textContent="Последние доступные значимые события";return chosen.slice(0,6)
}
function starIds(){try{return JSON.parse(localStorage.getItem("sr_favorites")||"[]")}catch(e){return[]}}
function saveStars(v){localStorage.setItem("sr_favorites",JSON.stringify(v))}
function typeLabel(x){var m={news:"Новость",research:"Исследование",forecast:"Прогноз",company_plan:"План компании"};return m[x.content_type]||"Материал"}
function card(x){
 var im=x.image_url?'<img src="'+esc(x.image_url)+'" loading="lazy" alt="" onerror="this.remove()">':'<div class="thumbLetter">'+esc((CAT[x.primary_category]||"SR").slice(0,2).toUpperCase())+'</div>';
 var why=(x.why_it_matters||x.summary||"Важный сигнал для понимания рынка и конкурентного контекста.");
 return'<article class="newsCard"><div class="sourceLine"><span class="source '+sourceClass(x.source)+'">'+esc(shortSource(x.source))+'</span><span class="time">'+fmt(x.published_at)+'</span></div><div class="thumb">'+im+'</div><div class="cardTags"><span>'+esc(typeLabel(x))+'</span><span>SR '+strategicScore(x)+'</span></div><h3>'+esc(x.title||"Без заголовка")+'</h3><div class="meaningLabel">Что это значит:</div><div class="meaning">'+esc(why.slice(0,170))+(why.length>170?"…":"")+'</div><button class="star '+(starIds().indexOf(x.id)>=0?"on":"")+'" data-star="'+esc(x.id)+'">'+(starIds().indexOf(x.id)>=0?"★":"☆")+'</button><a class="openCard" href="'+esc(x.url)+'" target="_blank" rel="noopener">Открыть</a></article>'
}
function bindStars(){$$("[data-star]").forEach(function(b){b.onclick=function(e){e.preventDefault();e.stopPropagation();var id=b.getAttribute("data-star"),f=starIds();f=f.indexOf(id)>=0?f.filter(function(x){return x!==id}):f.concat([id]);saveStars(f);renderTop();renderFavorites()}})}
function renderTop(){$("#topNews").innerHTML=topNews().map(card).join("")||'<div class="empty">Свежие значимые материалы временно не найдены.</div>';bindStars()}

function spark(history){
 if(!history||history.length<2)return"";
 var vals=history.map(function(x){return Number(x.value)}).filter(isFinite);if(vals.length<2)return"";
 var min=Math.min.apply(null,vals),max=Math.max.apply(null,vals),range=max-min||1;
 return'<div class="miniSpark">'+vals.map(function(v){var h=7+Math.round((v-min)/range*25);return'<i style="height:'+h+'px"></i>'}).join("")+'</div>'
}
function renderMetrics(){
 var rows=(METRICDB.metrics||[]).filter(function(m){return m&&m.value&&m.value!=="—"}).slice(0,6);
 $("#metricGrid").innerHTML=rows.map(function(m){
   return'<a class="metric" href="'+esc(m.source_url||"#")+'" target="_blank" rel="noopener"><div class="metricIcon">'+(m.id==="key-rate"?"%":m.id==="inflation"?"↗":m.id==="auto-sales"?"▣":m.id==="mortgage"?"⌂":m.id==="ecommerce"?"◫":"▤")+'</div><div><div class="metricLabel">'+esc(m.label)+'</div><div class="metricValue">'+esc(m.value)+'</div><div class="metricNote">'+esc((m.change?m.change+" · ":"")+m.period+" · "+m.source)+'</div></div>'+spark(m.history)+'</a>'
 }).join("")||'<div class="empty">Нет подтвержденных ключевых показателей.</div>'
}

function trendEvidence(def,scope){
 var items=highQuality().filter(function(x){return age(x)<=365&&(scope==="Global"?x.market_scope==="Global":x.market_scope!=="Global")});
 var hits=items.filter(function(x){var txt=(x.title+" "+x.summary+" "+(x.topics||[]).join(" ")).toLowerCase();return def.k.some(function(k){return txt.indexOf(k)>=0})}).sort(function(a,b){return importance(b)-importance(a)});
 var sources=[];hits.forEach(function(x){var s=shortSource(x.source);if(sources.indexOf(s)<0)sources.push(s)});
 var official=hits.some(function(x){return(Number(x.source_quality)||0)>=4.8&&((x.metrics||[]).length>0||x.content_type==="research")});
 return{hits:hits,sources:sources,confirmed:sources.length>=2||official}
}
function confirmedTrends(scope){
 var defs=scope==="Global"?TREND.global:TREND.ru,out=[];
 defs.forEach(function(d){var e=trendEvidence(d,scope);if(e.confirmed)out.push({d:d,e:e})});
 return out.slice(0,4)
}
function trendRow(obj){
 var d=obj.d,e=obj.e,links=e.hits.slice(0,4).map(function(x){return'<a href="'+esc(x.url)+'" target="_blank" rel="noopener">'+esc(shortSource(x.source))+'</a>'}).join(" · ");
 return'<div class="trendRow"><div class="trendIco">'+d.i+'</div><div class="trendCore"><div class="trendName">'+esc(d.n)+'</div><div class="trendDesc">'+esc(d.d)+'</div><div class="trendWhy"><b>Почему важно:</b> '+esc(d.why)+'</div><div class="evidence"><b>Основано на:</b> '+links+'</div></div></div>'
}
function renderTrends(){
 var ru=confirmedTrends("Russia"),gl=confirmedTrends("Global");
 ["#ruTrends","#ruTrendsFull"].forEach(function(s){$(s).innerHTML=ru.map(trendRow).join("")||'<div class="empty small">Пока нет тренда, прошедшего порог подтверждения.</div>'});
 ["#globalTrends","#globalTrendsFull"].forEach(function(s){$(s).innerHTML=gl.map(trendRow).join("")||'<div class="empty small">Пока нет тренда, прошедшего порог подтверждения.</div>'})
}

function outlookItems(){
 return highQuality().filter(function(x){return x.future_signal||x.content_type==="forecast"||x.content_type==="company_plan"||(x.future_horizon||[]).length}).sort(function(a,b){return importance(b)-importance(a)}).slice(0,5)
}
function renderOutlook(){
 var rows=outlookItems();
 $("#outlookGrid").innerHTML=rows.map(function(x){
   var horizon=(x.future_horizon||[]).filter(function(v){return v!=="future"}).join(", ");
   return'<a class="outlookCard" href="'+esc(x.url)+'" target="_blank" rel="noopener"><div class="outlookTop"><span class="outlookType">'+esc(typeLabel(x))+'</span><span>'+esc(shortSource(x.source))+'</span></div><h3>'+esc(x.title)+'</h3><p>'+esc((x.summary||x.why_it_matters||"").slice(0,180))+'</p><small>'+(horizon?"Горизонт: "+esc(horizon)+" · ":"")+fmt(x.published_at,true)+'</small></a>'
 }).join("")||'<div class="empty">Нет подтвержденных прогнозов и планов.</div>'
}
$("#outlookAll").onclick=function(){setView("news");$("#newsType").value="forecast";renderNews()};

function reportTabs(){
 var cats=(REPORTDB.categories&&REPORTDB.categories.length?REPORTDB.categories:["Ритейл","Авто","Недвижимость","Банки","Финансы"]);
 if(cats.indexOf(currentReport)<0)currentReport=cats[0];
 var html=cats.map(function(x){return'<button class="'+(x===currentReport?"active":"")+'" data-report="'+esc(x)+'">'+esc(x)+'</button>'}).join("");
 $("#previewTabs").innerHTML=html;$("#reportTabs").innerHTML=html;
 $$("[data-report]").forEach(function(b){b.onclick=function(){currentReport=b.getAttribute("data-report");renderReports()}})
}
function reportBadge(r){if(r.kind==="local_pdf")return"PDF внутри Strategy Radar";if(r.kind==="external_pdf")return"Внешний PDF ↗";if(r.kind==="paid_report")return"Платный отчет ↗";return"Внешний отчет ↗"}
function reportCard(r,big){
 var badge=reportBadge(r),ico=(r.kind==="external_pdf"||r.kind==="local_pdf")?"PDF":r.kind==="paid_report"?"PRO":"DOC",href=r.kind==="local_pdf"?(r.local_path||r.url):r.url;
 if(big)return'<a class="reportBig" href="'+esc(href)+'" target="_blank" rel="noopener"><div class="pdf '+(r.kind==="paid_report"?"paid":"")+'">'+ico+'</div><div><div class="reportMeta">'+esc(r.organization||"")+" · "+fmt(r.date,true)+'</div><h3>'+esc(r.title)+'</h3><p>'+esc(r.description||"")+'</p><span class="reportBadge">'+esc(badge)+'</span></div></a>';
 return'<a class="reportCard" href="'+esc(href)+'" target="_blank" rel="noopener"><div class="pdf '+(r.kind==="paid_report"?"paid":"")+'">'+ico+'</div><div><strong>'+esc(r.title)+'</strong><small>'+esc(r.organization||"")+" · "+fmt(r.date,true)+'</small><span class="reportBadge">'+esc(badge)+'</span></div></a>'
}
function renderReports(){
 reportTabs();
 var all=(REPORTDB.reports||[]).filter(function(r){return r.category===currentReport}).sort(function(a,b){return String(b.date).localeCompare(String(a.date))});
 $("#previewReports").innerHTML=all.slice(0,5).map(function(r){return reportCard(r,false)}).join("")||'<div class="empty">Нет отчетов в этой категории.</div>';
 $("#reportLibrary").innerHTML=all.map(function(r){return reportCard(r,true)}).join("")||'<div class="empty">Нет отчетов в этой категории.</div>';
 $("#reportStatus").textContent=(REPORTDB.report_count||REPORTDB.reports.length)+" конкретных исследований · проверка "+fmt(REPORTDB.updated_at||new Date(),true)
}

function fillFilters(){
 var cats=[],sources=[];(DB.items||[]).forEach(function(x){(x.categories||[]).forEach(function(c){if(cats.indexOf(c)<0)cats.push(c)});if(x.source&&sources.indexOf(x.source)<0)sources.push(x.source)});
 cats.sort();sources.sort();
 $("#newsCategory").innerHTML='<option value="">Все рынки</option>'+cats.map(function(c){return'<option value="'+esc(c)+'">'+esc(CAT[c]||c)+'</option>'}).join("");
 $("#newsSource").innerHTML='<option value="">Все источники</option>'+sources.map(function(s){return'<option value="'+esc(s)+'">'+esc(shortSource(s))+'</option>'}).join("")
}
function filteredNews(){
 var q=($("#search").value||"").trim().toLowerCase(),cat=$("#newsCategory").value,days=Number($("#newsPeriod").value||365),scope=$("#newsScope").value,source=$("#newsSource").value,type=$("#newsType").value,sort=$("#newsSort").value;
 var a=highQuality().filter(function(x){var txt=(x.title+" "+x.summary+" "+x.source+" "+(x.topics||[]).join(" ")+" "+(x.brands||[]).join(" ")).toLowerCase();return age(x)<=days&&(!cat||(x.categories||[]).indexOf(cat)>=0)&&(!scope||x.market_scope===scope)&&(!source||x.source===source)&&(!type||x.content_type===type)&&(!q||txt.indexOf(q)>=0)});
 a.sort(sort==="date"?function(a,b){return new Date(b.published_at)-new Date(a.published_at)}:function(a,b){return importance(b)-importance(a)});
 return a
}
function article(x){
 var tags=[typeLabel(x),x.market_scope==="Global"?"Мир":"Россия","SR "+strategicScore(x)];
 return'<article class="article"><div class="articleCat">'+esc(CAT[x.primary_category]||x.primary_category||"Рынок")+'</div><div><div class="articleTags">'+tags.map(function(z){return"<span>"+esc(z)+"</span>"}).join("")+'</div><h3><a href="'+esc(x.url)+'" target="_blank" rel="noopener">'+esc(x.title)+'</a></h3><p>'+esc((x.summary||x.why_it_matters||"").slice(0,300))+'</p></div><div class="articleMeta">'+esc(shortSource(x.source))+"<br>"+fmt(x.published_at,true)+'<button class="miniStar '+(starIds().indexOf(x.id)>=0?"on":"")+'" data-star="'+esc(x.id)+'">'+(starIds().indexOf(x.id)>=0?"★":"☆")+'</button></div></article>'
}
function renderNews(){var a=filteredNews();$("#newsMeta").textContent=a.length+" материалов · период "+$("#newsPeriod option:checked").textContent;$("#newsList").innerHTML=a.slice(0,180).map(article).join("")||'<div class="empty">Нет материалов по выбранным фильтрам.</div>';bindStars()}
function renderFavorites(){var ids=starIds(),a=(DB.items||[]).filter(function(x){return ids.indexOf(x.id)>=0});$("#favoritesList").innerHTML=a.length?a.map(article).join(""):'<div class="empty">Здесь будут материалы, которые вы отметите звездочкой.</div>';bindStars()}

function reportsForMarket(c){
 var rc=c==="Automotive"?"Авто":c==="RealEstate"?"Недвижимость":c==="BanksFintech"?"Банки":c==="FinanceEconomy"||c==="MediaAdvertising"?"Финансы":"Ритейл";
 return(REPORTDB.reports||[]).filter(function(r){return r.category===rc}).slice(0,3)
}
function marketItems(c){return highQuality().filter(function(x){return(x.categories||[]).indexOf(c)>=0}).sort(function(a,b){return importance(b)-importance(a)})}
function renderMarketDetail(c){
 currentMarket=c;$$("[data-market]").forEach(function(b){b.classList.toggle("active",b.getAttribute("data-market")===c)});
 var items=marketItems(c),news=items.filter(function(x){return age(x)<=30}).slice(0,5),out=items.filter(function(x){return x.future_signal}).slice(0,3),reports=reportsForMarket(c);
 var trends=(confirmedTrends("Russia").concat(confirmedTrends("Global"))).filter(function(z){return z.e.hits.some(function(x){return(x.categories||[]).indexOf(c)>=0})}).slice(0,3);
 var metricRows=(METRICDB.metrics||[]).filter(function(m){if(c==="Automotive")return m.id==="auto-sales";if(c==="RealEstate"||c==="BanksFintech")return m.id==="mortgage"||m.id==="key-rate";if(c==="FinanceEconomy")return m.id==="key-rate"||m.id==="inflation";if(c==="MediaAdvertising")return m.id==="ad-market";if(c==="DeliveryEcom"||c==="Retail")return m.id==="ecommerce";return false}).slice(0,3);
 $("#marketDetail").innerHTML='<section class="panel marketHero"><div><span class="marketIcon">'+MARKET_ICON[c]+'</span><h2>'+esc(CAT[c]||c)+'</h2><p>'+items.length+' значимых материалов за 12 месяцев</p></div></section>'+
 '<div class="marketColumns"><section class="panel marketSection"><div class="panelHead"><h2>Главное</h2></div><div>'+news.map(article).join("")+'</div></section>'+
 '<section class="panel marketSection"><div class="panelHead"><h2>Ключевые цифры</h2></div><div class="marketMetrics">'+metricRows.map(function(m){return'<a href="'+esc(m.source_url)+'" target="_blank"><b>'+esc(m.value)+'</b><span>'+esc(m.label)+'</span><small>'+esc(m.source+" · "+m.period)+'</small></a>'}).join("")+'</div><div class="panelHead mini"><h2>Прогнозы</h2></div><div class="marketOutlook">'+out.map(function(x){return'<a href="'+esc(x.url)+'" target="_blank"><b>'+esc(x.title)+'</b><small>'+esc(shortSource(x.source))+'</small></a>'}).join("")+'</div></section></div>'+
 '<div class="marketColumns lower"><section class="panel marketSection"><div class="panelHead"><h2>Тренды</h2></div>'+trends.map(trendRow).join("")+'</section><section class="panel marketSection"><div class="panelHead"><h2>Исследования</h2></div><div class="marketReports">'+reports.map(function(r){return reportCard(r,true)}).join("")+'</div></section></div>'
}
function renderMarkets(){
 $("#marketNav").innerHTML=MARKET_ORDER.map(function(c){return'<button data-market="'+c+'" class="'+(c===currentMarket?"active":"")+'"><span>'+MARKET_ICON[c]+'</span>'+esc(CAT[c])+'</button>'}).join("");
 $$("[data-market]").forEach(function(b){b.onclick=function(){renderMarketDetail(b.getAttribute("data-market"))}});
 renderMarketDetail(currentMarket)
}

function setView(v){
 currentView=v;$$(".view").forEach(function(x){x.classList.remove("active")});$("#view-"+v).classList.add("active");$$("#nav button").forEach(function(x){x.classList.toggle("active",x.getAttribute("data-view")===v)});
 var p={home:["homeTitle","homeSub"],news:["newsTitle","newsSub"],trends:["trendsTitle","trendsSub"],markets:["marketsTitle","marketsSub"],reports:["reportsTitle","reportsSub"],favorites:["favTitle","favSub"]};
 $("#pageTitle").textContent=t(p[v][0]);$("#pageSubtitle").textContent=t(p[v][1]);
 if(v==="news")renderNews();if(v==="markets")renderMarkets();if(v==="reports")renderReports();if(v==="favorites")renderFavorites();
 window.scrollTo({top:0,behavior:"smooth"})
}
function applyLang(){
 $$("[data-t]").forEach(function(el){el.textContent=t(el.getAttribute("data-t"))});
 $("#langRu").classList.toggle("active",lang==="ru");$("#langEn").classList.toggle("active",lang==="en");
 setView(currentView)
}
$$("#nav button").forEach(function(b){b.onclick=function(){setView(b.getAttribute("data-view"))}});
$$("[data-go]").forEach(function(b){b.onclick=function(){setView(b.getAttribute("data-go"))}});
$("#langRu").onclick=function(){lang="ru";localStorage.setItem("sr_lang",lang);applyLang()};
$("#langEn").onclick=function(){lang="en";localStorage.setItem("sr_lang",lang);applyLang()};
$("#globalPeriod").onchange=function(){var v=$("#globalPeriod").value;$("#newsPeriod").value=v; if(currentView==="news")renderNews()};
$("#search").addEventListener("input",function(){if(currentView!=="news"&&$("#search").value.trim())setView("news");else if(currentView==="news")renderNews()});
["newsPeriod","newsCategory","newsScope","newsSource","newsType","newsSort"].forEach(function(id){$("#"+id).addEventListener("change",renderNews)});

async function getJSON(url){var r=await fetch(url+"?v="+Date.now(),{cache:"no-store"});if(!r.ok)throw new Error(url+" HTTP "+r.status);return r.json()}
async function load(){
 var errs=[];
 try{DB=await getJSON("data/news.json")}catch(e){errs.push("news");DB=FALLBACK_BUNDLE.news||{items:[]};usingFallback=true}
 try{REPORTDB=await getJSON("data/reports.json")}catch(e){errs.push("reports");REPORTDB=FALLBACK_BUNDLE.reports||{reports:[],categories:["Ритейл","Авто","Недвижимость","Банки","Финансы"]};usingFallback=true}
 try{METRICDB=await getJSON("data/metrics.json")}catch(e){errs.push("metrics");METRICDB=FALLBACK_BUNDLE.metrics||{metrics:[]};usingFallback=true}
 if(!DB.items||!DB.items.length){DB=(FALLBACK_BUNDLE.news||{items:[]});usingFallback=true}
 if(!REPORTDB.reports||!REPORTDB.reports.length){REPORTDB=(FALLBACK_BUNDLE.reports||{reports:[],categories:["Ритейл","Авто","Недвижимость","Банки","Финансы"]});usingFallback=true}
 if(!METRICDB.metrics||!METRICDB.metrics.length){METRICDB=(FALLBACK_BUNDLE.metrics||{metrics:[]});usingFallback=true}
 var uniqueSources=new Set(DB.items.map(function(x){return x.source})).size;
 $("#fresh").textContent="Обновлено "+fmt(DB.updated_at||new Date(),true)+" · "+uniqueSources+" источников";
 if(usingFallback){$("#offlineBanner").hidden=false;$("#offlineBanner").textContent="Онлайн-данные временно недоступны. Показан последний успешно собранный снимок Strategy Radar."}
 fillFilters();renderMetrics();renderTop();renderTrends();renderOutlook();renderReports();renderNews();renderMarkets();renderFavorites();applyLang()
}
load();