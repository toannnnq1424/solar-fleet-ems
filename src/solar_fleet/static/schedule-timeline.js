import { l, t } from './i18n.js';

// Render persisted slots only; this diagram neither fills gaps nor sends commands.
export function scheduleTimeline(slots, days) {
  const node = (tag, attrs = {}, text = '') => {
    const el = document.createElementNS('http://www.w3.org/2000/svg',tag);
    for (const [k,v] of Object.entries(attrs)) el.setAttribute(k,String(v));
    el.textContent = text; return el;
  };
  const svg = node('svg',{viewBox:'0 0 900 330',class:'schedule-timeline',role:'img',
    'aria-label':l('Lịch tuần đã lưu · không phải trạng thái thực thi','Saved weekly schedule · not execution status')});
  const minute = text => {
    if (typeof text !== 'string' || !/^(?:[01]\d|2[0-3]):[0-5]\d$|^24:00$/.test(text)) return NaN;
    const [h,m] = text.split(':').map(Number); return h*60+m;
  };
  for (let hour=0;hour<=24;hour+=4) {
    const x = 90+hour/24*790;
    svg.append(node('line',{x1:x,x2:x,y1:30,y2:305,class:'chart-grid'}),
      node('text',{x,y:18,'text-anchor':hour===24?'end':'middle'},String(hour).padStart(2,'0')+':00'));
  }
  days.forEach((day,i)=>svg.append(node('text',{x:8,y:58+i*37},day)));
  for (const slot of slots) {
    if (!Number.isInteger(slot.day)||slot.day<0||slot.day>6||!slot.start||!slot.end) continue;
    const start=minute(slot.start),end=minute(slot.end);
    if (!Number.isFinite(start)||!Number.isFinite(end)||end<=start) continue;
    const rect=node('rect',{x:90+start/1440*790,y:38+slot.day*37,
      width:(end-start)/1440*790,height:27,rx:4,class:'schedule-slot mode-'+(['hold','charge','discharge','self_use'].includes(slot.mode)?slot.mode:'unknown')});
    rect.append(node('title',{},dayLabel(slot,days)));svg.append(rect);
  }
  return svg;
}
function dayLabel(slot,days) { return days[slot.day]+' · '+slot.start+'–'+slot.end+' · '+t(slot.mode); }
