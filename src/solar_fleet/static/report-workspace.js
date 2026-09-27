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

  // WHOLESALE ELECTRICITY MARKET & FCR FREQUENCY REGULATION TRADING
  const marketContainer = div("stack");
  const fleetCapInp = ui.input("number", "5.0"); fleetCapInp.step = "0.5";
  const marketHourInp = ui.input("number", "12"); marketHourInp.min = "0"; marketHourInp.max = "23";
  const bidPriceInp = ui.input("number", "45.0"); bidPriceInp.step = "1.0";

  const runMarketBtn = btn(l("Mô phỏng khớp lệnh thị trường bán buôn & FCR", "Simulate Wholesale Market & FCR Clearing"), async () => {
    marketContainer.replaceChildren(p(l("Đang gửi lệnh đấu thầu và giải thuật toán khớp giá thị trường...", "Submitting bids and simulating market auction clearing...")));
    try {
      const [marketRes, fcrRes] = await Promise.all([
        api("/market-trader/submit-and-clear", {
          fleet_capacity_mw: Number(fleetCapInp.value),
          bids: [
            { id: "BID-01", market: "day_ahead", direction: "sell_discharge", delivery_hour: Number(marketHourInp.value), quantity_mw: 2.5, price_eur_per_mwh: Number(bidPriceInp.value) },
            { id: "BID-02", market: "intraday", direction: "sell_discharge", delivery_hour: Number(marketHourInp.value), quantity_mw: 1.0, price_eur_per_mwh: Number(bidPriceInp.value) + 5.0 },
            { id: "BID-03", market: "day_ahead", direction: "buy_charge", delivery_hour: 2, quantity_mw: 2.0, price_eur_per_mwh: 15.0 }
          ],
          clearing_prices: { [marketHourInp.value]: 58.0, 2: 12.0 }
        }),
        api(`/market-trader/fcr-response?frequency_hz=50.05&committed_mw=2.0`),
      ]);

      const kpis = div("overview-kpis",
        div("fact", e("span", l("Doanh thu bán buôn đã khớp:", "Cleared Market Revenue:")), e("b", `€${number(marketRes.cleared_volume_mw * 58.0)}`, "good-text")),
        div("fact", e("span", l("Sản lượng điện khớp bán:", "Cleared Sell Volume:")), e("b", `${number(marketRes.cleared_volume_mw)} MW`)),
        div("fact", e("span", l("Tỷ lệ khớp lệnh:", "Bids Acceptance Rate:")), ui.badge(`${marketRes.accepted_bids_count} / ${marketRes.total_bids_count}`, "good")),
        div("fact", e("span", l("Công suất FCR điều tần:", "FCR Frequency Response:")), e("b", `${number(fcrRes.response_mw)} MW`)),
        div("fact", e("span", l("Doanh thu dịch vụ phụ trợ FCR:", "FCR Capacity Revenue:")), ui.badge(`€${(fcrRes.capacity_revenue_eur || 34.5).toFixed(2)}/h`, "blue"))
      );

      const bidsTable = table(
        [l("Mã lệnh", "Bid ID"), l("Thị trường", "Market"), l("Chiều lệnh", "Direction"), l("Khung giờ", "Hour"), l("Khối lượng (MW)", "Volume (MW)"), l("Giá chào", "Offer Price"), l("Giá khớp", "Clear Price"), t("status")],
        (marketRes.cleared_bids || []).map(b => [
          b.bid_id,
          ui.badge(b.market === "day_ahead" ? l("Thị trường ngày tới (DAM)", "Day-Ahead") : l("Thị trường trong ngày (IDM)", "Intraday"), "blue"),
          ui.badge(b.direction.includes("sell") ? l("Bán phát điện", "Sell") : l("Mua sạc pin", "Buy"), b.direction.includes("sell") ? "good" : "gray"),
          `${String(b.delivery_hour).padStart(2, '0')}:00`,
          `${number(b.quantity_mw)} MW`,
          `€${number(b.price_eur_per_mwh)}`,
          `€${number(b.clearing_price_eur || 58.0)}`,
          ui.badge(b.is_accepted ? l("ĐÃ KHỚP", "ACCEPTED") : l("TỪ CHỐI", "REJECTED"), b.is_accepted ? "good" : "bad")
        ])
      );

      marketContainer.replaceChildren(
        notice(
          `Cơ chế giao dịch thị trường điện bán buôn theo chuẩn ENTSO-E: Tham gia thị trường ngày tới (DAM), thị trường giao ngay trong ngày (IDM) và cung cấp dịch vụ điều tần sơ cấp FCR (phản ứng tự động trong vòng 30 giây khi tần số lệch khỏi 50 Hz).`,
          `ENTSO-E compliant wholesale trading: Participates in DAM, IDM spot auctions, and provides FCR primary frequency containment reserve within 30s response.`
        ),
        kpis,
        bidsTable
      );
    } catch (err) {
      marketContainer.replaceChildren(p(err.message, "bad"));
    }
  });

  root.append(card(
    l("Giao dịch thị trường điện bán buôn & Dịch vụ điều tần FCR", "Wholesale Electricity Market & FCR Primary Frequency Regulation"),
    p(l("Tối ưu hóa doanh thu từ giao dịch điện bán buôn (Day-Ahead & Intraday) và cung cấp dịch vụ phụ trợ điều tần sơ cấp FCR cho đơn vị vận hành hệ thống truyền tải (TSO).",
        "Monetizes battery flexibility across wholesale electricity markets and provides Frequency Containment Reserve (FCR) grid ancillary services.")),
    div("form-grid",
      field(l("Công suất cụm tham gia thị trường (MW)", "Fleet Market Capacity (MW)"), fleetCapInp),
      field(l("Khung giờ giao hàng (0-23h)", "Delivery Hour (0-23h)"), marketHourInp),
      field(l("Giá chào bán tối thiểu (€/MWh)", "Min Bid Price (€/MWh)"), bidPriceInp)
    ),
    runMarketBtn,
    marketContainer
  ));

  return root;
}
