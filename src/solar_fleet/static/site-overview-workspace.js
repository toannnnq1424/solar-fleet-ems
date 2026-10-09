import { energyFlowCard } from './energy-flow.js';
import { measurementChart, multiMeasurementChart } from './measurement-chart.js';
import { renderControlMainWorkspace } from './control-workspace.js';
import { renderScheduleMainWorkspace } from './schedule-workspace.js';
import { renderReportWorkspace } from './report-workspace.js';
import { renderJournalMainWorkspace } from './journal-workspace.js';
import { renderIncidentWorkspace } from './incident-workspace.js';
import { l, t, number, date } from './i18n.js';
import { icon } from './icons.js';
import { plantMedia } from './plant-media.js';
import { percentageGauge } from './ui-visuals.js';
import { reportedNotice, reportedFlow, reportedEnergyChart } from './vendor-report.js';
import { equipmentPower } from './device-report.js';

// All tiles display observed/stored values only. Missing is not zero or offline.
const quantity = (value, unit) => value == null ? '—' : number(value, 1) + ' ' + unit;
const stateLabel = value => ({
  ONLINE: l('Đang nhận dữ liệu', 'Receiving data'),
  OFFLINE: l('Mất kết nối', 'Offline'),
  UNKNOWN: l('Chưa xác định', 'Unknown'),
}[value] || t(value || 'UNKNOWN'));

function equipmentTable(ctx, rows) {
  return ctx.table([l('Thiết bị', 'Equipment'), l('Hãng / Model', 'Brand / Model'),
    l('Kết nối', 'Connection'), l('Công suất', 'Power'), l('Mức pin', 'Battery level')],
    rows.map(d => [
      ctx.btn(d.name || d.serial || d.id, () => ctx.deviceDetail(d.id), 'link'),
      [d.brand, d.model].filter(Boolean).join(' · ') || '—',
      ctx.badge(stateLabel(d.status), d.status === 'ONLINE' ? 'good' : 'warn'),
      equipmentPower(ctx, d), quantity(d.soc_pct, '%'),
    ]));
}

export async function renderSubtabOverview(ctx, siteId, data) {
  const {div, e, card, p, btn, badge} = ctx;
  const ps = data.plant_status || {}, flow = data.energy_flow || {};
  const report = data.vendor_report, nativePower = report?.power || {}, energy = report?.periods || {};
  const to = tab => ctx.go('overview', tab, 'main');
  const tiles = [
    ['sun', l('Điện mặt trời', 'Solar power'), flow.pv_w, 'kW', 'solar', nativePower.pv_w, 1000],
    ['home', l('Đang tiêu thụ', 'Consumption'), flow.load_w, 'kW', 'blue', nativePower.load_w, 1000],
    ['battery', l('Mức pin', 'Battery level'), flow.battery_soc, '%', 'purple', nativePower.battery_soc, 1],
    ['chart', l('Sản lượng hôm nay', 'Generated today'), ps.today_yield_kwh, 'kWh', 'green', energy.today?.generation_kwh, 1],
    ['calendar', l('Sản lượng tháng này', 'Generated this month'), ps.month_yield_kwh, 'kWh', 'blue', energy.month?.generation_kwh, 1],
    ['bolt', l('Tiêu thụ hôm nay', 'Consumed today'), ps.today_consumption_kwh, 'kWh', 'solar', energy.today?.consumption_kwh, 1],
  ];
  const root = div('stack site-dashboard',
    div('site-metrics', ...tiles.map(([glyph,label,value,unit,tone,reported,scale]) =>
      div('site-metric', div('metric-icon ' + tone, icon(glyph)),
        div('stack gap-none', e('span', label, 'muted small'),
          e('strong', quantity((value ?? reported) == null ? null : (value ?? reported) / scale, unit)),
          e('small', value == null && reported != null ? l('Hãng báo cáo', 'Vendor reported') : value == null ? l('Chưa có số đo', 'No measurement') : l('Theo dữ liệu đã nhận', 'From received data'), 'muted'))))));
  if (report) root.append(reportedNotice(ctx, report));
  const aside = div('stack');
  const items = data.equipment?.items || [];
  aside.append(card(l('Tình trạng nhà máy', 'Plant status'),
    div('fact', e('span', l('Kết nối', 'Connection')), badge(stateLabel(ps.status), ps.status === 'ONLINE' ? 'good' : 'warn')),
    div('fact', e('span', l('Thiết bị đã liên kết', 'Linked equipment')), e('b', String(items.length))),
    div('fact', e('span', l('Đã nhận thông số', 'Readings received')), e('b', String(items.filter(d => d.reading_summary?.sample_count > 0).length))),
    div('fact', e('span', l('Có số đo mới đã xác minh', 'With verified recent readings')), e('b', String(items.filter(d => d.reading_summary?.verified_recent_count > 0).length))),
    p(l('Có thông số gốc chưa có nghĩa đã đủ dữ liệu cho biểu đồ, tính tiền hoặc điều khiển. Không có số đo mới chưa đủ để kết luận thiết bị đã tắt.', 'Native readings alone do not establish chart, billing or control readiness. Missing recent readings does not mean equipment is switched off.')),
    btn(l('Xem thiết bị & thông số gốc', 'View equipment & native readings'), () => to('devices'), 'link')));
  aside.append(card(l('Thao tác nhanh', 'Quick actions'),
    p(l('Xem trạng thái và điều kiện trước khi thay đổi thiết bị.', 'Review equipment state and requirements before making changes.')),
    div('quick-action-list',
      ...[['control','control',l('Điều khiển thiết bị','Equipment control')],
        ['calendar','schedules',l('Đặt lịch vận hành','Operating schedules')],
        ['shield','diagnostics',l('Kiểm tra lắp đặt','Installation checks')]]
        .map(([glyph,tab,label]) => {
          const action = btn(label, () => to(tab), 'secondary');
          action.prepend(icon(glyph)); return action;
        }))));
  const weather = data.weather || {};
  aside.append(card(l('Thời tiết tại trạm', 'Site weather'),
    div('row', div('metric-icon solar', icon('sun')), e('strong', quantity(weather.temperature_c, '°C'))),
    p(weather.condition && weather.condition !== 'UNKNOWN' ? weather.condition : l('Chưa có dữ liệu thời tiết', 'Weather unavailable')),
    p(data.location_info?.address || l('Chưa khai báo địa chỉ', 'Address not recorded'))));
  const dashboardGrid = div('site-dashboard-grid');
  const flowCard = energyFlowCard(ctx, reportedFlow(flow, report), to);
  flowCard.classList.add('dashboard-flow');
  dashboardGrid.append(flowCard);
  root.append(dashboardGrid);
  const chartBody = div('stack');
  try {
    const series = await ctx.api('/sites/' + encodeURIComponent(siteId) + '/telemetry-timeseries?metric=pv_w&period=today');
    chartBody.append(measurementChart(series.samples || [], l('Điện mặt trời', 'Solar power'), 'W'),
      p(l('Chỉ hiển thị các số đo đã lưu; không nội suy thời gian thiếu dữ liệu.', 'Stored observations only; missing intervals are not interpolated.')));
  } catch (error) {
    chartBody.append(p(l('Không tải được số đo: ', 'Measurements unavailable: ') + error.message));
  }
  const powerCard=card(l('Công suất trong ngày', 'Power today'), chartBody,
    btn(l('Xem lịch sử chi tiết', 'View measurement history'), () => to('data'), 'link'));
  powerCard.classList.add('dashboard-chart');
  dashboardGrid.append(powerCard);
  const [statusCard,quickCard,weatherCard]=[...aside.children];
  statusCard.classList.add('dashboard-status');
  quickCard.classList.add('dashboard-actions');
  weatherCard.classList.add('dashboard-weather');
  dashboardGrid.append(statusCard,quickCard);
  const periods = data.comparison_yield_load || {};
  const usage = data.self_consumption || {};
  const energyCard=card(l('Sản lượng & tiêu thụ','Generation & consumption'),
      div('energy-periods',...[['today',l('Hôm nay','Today')],['month',l('Tháng này','This month')],['year',l('Năm nay','This year')]]
        .map(([key,label])=>div('energy-period',e('h3',label),
          div('fact',e('span',l('Sản lượng','Generation')),e('b',quantity(periods[key]?.yield_kwh ?? energy[key]?.generation_kwh,'kWh'))),
          div('fact',e('span',l('Tiêu thụ','Consumption')),e('b',quantity(periods[key]?.consumption_kwh ?? energy[key]?.consumption_kwh,'kWh'))),
          energy[key] ? p(l('Bổ sung từ báo cáo hãng · ', 'Supplemented by vendor report · ') + energy[key].start_date + ' → ' + energy[key].end_date, 'small muted') : null))));
  if (report?.daily_energy?.length) energyCard.append(reportedEnergyChart(report));
  energyCard.classList.add('dashboard-energy');
  const usageCard=card(l('Hiệu quả sử dụng năng lượng','Energy use'),
      div('energy-use-summary',percentageGauge(usage.self_consumption_pct,l('Tự dùng','Self use')),
        div('stack',div('fact',e('span',l('Tỷ lệ tự dùng','Self consumption')),e('b',quantity(usage.self_consumption_pct,'%'))),
          div('fact',e('span',l('Tỷ lệ tự chủ','Self sufficiency')),e('b',quantity(usage.self_sufficiency_pct,'%'))))),
      p(l('Chỉ tính khi đủ dữ liệu đo và xác định được nguồn năng lượng.','Calculated only with sufficient measurements and energy-source attribution.')));
  usageCard.classList.add('dashboard-usage');
  dashboardGrid.append(energyCard,usageCard,weatherCard);
  const alerts = (data.recent_alerts || []).filter(a => !['closed','resolved'].includes(a.status));
  const equipmentCard=card(l('Thiết bị trong nhà máy', 'Plant equipment'),
      items.length ? equipmentTable(ctx, items) : p(l('Chưa có thiết bị được đồng bộ.', 'No synchronized equipment.')),
      btn(l('Xem tất cả thiết bị', 'View all equipment'), () => to('devices'), 'link'));
  equipmentCard.classList.add('dashboard-equipment');
  const alertsCard=card(l('Cảnh báo cần xem', 'Alerts to review'),
      alerts.length ? div('stack', ...alerts.map(a => div('alert-list-item',
        icon('alert'), div('stack gap-none', e('b', a.title || a.code || l('Cảnh báo','Alert')),
          e('span', t(a.status), 'small muted')))))
        : p(l('Không có cảnh báo đang mở trong dữ liệu đã nhận.', 'No open alerts in received data.')),
      btn(l('Mở trung tâm cảnh báo', 'Open alert center'), () => to('incidents'), 'link'));
  alertsCard.classList.add('dashboard-alerts');
  const commandsCard=card(l('Lệnh gần đây','Recent commands'),
      ctx.table([l('Thời điểm','Time'),l('Thao tác','Action'),l('Kết quả','Outcome')],
        (data.recent_commands||[]).map(command=>[date(command.created_at),t(command.intent),badge(command.status)])),
      btn(l('Xem nhật ký điều khiển','View command journal'),()=>to('journal'),'link'));
  commandsCard.classList.add('dashboard-commands');
  const connectionCard=card(l('Đường kết nối','Connection paths'),
      ...[['cloud_api',l('Tài khoản hãng','Vendor cloud')],['local_agent',l('Bộ thu thập tại trạm','On-site collector')],['direct_modbus',l('Kết nối thiết bị trực tiếp','Direct equipment connection')]]
        .map(([key,label])=>div('fact',e('span',label),badge(data.connectivity?.[key]?.status||'UNKNOWN'))),
      btn(l('Xem chi tiết kết nối','View connection details'),()=>to('network'),'link'));
  connectionCard.classList.add('dashboard-connections');
  dashboardGrid.append(equipmentCard,connectionCard,alertsCard,commandsCard);
  return root;
}

export async function renderSubtabData(ctx, siteId) {
  const {div,e,p,btn,card,api,select,field,table,input}=ctx;
  const options=[
    ['pv_w',l('Điện mặt trời','Solar power'),'W'],['load_w',l('Tiêu thụ','Consumption'),'W'],
    ['grid_import_w',l('Mua từ lưới','Grid import'),'W'],['grid_export_w',l('Phát lên lưới','Grid export'),'W'],
    ['battery_charge_w',l('Sạc pin','Battery charge'),'W'],['battery_discharge_w',l('Xả pin','Battery discharge'),'W'],
    ['soc_pct',l('Mức pin','Battery level'),'%']];
  const period=select([['today',l('Hôm nay','Today')],['week',l('7 ngày','7 days')],['month',l('Tháng này','This month')],['year',l('Năm nay','This year')]]);
  const out=div('stack'),summary=div('stack'),selectors=div('measurement-selectors'),checks=[];
  let requestId=0;
  for(const [i,[key,label]] of options.entries()){
    const control=input('checkbox');control.checked=i<2;control.dataset.metric=key;checks.push(control);
    const item=field(label,control);item.classList.add('series-'+i);selectors.append(item);control.onchange=loadData;
  }
  async function loadData(){
    const current=++requestId,selected=options.flatMap((v,i)=>checks[i].checked?[{key:v[0],label:v[1],unit:v[2],color:i}]:[]);
    out.replaceChildren(p(l('Đang tải số đo…','Loading measurements…')));summary.replaceChildren();
    if(!selected.length){out.replaceChildren(div('measurement-plot-scroll',multiMeasurementChart([])),p(l('Chọn ít nhất một thông số trong phần chọn hiển thị.','Choose at least one metric in the display options.')));return;}
    const results=await Promise.all(selected.map(async c=>{
      try{return {...c,...await api('/sites/'+encodeURIComponent(siteId)+'/telemetry-timeseries?'+new URLSearchParams({metric:c.key,period:period.value}))};}
      catch(err){return {...c,samples:[],failure:err.message};}
    }));
    if(current!==requestId)return;
    const rows=results.flatMap(c=>(c.samples||[]).map(s=>({...s,label:c.label}))).sort((a,b)=>Date.parse(b.source_timestamp)-Date.parse(a.source_timestamp));
    for(const c of results)summary.append(div('measurement-channel-summary series-'+c.color,e('b',c.label),p(c.failure||(
      c.reason==='AMBIGUOUS_SOURCE'?l('Cần phân định nguồn đo','Resolve ambiguous sources'):
      c.reason==='EXPORT_LIMIT'?l('Chọn khoảng ngắn hơn','Choose a shorter period'):
      number(c.samples?.length||0,0)+' '+l('số đo đã lưu','stored observations')))));
    const details=e('details','','measurement-table');details.append(e('summary',l('Bảng số đo gần nhất (tối đa 100 dòng)','Recent observations (up to 100 rows)')),
      table([l('Thời điểm','Time'),l('Thông số','Metric'),l('Giá trị','Value'),l('Đơn vị','Unit'),l('Thiết bị','Device'),l('Nguồn','Source')],rows.slice(0,100).map(s=>[date(s.source_timestamp),s.label,number(s.value),s.unit,s.device_id,t(s.source)])));
    out.replaceChildren(div('measurement-plot-scroll',multiMeasurementChart(results)),
      p(l('Chỉ nối các số đo cùng nguồn cách nhau tối đa 5 phút. Mỗi đường tối đa 1.500 điểm quan sát; không cộng các thiết bị hoặc điền khoảng thiếu.','Only same-source observations at most 5 minutes apart are joined. Up to 1,500 observed points per trace; no device summing or gap filling.'),'field-help'),details,
      btn(l('Xuất dữ liệu thiết bị','Export device data'),()=>ctx.go('reports','telemetry','analytics')));
  }
  period.onchange=loadData;
  const periodField=field(l('Khoảng thời gian','Period'),period);periodField.classList.add('measurement-period');
  const root=div('measurement-reference-layout',
    card(l('Công suất và mức pin theo thời gian','Power and battery level over time'),periodField,out),
    card(l('Chọn thông số hiển thị','Choose displayed metrics'),selectors,summary));
  await loadData();return root;
}

export async function renderSubtabDevices(ctx, siteId, data) {
  const all = data.equipment?.items || [];
  const query = ctx.input('search');
  query.placeholder = l('Tìm tên, hãng hoặc số sê-ri', 'Search name, brand or serial');
  query.setAttribute('aria-label', query.placeholder);
  const content = ctx.div('stack');
  function update() {
    const term = query.value.trim().toLocaleLowerCase();
    const rows = all.filter(d => [d.name,d.brand,d.model,d.serial].join(' ').toLocaleLowerCase().includes(term));
    content.replaceChildren(equipmentTable(ctx, rows));
  }
  query.oninput = update; update();
  return ctx.card(l('Thiết bị đã liên kết', 'Linked equipment'), query, content);
}
export async function renderSubtabControl(ctx) { return renderControlMainWorkspace(ctx); }
export async function renderSubtabSchedules(ctx) { return renderScheduleMainWorkspace(ctx); }
export async function renderSubtabIncidents(ctx) { return renderIncidentWorkspace(ctx); }
export async function renderSubtabJournal(ctx) { return renderJournalMainWorkspace(ctx); }
export async function renderSubtabDiagnostics(ctx, siteId) {
 const {card,table,select,field,input,btn,api,notice,div}=ctx;
 const root=div("stack");
 try {
 const data=await api(`/sites/${encodeURIComponent(siteId)}/diagnostics-checklist`);
 const labels={topology:l("Sơ đồ đấu nối","Topology"),meter_ct:"Meter / CT",power_direction:l("Chiều công suất","Power direction"),battery:"BMS",control_readback:l("Điều khiển & đọc lại","Control & readback"),alarms:l("Cảnh báo","Alarms")};
 root.append(card(l("Kiểm tra nghiệm thu","Commissioning checks"),
  notice("Đây là biên bản xác nhận thủ công, không tự cấp chứng chỉ hay mở quyền điều khiển.","These are manual attestations; they do not issue certificates or unlock control."),
  table([l("Hạng mục","Check"),t("status"),l("Bằng chứng","Evidence")],data.steps.map(s=>[labels[s.id],t(s.status),s.evidence||"—"]))));
 if(["Installer","Senior Engineer"].includes(ctx.state.me.user.role)) {
 const check=select(Object.entries(labels)),result=select(["pending","pass","warning","fail"].map(key=>[key,t(key)])),evidence=input("text","");
 const save=btn(l("Ghi nhận kết quả","Record result"),async()=>{
  try {await api(`/sites/${encodeURIComponent(siteId)}/diagnostics-checklist`,{site_id:siteId,check:check.value,result:result.value,evidence:evidence.value});await ctx.render();}
  catch(error){root.append(ctx.p(error.message,"bad"));}
 });
 root.append(card(l("Ghi nhận tại hiện trường","Field attestation"),field(l("Hạng mục","Check"),check),field(t("status"),result),field(l("Bằng chứng đo/quan sát","Measurement/observation evidence"),evidence),save));
 }
 } catch(error){root.append(ctx.p(error.message,"bad"));}
 return root;
}



export async function renderSubtabReports(ctx) { return renderReportWorkspace(ctx); }
export async function renderSubtabNetwork(ctx, siteId) {
  const data=await ctx.api('/sites/'+encodeURIComponent(siteId)+'/network-status');
  return networkWorkspace(ctx,siteId,data);
}
export function renderSubtabPlantInfo(ctx, siteId, data) {
  const site = data.site || {}, loc = data.location_info || {}, specs = site.declared_specs || {};
  const fields = [
    [l('Tên nhà máy','Plant name'), site.name],
    [l('Chủ sở hữu','Owner'), loc.customer || site.customer],
    [l('Địa chỉ','Address'), loc.address],
    [l('Múi giờ','Timezone'), loc.timezone],
    [l('Tọa độ','Coordinates'), loc.latitude != null && loc.longitude != null ? loc.latitude + ', ' + loc.longitude : null],
    [l('Công suất lắp đặt','Installed capacity'), quantity(site.capacity_kwp ?? loc.capacity_kwp,'kWp')],
    [l('Dung lượng pin khai báo','Declared battery capacity'), quantity(specs.battery_capacity_kwh,'kWh')],
    [l('Giới hạn phát lưới khai báo','Declared export limit'), quantity(specs.grid_limit_kw,'kW')],
    [l('Ngày khởi tạo','Created'), site.created_at ? date(site.created_at) : null],
  ];
  return ctx.card(l('Hồ sơ nhà máy','Plant information'),
    plantMedia(ctx,site),
    ctx.div('plant-info-attrs-grid', ...fields.map(([label,value]) =>
      ctx.div('plant-info-attr', ctx.e('span',label,'attr-label'),ctx.e('b',value ?? '—','attr-val')))),
    ctx.admin() ? ctx.btn(l('Chỉnh sửa hồ sơ','Edit plant information'), () => ctx.siteForm(site)) : null);
}
export async function renderSiteOverviewWorkspace(ctx, siteId) {
  const container = ctx.div('stack site-workspace');
  let data;
  try { data = await ctx.api('/sites/' + encodeURIComponent(siteId) + '/overview-summary'); }
  catch (error) {
    return ctx.empty(l('Không tải được dữ liệu nhà máy','Could not load plant data'),error.message,
      ctx.btn(l('Thử lại','Retry'),() => ctx.render()));
  }
  const site = data.site || {}, ps = data.plant_status || {};
  container.append(ctx.div('site-heading',
    ctx.div('row', plantMedia(ctx,site,true),
      ctx.div('stack gap-none', ctx.e('h2',site.name || siteId),
        ctx.e('p',data.location_info?.address || l('Chưa khai báo địa chỉ','Address not recorded'),'muted small'))),
    ctx.div('row',ctx.badge(stateLabel(ps.status),ps.status === 'ONLINE' ? 'good' : 'warn'),
      ctx.btn(l('Hồ sơ nhà máy','Plant information'), () => ctx.go('overview','plant_info','main')))));
  const subtabs = [
    ['overview',l('Tổng quan','Overview')], ['data',l('Dữ liệu','Data')], ['devices',l('Thiết bị','Equipment')],
    ['control',l('Điều khiển','Control')], ['schedules',l('Lịch vận hành','Schedules')],
    ['incidents',l('Cảnh báo','Alerts')], ['journal',l('Nhật ký','Journal')],
    ['reports',l('Báo cáo','Reports')], ['diagnostics',l('Kiểm tra lắp đặt','Installation checks')],
    ['network',l('Kết nối','Connections')], ['plant_info',l('Hồ sơ','Plant information')],
  ];
  const current = ctx.state.tab || 'overview';
  container.append(ctx.tabs(subtabs,current,tab=>ctx.go('overview',tab,'main')));
  const views = {overview:renderSubtabOverview,data:renderSubtabData,devices:renderSubtabDevices,
    control:renderSubtabControl,schedules:renderSubtabSchedules,incidents:renderSubtabIncidents,
    journal:renderSubtabJournal,diagnostics:renderSubtabDiagnostics,reports:renderSubtabReports,
    network:renderSubtabNetwork,plant_info:renderSubtabPlantInfo};
  container.append(await (views[current] || renderSubtabOverview)(ctx,siteId,data));
  return container;
}
import { networkWorkspace } from './network-workspace.js';
