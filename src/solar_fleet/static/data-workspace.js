import { l, t, date } from "./i18n.js";
import { renderMappingWorkspace } from "./mapping-workspace.js";

const aliases = {quality: "overview", sync: "sync_logs", agents: "agent"};
const sections = new Set(["overview", "sources", "meters", "cloud", "agent", "collection", "mapping", "diagnostics", "sync_logs"]);

export function dataWorkspaceSection(state) {
  const section = state.section === "main" ? state.tab || "overview" : state.section;
  return aliases[section] || section;
}

export function ownsDataWorkspaceRoute(state) {
  return state.page === "reports" && sections.has(dataWorkspaceSection(state));
}

export async function renderDataConnectionsWorkspace(ui, forcedSection) {
  const {state, div, e, p, btn, badge, number, card, table, tabs, select, field, notice, api, go, form, input, showDialog, closeDialog, refresh, admin} = ui;
  const root=div("stack data-connections-root");
  const selected=forcedSection||dataWorkspaceSection(state);
  const key=aliases[selected]||selected||'overview';
  root.append(tabs([['overview',l('Tổng quan','Overview')],['sources',l('Nguồn dữ liệu','Sources')],['meters',l('Công tơ 3 pha','Smart Meters')],['cloud',l('Tài khoản cloud','Cloud accounts')],['agent','Local Agent'],['collection',l('Thu thập','Collection')],['mapping',l('Ánh xạ','Mapping')],['diagnostics',l('Chẩn đoán','Diagnostics')],['sync_logs',l('Nhật ký đồng bộ','Sync log')],['telemetry',l('Dữ liệu đo','Measurements')]],key,
    tab=>go('reports',tab,'main')));
  if(key==='meters') {
    const meters = (state.fleet.devices || []).filter(d => (!state.site || d.site_id === state.site) && /meter/i.test(d.type || ""));
    root.append(card(l("Công tơ & số đo đã thu thập", "Meters & collected observations"),
      p(l("Số đo lấy từ thiết bị đã liên kết. Chưa có dữ liệu thì không suy đoán công suất, điện năng hay chất lượng điện.", "Measurements come from bound devices. Missing power, energy or quality readings are not synthesized.")),
      table([l("Thiết bị", "Device"), l("Model", "Model"), l("Thao tác", "Action")], meters.map(d => [d.name || d.id, d.model || "—",
        btn(l("Mở dữ liệu thiết bị", "Open device measurements"), () => go("devices", d.id))]))));
    return root;
  }
  if(key==='cloud') {
    root.append(card(l('Tài khoản cloud dùng chung','Shared cloud accounts'),p(l('Thêm kết nối, kiểm tra và đồng bộ thiết bị tại trang tài khoản hãng.','Add connections, check access and synchronize devices in vendor accounts.')),
      btn(l('Mở tài khoản hãng','Open vendor accounts'),()=>go('settings','connections'),'primary')));
    return root;
  }
  if(key==='agent') {
    root.append(card('Local Agent',p(l('Quản lý agent đã đăng ký và khóa gửi dữ liệu tại chỗ.','Manage enrolled agents and local ingestion credentials.')),
      btn(l('Quản lý agent','Manage agents'),()=>go('settings','','agents'))));return root;
  }
  if(key==='collection') {
    if(!admin()){root.append(p(l('Cần quyền quản trị để thay đổi chu kỳ thu thập.','Administrator access is required for collection policies.')));return root;}
    const data=await api('/collection');
    const editPolicy=(c)=>{
      const interval=input('number',c.policy.interval_seconds), limit=input('number',c.policy.max_devices_per_poll);
      interval.min=String(c.minimum_interval_seconds||120);interval.max='3600';limit.min='1';limit.max='50';
      const f=form(async()=>{await api('/collection/'+encodeURIComponent(c.integration_id),{revision:c.policy.revision,interval_seconds:Number(interval.value),max_devices_per_poll:Number(limit.value)});closeDialog();await refresh();});
      f.finish(field(l('Chu kỳ (giây)','Interval (seconds)'),interval),field(l('Thiết bị mỗi lượt','Devices per poll'),limit));showDialog(c.name,f);
    };
    root.append(card(l('Chính sách thu thập','Collection policies'),table([t('name'),l('Chu kỳ (giây)','Interval (seconds)'),l('Thiết bị mỗi lượt','Devices per poll'),t('status'),l('Lần thử gần nhất','Last attempt'),l('Thao tác','Action')],data.connections.map(c=>[
      c.name,c.policy.interval_seconds,c.policy.max_devices_per_poll,c.state?.state||'UNKNOWN',date(c.state?.last_attempt),admin()?btn(l('Chỉnh sửa','Edit'),()=>editPolicy(c)):'—']))));
    return root;
  }
  const plantId=state.site||(state.fleet.sites||[])[0]?.id;
  if(!plantId){root.append(p(l('Thêm nhà máy và kết nối trước.','Add a plant and connection first.')));return root;}
  const picker=select((state.fleet.sites||[]).map(s=>[s.id,s.name]),plantId);
  picker.onchange=()=>{state.site=picker.value;ui.render();};root.append(field(t('plants'),picker));
  if(key==='mapping') {
    root.append(await renderMappingWorkspace(ui,plantId));
    return root;
  }
  const data=await api('/data-sources?site_id='+encodeURIComponent(plantId));
  if(key==='sync_logs') {
    root.append(card(l('Sự kiện đồng bộ','Synchronization events'),table([l('Thời điểm','Time'),l('Sự kiện','Event'),l('Chi tiết','Details')],
      data.recent_sync_errors.map(r=>[date(r.time),r.title,r.desc||'—']))));
  } else if(key==='diagnostics') {
    root.append(card(l('Chất lượng dữ liệu','Data quality'),p(data.diagnostics.status),p(data.diagnostics.data_freshness)),
      btn(l('Nghiệm thu / bàn giao','Commissioning / handover'),()=>{state.site=plantId;return go('operations','','handover');}));
  } else {
    root.append(card(l('Nguồn dữ liệu đã kết nối','Configured data sources'),table([t('name'),l('Loại','Type'),t('status'),l('Quyền','Access'),l('Đồng bộ cuối','Last sync')],
      data.sources.map(s=>[s.name,s.type,s.status,s.permissions,date(s.last_sync)]))),
      card(l('Ưu tiên nguồn','Source priority'),p(data.priority.map(s=>s.title).join(' → ')),
        btn(l('Sửa chính sách nguồn','Edit source policy'),()=>go('settings','','source_policy'))),
      notice('Trạng thái đã đăng ký agent không đồng nghĩa thiết bị đang trực tuyến. Dữ liệu thiếu nguồn xác minh chưa được dùng làm chỉ số vận hành.',
        'Agent enrollment does not establish online status. Unverified measurements are not used as operational KPIs.'));
  }
  return root;
}

export function createDataWorkspace(ui) {
  return {view:section=>renderDataConnectionsWorkspace(ui,section)};
}
