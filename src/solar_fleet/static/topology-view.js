import { l, t, number } from './i18n.js';

export function createTopologyView(ui) { return {render:()=>renderTopologyWorkspace(ui), renderTopology:()=>renderTopologyWorkspace(ui)}; }

export async function renderTopologyWorkspace(ui) {
  const {state,div,p,btn,card,table,select,field,api,go,sites,deviceDetail}=ui;
  const plants=sites();
  if(!plants.length)return card(l('Sơ đồ thiết bị','Equipment topology'),p(t('noData')));
  const id=state.site||plants[0].id;
  const data=await api('/sites/'+encodeURIComponent(id)+'/topology-detail');
  const picker=select(plants.map(s=>[s.id,s.name]),id);
  picker.onchange=()=>{state.site=picker.value;ui.render();};
  const node=(tag,attrs={},text='')=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));n.textContent=text;return n;};
  const height=Math.max(230,Math.ceil(data.nodes.length/3)*130+40);
  const svg=node('svg',{viewBox:`0 0 900 ${height}`,class:'measurement-chart',role:'img','aria-label':l('Kết nối thiết bị đã khai báo','Recorded equipment connections')});
  const positions=new Map(data.nodes.map((d,i)=>[d.id,{x:50+i%3*300,y:45+Math.floor(i/3)*130}]));
  data.edges.forEach(edge=>{const a=positions.get(edge.source),b=positions.get(edge.target);if(a&&b)svg.append(node('line',{x1:a.x+100,y1:a.y+35,x2:b.x+100,y2:b.y+35,class:'topology-link'}));});
  data.nodes.forEach(d=>{const pos=positions.get(d.id),g=node('g',{role:'button',tabindex:0,'aria-label':d.name||d.serial});
    g.append(node('rect',{x:pos.x,y:pos.y,width:220,height:78,rx:10,class:'topology-node'}),node('text',{x:pos.x+12,y:pos.y+25},d.name||d.serial),node('text',{x:pos.x+12,y:pos.y+48},d.type+' · '+d.status),node('text',{x:pos.x+12,y:pos.y+65},number(d.power_kw)+' kW'));
    g.onclick=()=>deviceDetail(d.id);g.onkeydown=ev=>{if(ev.key==='Enter')deviceDetail(d.id);};svg.append(g);
  });
  return div('stack',div('row',field(t('plants'),picker),btn(l('Sửa kết nối','Edit connections'),()=>{state.site=id;go('devices','','topology');}),btn(l('Chi tiết nhà máy','Plant details'),()=>{state.site=id;go('overview');})),
    card(l('Sơ đồ thiết bị đã khai báo','Recorded equipment graph'),svg,p(l('Sơ đồ thể hiện danh mục và kết nối đã khai báo; chưa phải bản vẽ điện nghiệm thu.','This graph shows recorded equipment and connections; it is not an accepted electrical drawing.'))),
    card(l('Các đường kết nối','Connections'),table([l('Từ','From'),l('Đến','To'),l('Kiểu kết nối','Connection')],data.edges.map(e=>[e.source,e.target,e.connection]))),
    card(l('Thông số thiết bị','Equipment readings'),table([t('name'),'Model',t('status'),'kW'],data.nodes.map(d=>[d.name||d.serial,d.model,d.status,number(d.power_kw)]))),
    card(l('Kiểm tra điện','Electrical checks'),table([l('Hạng mục','Check'),t('status'),l('Còn thiếu','Missing evidence')],Object.entries(data.validation).map(([k,v])=>[k,v.status,v.reason]))));
}
