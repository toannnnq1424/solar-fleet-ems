import { l, t, number } from './i18n.js';
import { plantMedia } from './plant-media.js';
import { geographicMap, validPosition } from './geographic-map.js';
import { metricTiles } from './ui-visuals.js';

export async function renderGisMapWorkspace(ui) {
  const {state,div,e,p,btn,card,input,select,field,api,go}=ui;
  const data=await api('/fleet/map-data');
  const search=input('search');
  const scopePlants=data.plants.filter(s=>!state.site||s.id===state.site);
  const vendor=select([['',l('Tất cả hãng','All vendors')],...Array.from(new Set(scopePlants.map(s=>s.vendor).filter(Boolean))).map(v=>[v,v])]);
  const status=select([['',l('Tất cả trạng thái','All statuses')],...Array.from(new Set(scopePlants.map(s=>s.status).filter(Boolean))).map(v=>[v,t(v)])]);
  const viewState={};
  const out=div('map-reference-layout');
  let selectedId=data.plants[0]?.id;
  const open=s=>{state.site=s.id;go('overview');};
  const draw=()=>{
    const rows=scopePlants.filter(s=>(!vendor.value||s.vendor===vendor.value)&&(!status.value||s.status===status.value)&&(s.name+' '+(s.address||'')+' '+(s.vendor||'')).toLocaleLowerCase().includes(search.value.toLocaleLowerCase()));
    if(!rows.some(s=>s.id===selectedId))selectedId=rows[0]?.id;
    const selected=rows.find(s=>s.id===selectedId);
    const svg=geographicMap(ui,rows,selectedId,id=>{selectedId=id;draw();},viewState);
    const directory=card(l('Danh sách nhà máy','Plant directory'),div('map-site-list',...rows.map(s=>{
      const item=btn('',()=>{selectedId=s.id;draw();},'map-site-button');
      item.setAttribute('aria-pressed',String(s.id===selectedId));
      item.append(plantMedia(ui,state.fleet.sites.find(v=>v.id===s.id)||s,true),div('stack gap-none',e('b',s.name),e('small',s.capacity_kwp==null?'—':number(s.capacity_kwp)+' kWp','muted')));
      if(!validPosition(s))item.append(e('small',l('Chưa có vị trí GPS','GPS unavailable'),'muted'));
      return item;
    })));
    if(!rows.length)directory.append(p(l('Không có nhà máy phù hợp với bộ lọc.','No plants match these filters.'),'field-help'));
    const detail=card(l('Thông tin nhà máy','Plant information'));
    detail.classList.add('map-site-detail');
    if(selected){
      const site=state.fleet.sites.find(s=>s.id===selected.id)||selected;
      detail.append(plantMedia(ui,site),e('h2',selected.name),p(selected.address||l('Chưa có địa chỉ','Address not recorded')),
        div('fact',e('span',t('status')),ui.badge(selected.status||'UNKNOWN')),
        div('fact',e('span',l('Công suất khai báo','Declared capacity')),e('b',selected.capacity_kwp==null?'—':number(selected.capacity_kwp)+' kWp')),
        div('fact',e('span',l('Công suất hiện tại','Current power')),e('b',selected.current_power_kw==null?'—':number(selected.current_power_kw)+' kW')),
        div('fact',e('span','GPS'),e('b',selected.latitude==null||selected.longitude==null?'—':number(selected.latitude,4)+', '+number(selected.longitude,4))),
        btn(l('Mở nhà máy','Open plant'),()=>open(selected),'primary'));
      if(ui.admin())detail.append(btn(l('Chỉnh sửa hồ sơ','Edit plant information'),()=>ui.siteForm(site)));
    }else detail.append(p(l('Không có nhà máy phù hợp.','No matching plants.')));
    out.replaceChildren(directory,div('map-canvas',svg),detail);
  };
  const filter=()=>{delete viewState.box;draw();};
  search.oninput=filter;vendor.onchange=filter;status.onchange=filter;draw();
  return div('stack map-workspace-root',metricTiles(ui,[['plant',l('Nhà máy trong phạm vi','Plants in scope'),scopePlants.length],
    ['map',l('Có tọa độ','With coordinates'),scopePlants.filter(validPosition).length,'','green']]),
    div('map-filters',field(l('Tìm nhà máy','Find a plant'),search),field(l('Hãng','Vendor'),vendor),field(t('status'),status)),out,p(l('Bản đồ bờ biển ngoại tuyến độ chi tiết thấp, không dùng để dẫn đường. Vị trí lấy từ hồ sơ nhà máy, không gửi ra bên ngoài. Dùng phím mũi tên để di chuyển và +/− để thu phóng.','Low-detail offline coastline map, not for navigation. Positions come from plant records and never leave this app. Use arrow keys to pan and +/− to zoom.'),'field-help'));
}
export function createGisMapView(ui){return {renderMap:()=>renderGisMapWorkspace(ui)};}
