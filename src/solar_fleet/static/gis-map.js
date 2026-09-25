import { l, t, number } from './i18n.js';

export async function renderGisMapWorkspace(ui) {
  const {state,div,p,btn,card,table,input,field,api,go,siteForm}=ui;
  const data=await api('/fleet/map-data');
  const search=input('search');
  const out=div('stack');
  const open=s=>{state.site=s.id;go('overview');};
  const node=(tag,attrs={},text='')=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));n.textContent=text;return n;};
  const draw=()=>{
    const rows=data.plants.filter(s=>(s.name+' '+(s.address||'')+' '+(s.vendor||'')).toLocaleLowerCase().includes(search.value.toLocaleLowerCase()));
    const known=rows.filter(s=>s.latitude!=null&&s.longitude!=null);
    const svg=node('svg',{viewBox:'0 0 800 390',class:'measurement-chart',role:'img','aria-label':l('Vị trí GPS đã khai báo','Recorded GPS positions')});
    if(known.length){
      const lat=known.map(s=>s.latitude),lon=known.map(s=>s.longitude),loX=Math.min(...lon),hiX=Math.max(...lon),loY=Math.min(...lat),hiY=Math.max(...lat);
      svg.append(node('text',{x:50,y:28},l('Vĩ độ / Kinh độ • Sơ đồ tọa độ','Latitude / Longitude • Coordinate plot')));
      known.forEach(s=>{const x=80+(s.longitude-loX)/Math.max(0.1,hiX-loX)*620,y=330-(s.latitude-loY)/Math.max(0.1,hiY-loY)*260;
        const g=node('g',{tabindex:0,role:'button','aria-label':s.name});g.append(node('circle',{cx:x,cy:y,r:8,class:'chart-point'}),node('text',{x:x+12,y:y+4},s.name),node('title',{},s.latitude+', '+s.longitude));g.onclick=()=>open(s);g.onkeydown=ev=>{if(ev.key==='Enter')open(s);};svg.append(g);});
    }else svg.append(node('text',{x:400,y:195,'text-anchor':'middle'},l('Chưa có nhà máy có tọa độ GPS','No plants with recorded GPS')));
    out.replaceChildren(card(l('Vị trí nhà máy','Plant locations'),svg,p(l('Sơ đồ GPS không có lớp đường phố hoặc vệ tinh. Nhà máy chưa khai báo tọa độ chỉ xuất hiện trong bảng.','This GPS plot has no street or satellite layer. Plants without coordinates appear only in the directory.'))),
      card(l('Danh bạ vị trí','Location directory'),table([t('name'),t('status'),'GPS','kWp',l('Công suất','Power'),l('Thao tác','Action')],rows.map(s=>[btn(s.name,()=>open(s)),s.status,s.latitude==null||s.longitude==null?'—':s.latitude+', '+s.longitude,number(s.capacity_kwp),number(s.current_power_kw)+' kW',ui.admin()?btn(t('edit'),()=>siteForm(s)):'—']))),
      card(l('Nhóm vị trí gần nhau','Nearby location groups'),table([l('Nhóm','Group'),l('Nhà máy','Plants'),'GPS'],data.clusters.map(c=>[c.name||c.cluster_id,c.count||1,c.latitude+', '+c.longitude]))));
  };
  search.oninput=draw;draw();
  return div('stack',field(l('Tìm nhà máy','Find a plant'),search),out);
}
export function createGisMapView(ui){return {renderMap:()=>renderGisMapWorkspace(ui)};}
