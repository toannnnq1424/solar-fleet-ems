import { l, number } from "./i18n.js";

export async function renderReportWorkspace(ui) {
  const {state, div, e, p, btn, card, table, select, field, notice, api, download} = ui;
  const root = div("stack report-workspace-root");
  const period = state.reportPeriod || "month";
  const picker = select([["day",l("Hôm nay","Today")],["week",l("7 ngày","7 days")],
    ["month",l("Tháng này","This month")],["year",l("Năm nay","This year")]],period);
  picker.onchange = () => {state.reportPeriod = picker.value; ui.render();};
  root.append(div("row", e("h2",l("Báo cáo & phân tích","Reports & analytics")), field(l("Khoảng thời gian","Period"),picker)));
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
  const metric = (label,key,unit) => div("fact",e("span",label),e("b",summary[key] == null ? "—" : number(summary[key])+" "+unit));
  root.append(div("overview-kpis",
    metric(l("Sản lượng","Generation"),"pv_generation_kwh","kWh"),
    metric(l("Tiêu thụ","Consumption"),"load_consumption_kwh","kWh"),
    metric(l("Nhập lưới","Grid import"),"grid_import_kwh","kWh"),
    metric(l("Xuất lưới","Grid export"),"grid_export_kwh","kWh"),
    metric(l("Tự dùng","Self consumption"),"self_consumption_rate_pct","%"),
    metric(l("Tiết kiệm","Savings"),"cost_savings_vnd","VND"),
    metric(l("Giảm phát thải","Avoided emissions"),"avoided_co2_kg","kg"),
    metric(l("Thời gian hoạt động","Availability"),"uptime_pct","%")));
  root.append(notice(
    "Dấu — nghĩa là chưa đủ bằng chứng đo đếm. Chưa tính tiền tiết kiệm, phát thải hoặc tỷ lệ tự dùng khi thiếu cấu hình và nguồn năng lượng pin.",
    "A dash means insufficient measurement evidence. Savings, emissions and storage attribution require additional configuration."));
  root.append(card(l("Sản lượng theo ngày","Daily energy"),
    table([l("Ngày","Date"),"PV (kWh)",l("Tiêu thụ (kWh)","Load (kWh)"),l("Xuất lưới (kWh)","Export (kWh)")],
      series.main_chart.map(row=>[row.date,...["pv_kwh","load_kwh","grid_export_kwh"].map(k=>row[k]==null?"—":number(row[k]))]))));
  const format = select([["csv","CSV"],["excel","Excel (.xlsx)"],["html",l("HTML có thể in","Printable HTML")]],"csv");
  const outcome = div("stack");
  const generate = btn(l("Tạo báo cáo","Generate report"), async()=>{
    generate.disabled = true;
    try {
      const record=await api("/reports/generate",{site_id:state.site||null,period,format:format.value,report_type:"energy"});
      await download(record.download_url.replace(/^\/api/,""),"solarone-report."+record.extension);
      outcome.replaceChildren(p(l("Đã lưu báo cáo và tải tệp.","Report saved and downloaded.")));
    } catch(error) {outcome.replaceChildren(p(error.message,"bad"));}
    finally {generate.disabled=false;}
  },"primary");
  root.append(card(l("Xuất báo cáo","Export report"),field(l("Định dạng","Format"),format),generate,outcome));
  root.append(card(l("Báo cáo đã lưu","Report archive"),
    table([l("Tên","Title"),l("Định dạng","Format"),l("Kích thước","Size"),l("Thao tác","Action")],
      archive.map(r=>[r.title,r.format,number(r.size_bytes)+" B",
        btn(l("Tải xuống","Download"),()=>download(r.download_url.replace(/^\/api/,""),"report."+r.extension))]))));
  return root;
}
