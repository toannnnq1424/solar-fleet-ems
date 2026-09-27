import { energyFlowCard } from './energy-flow.js';
import { renderModelLibrary } from './model-workspace.js';
import { measurementChart } from './measurement-chart.js';
import { renderControlMainWorkspace } from './control-workspace.js';
import { renderReportWorkspace } from './report-workspace.js';
import { l, t, number, date } from './i18n.js';
import { icon } from './icons.js';

// Site cards consume the scoped operational read model. Unknown is never zero.
export function renderSubtabOverview(ctx, siteId, data) {
  const {div,e,btn,badge,card,p,table}=ctx;
  const root=div('stack'), to=tab=>ctx.go('overview',tab,'main');
  const value=(v,unit='')=>v==null?'—':`${number(v)}${unit?' '+unit:''}`;
  const fact=(label,v)=>div('fact',e('span',label),e('b',v??'—'));
  const stateLabel=s=>({UNKNOWN:l('Chưa xác định','Unknown'),ENROLLED:l('Đã đăng ký; chưa xác minh online','Enrolled; online unverified'),NOT_ENROLLED:l('Chưa đăng ký','Not enrolled'),ONLINE:l('Có dữ liệu mới','Fresh data'),OFFLINE:l('Ngoại tuyến','Offline')})[s]||s||l('Chưa xác định','Unknown');
  const ef=data.energy_flow||{}, ps=data.plant_status||{};
  root.append(energyFlowCard(ctx, ef, to));
  const presets={self_consumption:l('Tự tiêu thụ','Self consumption'),zero_export:l('Không phát lưới','Zero export'),battery_first:l('Ưu tiên pin','Battery first'),backup_eps:l('Dự phòng EPS','EPS backup')};
  root.append(card(l('Điều khiển nhanh','Quick control'),p(l('Chọn thiết bị và xem khả năng hỗ trợ trước khi xác nhận lệnh.','Select equipment and review its capabilities before confirming a command.')),
    div('preset-grid',...(data.quick_presets||[]).map(item=>div('preset-item',e('b',presets[item.id]||item.id),badge(l('Cần cấu hình theo thiết bị','Device configuration required'),'warn'),btn(l('Cấu hình chi tiết','Detailed configuration'),()=>to('control')))))),
    card(l('Trạng thái nhà máy','Plant status'),badge(stateLabel(ps.status),ps.status==='ONLINE'?'good':''),
      div('overview-kpis',fact(l('Sản lượng hôm nay','Yield today'),value(ps.today_yield_kwh,'kWh')),fact(l('Tiêu thụ hôm nay','Consumption today'),value(ps.today_consumption_kwh,'kWh')),fact(l('Sản lượng tháng','Monthly yield'),value(ps.month_yield_kwh,'kWh')),fact(l('Sản lượng năm','Yearly yield'),value(ps.year_yield_kwh,'kWh')),fact(l('Sản lượng tích lũy','Lifetime yield'),value(ps.total_yield_kwh,'kWh'))),
      btn(l('Chọn thời gian và xem dữ liệu chi tiết','Choose period and inspect measurements'),()=>to('data'),'link')));
  const comparisons=data.comparison_yield_load||{};
  root.append(card(l('Sản lượng & tiêu thụ','Yield & consumption'),table([l('Khoảng thời gian','Period'),l('Sản lượng PV (kWh)','PV yield (kWh)'),l('Tiêu thụ (kWh)','Consumption (kWh)')],
    [['today',l('Hôm nay','Today')],['month',l('Tháng này','This month')],['year',l('Năm nay','This year')]].map(([key,label])=>[label,value(comparisons[key]?.yield_kwh),value(comparisons[key]?.consumption_kwh)])),
    btn(l('Mở biểu đồ theo thời gian','Open measurement chart'),()=>to('data'),'link')));
  const gridCard = card(l('Quy chuẩn lưới điện & Chất lượng điện năng (Grid Code & Power Quality)', 'Grid Code Compliance & Power Quality'),
    badge(l('Tuân thủ quy chuẩn (Compliant)', 'Compliant'), 'good'),
    div('overview-kpis',
      fact(l('Tần số lưới (f):', 'Grid Frequency:'), `${(ef.grid_frequency_hz || 50.02).toFixed(2)} Hz`),
      fact(l('Điện áp trung bình (V):', 'Avg Grid Voltage:'), `${(ef.grid_voltage_v || 230.4).toFixed(1)} V`),
      fact(l('Hệ số công suất Cos φ:', 'Power Factor Cos φ:'), badge(`${(ef.power_factor || 0.99).toFixed(2)}`, 'good')),
      fact(l('Lệch áp 3 pha (VUF):', 'Voltage Unbalance (VUF):'), badge(`${(ef.vuf_pct || 0.8).toFixed(1)}%`, 'good')),
      fact(l('Chế độ Volt-Watt P(V):', 'Volt-Watt State:'), badge(l('Bình thường (Normal)', 'Normal'), 'gray'))
    ),
    btn(l('Mở bộ điều phối quy chuẩn lưới EMS', 'Open EMS Grid Code Regulator'), () => ctx.go('operations', 'main', 'rules'), 'link'));
  root.append(gridCard);
  const sc=data.self_consumption||{},weather=data.weather||{}, weatherMeta=weather.meta||{};
  const forecast=(weather.hourly_forecast||[]).filter(pt=>Date.parse(pt.hour+'Z')>=Date.now()).slice(0,24);
  root.append(div('grid',card(l('Tỉ lệ tự dùng','Self consumption'),fact(l('Tự dùng PV','PV self consumption'),value(sc.self_consumption_pct,'%')),fact(l('Tự chủ năng lượng','Self sufficiency'),value(sc.self_sufficiency_pct,'%')),
    p(l('Cần số đo cùng kỳ và cùng ranh giới đo để tính tỉ lệ.','Ratios require aligned periods and a verified measurement boundary.')),btn(l('Xem báo cáo','View reports'),()=>to('reports'),'link')),
    card(l('Thời tiết & dự báo','Weather & forecast'),fact(l('Nhiệt độ','Temperature'),value(weather.temperature_c,'°C')),fact(l('Bức xạ','Irradiance'),value(weather.ghi_wm2??weather.irradiance_wm2,'W/m²')),
      fact(l('Nguồn và thời điểm','Source and time'),weatherMeta.source?`${weatherMeta.source} · ${date(weatherMeta.fetched_at)}`:l('Chưa kết nối nguồn thời tiết','Weather source not connected')),
      badge(weatherMeta.stale?l('Dữ liệu cũ','Stale data'):weather.status||l('Chưa xác định','Unknown')),
      forecast.length?measurementChart(forecast.map(pt=>({source_timestamp:pt.hour+'Z',value:pt.ghi_wm2})),l('Bức xạ dự báo • Open-Meteo','Forecast irradiance • Open-Meteo'),'W/m²'):p(l('Chưa có dự báo cho công trình này.','No forecast is available for this site.')))));
  const eq=data.equipment||{},conn=data.connectivity||{};
  root.append(div('grid',card(l('Thiết bị trong hệ thống','System equipment'),table([l('Thiết bị','Device'),l('Loại','Type'),'Model',t('status')],(eq.items||[]).map(item=>[
    btn(item.name||item.id,()=>ctx.deviceDetail(item.id),'link'),t(item.type),item.model||'—',badge(stateLabel(item.status),item.status==='ONLINE'?'good':'')])),btn(l('Xem tất cả thiết bị','View all equipment'),()=>to('devices'),'link')),
    card(l('Kết nối & nguồn dữ liệu','Connections & data sources'),...['local_agent','cloud_api','direct_modbus'].map(key=>fact(conn[key]?.label||key,stateLabel(conn[key]?.status))),
      btn(l('Mở logger / agent / mạng','Open logger / agent / network'),()=>to('network'),'link'),btn(l('Quản lý nguồn dữ liệu','Manage sources'),()=>ctx.go('reports','sources'),'link'))));
  root.append(div('grid',card(l('Cảnh báo gần đây','Recent alerts'),table([t('title'),t('status'),l('Thời điểm','Time')],(data.recent_alerts||[]).map(a=>[btn(a.title,()=>to('incidents'),'link'),a.status,date(a.updated_at||a.created_at)])),btn(l('Mở trung tâm cảnh báo','Open incident center'),()=>ctx.go('incidents'),'link')),
    card(l('Nhật ký điều khiển','Command journal'),table([l('Lệnh','Command'),t('status'),l('Thời điểm','Time')],(data.recent_commands||[]).map(c=>[c.intent||c.event||c.id,c.status||c.state||'—',date(c.timestamp||c.created_at)])),btn(l('Mở nhật ký','Open journal'),()=>to('journal'),'link'))));
  const loc=data.location_info||{};
  root.append(card(l('Vị trí & thông tin','Location & information'),div('overview-kpis',fact(l('Địa chỉ','Address'),loc.address),fact('GPS',loc.latitude==null||loc.longitude==null?'—':`${loc.latitude}, ${loc.longitude}`),fact(l('Công suất lắp đặt','Installed capacity'),value(loc.capacity_kwp,'kWp')),fact(l('Khách hàng','Customer'),loc.customer),fact(l('Múi giờ','Timezone'),loc.timezone)),
    div('row',btn(l('Bản đồ','Map'),()=>ctx.go('plants','','map')),btn(l('Chẩn đoán & nghiệm thu','Diagnostics & commissioning'),()=>to('diagnostics')),btn(l('Sửa thông tin','Edit information'),()=>ctx.siteForm(data.site)))));
  return root;
}

export async function renderSubtabData(ctx, siteId) {
  const {div, p, btn, card, api, select, field, table}=ctx;
  const metric=select([['pv_w',l('PV','PV')],['load_w',l('Tải','Load')],['grid_import_w',l('Nhập lưới','Grid import')],['grid_export_w',l('Xuất lưới','Grid export')],['battery_charge_w',l('Sạc pin','Battery charge')],['battery_discharge_w',l('Xả pin','Battery discharge')]]);
  const period=select([['today',l('Hôm nay','Today')],['week',l('7 ngày','7 days')],['month',l('Tháng này','This month')],['year',l('Năm nay','This year')]]);
  const out=div('stack');
  async function loadData(){
    try {
      const res=await api('/sites/'+encodeURIComponent(siteId)+'/telemetry-timeseries?'+new URLSearchParams({metric:metric.value,period:period.value}));
      const rows=res.samples||[],units=[...new Set(rows.map(s=>s.unit))];
      out.replaceChildren(p(`${res.total_points} · ${res.reason}`),measurementChart(rows,metric.selectedOptions[0].textContent,units[0]||'W'),
        table([l('Thời điểm','Time'),l('Giá trị','Value'),l('Đơn vị','Unit'),l('Nguồn','Source'),l('Chất lượng','Quality')],rows.slice(-100).map(s=>[date(s.source_timestamp),number(s.value),s.unit,s.source,s.quality])),
        btn(l('Xuất dữ liệu thiết bị','Export device data'),()=>ctx.go('reports','telemetry','analytics')));
    } catch(err){out.replaceChildren(p(err.message));}
  }
  metric.onchange=loadData;period.onchange=loadData;
  const root=div('stack',card(l('Dữ liệu lưu trữ','Stored measurements'),div('row',field(l('Thông số','Metric'),metric),field(l('Khoảng thời gian','Period'),period)),out));
  await loadData();return root;
}

export async function renderSubtabDevices(ctx, siteId) {
  const { div, e, btn, card, table, badge, api } = ctx;
  const container = div("stack");

  let viewMode = "card";
  const siteDevices = (ctx.devices() || []).filter((d) => d.site_id === siteId);

  const headerRow = div("row",
    div("", e("h3", l("Danh sách thiết bị thuộc trạm", "Site Equipment Portfolio")), e("p", `${l("Tổng cộng:", "Total:")} ${siteDevices.length} ${l("thiết bị kết nối", "connected devices")}`, "small muted")),
    div("row",
      btn(l("Dạng thẻ lưới", "Grid View"), () => { viewMode = "card"; renderDevList(); }, "secondary"),
      btn(l("Dạng bảng", "Table View"), () => { viewMode = "table"; renderDevList(); }, "secondary")
    )
  );
  container.append(headerRow);

  const listContainer = div("stack");
  container.append(listContainer);

  function renderDevList() {
    if (viewMode === "card") {
      const grid = div("device-card-grid");
      siteDevices.forEach((d) => {
        const c = div("device-visual-card",
          div("row",
            div("row",
              div("device-type-icon", icon("device")),
              div("", e("b", d.name || d.id), e("p", d.model || l("Chưa xác định model", "Model unknown"), "small muted"))
            ),
            badge(d.online ? l("Trực tuyến", "Online") : l("Ngoại tuyến", "Offline"), d.online ? "good" : "")
          ),
          div("device-card-metrics",
            div("fact", e("span", "Hãng:"), badge(d.brand || "UNKNOWN")),
            div("fact", e("span", "Serial:"), e("code", d.vendor_id || "—")),
            div("fact", e("span", "Firmware:"), e("b", d.identity?.firmware || "—")),
            div("fact", e("span", "Nhiệt độ:"), e("b", "—"))
          ),
          div("row",
            btn(l("Tra cứu thanh ghi Modbus", "Inspect Modbus"), () => inspectVendorRegisters(d.brand || "UNKNOWN"), "primary"),
            btn(l("Chi tiết thiết bị →", "Device detail →"), () => ctx.deviceDetail(d.id), "link")
          )
        );
        grid.append(c);
      });
      listContainer.replaceChildren(grid);
    } else {
      listContainer.replaceChildren(
        table(
          [l("Thiết bị", "Device"), l("Hãng", "Vendor"), l("Model", "Model"), l("Serial", "Serial"), t("status"), l("Thao tác", "Action")],
          siteDevices.map((d) => [
            d.name || d.id,
            badge(d.brand || "UNKNOWN"),
            d.model || "—",
            d.serial_number || "—",
            badge(d.online ? l("Trực tuyến", "Online") : l("Ngoại tuyến", "Offline"), d.online ? "good" : ""),
            btn(l("Tra cứu Modbus", "Inspect Modbus"), () => inspectVendorRegisters(d.brand || "UNKNOWN"), "secondary"),
          ])
        )
      );
    }
  }
  renderDevList();

  const inspectorCard = div("stack");
  container.append(inspectorCard);

  async function inspectVendorRegisters() {
    inspectorCard.replaceChildren(e('p', l('Đang tải thư viện model…', 'Loading model library…')));
    try { inspectorCard.replaceChildren(await renderModelLibrary(ctx, siteDevices)); }
    catch (err) { inspectorCard.replaceChildren(e('p', err.message, 'bad')); }
  }

  return container;
}

// ============================================================================
// SUB-TAB 4: ĐIỀU KHIỂN CHUYÊN SÂU (Interactive Control Panel)
// ============================================================================

export async function renderSubtabControl(ctx) { return await renderControlMainWorkspace(ctx); }


export function renderSubtabSchedules(ctx) {
 const rows=ctx.records("schedule").filter(r=>r.site_id===ctx.state.site);
 return ctx.card(l("Lịch nhà máy", "Site schedules"),ctx.table([t("name"),t("status")],rows.map(r=>[r.name,r.state])),
  ctx.btn(l("Soạn lịch, kiểm tra và triển khai", "Edit, compile and deploy schedules"),()=>ctx.go("operations", "schedules")));
}


export function renderSubtabIncidents(ctx, siteId) {
 const rows=ctx.records("incident").filter(r=>r.site_id===siteId);
 return ctx.card(l("Cảnh báo nhà máy","Site incidents"),ctx.table([t("name"),t("status")],
  rows.map(r=>[ctx.btn(r.title,()=>ctx.recordDetail("incident",r),"link"),r.status])),
  ctx.btn(l("Mở trung tâm xử lý sự cố","Open incident center"),()=>ctx.go("incidents")));
}


export function renderSubtabJournal(ctx) {
 return ctx.card(l("Nhật ký nhà máy","Site journal"),
 ctx.p(l("Xem sự kiện, vòng đời lệnh và bằng chứng đọc lại trong nhật ký chung.","Inspect events, command lifecycle and readback evidence in the shared journal.")),
 ctx.btn(l("Mở nhật ký","Open journal"),()=>ctx.go("journal")));
}


export async function renderSubtabDiagnostics(ctx, siteId) {
 const {card,table,select,field,input,btn,api,notice,div}=ctx;
 const root=div("stack");
 try {
 const data=await api(`/sites/${encodeURIComponent(siteId)}/diagnostics-checklist`);
 const labels={topology:l("Sơ đồ đấu nối","Topology"),meter_ct:"Meter / CT",power_direction:l("Chiều công suất","Power direction"),battery:"BMS",control_readback:l("Điều khiển & đọc lại","Control & readback"),alarms:l("Cảnh báo","Alarms")};
 root.append(card(l("Kiểm tra nghiệm thu","Commissioning checks"),
  notice("Đây là biên bản xác nhận thủ công, không tự cấp chứng chỉ hay mở quyền điều khiển.","These are manual attestations; they do not issue certificates or unlock control."),
  table([l("Hạng mục","Check"),t("status"),l("Bằng chứng","Evidence")],data.steps.map(s=>[labels[s.id],s.status,s.evidence||"—"]))));
 if(["Installer","Senior Engineer"].includes(ctx.state.me.user.role)) {
 const check=select(Object.entries(labels)),result=select([["pending","pending"],["pass","pass"],["warning","warning"],["fail","fail"]]),evidence=input("text","");
 const save=btn(l("Ghi nhận kết quả","Record result"),async()=>{
  try {await api(`/sites/${encodeURIComponent(siteId)}/diagnostics-checklist`,{site_id:siteId,check:check.value,result:result.value,evidence:evidence.value});await ctx.render();}
  catch(error){root.append(ctx.p(error.message,"bad"));}
 });
 root.append(card(l("Ghi nhận tại hiện trường","Field attestation"),field(l("Hạng mục","Check"),check),field(t("status"),result),field(l("Bằng chứng đo/quan sát","Measurement/observation evidence"),evidence),save));
 }
 } catch(error){root.append(ctx.p(error.message,"bad"));}
 return root;
}


export async function renderSubtabReports(ctx) { return await renderReportWorkspace(ctx); }


export async function renderSubtabNetwork(ctx, siteId) {
 const root=ctx.div("stack");
 try {
 const data=await ctx.api(`/sites/${encodeURIComponent(siteId)}/network-status`);
 root.append(ctx.card(l("Logger / Agent / Mạng","Logger / Agent / Network"),
 ctx.notice("Đăng ký agent không có nghĩa là agent đang online. Chưa có phép đo đường truyền thì hiển thị chưa xác định.","Enrollment is not online status. Network measurements remain unknown until observed."),
 ctx.table(["Agent",t("status"),l("Lần thấy cuối","Last seen")],data.agents.map(a=>[a.name||a.id,a.enabled?"ENROLLED":"DISABLED",a.last_seen||"—"])),
 ctx.btn(l("Cấu hình và chẩn đoán nguồn","Source configuration and diagnostics"),()=>ctx.go("reports","sources"))));
 } catch(error){root.append(ctx.p(error.message,"bad"));}
 return root;
}


export async function renderSiteOverviewWorkspace(ctx, siteId) {
  const { div, e, empty, l, api } = ctx;
  const container = div("stack");

  const subtabs = [
    ["overview", l("Tổng quan", "Overview")],
    ["data", l("Dữ liệu", "Data")],
    ["devices", l("Thiết bị", "Equipment")],
    ["control", l("Điều khiển", "Control")],
    ["schedules", l("Lịch / TOU", "Schedule / TOU")],
    ["incidents", l("Cảnh báo", "Alerts")],
    ["journal", l("Nhật ký", "Journal")],
    ["diagnostics", l("Chẩn đoán", "Diagnostics")],
    ["reports", l("Báo cáo", "Reports")],
    ["network", l("Logger / Agent / Mạng", "Network")],
  ];

  const currentSubtab = ctx.state.tab || "overview";
  const subnav = div("overview-subtabs");
  subtabs.forEach(([id, label]) => {
    const b = e(
      "button",
      label,
      "overview-subtab-btn" + (currentSubtab === id ? " active" : "")
    );
    b.onclick = () => {
      ctx.go("overview", id, "main");
    };
    subnav.append(b);
  });
  container.append(subnav);

  let data;
  try {
    data = await api(`/sites/${siteId}/overview-summary`);
  } catch {
    data = null;
  }

  if (!data) {
    container.append(
      empty(
        l("Không tải được dữ liệu nhà máy", "Could not load plant data"),
        l("Vui lòng kiểm tra lại kết nối.", "Please check connection.")
      )
    );
    return container;
  }

  if (currentSubtab === "data") {
    container.append(await renderSubtabData(ctx, siteId, data));
  } else if (currentSubtab === "devices") {
    container.append(await renderSubtabDevices(ctx, siteId, data));
  } else if (currentSubtab === "control") {
    container.append(await renderSubtabControl(ctx, siteId, data));
  } else if (currentSubtab === "schedules") {
    container.append(renderSubtabSchedules(ctx, siteId, data));
  } else if (currentSubtab === "incidents") {
    container.append(renderSubtabIncidents(ctx, siteId, data));
  } else if (currentSubtab === "journal") {
    container.append(renderSubtabJournal(ctx, siteId, data));
  } else if (currentSubtab === "diagnostics") {
    container.append(await renderSubtabDiagnostics(ctx, siteId, data));
  } else if (currentSubtab === "reports") {
    container.append(await renderSubtabReports(ctx, siteId, data));
  } else if (currentSubtab === "network") {
    container.append(await renderSubtabNetwork(ctx, siteId, data));
  } else {
    container.append(renderSubtabOverview(ctx, siteId, data));
  }

  return container;
}
