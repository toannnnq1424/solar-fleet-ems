import { l, number } from "./i18n.js";
import { metricTiles, dailyEnergyChart, percentageGauge } from './ui-visuals.js';
import { icon } from './icons.js';
import { marketScenarioEditor } from './market-scenario-editor.js';
import { reportedSummary, reportedEnergyChart } from './vendor-report.js';

export async function renderReportWorkspace(ui) {
  const {state, div, e, p, btn, card, table, select, field, notice, api, download, operator} = ui;
  const root = div("stack report-workspace-root");
  const period = state.reportPeriod || "month";
  const picker = select([["day",l("Hôm nay","Today")],["week",l("7 ngày","7 days")],
    ["month",l("Tháng này","This month")],["year",l("Năm nay","This year")]],period);
  picker.onchange = () => {state.reportPeriod = picker.value; ui.render();};
  root.append(div("row", e("h2",l("Báo cáo & phân tích","Reports & analytics")), field(l("Khoảng thời gian","Period"),picker)));
  const scopedSites = (ui.sites?.() || []).filter(site => !state.site || site.id === state.site);
  for (const site of scopedSites) {
    const report = site.vendor_report;
    if (!report) continue;
    root.append(card(l('Báo cáo từ hãng · ', 'Vendor report · ') + (site.name || site.id),
      reportedSummary(ui, report, period === 'day' ? 'today' : period),
      ...(period === 'month' ? [reportedEnergyChart(report)] : []),
      p(l('Phần bên dưới và tệp xuất hiện vẫn dùng số đo SolarOne đã xác minh; chưa gộp hai loại dữ liệu.',
        'The section below and current exports still use SolarOne-verified measurements; these data categories are not merged.'))));
  }
  const params = new URLSearchParams({period});
  if (state.site) params.set("site_id",state.site);
  let summary, series, archive;
  try {
    [summary,series,archive] = await Promise.all([
      api("/reports/analytics/summary?"+params),api("/reports/analytics/timeseries?"+params),
      api("/reports/recent"+(state.site ? "?site_id="+encodeURIComponent(state.site) : ""))]);
  } catch(error) {
    root.append(notice("Không tải được báo cáo: "+error.message,"Report unavailable: "+error.message,true));
    return root;
  }
  root.append(metricTiles(ui,[
    ['sun',l('Sản lượng','Generation'),summary.pv_generation_kwh,'kWh','green'],
    ['home',l('Tiêu thụ','Consumption'),summary.load_consumption_kwh,'kWh','solar'],
    ['bolt',l('Nhập lưới','Grid import'),summary.grid_import_kwh,'kWh'],
    ['grid',l('Xuất lưới','Grid export'),summary.grid_export_kwh,'kWh','purple'],
    ['refresh',l('Tự dùng','Self consumption'),summary.self_consumption_rate_pct,'%','green'],
    ['chart',l('Tiết kiệm','Savings'),summary.cost_savings_vnd,'VND','solar'],
    ['leaf',l('Giảm phát thải','Avoided emissions'),summary.avoided_co2_kg,'kg','green'],
    ['shield',l('Thời gian hoạt động','Availability'),summary.uptime_pct,'%','green'],
  ],'report-metrics'));
  root.append(notice(
    "Dấu — nghĩa là chưa đủ bằng chứng đo đếm. Chưa tính tiền tiết kiệm, phát thải hoặc tỷ lệ tự dùng khi thiếu cấu hình và nguồn năng lượng pin.",
    "A dash means insufficient measurement evidence. Savings, emissions and storage attribution require additional configuration."));
  const channels=[['pv_kwh',l('Sản lượng','Generation'),'generation'],['load_kwh',l('Tiêu thụ','Consumption'),'consumption'],
    ['self_consumption_kwh',l('Tự dùng','Self consumption'),'self-use'],['grid_export_kwh',l('Xuất lưới','Grid export'),'export']];
  const visible=new Set(channels.map(([key])=>key)),plot=div('report-main-plot'),legend=div('chart-legend report-chart-toggles');
  const plotStatus=p('','chart-reading');plotStatus.setAttribute('role','status');
  const drawPlot=()=>{
    plot.replaceChildren(dailyEnergyChart(series.main_chart || [],{keys:channels.filter(([key])=>visible.has(key)),lineKeys:['pv_kwh','load_kwh'],
      emptyLabel:visible.size?undefined:l('Chọn thông số phía trên để xem biểu đồ','Select a metric above to view the chart')}));
    plot.querySelectorAll('.energy-bar,.energy-point').forEach(bar=>{bar.onfocus=()=>plotStatus.textContent=bar.getAttribute('aria-label');bar.onmouseenter=bar.onfocus;});
  };
  channels.forEach(([key,label,tone])=>{const button=btn(label,()=>{
    if(visible.has(key))visible.delete(key);else visible.add(key);button.setAttribute('aria-pressed',String(visible.has(key)));plotStatus.textContent='';drawPlot();
  },tone);button.setAttribute('aria-pressed','true');legend.append(button);});drawPlot();
  const dataTable=e('details','','report-data-table');
  dataTable.append(e('summary',l('Xem bảng số liệu theo ngày','View daily data table')),
    table([l('Ngày','Date'),...channels.map(([,label])=>label+' (kWh)')],(series.main_chart||[]).map(row=>[row.date,...channels.map(([key])=>row[key]==null?'—':number(row[key]))])));
  const daily = card(l("Sản lượng theo ngày","Daily energy"),legend,plot,plotStatus,dataTable);
  daily.classList.add('report-chart-panel');
  const reportAside=div('stack report-aside');
  const reportMain=div('stack report-main',daily);
  root.append(div('report-layout',reportMain,reportAside));
  const format = select([["csv","CSV"],["excel","Excel (.xlsx)"],["html",l("HTML có thể in","Printable HTML")]],"csv");
  const outcome = div("stack");
  const includeEstimate = select([["no",l("Không", "No")],["yes",l("Có", "Yes")]], "no");
  const generate = btn(l("Tạo báo cáo","Generate report"), async()=>{
    generate.disabled = true;
    try {
      const record=await api("/reports/generate",{site_id:state.site||null,period,format:format.value,report_type:"energy",include_import_estimate:includeEstimate.value === "yes"});
      await download(record.download_url.replace(/^\/api/,""),"solarone-report."+record.extension);
      outcome.replaceChildren(p(l("Đã lưu báo cáo và tải tệp.","Report saved and downloaded.")));
    } catch(error) {outcome.replaceChildren(p(error.message,"bad"));}
    finally {generate.disabled=false;}
  },"primary");
  if (operator()) reportAside.append(card(l("Xuất báo cáo","Export report"),field(l("Định dạng","Format"),format),
    field(l("Kèm chi phí mua điện ước tính", "Include import estimate snapshot"), includeEstimate),
    p(l("Chi phí là ước tính, không phải hóa đơn. Cần chọn công tơ tính tiền và khai báo giá điện. Giới hạn: 30 ngày, 20 nhà máy, 10.000 mẫu đo mỗi nhà máy.",
      "Costs are estimates, not a utility bill. Select a billing meter and declare electricity rates first. Limited to 30 days, 20 plants and 10,000 readings per plant.")),generate,outcome));
  else reportAside.append(p(l("Cần quyền vận hành để tạo báo cáo. Có thể tải báo cáo đã lưu trong phạm vi được phép.", "Operator access is required to generate reports. Authorized archived reports remain downloadable.")));
  const mini=series.mini_charts||series;
  const smallChart=(rows,keys,unit,label)=>dailyEnergyChart(rows||[],{keys,unit,label,compact:true,integer:keys[0][0]==='count',emptyLabel:l('Chưa đủ dữ liệu','Insufficient data')});
  const ratio=mini.self_consumption_donut||{};
  reportMain.append(div('report-mini-grid',
    card(l('Tỷ lệ tự dùng','Self consumption'),percentageGauge(ratio.rate_pct??summary.self_consumption_rate_pct,l('Tự dùng','Self use')),
      ui.fact(l('Điện tự dùng','Self-used energy'),ratio.self_consumption_kwh==null?'—':number(ratio.self_consumption_kwh)+' kWh')),
    card(l('Chu kỳ pin','Battery cycles'),smallChart(mini.battery_bars,[['cycles',l('Chu kỳ','Cycles'),'self-use']],l('chu kỳ','cycles'),l('Chu kỳ pin theo ngày','Daily battery cycles')),
      p(l('Chỉ hiển thị khi có số chu kỳ được xác minh.','Only shown when cycle counts are verified.'))),
    card(l('Nhập / xuất lưới','Grid import / export'),smallChart(mini.grid_bars,[['import_kwh',l('Nhập lưới','Import'),'grid-import'],['export_kwh',l('Xuất lưới','Export'),'export']],'kWh',l('Điện năng trao đổi với lưới','Grid energy exchange')),
      div('chart-legend',e('span',l('Nhập','Import'),'grid-import'),e('span',l('Xuất','Export'),'export'))),
    card(l('Cảnh báo theo ngày','Daily alerts'),smallChart(mini.incident_bars,[['count',l('Cảnh báo','Alerts'),'incident']],l('lần','events'),l('Số cảnh báo theo ngày','Daily alert count')),
      p(l('Từ sự cố đã được ghi nhận trong kỳ.','From incidents recorded in this period.')))));
  const archiveList=div('report-archive-list');
  archive.forEach(r=>{
    const action=btn(icon('download'),()=>download(r.download_url.replace(/^\/api/,""),"report."+r.extension),'icon-button');
    action.setAttribute('aria-label',l('Tải xuống','Download')+' · '+r.title);
    archiveList.append(div('report-archive-item',icon('fileText'),div('stack',e('b',r.title),p(r.format+' · '+number(r.size_bytes)+' B','muted')),action));
  });
  if(!archive.length)archiveList.append(div('report-archive-empty',icon('fileText'),p(l('Chưa có báo cáo đã lưu','No saved reports yet')),
    p(l('Tệp sẽ xuất hiện ở đây sau khi tạo báo cáo.','Files appear here after a report is generated.'))));
  reportAside.append(card(l("Báo cáo đã lưu","Report archive"),archiveList));

  const marketTools=e('details','','engineering-tools');
  marketTools.append(e('summary',l('Công cụ kỹ sư · kịch bản thị trường','Engineering tools · market scenarios')),card(
    l("Ước tính kịch bản thị trường", "Advisory market scenario"),
    marketScenarioEditor(ui)
  ));
  root.append(marketTools);

  return root;
}
