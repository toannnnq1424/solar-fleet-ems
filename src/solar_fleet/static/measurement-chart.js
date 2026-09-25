import { l, date, number } from './i18n.js';

// Plot individual observations; do not interpolate missing samples or invent other channels.
export function measurementChart(samples, label, unit) {
  const node=(tag,attrs={},text='')=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));n.textContent=text;return n;};
  const svg=node('svg',{viewBox:'0 0 720 260',class:'measurement-chart',role:'img','aria-label':label});
  const points=samples.filter(s=>s.value!=null&&Number.isFinite(Number(s.value))&&Number.isFinite(Date.parse(s.source_timestamp)));
  if(!points.length){svg.append(node('text',{x:360,y:130,'text-anchor':'middle'},l('Chưa có số đo phù hợp','No matching observations')));return svg;}
  const xs=points.map(s=>Date.parse(s.source_timestamp)), ys=points.map(s=>Number(s.value));
  const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(0,...ys),maxY=Math.max(1,...ys);
  const x=v=>65+(v-minX)/Math.max(1,maxX-minX)*615,y=v=>210-(v-minY)/(maxY-minY)*180;
  for(let i=0;i<=4;i++){const v=minY+(maxY-minY)*i/4;svg.append(node('line',{x1:65,x2:680,y1:y(v),y2:y(v),class:'chart-grid'}),node('text',{x:58,y:y(v)+4,'text-anchor':'end'},number(v)));}
  points.forEach((s,i)=>{const dot=node('circle',{cx:x(xs[i]),cy:y(ys[i]),r:3,class:'chart-point'});dot.append(node('title',{},`${date(s.source_timestamp)} · ${number(s.value)} ${unit}`));svg.append(dot);});
  svg.append(node('text',{x:65,y:25},`${label} (${unit})`),node('text',{x:65,y:245},date(new Date(minX).toISOString())),node('text',{x:680,y:245,'text-anchor':'end'},date(new Date(maxX).toISOString())));
  return svg;
}
