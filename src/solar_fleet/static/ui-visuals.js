import { l, number } from './i18n.js';
import { inspectDailyChart } from './chart-inspector.js';
import { icon } from './icons.js';

// Presentation only. Values must come from callers; absence never becomes zero.
export function metricTiles(ui, items, extraClass = '') {
  return ui.div('metric-tiles ' + extraClass, ...items.map(([glyph,label,value,unit = '',tone = 'blue',hint = '']) =>
    ui.div('metric-tile', ui.div('metric-icon ' + tone, icon(glyph)),
      ui.div('metric-copy', ui.e('span',label,'metric-label'),
        ui.e('strong',value == null || (typeof value === 'number' && !Number.isFinite(value)) ? '—' :
          (typeof value === 'number' ? number(value) : value) + (unit ? ' ' + unit : '')),
        hint ? ui.e('small',hint,'muted') : null))));
}

function svgNode(tag, attrs = {}, text = '') {
  const node = document.createElementNS('http://www.w3.org/2000/svg',tag);
  for (const [key,value] of Object.entries(attrs)) node.setAttribute(key,String(value));
  node.textContent = text; return node;
}

export function countChart(rows, label, horizontal = false) {
  const values=rows.map(r=>typeof r.value==='number'&&Number.isFinite(r.value)&&r.value>=0?r.value:null);
  const max=Math.max(1,...values.filter(v=>v!=null));
  const height=horizontal?Math.max(180,rows.length*26+20):180;
  const svg=svgNode('svg',{viewBox:`0 0 420 ${height}`,class:'count-chart',role:'img','aria-label':label});
  if(horizontal) rows.forEach((row,i)=>{
    const y=16+i*26;
    svg.append(svgNode('text',{x:0,y:y+10},row.label));
    svg.append(svgNode('line',{x1:120,x2:385,y1:y+5,y2:y+5,class:'chart-grid'}));
    if(values[i]!=null)svg.append(svgNode('rect',{x:120,y,width:values[i]/max*255,height:12,rx:3,class:'count-bar'}));
    svg.append(svgNode('text',{x:416,y:y+10,'text-anchor':'end'},values[i]==null?'—':String(values[i])));
  });
  else {
    [0,1,2,3].forEach(i=>{const y=142-i*40;svg.append(svgNode('line',{x1:30,x2:412,y1:y,y2:y,class:'chart-grid'}));});
    rows.forEach((row,i)=>{const step=380/Math.max(1,rows.length),x=30+i*step+step/2,h=(values[i]??0)/max*110;
      if(values[i]!=null){const bar=svgNode('rect',{x:x-9,y:142-h,width:18,height:h,rx:2,class:'count-bar'});bar.append(svgNode('title',{},row.label+': '+values[i]));svg.append(bar);}
      svg.append(svgNode('text',{x,y:164,'text-anchor':'middle'},row.label));
    });
  }
  if(!values.some(v=>v>0))svg.append(svgNode('text',{x:210,y:86,'text-anchor':'middle',class:'chart-empty'},l('Chưa ghi nhận cảnh báo','No alerts recorded')));
  return svg;
}

export function percentageGauge(value, label) {
  const known = typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 100;
  const svg = svgNode('svg',{viewBox:'0 0 160 160',class:'percentage-gauge',role:'img','aria-label':label});
  svg.append(svgNode('circle',{cx:80,cy:80,r:61,class:'gauge-track'}));
  if (known) svg.append(svgNode('circle',{cx:80,cy:80,r:61,pathLength:100,
    'stroke-dasharray':`${value} ${100-value}`,transform:'rotate(-90 80 80)',class:'gauge-value'}));
  svg.append(svgNode('text',{x:80,y:79,'text-anchor':'middle',class:'gauge-number'},known ? number(value,1)+'%' : '—'),
    svgNode('text',{x:80,y:101,'text-anchor':'middle',class:'gauge-caption'},known ? label : l('Chưa đủ dữ liệu','Insufficient data')));
  return svg;
}

export function dailyEnergyChart(rows, options = {}) {
  const compact=!!options.compact,w=compact?320:800,h=compact?200:260;
  const left=compact?42:56,right=w-20,bottom=compact?164:214,plotHeight=compact?134:180;
  const svg = svgNode('svg',{viewBox:`0 0 ${w} ${h}`,class:'daily-energy-chart',role:'img',
    'aria-label':options.label || l('Điện năng theo ngày từ dữ liệu báo cáo','Daily energy from report observations')});
  const keys = options.keys || [['pv_kwh',l('Sản lượng','Generation'),'generation'],['load_kwh',l('Tiêu thụ','Consumption'),'consumption'],
    ['grid_export_kwh',l('Xuất lưới','Grid export'),'export']];
  const valid = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
  const values = rows.flatMap(row => keys.map(([key])=>row[key])).filter(valid);
  const observedMax=Math.max(1,...values);
  const max=options.integer?Math.ceil(observedMax/4)*4:observedMax;
  for (let i=0;i<=4;i++) {
    const y=bottom-i*plotHeight/4;
    svg.append(svgNode('line',{x1:left,x2:right,y1:y,y2:y,class:'chart-grid'}),
      svgNode('text',{x:left-8,y:y+4,'text-anchor':'end'},values.length?number(max*i/4):'—'));
  }
  svg.append(svgNode('text',{x:left,y:18},options.unit || 'kWh'));
  if (!values.length) {
    svg.append(svgNode('text',{x:(left+right)/2,y:bottom-plotHeight/2,'text-anchor':'middle',class:'chart-empty'},options.emptyLabel || l('Chưa có điện năng đo đếm phù hợp','No matching energy observations')));
    return svg;
  }
  const step=(right-left)/Math.max(1,rows.length),width=Math.min(12,step/(keys.length+1));
  const lineKeys=new Set(options.lineKeys||[]);
  keys.filter(([key])=>lineKeys.has(key)).forEach(([key,,tone])=>{
    let segment=[];
    const flush=()=>{if(segment.length>1)svg.append(svgNode('polyline',{points:segment.join(' '),class:'energy-line '+tone}));segment=[];};
    rows.forEach((row,index)=>{
      if(!valid(row[key])){flush();return;}
      segment.push(`${left+index*step+step/2},${bottom-row[key]/max*plotHeight}`);
    });flush();
  });
  rows.forEach((row,index)=>{
    keys.forEach(([key,label,tone],channel)=>{
      if (!valid(row[key])) return;
      const h=row[key]/max*plotHeight;
      const description=`${row.date} · ${label}: ${number(row[key])} ${options.unit || 'kWh'}`;
      const bar=lineKeys.has(key)?svgNode('circle',{cx:left+index*step+step/2,cy:bottom-h,r:3.5,
        class:'energy-point '+tone,tabindex:0,role:'img','aria-label':description}):svgNode('rect',{x:left+index*step+step/2+(channel-keys.length/2)*width,y:bottom-h,
        width:Math.max(1,width-1),height:h,rx:1,class:'energy-bar '+tone,tabindex:0,role:'img','aria-label':description});
      bar.append(svgNode('title',{},description)); svg.append(bar);
    });
    if (index % Math.max(1,Math.ceil(rows.length/(compact?3:8)))===0) svg.append(svgNode('text',{
      x:left+index*step+step/2,y:bottom+27,'text-anchor':'middle'},String(row.date).slice(5)));
  });
  return inspectDailyChart(svg, rows, keys, {left, right, top: bottom-plotHeight, bottom}, options.unit || 'kWh');
}
