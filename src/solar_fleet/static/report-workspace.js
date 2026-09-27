import { l, number } from "./i18n.js";

export async function renderReportWorkspace(ui) {
  const {state, div, e, p, btn, card, table, select, field, notice, api, download, operator} = ui;
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
  if (operator()) root.append(card(l("Xuất báo cáo","Export report"),field(l("Định dạng","Format"),format),generate,outcome));
  else root.append(p(l("Cần quyền vận hành để tạo báo cáo. Có thể tải báo cáo đã lưu trong phạm vi được phép.", "Operator access is required to generate reports. Authorized archived reports remain downloadable.")));
  root.append(card(l("Báo cáo đã lưu","Report archive"),
    table([l("Tên","Title"),l("Định dạng","Format"),l("Kích thước","Size"),l("Thao tác","Action")],
      archive.map(r=>[r.title,r.format,number(r.size_bytes)+" B",
        btn(l("Tải xuống","Download"),()=>download(r.download_url.replace(/^\/api/,""),"report."+r.extension))]))));

  // WHOLESALE ELECTRICITY MARKET & FCR FREQUENCY REGULATION TRADING
  const marketContainer = div("stack");
  const marketInput = e("textarea");
  marketInput.rows = 10;

  const runMarketBtn = btn(l("Tính kịch bản từ dữ liệu nhập", "Calculate supplied market scenario"), async () => {
    marketContainer.replaceChildren(p(l("Đang tính ước tính...", "Calculating estimate...")));
    try {
      const marketRes = await api("/market-trader/submit-and-clear", JSON.parse(marketInput.value));

      const kpis = div("overview-kpis",
        div("fact", e("span", l("Giá trị ròng ước tính (EUR)", "Estimated net value (EUR)")), e("b", number(marketRes.net_market_settlement_eur))),
        div("fact", e("span", l("Số lệnh có thể khớp", "Estimated cleared bids")), e("b", number(marketRes.cleared_bids))),
        div("fact", e("span", l("Tổng số lệnh", "Input bids")), e("b", number(marketRes.total_bids)))
      );


      marketContainer.replaceChildren(
        notice(
          "Chỉ ước tính từ dữ liệu nhập. Không gửi lệnh thị trường, không thanh toán và không cung cấp dịch vụ FCR.",
          "Estimated from supplied inputs only. No market submission, settlement or FCR service has occurred."
        ),
        kpis
      );
    } catch (err) {
      marketContainer.replaceChildren(p(err.message, "bad"));
    }
  });

  root.append(card(
    l("Ước tính kịch bản thị trường", "Advisory market scenario"),
    p(l("Nhập công suất, lệnh và giá từng giờ rõ ràng; chưa kết nối sàn giao dịch.",
        "Supply explicit capacity, bids and hourly prices; no exchange connection is configured.")),
    p("JSON: fleet_capacity_mw, bids [{id, market (day_ahead/intraday), direction (buy_charge/sell_discharge), delivery_hour (0–23), quantity_mw, price_eur_per_mwh}], clearing_prices {hour: EUR/MWh}."),
    field(l("Đầu vào thị trường (JSON)", "Market inputs (JSON)"), marketInput),
    runMarketBtn,
    marketContainer
  ));

  return root;
}
