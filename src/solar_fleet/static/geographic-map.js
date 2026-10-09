import { landPaths } from './map-land.js';
import { l, t } from './i18n.js';

const node=(tag,attrs={},text='')=>{const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [key,value] of Object.entries(attrs))el.setAttribute(key,String(value));el.textContent=text;return el;};
export function validPosition(site) {
  return Number.isFinite(site.latitude)&&Number.isFinite(site.longitude)&&Math.abs(site.latitude)<=85.0511&&Math.abs(site.longitude)<=180;
}
const project=site=>{
  const phi=site.latitude*Math.PI/180;
  return [(site.longitude+180)/360*1024,(1-Math.log(Math.tan(phi)+1/Math.cos(phi))/Math.PI)/2*1024];
};

// Physical coastline only. Plant positions and status always come from the API.
export function geographicMap(ui,sites,selectedId,onSelect,viewState={}) {
  const {div,btn,p,e,input,field}=ui;
  const known=sites.filter(validPosition);
  const svg=node('svg',{class:'geographic-map',role:'group','aria-label':l('Bản đồ vị trí nhà máy','Plant location map'),tabindex:0});
  const land=node('g',{class:'geographic-land'});
  landPaths.forEach(path=>land.append(node('path',{d:path})));
  svg.append(land);
  const markers=node('g');svg.append(markers);
  const fit=()=>{
    if(!known.length)return [0,120,1024,650];
    const pts=known.map(project),xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);
    const width=Math.max(30,Math.max(...xs)-Math.min(...xs)+24);
    const height=Math.max(30,Math.max(...ys)-Math.min(...ys)+24);
    return [(Math.max(...xs)+Math.min(...xs)-width)/2,(Math.max(...ys)+Math.min(...ys)-height)/2,width,height];
  };
  let box=viewState.box||fit();
  const names=input('checkbox'),coast=input('checkbox'),states=input('checkbox');
  names.checked=viewState.names===true;coast.checked=viewState.coast!==false;states.checked=viewState.states!==false;
  const draw=()=>{
    viewState.box=box;svg.setAttribute('viewBox',box.join(' '));
    viewState.names=names.checked;viewState.coast=coast.checked;viewState.states=states.checked;
    land.setAttribute('visibility',coast.checked?'visible':'hidden');
    const size=Math.max(box[2],box[3])/65;
    markers.replaceChildren(...known.map(site=>{
      const [x,y]=project(site);
      const tone=states.checked?({NORMAL:'normal',ONLINE:'online',WARNING:'warning',ALARM:'warning',OFFLINE:'offline',STALE:'unknown'})[site.status]||'unknown':'plain';
      const g=node('g',{role:'button',tabindex:0,'aria-label':site.name,'aria-pressed':String(site.id===selectedId),class:'geo-marker geo-'+tone+(site.id===selectedId?' selected':'')});
      g.append(node('circle',{cx:x,cy:y,r:size}),node('circle',{cx:x,cy:y,r:size/3,class:'geo-marker-core'}),node('title',{},site.name+' · '+t(site.status||'UNKNOWN')+' · '+site.latitude+', '+site.longitude));
      if(names.checked)g.append(node('text',{x:x+size*1.7,y:y+size*.4,'font-size':size*1.6,class:'geo-name'},site.name));
      const choose=()=>onSelect(site.id);
      g.onclick=choose;g.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();event.stopPropagation();choose();}};
      return g;
    }));
  };
  const zoom=factor=>{const w=Math.min(1600,Math.max(8,box[2]*factor)),h=w*box[3]/box[2];box=[box[0]+(box[2]-w)/2,box[1]+(box[3]-h)/2,w,h];draw();};
  svg.onkeydown=event=>{
    if(event.target!==svg)return;
    const move={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];
    if(move){event.preventDefault();box=[box[0]+move[0]*box[2]/8,box[1]+move[1]*box[3]/8,...box.slice(2)];draw();}
    else if(event.key==='+'||event.key==='='){event.preventDefault();zoom(.7);}
    else if(event.key==='-'){event.preventDefault();zoom(1/.7);}
  };
  let drag=null;
  svg.onpointerdown=event=>{
    if(event.button!==0||event.target.closest('.geo-marker'))return;
    const matrix=svg.getScreenCTM();if(!matrix)return;
    drag={x:event.clientX,y:event.clientY,box:[...box],scale:matrix.a};svg.setPointerCapture(event.pointerId);
  };
  svg.onpointermove=event=>{if(!drag)return;box=[drag.box[0]-(event.clientX-drag.x)/drag.scale,drag.box[1]-(event.clientY-drag.y)/drag.scale,...drag.box.slice(2)];draw();};
  svg.onpointerup=svg.onpointercancel=()=>{drag=null;};
  draw();
  names.onchange=coast.onchange=states.onchange=draw;
  const more=btn('+',()=>zoom(.7),'icon-button'),less=btn('−',()=>zoom(1/.7),'icon-button');
  more.setAttribute('aria-label',l('Phóng to bản đồ','Zoom in map'));less.setAttribute('aria-label',l('Thu nhỏ bản đồ','Zoom out map'));
  const layers=e('details','','map-layers');
  layers.append(e('summary',l('Lớp hiển thị','Map layers')),field(l('Bờ biển','Coastline'),coast),field(l('Tên nhà máy','Plant names'),names),field(l('Màu theo trạng thái','Status colors'),states),p(l('Xám: chưa rõ · Xanh lam: có số đo · Xanh lá: trực tuyến · Cam: cảnh báo · Đỏ: ngoại tuyến. Có số đo không tự xác nhận kết nối trực tuyến.','Gray: unknown · Blue: readings available · Green: online · Amber: warning · Red: offline. Available readings do not establish online connectivity.'),'field-help'));
  const root=div('geographic-map-frame',svg,div('map-navigation',more,less,btn(l('Vừa khung','Fit plants'),()=>{box=fit();draw();})),layers,p(l('Natural Earth · Bản đồ địa hình tổng quát','Natural Earth · Physical overview map'),'map-attribution'));
  if(!known.length)root.append(div('map-empty-overlay',p(l('Chưa có vị trí GPS hợp lệ trong phạm vi này','No valid GPS positions in this scope')),p(l('Thêm tọa độ trong hồ sơ nhà máy để hiển thị vị trí.','Add coordinates in plant information to show its position.'),'field-help')));
  return root;
}
