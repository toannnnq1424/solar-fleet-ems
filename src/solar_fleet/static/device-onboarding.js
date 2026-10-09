import {l, t, date} from './i18n.js';
import {icon} from './icons.js';

// Inventory guidance only. Cloud authentication, local enrollment and commissioning
// keep their existing owners; this screen never scans or sends hardware commands.
export function deviceOnboarding(ui) {
  const {state,e,div,p,btn,card,badge,input,field,table,form,api,showDialog,closeDialog,refresh,go,siteName}=ui;
  const inventory=state.fleet.devices.filter(d=>!state.site||d.site_id===state.site);
  let {step=0,brand='',kind=''}=state.onboarding||{};
  let selected='',generation=0;
  const query=input('search','');query.placeholder=l('Tên thiết bị, số sê-ri hoặc model','Equipment name, serial number or model');
  const steps=div('onboarding-steps'),content=div('stack'),list=div('stack'),detail=div('stack onboarding-inspector');
  const brands=[...new Set([...state.providers.map(s=>s.id),'Bluesun',...inventory.flatMap(d=>[d.identity?.vendor,d.metadata?.declared_equipment_brand]).filter(Boolean)])];
  const labels=[l('Chọn hãng / thiết bị','Choose vendor / equipment'),l('Kết nối và đồng bộ','Connect and synchronize'),l('Xem nhà máy liên kết','Review linked plant'),l('Kiểm tra và bàn giao','Review and handover')];
  const types=[['inverter','device',l('Biến tần','Inverter')],['battery','battery',l('Pin lưu trữ','Battery')],['meter','gauge',l('Công tơ','Meter')],['logger','database','Logger'],['','settings',l('Tất cả','All types')]];
  const matches=()=>inventory.filter(d=>(!brand||[d.identity?.vendor,d.metadata?.declared_equipment_brand].some(v=>String(v||'').toLowerCase()===brand.toLowerCase()))&&(!kind||String(d.type||'').toLowerCase().includes(kind)||(kind==='logger'&&String(d.type||'').toLowerCase().includes('collector')))&&[d.name,d.vendor_id,d.identity?.model].join(' ').toLowerCase().includes(query.value.trim().toLowerCase()));
  const emptyDetail=()=>detail.replaceChildren(card(l('Thông tin và kiểm tra kết nối','Connection details and checks'),
    div('onboarding-empty-inspector',icon('device'),e('h3',l('Chọn một thiết bị để xem','Select equipment to inspect')),p(l('Model, phần mềm và nguồn dữ liệu sẽ lấy từ hồ sơ thật. Chưa có dữ liệu thì giữ trống, không tạo kết quả kiểm tra.','Model, firmware and data sources come from actual records. Missing data stays empty; no checks are fabricated.')))));
  const rename=d=>{
    const name=input('text',d.name||d.vendor_id);name.required=true;
    const f=form(async()=>{await api('/admin/devices/onboard-complete',{site_id:d.site_id,vendor:d.identity.vendor,serial_number:d.vendor_id,integration_id:d.integration_id,device_name:name.value.trim()});closeDialog();await refresh();});
    f.finish(field(t('name'),name));showDialog(l('Đặt tên thiết bị','Name equipment'),f);
  };
  async function inspect(d) {
    selected=d.id;const version=++generation;renderList();
    detail.replaceChildren(card(l('Thông tin và kiểm tra kết nối','Connection details and checks'),p(l('Đang đọc hồ sơ…','Reading stored details…'))));
    try {
      const data=await api('/devices/'+encodeURIComponent(d.id));
      if(version!==generation||selected!==d.id)return;
      const actual=data.device||d,identity=actual.identity||{},samples=data.latest?.samples||[],bindings=data.bindings||[];
      const record=(label,value)=>div('onboarding-fact',e('span',label),e('strong',value==null||value===''?'—':String(value)));
      const node=(glyph,label,value)=>div('onboarding-record-node',icon(glyph),div('',e('small',label),e('strong',value||'—')));
      const sourceDetails=e('details','','onboarding-source-details');
      sourceDetails.append(e('summary',l('Liên kết nguồn','Source bindings')+' ('+bindings.length+')'),
        table([l('Nguồn đã liên kết','Linked source'),l('Loại kết nối','Connection type'),t('status')],bindings.map(b=>[b.integration_id||b.agent_id||'—',t(b.source||b.transport||'—'),b.enabled===false?l('Đã tắt','Disabled'):l('Đã lưu · cần kiểm tra','Recorded · verify separately')])));
      detail.replaceChildren(card(l('Thông tin và kiểm tra kết nối','Connection details and checks'),
        div('onboarding-device-heading',div('metric-icon blue',icon('device')),div('',e('h3',actual.name||actual.vendor_id),p([identity.vendor,identity.model].filter(Boolean).join(' · ')||'—'))),
        div('onboarding-record-path',node('cloud',l('Nền tảng kết nối','Connection platform'),identity.vendor),node('home',t('plants'),siteName(actual.site_id)),node('device',l('Thiết bị đã lưu','Stored equipment'),actual.vendor_id)),
        p(l('Sơ đồ hồ sơ trong SolarOne, không phải sơ đồ đấu dây DC/AC.','SolarOne record links, not a DC/AC wiring diagram.'),'field-help'),
        div('onboarding-facts',record(l('Thương hiệu khai báo','Declared brand'),actual.metadata?.declared_equipment_brand),record('Model',identity.model),record(l('Phần mềm ghi nhận','Recorded firmware'),identity.firmware),record('Logger',identity.logger_model),record(l('Ghi nhận lần cuối','Last recorded'),actual.last_seen?date(actual.last_seen):null),record(l('Chất lượng số đo','Reading quality'),samples.length?[...new Set(samples.map(s=>t(s.quality||'UNKNOWN')))].join(' · '):l('Chưa có số đo','No readings'))),
        sourceDetails,
        p(l('Có hồ sơ không đồng nghĩa đang online hoặc đã đủ quyền điều khiển. Kiểm tra tài khoản và nghiệm thu là các bước riêng.','A record does not establish current connectivity or control permission. Account checks and commissioning are separate steps.'),'notice'),
        div('form-actions',btn(l('Đặt tên thiết bị','Name equipment'),()=>rename(actual)),btn(l('Kiểm tra tài khoản','Check account'),()=>go('settings','connections')))));
    }catch(error){if(version===generation)detail.replaceChildren(card(l('Chưa đọc được hồ sơ','Could not read details'),p(error.message,'error'),btn(l('Thử lại','Retry'),()=>inspect(d))));}
  }
  function renderList(){
    const rows=matches();
    list.replaceChildren(div('row space-between',e('h3',l('Thiết bị đã được nhận diện','Discovered equipment')),badge(String(rows.length))),
      p(l('Danh mục đã đồng bộ, không phải kết quả quét mới.','Synchronized inventory, not a fresh scan result.'),'field-help'),
      table([t('name'),l('Hãng / Model','Vendor / Model'),l('Thao tác','Action')],rows.map(d=>{
        const choose=btn(l('Xem chi tiết','Inspect equipment'),()=>inspect(d));choose.setAttribute('aria-pressed',String(selected===d.id));
        return [div('stack gap-xs',e('strong',d.name||d.vendor_id),e('small',d.vendor_id)),[d.metadata?.declared_equipment_brand||d.identity?.vendor,d.identity?.model].filter(Boolean).join(' / ')||'—',choose];
      })),...(!rows.length?[p(l('Chưa có thiết bị phù hợp. Kết nối và đồng bộ tài khoản hãng ở bước 2.','No matching equipment. Connect and synchronize a vendor account in step 2.'))]:[]));
    if(selected&&!rows.some(d=>d.id===selected)){selected='';generation++;emptyDetail();}
  }
  query.oninput=()=>draw();
  function draw(){
    state.onboarding={step,brand,kind};
    steps.replaceChildren(...labels.map((label,i)=>{const b=btn('',()=>{step=i;draw();},'onboarding-step');b.append(e('span',String(i+1),'step-number'),e('b',label));if(i===step)b.setAttribute('aria-current','step');return b;}));
    const brandChoices=div('brand-choice-grid',...brands.map(value=>{const b=btn(value,()=>{brand=brand===value?'':value;draw();},'vendor-choice');b.setAttribute('aria-pressed',String(brand===value));return b;}));
    const typeChoices=div('equipment-choice-grid',...types.map(([id,glyph,label])=>{const b=btn('',()=>{kind=id;draw();},'equipment-choice');b.append(icon(glyph),e('span',label));b.setAttribute('aria-pressed',String(kind===id));return b;}));
    if(step===0)content.replaceChildren(card(labels[0],p(l('Chọn để lọc danh mục đã đồng bộ; chọn hãng không có nghĩa đã kết nối.','Filter the synchronized inventory; selecting a vendor does not connect an account.'),'field-help'),e('h3',l('Hãng hoặc nền tảng','Brand or platform')),brandChoices,
      p(l('SOLARMAN và Eybond là nền tảng kết nối; thương hiệu trên máy có thể là Bluesun hoặc hãng khác. Chỉ lọc Bluesun khi hồ sơ đã khai báo đúng thương hiệu.','SOLARMAN and Eybond are connection platforms; equipment may carry Bluesun or another brand. Bluesun filtering uses the recorded brand, never a guess.'),'field-help'),e('h3',l('Loại thiết bị','Equipment type')),typeChoices));
    if(step===1)content.replaceChildren(card(labels[1],p(l('Quyền ứng dụng và quyền xem nhà máy tùy từng hãng. Màn kết nối sẽ kiểm tra điều kiện trước khi yêu cầu mật khẩu.','Application and plant-access requirements vary by platform. The account workflow checks prerequisites before password entry.'),'field-help'),
      div('connection-method-grid',card(l('Qua tài khoản hãng','Vendor cloud'),icon('cloud'),p(l('Người dùng liên kết tài khoản đã có. Quản trị viên chuẩn bị khóa ứng dụng nếu hãng yêu cầu.','Link an existing account. An administrator prepares application keys where the vendor requires them.')),btn(l('Mở tài khoản hãng','Open vendor accounts'),()=>go('settings','connections'),'primary')),
        card(l('Qua bộ thu thập tại trạm','On-site collector'),icon('database'),p(l('Dành cho kỹ thuật viên đã xác nhận logger, model, giao thức và mạng tại trạm.','For technicians with confirmed logger, model, protocol and site-network details.')),btn(l('Mở kết nối nội bộ','Open local connections'),()=>go('reports','agent','main'))))));
    if(step===2)content.replaceChildren(card(labels[2],p(l('Đây là liên kết đã lưu. Chuyển bước không đổi quyền sở hữu hoặc chuyển thiết bị sang nhà máy khác.','These are saved bindings. Changing steps does not transfer ownership or move equipment.')),table([t('name'),t('plants')],matches().map(d=>[d.name||d.vendor_id,siteName(d.site_id)]))));
    if(step===3)content.replaceChildren(card(labels[3],p(l('Xem chi tiết thiết bị bên phải, đặt tên dễ nhớ rồi kiểm tra hồ sơ bàn giao. Không tự nghiệm thu hay gửi lệnh điện.','Inspect equipment, set a recognizable name and review handover records. No automatic commissioning or electrical commands.')),btn(l('Mở hồ sơ bàn giao','Open handover records'),()=>go('operations','','handover'),'primary')));
    const back=btn(l('Quay lại','Back'),()=>{step--;draw();});back.disabled=step===0;
    const next=btn(l('Tiếp theo','Next'),()=>{step++;draw();},'primary');next.disabled=step===3;
    content.append(div('form-actions between',back,next));renderList();
  }
  const results=div('stack',card(l('Kết quả từ danh mục hiện có','Stored inventory results'),field(l('Tìm thiết bị','Find equipment'),query),list),detail);
  emptyDetail();draw();return div('stack onboarding-workspace',div('onboarding-layout',div('stack',steps,content),results));
}
