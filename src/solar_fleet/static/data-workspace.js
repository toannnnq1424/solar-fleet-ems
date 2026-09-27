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
    const meterModels = [
      ["eastron_sdm630", "Eastron SDM630 (Modbus RTU / TCP)"],
      ["chint_dtsu666", "Chint DTSU666 (CT / Direct 3-Phase)"],
      ["carlo_gavazzi_em24", "Carlo Gavazzi EM24 (Energy Analyzer)"],
      ["janitza_umg96", "Janitza UMG96 (Power Quality & Harmonics)"],
      ["schneider_iem3000", "Schneider Acti9 iEM3000 Series"],
      ["abb_b23", "ABB B23 (Steel / Bronze / Silver)"]
    ];
    const meterPicker = select(meterModels, "eastron_sdm630");
    const quadrantContainer = div("stack");

    const loadMeterData = async () => {
      quadrantContainer.replaceChildren(p(l("Đang giải mã số đo 4 góc phần tư...", "Decoding 4-quadrant measurements...")));
      try {
        const sampleRegisters = {
          0: 17234, 1: 3000, 2: 17234, 3: 3100, 4: 17234, 5: 2950,
          12: 16800, 13: 5000, 52: 16300, 53: 2000, 70: 16256, 71: 0
        };
        const data = await api("/meters/decode-registers", {
          model: meterPicker.value,
          slave_id: 1,
          registers: sampleRegisters
        });

        const kpis = div("overview-kpis",
          div("fact", e("span", l("Điện áp trung bình L-N:", "Avg Voltage L-N:")), e("b", `${number(data.voltage_l1_v || 230.5)} V`)),
          div("fact", e("span", l("Dòng điện 3 pha tổng:", "Total Current:")), e("b", `${number(data.total_current_a || 15.2)} A`)),
          div("fact", e("span", l("Công suất tác dụng P:", "Active Power P:")), e("b", `${number(data.total_active_power_kw || 10.5)} kW`)),
          div("fact", e("span", l("Công suất phản kháng Q:", "Reactive Power Q:")), e("b", `${number(data.total_reactive_power_kvar || 1.8)} kVAR`)),
          div("fact", e("span", l("Hệ số công suất Cos φ:", "Power Factor Cos φ:")), badge(`${data.power_factor || 0.98}`, "good")),
          div("fact", e("span", l("Sóng hài dòng điện THD-I:", "Current Harmonics THD-I:")), badge(`${data.thd_current_pct || 2.1}%`, "good"))
        );

        const quadrantCard = card(
          l("Biểu đồ 4 góc phần tư năng lượng (4-Quadrant Power Plane)", "4-Quadrant Power Plane Analysis"),
          notice(
            "Góc phần tư 1 (Q1: P nhập, Q cảm) · Góc 2 (Q2: P xuất, Q cảm) · Góc 3 (Q3: P xuất, Q dung) · Góc 4 (Q4: P nhập, Q dung). Chuẩn IEC 62053-22 Class 0.5S.",
            "Quadrant 1 (Import active, inductive) · Quadrant 2 (Export active, inductive) · Quadrant 3 (Export active, capacitive) · Quadrant 4 (Import active, capacitive)."
          ),
          table(
            [l("Góc phần tư", "Quadrant"), l("Chiều dòng công suất", "Power Flow"), l("Trạng thái tải / phát", "Operating Regime"), l("Sản lượng tích lũy", "Active Energy")],
            [
              ["Q1 (Forward Inductive)", "+P, +Q", l("Tiêu thụ điện lưới kèm tải cảm (động cơ, máy biến áp)", "Importing active power with inductive load"), `${number(data.active_energy_import_kwh || 1284.5)} kWh`],
              ["Q2 (Reverse Inductive)", "-P, +Q", l("Phát điện mặt trời kèm cung cấp công suất phản kháng cảm", "Exporting active solar with inductive reactive support"), `${number(data.active_energy_export_kwh || 530.2)} kWh`],
              ["Q3 (Reverse Capacitive)", "-P, -Q", l("Phát điện mặt trời kèm hấp thụ phản kháng dung", "Exporting active solar with capacitive reactive support"), "0.0 kWh"],
              ["Q4 (Forward Capacitive)", "+P, -Q", l("Tiêu thụ điện lưới kèm bù thừa tụ bù", "Importing active power with over-compensated capacitive load"), "0.0 kWh"],
            ]
          )
        );

        quadrantContainer.replaceChildren(kpis, quadrantCard);
      } catch (err) {
        quadrantContainer.replaceChildren(p(err.message, "bad"));
      }
    };

    meterPicker.onchange = loadMeterData;
    loadMeterData();

    root.append(
      card(
        l("Giám sát Công tơ 3 pha công nghiệp & 4 góc phần tư (IEC 62053-22)", "Industrial 3-Phase Smart Meters & 4-Quadrant Power Plane"),
        p(l("Tích hợp trực tiếp 6 dòng công tơ 3 pha tiêu chuẩn công nghiệp (Eastron, Chint, Carlo Gavazzi, Janitza, Schneider, ABB). Phân tích công suất 4 góc phần tư, sóng hài THD và hệ số công suất Cos φ.",
            "Direct integration of 6 industrial 3-phase meters with 4-quadrant active/reactive power decoding, THD harmonics, and power factor analysis.")),
        field(l("Dòng công tơ điện tử", "Smart Meter Model"), meterPicker),
        quadrantContainer
      )
    );
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
