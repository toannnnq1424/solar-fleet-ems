'use strict';

const $ = (selector, parent = document) => parent.querySelector(selector);
const state = {page: 'fleet', me: null, csrf: '', research: null, fleet: null, detail: null};
const titles = {
  fleet: ['FLEET OVERVIEW', 'Tổng quan công trình', 'Theo dõi công trình và trạng thái dữ liệu trong phạm vi được phân quyền.'],
  devices: ['DEVICE INVENTORY', 'Thiết bị & logger', 'Tách inverter, logger và đường truyền dữ liệu. Model chưa xác minh được giữ ở UNKNOWN.'],
  native: ['VENDOR WORKSPACE', 'Deye Native', 'Toàn bộ catalog OpenAPI cùng các nhóm quan sát trên web. Mỗi mục giữ nguyên phạm vi bằng chứng.'],
  control: ['CONTROL JOURNAL', 'Nhật ký điều khiển', 'Theo dõi người vận hành, kế hoạch, order ID và trạng thái xác minh.'],
  security: ['ACCESS & SECURITY', 'Nhật ký bảo mật', 'Đăng nhập, thay đổi credential và quyền được ghi riêng với nhật ký điều khiển.'],
  research: ['EVIDENCE LIBRARY', 'Bằng chứng & hỗ trợ', 'Mỗi kết luận gắn với nguồn, phạm vi thiết bị và phần còn chưa xác minh.'],
  integrations: ['CONNECTIONS', 'Kết nối dữ liệu', 'Kết nối API chính thức bằng credential được cấp quyền và lưu mã hóa trên máy.']
};
const labels = {
  SET_WORK_MODE: 'Chế độ làm việc', SET_SELF_CONSUMPTION: 'Ưu tiên tự tiêu thụ', SET_EXPORT_LIMIT: 'Giới hạn phát lưới',
  SET_ZERO_EXPORT: 'Không phát lưới', SET_GRID_IMPORT_LIMIT: 'Giới hạn mua điện', SET_RESERVE_SOC: 'SOC dự phòng',
  SET_MIN_SOC: 'SOC tối thiểu', SET_SHUTDOWN_SOC: 'SOC dừng pin', SET_RESTART_SOC: 'SOC khởi động lại',
  SET_MAX_CHARGE_CURRENT: 'Dòng sạc tối đa', SET_MAX_DISCHARGE_CURRENT: 'Dòng xả tối đa',
  SET_MAX_CHARGE_POWER: 'Công suất sạc tối đa', SET_MAX_DISCHARGE_POWER: 'Công suất xả tối đa',
  ENABLE_GRID_CHARGE: 'Cho phép sạc từ lưới', DISABLE_GRID_CHARGE: 'Tắt sạc từ lưới', SET_TOU: 'Lịch sử dụng pin (TOU)',
  ENABLE_TOU: 'Bật lịch TOU', DISABLE_TOU: 'Tắt lịch TOU', FORCE_CHARGE: 'Sạc cưỡng bức', FORCE_DISCHARGE: 'Xả cưỡng bức',
  STOP_FORCE_OPERATION: 'Dừng thao tác cưỡng bức', SET_PEAK_SHAVING: 'Giới hạn phụ tải đỉnh', SET_ACTIVE_POWER_LIMIT: 'Giới hạn công suất tác dụng',
  SET_REACTIVE_POWER: 'Công suất phản kháng', SET_POWER_FACTOR: 'Hệ số công suất', SET_BACKUP_EPS: 'Nguồn dự phòng EPS',
  SET_SMART_LOAD: 'Tải thông minh', SET_GENERATOR_POLICY: 'Chính sách máy phát', SET_GENERATOR_METER: 'Meter máy phát',
  SET_METER: 'Công tơ đo lường', SET_CT_RATIO: 'Tỷ số CT', POWER_ON_INVERTER: 'Bật inverter',
  POWER_OFF_INVERTER: 'Tắt inverter', RESTART_INVERTER: 'Khởi động lại inverter'
};
const errors = {
  invalid_credentials: 'Tài khoản hoặc mật khẩu chưa đúng.', authentication_required: 'Vui lòng đăng nhập.',
  login_rate_limited: 'Có nhiều lần đăng nhập thất bại. Vui lòng đợi 5 phút.',
  controller_is_read_only: 'Controller đang ở chế độ chỉ đọc.', capability_or_parameter_unverified: 'Chưa có capability và giới hạn được nghiệm thu cho thiết bị này.',
  control_role_denied: 'Vai trò hiện tại chưa có quyền điều khiển.', vendor_auth_or_permission_denied: 'Deye từ chối xác thực hoặc quyền API. Kiểm tra app, account và data center.',
  vendor_rate_limited: 'Deye yêu cầu giảm tần suất. Controller đang chờ hết thời gian backoff.',
  local_rate_budget_exhausted: 'Đã chạm ngân sách API của controller. Thử lại sau một phút.',
  poll_cooldown: 'Vừa đồng bộ. Vui lòng đợi ít nhất 15 giây.', poll_already_running: 'Một lần đồng bộ đang chạy.',
  site_access_denied: 'Bạn không có quyền truy cập công trình này.', integration_not_available: 'Kết nối chưa sẵn sàng.',
  vendor_network_outcome_unknown: 'Không nhận được phản hồi mạng từ Deye. Chưa xác định kết quả request.',
  request_validation_failed: 'Dữ liệu nhập chưa đúng định dạng.', session_or_csrf_invalid: 'Phiên đã hết hạn. Hãy đăng nhập lại.'
};

// Vendor strings only enter textContent. No HTML rendering, cookies in JS, or browser storage of credentials.
function node(tag, text = '', className = '') {
  const el = document.createElement(tag); if (text !== '') el.textContent = text; if (className) el.className = className; return el;
}
function append(parent, ...children) { for (const child of children) if (child) parent.append(child); return parent; }
function badge(text, kind = 'neutral') { return node('span', text, `badge ${kind}`); }
function button(text, action, className = '') { const b = node('button', text, className); b.type = 'button'; b.addEventListener('click', () => run(action)); return b; }
function pre(value) { return node('pre', JSON.stringify(value, null, 2), 'schema'); }
function time(value) { if (!value) return 'Chưa biết'; const t = new Date(value); return Number.isNaN(+t) ? 'Chưa biết' : t.toLocaleString('vi-VN'); }
function toast(message) { const t = $('#toast'); t.textContent = message; t.hidden = false; clearTimeout(toast.timer); toast.timer = setTimeout(() => t.hidden = true, 8000); }
async function run(action) { try { await action(); } catch (e) { toast(e.message || 'Không hoàn tất thao tác.'); } }
async function api(path, body) {
  const options = {credentials: 'same-origin', headers: {}};
  if (body !== undefined) { options.method = 'POST'; options.headers = {'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf}; options.body = JSON.stringify(body); }
  const response = await fetch('/api' + path, options);
  let result; try { result = await response.json(); } catch { throw new Error('Không đọc được phản hồi controller.'); }
  if (!response.ok) {
    if (response.status === 401 && path !== '/login') showLogin();
    const key = result.error || result.detail;
    throw new Error(errors[key] || (typeof key === 'string' ? key : 'Không hoàn tất yêu cầu.'));
  }
  return result;
}
function showLogin() {
  state.me = null; state.csrf = ''; $('#app-view').hidden = true; $('#login-view').hidden = false;
  if ($('#detail-dialog').open) $('#detail-dialog').close();
}
async function signedIn() {
  state.me = await api('/me'); state.csrf = state.me.csrf;
  $('#login-view').hidden = true; $('#app-view').hidden = false;
  $('#account-label').textContent = `${state.me.user.id} · ${state.me.user.role}`;
  $('#write-status').textContent = state.me.writes_enabled ? 'CHƯA CÓ PROFILE ĐIỀU KHIỂN' : 'CHỈ ĐỌC';
  document.querySelectorAll('[data-admin]').forEach(el => el.hidden = state.me.user.role !== 'Administrator');
  await render();
}
$('#login-form').addEventListener('submit', async e => {
  e.preventDefault(); const submit = $('#login-form button'); submit.disabled = true; $('#login-error').textContent = '';
  try { const res = await api('/login', {username: $('#username').value, password: $('#password').value}); state.csrf = res.csrf; $('#password').value = ''; await signedIn(); }
  catch (error) { $('#login-error').textContent = error.message; }
  finally { submit.disabled = false; }
});
$('#logout').addEventListener('click', () => run(async () => { await api('/logout', {}); showLogin(); }));
$('#refresh').addEventListener('click', () => run(render));
$('#close-detail').addEventListener('click', () => $('#detail-dialog').close());
document.querySelectorAll('[data-page]').forEach(b => b.addEventListener('click', () => run(async () => { state.page = b.dataset.page; await render(); })));

function panel(title, right) { const p = node('section', '', 'panel'); const h = append(node('div', '', 'panel-header'), node('h2', title), right); p.append(h); return p; }
function empty(title, description, command) {
  const el = append(node('div', '', 'empty'), node('div', '◈', 'empty-symbol'), node('h3', title), node('p', description));
  if (command) el.append(node('code', command)); return el;
}
function table(headers, rows) {
  const t = node('table'); const head = node('thead'); const tr = node('tr'); headers.forEach(h => tr.append(node('th', h))); head.append(tr); t.append(head);
  const body = node('tbody'); for (const cells of rows) { const row = node('tr'); for (const value of cells) { const td = node('td'); if (value instanceof Node) td.append(value); else td.textContent = value ?? '—'; row.append(td); } body.append(row); } t.append(body);
  return append(node('div', '', 'table-wrap'), t);
}
function statistic(title, value, detail) { return append(node('div', '', 'stat'), node('p', title), node('strong', value), node('small', detail)); }
function flow(samples = []) {
  const metric = key => { const s = samples.find(x => x.metric === key && x.quality === 'GOOD' && !x.stale); return s && s.value != null ? `${(s.value / 1000).toLocaleString('vi-VN', {maximumFractionDigits: 2})} kW` : '—'; };
  const p = panel('Dòng năng lượng', badge('NGUỒN CÓ KIỂM CHỨNG'));
  const row = node('div', '', 'flow');
  const f = (label, value, sub, cls='') => append(node('div', '', `flow-node ${cls}`), node('small', label), node('strong', value), node('small', sub));
  append(row, f('ĐIỆN MẶT TRỜI', metric('pv_power_w'), 'PV'), node('div', '', 'flow-connector'),
    f('PHỤ TẢI', metric('load_power_w'), 'Tổng tiêu thụ', 'center'), node('div', '', 'flow-connector'), f('LƯỚI ĐIỆN', metric('grid_import_w'), 'Mua từ lưới'));
  const soc=samples.find(s=>s.metric==='battery_soc_pct' && s.quality==='GOOD' && !s.stale && s.value!=null);
  const storage=append(node('div','','storage-flow'),f('PIN · SẠC',metric('battery_charge_w'),'Vào pin'),
    f('PIN · SOC',soc?`${soc.value} %`:'—','Dung lượng hiện tại'),f('PIN · XẢ',metric('battery_discharge_w'),'Từ pin'),
    f('PHÁT LƯỚI',metric('grid_export_w'),'Ra lưới'));
  p.append(row, storage, node('p', 'Luồng tổng hợp chỉ dùng metric đã xác minh đơn vị, dấu và timestamp. Số liệu native được giữ riêng ở bảng dữ liệu gốc.', 'flow-caption'));
  return p;
}
async function render() {
  const activePage = state.page; const [kicker, title, description] = titles[activePage];
  $('#page-kicker').textContent = kicker; $('#page-title').textContent = title; $('#page-description').textContent = description;
  $('#breadcrumb').textContent = 'Không gian vận hành / ' + title;
  document.querySelectorAll('[data-page]').forEach(b => b.classList.toggle('selected', b.dataset.page === activePage));
  const content = $('#content'); content.replaceChildren(node('div', 'Đang đọc dữ liệu controller…', 'loading'));
  let el;
  if (activePage === 'fleet' || activePage === 'devices') {
    const fleet = await api('/fleet'); state.fleet = fleet; el = activePage === 'fleet' ? fleetView(fleet) : deviceView(fleet);
  } else if (activePage === 'native' || activePage === 'research') {
    state.research ||= await api('/research'); el = activePage === 'native' ? nativeView(state.research) : researchView(state.research);
  } else if (activePage === 'integrations') el = await integrationView();
  else el = await logView(activePage);
  if (state.page === activePage) content.replaceChildren(el);
}
function fleetView(fleet) {
  const el = node('div'); const devices = fleet.devices; const fresh = devices.filter(d => d.online && !d.stale).length;
  el.append(append(node('div', '', 'stats'), statistic('CÔNG TRÌNH', String(fleet.sites.length), 'Trong phạm vi tài khoản'),
    statistic('THIẾT BỊ', String(devices.length), 'Theo discovery từ hãng'), statistic('DỮ LIỆU MỚI', String(fresh), 'Online và cập nhật ≤ 5 phút'),
    statistic('PROFILE ĐIỀU KHIỂN', '0', 'Chờ nghiệm thu phần cứng')));
  const p = panel('Danh sách công trình', badge('VENDOR CLOUD'));
  if (!fleet.sites.length) {
    p.append(empty('Chưa có công trình được đồng bộ', fleet.state === 'NO_INTEGRATION' ? 'Thêm kết nối Deye OpenAPI để bắt đầu discovery. Đăng nhập Deye trên web giúp đối chiếu thông tin, nhưng không thay thế credential API.' : 'Kết nối đã được cấu hình. Kiểm tra trạng thái API hoặc phạm vi công trình của tài khoản.'));
  } else p.append(table(['Công trình', 'Nguồn', 'Thiết bị', 'Múi giờ'], fleet.sites.map(s => [
    button(s.name, async () => { state.page = 'devices'; await render(); }, 'text-button'), s.vendor,
    String(devices.filter(d => d.site_id === s.id).length), s.timezone || 'UNKNOWN'])));
  el.append(p);
  const column = node('div', '', 'grid-two'); const integrity = panel('Độ tin cậy dữ liệu', badge('PILOT', 'warn'));
  integrity.append(append(node('div', '', 'panel-body'), node('p', 'Nguồn trước, con số sau.', 'eyebrow'),
    node('p', 'Dữ liệu thiếu timestamp, đơn vị hoặc ý nghĩa chiều công suất chưa được đưa vào tổng năng lượng. Không có dữ liệu không đồng nghĩa công suất bằng 0.', 'muted'),
    button('Xem phạm vi hỗ trợ →', async () => { state.page = 'research'; await render(); }, 'text-button')));
  append(column, flow(), integrity); el.append(column); return el;
}
function deviceView(fleet) {
  const p = panel('Danh sách thiết bị', badge(`${fleet.devices.length} THIẾT BỊ`));
  if (!fleet.devices.length) { p.append(empty('Chưa có thiết bị', 'Thiết bị và logger sẽ xuất hiện sau khi discovery thành công. Không tự suy ra logger từ serial của inverter.')); return p; }
  const toolbar = node('div', '', 'toolbar'); const filter = node('input'); filter.placeholder = 'Tìm theo tên, serial, loại hoặc công trình'; filter.setAttribute('aria-label', 'Tìm thiết bị'); toolbar.append(filter); p.append(toolbar);
  const rows = node('div'); p.append(rows);
  const draw = () => {
    const list = fleet.devices.filter(d => JSON.stringify([d.name, d.vendor_id, d.type, d.site_id]).toLowerCase().includes(filter.value.toLowerCase()));
    rows.replaceChildren(table(['Thiết bị / serial', 'Loại', 'Công trình', 'Model', 'Kết nối', 'Dữ liệu cuối'], list.map(d => [
      button(d.name || d.vendor_id, () => deviceDetail(d.id), 'text-button'), d.type,
      fleet.sites.find(s => s.id === d.site_id)?.name || d.site_id, d.identity.model || 'UNKNOWN',
      badge(d.stale ? 'DỮ LIỆU CŨ' : d.online ? 'ONLINE' : 'OFFLINE', d.stale || !d.online ? 'warn' : ''), time(d.last_seen)])));
  }; filter.addEventListener('input', draw); draw(); return p;
}
async function deviceDetail(id) {
  const info = await api(`/devices/${encodeURIComponent(id)}`); state.detail = info;
  $('#detail-title').textContent = info.device.name || info.device.vendor_id;
  const body = $('#detail-body'); body.replaceChildren(); const identity = node('div', '', 'identity');
  for (const [label, value] of [['Hãng', info.device.identity.vendor], ['Model', info.device.identity.model], ['Logger model', info.device.identity.logger_model],
    ['Firmware', info.device.identity.firmware], ['Protocol', info.device.identity.protocol_version], ['Quyền API', info.device.identity.privilege]])
    identity.append(append(node('div'), node('small', label), node('span', value || 'UNKNOWN')));
  body.append(identity); const tabs = node('div', '', 'tabs'); const area = node('div');
  const actions = {
    'Dữ liệu': async () => { area.replaceChildren(flow(info.latest.samples), samplesPanel(info.latest)); },
    'Lịch sử': async () => {
      const history = await api(`/devices/${id}/history`); const p = panel('Lịch sử đã lưu tại controller', badge('7 NGÀY'));
      p.append(samplesPanel({samples: history.samples}));
      const form = node('form', '', 'history-form');
      const start = node('input'); start.type='datetime-local'; start.required=true;
      const end = node('input'); end.type='datetime-local'; end.required=true;
      const points = node('input'); points.placeholder='Tên measure point gốc, phân cách bằng dấu phẩy'; points.required=true;
      for (const [label, input] of [['Từ (giờ máy)', start], ['Đến (tối đa 24h)', end], ['Measure points', points]]) form.append(append(node('label', label), input));
      const submit = node('button', 'Đọc lịch sử từ Deye'); submit.type='submit'; form.append(submit); const result=node('div');
      form.addEventListener('submit', e => { e.preventDefault(); run(async () => { submit.disabled=true; try {
        const payload = await api(`/devices/${id}/history`, {start: Math.floor(new Date(start.value).getTime()/1000), end: Math.floor(new Date(end.value).getTime()/1000), points: points.value.split(',').map(v=>v.trim()).filter(Boolean)});
        result.replaceChildren(pre(payload)); } finally {submit.disabled=false;} }); });
      area.replaceChildren(p, node('p','Đọc API theo timestamp. Trường và đơn vị chưa đối chiếu được giữ native.','muted'),form,result);
    },
    'Cảnh báo': async () => { area.replaceChildren(node('p','Đọc cảnh báo 24 giờ gần nhất từ Deye. Không có phản hồi khác với không có cảnh báo.','muted'),
      button('Đọc cảnh báo từ hãng', async () => { const payload=await api(`/devices/${id}/alerts`,{}); area.append(pre(payload)); })); },
    'Điều khiển': async () => {
      const quick = info.capabilities.filter(c=>['SET_WORK_MODE','SET_ZERO_EXPORT','SET_RESERVE_SOC','SET_TOU'].includes(c.intent));
      const p=panel('Điều khiển nhanh',badge('CẦN NGHIỆM THU','warn')); const list=node('div','','cap-list panel-body');
      quick.forEach(c=>list.append(capabilityCard(c))); p.append(list);
      const advanced=node('details'); advanced.append(node('summary','Tất cả 34 intent · Advanced'),append(node('div','','cap-list'),...info.capabilities.map(capabilityCard)));
      area.replaceChildren(node('p','Lịch native lưu trên inverter khác với automation chạy tại controller. Phiên bản này chưa chạy optimizer hoặc policy tự động.','notice'),p,advanced,
        button('Đọc cấu hình gốc từ Deye',async()=>{const config=await api(`/devices/${id}/configuration`,{}); area.append(node('p',config.freshness_verified?'Readback có freshness đã xác minh.':'Cấu hình cloud chưa có freshness được xác minh. Không dùng để cho phép lệnh.','notice'),pre(config));}));
    },
    'Nguồn gốc': async () => area.replaceChildren(pre({bindings:info.bindings, identity:info.device.identity, metadata:info.device.metadata}))
  };
  for (const [label, action] of Object.entries(actions)) { const b=button(label,async()=>{tabs.querySelectorAll('button').forEach(x=>x.classList.remove('active'));b.classList.add('active');await action();}); tabs.append(b); }
  body.append(tabs,area); tabs.firstChild.classList.add('active'); await actions['Dữ liệu']();
  if (!$('#detail-dialog').open) $('#detail-dialog').showModal();
}
function samplesPanel(latest) {
  const p = panel('Dữ liệu gốc & chất lượng',badge('VENDOR CLOUD'));
  const samples=latest.samples || [];
  if (!samples.length) p.append(node('p','Chưa có mẫu đo được lưu.','metrics-empty'));
  else p.append(table(['Metric', 'Giá trị', 'Đơn vị', 'Thời điểm nguồn', 'Chất lượng'],samples.map(s=>[
    s.metric, s.value == null ? '—' : String(s.value), s.unit || 'UNKNOWN',time(s.source_timestamp),badge(s.stale?'STALE · '+s.quality:s.quality,s.stale||s.quality!=='GOOD'?'warn':'')])));
  if (latest.native) { const details=node('details'); details.append(node('summary','Phản hồi native (đã lọc trường bí mật)'),append(node('div'),pre(latest.native)));p.append(details); } return p;
}
function capabilityCard(c) {
  const card=node('div','','cap');const text=append(node('div'),node('h3',labels[c.intent] || c.intent),node('code',c.intent),node('p',c.reason));
  const b=button('Xem trước lệnh',async()=>{const plan=await api('/plans',{device_id:state.detail.device.id,intent:c.intent,parameters:{}});toast('Đã tạo dry-run '+plan.id);});
  // All shipping profiles are UNKNOWN. A reviewed profile must add its typed form before enabling UI control.
  b.disabled=true; b.title=c.reason;append(card,text,append(node('div'),badge(c.state,'warn'),node('p',''),b));return card;
}
function nativeView(research) {
  const el=node('div');el.append(node('p','Catalog endpoint không cấp quyền gửi lệnh. Raw command, grid code, firmware và các thao tác phá hủy tiếp tục bị khóa.','notice'));
  const p=panel('Deye OpenAPI v1.0',badge(`${research.native.length} ENDPOINT`));const toolbar=node('div','','toolbar');const filter=node('input');filter.placeholder='Tìm battery, tou, workMode, smartload…';filter.setAttribute('aria-label','Tìm endpoint');toolbar.append(filter);p.append(toolbar);const list=node('div','','panel-body');p.append(list);
  const draw=()=>{list.replaceChildren();for(const row of research.native.filter(x=>x.path.toLowerCase().includes(filter.value.toLowerCase()))){const detail=node('details');append(detail,append(node('summary'),badge(row.mode,row.mode==='CONTROL'?'warn':'neutral'),node('code',`${row.method} ${row.path}`)),append(node('div'),node('p',row.reason,'muted'),badge('HARDWARE UNKNOWN','warn'),pre(row.request_schema),node('p',row.evidence_ids.join(' · '),'muted')));list.append(detail);}};
  filter.addEventListener('input',draw);draw();el.append(p);
  const observed=research.observed_ui;const ui=panel('Nhóm quan sát trên Deye Cloud web',badge('E · UI OBSERVED','warn'));const groups=node('div','','panel-body');
  groups.append(node('p',observed.reason,'muted'));
  for(const group of observed.groups){const details=node('details');details.append(node('summary',group.name),append(node('div'),node('p',group.state,'muted'),append(node('div','','native-groups'),...group.fields.map(f=>node('span',f)))));groups.append(details);}ui.append(groups);el.append(ui);return el;
}
function researchView(research) {
  const el=node('div');el.append(node('p','Chưa vendor nào đạt Supported theo tiêu chí nghiệm thu end-to-end. Deye là adapter đầu tiên; các hệ sinh thái khác đang ở giai đoạn nghiên cứu hoặc chờ quyền/tài liệu.','notice'));
  const vendors=panel('Phạm vi tương thích',badge(`${research.vendors.length} PHẠM VI`));
  for(const vendor of research.vendors){const d=node('details');d.append(node('summary',vendor.vendor || vendor.ecosystem || vendor.scope || 'Vendor'),append(node('div'),pre(vendor)));vendors.append(d);}el.append(vendors);
  const sources=panel('Thư viện nguồn',badge(`${research.sources.length} NGUỒN`));
  for(const source of research.sources){const item=node('div','','source-item');const title=source.title || source.id;const link=node('a',title);try{const url=new URL(source.url);if(url.protocol==='https:'){link.href=url.href;link.target='_blank';link.rel='noreferrer noopener';}}catch{}
    append(item,badge(source.grade || source.evidence_grade || '?','neutral'),node('span',' '+source.id+' · '),link,node('p',source.scope || source.claims || source.status || ''),node('p',source.limitations || source.open_questions || ''));sources.append(item);}el.append(sources);return el;
}
async function integrationView() {
  const rows=await api('/integrations');const p=panel('Kết nối được cấu hình',button('Đồng bộ chỉ đọc',async()=>{await api('/sync',{});await render();toast('Đã hoàn tất lượt đồng bộ. Xem trạng thái từng kết nối.');},'secondary'));
  if(!rows.length) p.append(empty('Kết nối Deye OpenAPI', 'Dừng controller rồi chạy lệnh dưới đây trong terminal. Nhập App ID, App Secret và tài khoản ngay trên máy; chúng được mã hóa bằng khóa lưu trong OS keyring.','solar-fleet add-deye --name "Deye EU" --region eu'));
  else p.append(table(['Kết nối','Data center','Trạng thái','Lần thử gần nhất'],rows.map(r=>[r.name,r.region,append(node('div'),badge(r.status?.state || 'CHƯA THỬ',r.status?.state==='CONNECTED'?'':'warn'),node('small',errors[r.status?.error] || r.status?.error || '')),time(r.status?.last_attempt)])));
  p.append(append(node('div','','panel-body'),node('p','Phiên Deye trên web và OpenAPI app là hai cơ chế xác thực riêng. Kết nối này gọi HTTPS tới data center đã chọn. Không trích cookie hay token trình duyệt.','muted')));return p;
}
async function logView(page) {
  const data=await api('/audit/'+page);const el=node('div');el.append(node('p',data.hash_chain_valid?'Chuỗi hash audit hợp lệ trong database hiện tại. Checkpoint ngoài máy vẫn cần cho môi trường production.':'Chuỗi audit không hợp lệ. Cần kiểm tra tính toàn vẹn database.','notice'));
  const p=panel(page==='control'?'Nhật ký điều khiển của platform':'Nhật ký bảo mật',badge(`${data.entries.length} BẢN GHI`));
  const filters=node('div','','toolbar filter-bar');const search=node('input');search.placeholder='Lọc người vận hành, site, thiết bị, lệnh, trạng thái, thời gian';search.setAttribute('aria-label','Lọc nhật ký');filters.append(search);p.append(filters);const area=node('div');p.append(area);
  const draw=()=>{const rows=data.entries.filter(r=>JSON.stringify(r.body).toLowerCase().includes(search.value.toLowerCase()));
    if(!rows.length) area.replaceChildren(empty('Chưa có bản ghi phù hợp',data.entries.length?'Không có bản ghi khớp bộ lọc.':page==='control'?'Dry-run và mọi chuyển trạng thái lệnh sẽ được ghi tại đây.':'Sự kiện đăng nhập và thay đổi quyền sẽ xuất hiện tại đây.'));
    else area.replaceChildren(table(['Thời gian','Người vận hành','Sự kiện','Trạng thái / chi tiết'],rows.map(r=>[time(r.body.timestamp),r.body.operator || 'controller',r.body.event,pre(r.body)])));};search.addEventListener('input',draw);draw();el.append(p);
  if(page==='control'){const commands=await api('/commands');const q=panel('Trạng thái lệnh',badge(`${commands.length} LỆNH`));q.append(commands.length?table(['ID','Thiết bị','Trạng thái','Order IDs','Lỗi'],commands.map(c=>[c.id,c.device_id,badge(c.status,c.status==='VERIFIED'?'':'warn'),c.order_ids,c.error || '—'])):node('p','Chưa có lệnh được xác nhận.','metrics-empty'));el.append(q);}return el;
}

signedIn().catch(() => showLogin());
