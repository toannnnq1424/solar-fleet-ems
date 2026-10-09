import { l, date, number } from './i18n.js';

// Each trace keeps its own source and timestamp. No summing, imputation or smoothing.
export function multiMeasurementChart(channels) {
  const node=(tag,attrs={},text='')=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));n.textContent=text;return n;};
  const svg=node('svg',{viewBox:'0 0 900 330',class:'measurement-chart multi-measurement-chart',role:'img','aria-label':l('Biểu đồ số đo đa kênh','Multichannel observations')});
  const series=channels.map(c=>({...c,points:[...(c.samples||[])].sort((a,b)=>Date.parse(a.source_timestamp)-Date.parse(b.source_timestamp)).map((s,i)=>({...s,plotIndex:i})).filter(s=>typeof s.value==='number'&&Number.isFinite(s.value)&&s.unit===c.unit&&Number.isFinite(Date.parse(s.source_timestamp))&&(!s.quality||s.quality==='GOOD')&&(c.unit!=='%'||(s.value>=0&&s.value<=100)))}));
  const all=series.flatMap(c=>c.points),power=series.filter(c=>c.unit==='W').flatMap(c=>c.points.map(p=>p.value));
  const minX=all.length?Math.min(...all.map(s=>Date.parse(s.source_timestamp))):0,maxX=all.length?Math.max(...all.map(s=>Date.parse(s.source_timestamp))):1;
  const lo=Math.min(0,...power),hi=Math.max(1,...power),x=v=>64+(v-minX)/Math.max(1,maxX-minX)*766,y=(v,unit)=>278-(unit==='%'?v/100:(v-lo)/(hi-lo))*236;
  for(let i=0;i<=4;i++){
    const yy=278-i*59;svg.append(node('line',{x1:64,x2:830,y1:yy,y2:yy,class:'chart-grid'}));
    if(power.length)svg.append(node('text',{x:55,y:yy+4,'text-anchor':'end'},number((lo+(hi-lo)*i/4)/1000)));
    if(series.some(c=>c.unit==='%'&&c.points.length))svg.append(node('text',{x:841,y:yy+4},String(i*25)));
  }
  svg.append(node('text',{x:64,y:24},'kW'),node('text',{x:830,y:24},'%'));
  if(!all.length){svg.append(node('text',{x:450,y:158,'text-anchor':'middle',class:'chart-empty'},l('Chưa có số đo phù hợp','No matching observations')));return svg;}
  const tickCount=maxX===minX?1:5;
  for(let i=0;i<tickCount;i++){
    const ts=minX+(maxX-minX)*i/4,instant=new Date(ts),xx=x(ts);
    const tick=node('text',{x:xx,y:302,'text-anchor':i===0?'start':i===4?'end':'middle',class:'measurement-time-tick'});
    tick.append(node('tspan',{x:xx},instant.toLocaleTimeString(l('vi-VN','en-GB'),{hour:'2-digit',minute:'2-digit',hour12:false})),
      node('tspan',{x:xx,dy:17},instant.toLocaleDateString(l('vi-VN','en-GB'),{day:'2-digit',month:'2-digit'})),
      node('title',{},date(instant.toISOString())));svg.append(tick);
  }
  for(const c of series){
    const group=node('g',{class:'measurement-series series-'+c.color});
    // Bounded rendering selects existing observations, never synthetic samples.
    const stride=Math.max(1,Math.ceil(c.points.length/1500)),points=c.points.filter((_,i)=>i%stride===0);
    points.forEach((s,i)=>{
      const xx=x(Date.parse(s.source_timestamp)),yy=y(s.value,c.unit),prev=points[i-1];
      if(prev&&s.plotIndex===prev.plotIndex+1&&s.binding_id===prev.binding_id&&s.device_id===prev.device_id&&s.source===prev.source&&Date.parse(s.source_timestamp)-Date.parse(prev.source_timestamp)<=300000&&Date.parse(s.source_timestamp)>Date.parse(prev.source_timestamp))group.append(node('line',{x1:x(Date.parse(prev.source_timestamp)),y1:y(prev.value,c.unit),x2:xx,y2:yy,class:'measurement-segment'}));
      const point=node('circle',{cx:xx,cy:yy,r:2.5});point.append(node('title',{},c.label+' · '+date(s.source_timestamp)+' · '+number(s.value)+' '+c.unit+' · '+(s.device_id||'')));group.append(point);
    });svg.append(group);
  }
  return svg;
}

// Plot individual observations; do not interpolate missing samples or invent other channels.
export function measurementChart(samples, label, unit, options = {}) {
  const node=(tag,attrs={},text='')=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));n.textContent=text;return n;};
  const width=options.compact?360:720,height=options.compact?220:260,left=options.compact?48:65,right=width-25,bottom=height-45,top=40;
  const svg=node('svg',{viewBox:`0 0 ${width} ${height}`,class:'measurement-chart'+(options.compact?' compact-measurement-chart':''),role:'img','aria-label':label});
  const points=[...samples.map(s=>({...s,comparison:false})),...(options.comparison||[]).map(s=>({...s,comparison:true}))]
    .filter(s=>typeof s.value==='number'&&Number.isFinite(s.value)&&s.unit===unit&&Number.isFinite(Date.parse(s.source_timestamp))&&
      (!s.quality||s.quality==='GOOD'||(options.allowUnverified&&s.quality==='UNVERIFIED')));
  if(!points.length){
    for(let i=0;i<=4;i++)svg.append(node('line',{x1:left,x2:right,y1:top+i*(bottom-top)/4,y2:top+i*(bottom-top)/4,class:'chart-grid'}));
    svg.append(node('text',{x:left,y:25},`${label} (${unit})`),
      node('text',{x:width/2,y:height/2,'text-anchor':'middle',class:'chart-empty'},l('Chưa có số đo phù hợp','No matching observations')));
    return svg;
  }
  const xs=points.map(s=>Date.parse(s.source_timestamp)), ys=points.map(s=>Number(s.value));
  const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(0,...ys),maxY=Math.max(1,...ys);
  const x=v=>left+(v-minX)/Math.max(1,maxX-minX)*(right-left),y=v=>bottom-(v-minY)/(maxY-minY)*(bottom-top);
  for(let i=0;i<=4;i++){const v=minY+(maxY-minY)*i/4;svg.append(node('line',{x1:left,x2:right,y1:y(v),y2:y(v),class:'chart-grid'}),node('text',{x:left-7,y:y(v)+4,'text-anchor':'end'},number(v)));}
  points.forEach((s,i)=>{const dot=node('circle',{cx:x(xs[i]),cy:y(ys[i]),r:3,class:'chart-point'+(s.comparison?' comparison-point':'')+(s.quality==='UNVERIFIED'?' unverified-point':'')});dot.append(node('title',{},`${date(s.source_timestamp)} · ${number(s.value)} ${unit} · ${s.metric||label} · ${s.binding_id||'—'} · ${s.quality||'—'}`));svg.append(dot);});
  const stamp=value=>options.compact?new Date(value).toLocaleTimeString(l('vi-VN','en-GB'),{hour:'2-digit',minute:'2-digit',hour12:false}):date(new Date(value).toISOString());
  svg.append(node('text',{x:left,y:25},`${label} (${unit})`),node('text',{x:left,y:height-15},stamp(minX)),node('text',{x:right,y:height-15,'text-anchor':'end'},stamp(maxX)));
  return svg;
}
