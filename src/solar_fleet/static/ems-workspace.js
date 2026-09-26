import { l, t, date, number } from "./i18n.js";
import { icon } from "./icons.js";

export async function renderEmsWorkspace(ui) {
  const {state, div, e, p, btn, badge, card, table, select, field, notice, api, go, operator, ruleForm, showDialog, raw} = ui;
  const root = div("stack ems-workspace-root");
  root.append(div("form-actions",
    btn(l("Triển khai nhiều thiết bị","Fleet rollout"),()=>go("operations","","rollouts")),
    btn(l("Lịch / TOU","Schedules / TOU"),()=>go("operations","schedules")),
    btn(l("Nhật ký lệnh","Command journal"),()=>go("operations","journal"))));
  root.append(notice(
    "Quy tắc và điều độ sử dụng mẫu đo đã xác minh. Kế hoạch điều độ 24h tính toán theo biểu giá điện EVN (QĐ 2699/QĐ-BCT) và cơ chế giảm phát phạt Cos(phi) (TT 15/2014/TT-BCT).",
    "Rules and dispatch use verified observations. 24h dispatch plan optimizes under EVN TOU tariffs and Circular 15 reactive power penalty rules."
  ));

  if(operator()) root.append(btn(l("+ Tạo quy tắc nháp","+ Create draft rule"),ruleForm,"primary"));

  // 1. OPERATING RULES
  const rules = (state.ops.rule||[]).filter(r=>!state.site||r.site_id===state.site);
  root.append(card(l("Quy tắc vận hành","Operating rules"), table([t("name"),t("plants"),t("status"),l("Thao tác","Action")],rules.map(r=>[
    r.name,ui.siteName(r.site_id),r.state,
    btn(l("Đánh giá dữ liệu hiện tại","Evaluate current readings"),async()=>{
      const result=await api("/rules/"+encodeURIComponent(r.id)+"/evaluate",{});
      showDialog(r.name,raw(r.name,result));
    })]))));
  if(!rules.length) root.append(p(l("Chưa có quy tắc đã lưu.","No saved rules.")));

  const runs = (state.ops.rule_run||[]).filter(r=>!state.site||r.site_id===state.site);
  root.append(card(l("Lịch sử đánh giá","Evaluation history"),table([l("Quy tắc","Rule"),l("Thời điểm","Time"),l("Kết quả điều kiện","Condition state")],
    runs.map(r=>[rules.find(s=>s.id===r.rule_id)?.name||r.rule_id,date(r.evaluated_at),r.condition_state]))));

  // 2. 24-HOUR ECONOMIC DISPATCH & EVN TOU SCHEDULE
  const currentSiteId = state.site || (state.fleet.sites?.[0]?.id);
  const dispatchContainer = div("stack");
  const dispatchCard = card(l("Điều độ kinh tế 24 giờ & Giờ cao điểm EVN", "24-Hour Economic Dispatch & EVN Peak Optimizer"));

  const loadDispatchBtn = btn(l("Tính toán điều độ kinh tế 24h", "Calculate 24h Economic Dispatch"), async () => {
    if (!currentSiteId) {
      dispatchContainer.replaceChildren(p(l("Vui lòng chọn nhà máy trước.", "Please select a plant first.")));
      return;
    }
    dispatchContainer.replaceChildren(p(l("Đang giải bài toán tối ưu hóa điều độ...", "Solving dispatch optimization problem...")));
    try {
      const plan = await api(`/sites/${encodeURIComponent(currentSiteId)}/dispatch-schedule`);
      const kpis = div("overview-kpis",
        div("fact", e("span", l("Tổng phát điện PV dự kiến:", "Forecast PV Gen:")), e("b", `${number(plan.total_pv_generation_kwh)} kWh`)),
        div("fact", e("span", l("Tiêu thụ phụ tải dự kiến:", "Forecast Site Load:")), e("b", `${number(plan.total_load_consumption_kwh)} kWh`)),
        div("fact", e("span", l("Chi phí không có EMS:", "Cost without EMS:")), e("b", `${number(plan.total_cost_without_ems_vnd)} VNĐ`)),
        div("fact", e("span", l("Chi phí có điều độ EMS:", "Cost with EMS:")), e("b", `${number(plan.total_cost_with_ems_vnd)} VNĐ`, "good-text")),
        div("fact", e("span", l("Tiết kiệm dự kiến:", "Estimated Savings:")), badge(`${number(plan.total_savings_vnd)} VNĐ (-${plan.savings_percentage}%)`, "good"))
      );

      const dispatchTable = table(
        [
          l("Giờ", "Hour"),
          l("Khung giờ EVN", "EVN Tier"),
          l("Giá điện (VNĐ/kWh)", "Tariff (VND)"),
          l("PV (W)", "PV (W)"),
          l("Phụ tải (W)", "Load (W)"),
          l("Pin lưu trữ (W)", "Battery (W)"),
          l("SOC dự kiến", "Predicted SOC"),
          l("Nhập lưới (W)", "Grid Import (W)"),
          l("Tiết kiệm (VNĐ)", "Savings (VND)")
        ],
        (plan.dispatch_points || []).map(pt => [
          `${String(pt.hour).padStart(2, '0')}:00`,
          badge(pt.tariff_tier === "PEAK" ? l("Cao điểm", "Peak") : pt.tariff_tier === "OFF_PEAK" ? l("Thấp điểm", "Off-peak") : l("Bình thường", "Normal"),
                pt.tariff_tier === "PEAK" ? "bad" : pt.tariff_tier === "OFF_PEAK" ? "good" : "blue"),
          number(pt.tariff_rate_vnd),
          number(pt.pv_power_w),
          number(pt.load_power_w),
          e("b", pt.battery_power_w > 0 ? `+${number(pt.battery_power_w)} (${l("Sạc", "Charge")})` : pt.battery_power_w < 0 ? `${number(pt.battery_power_w)} (${l("Xả", "Discharge")})` : "0", pt.battery_power_w < 0 ? "good-text" : ""),
          `${pt.battery_soc_percent}%`,
          number(pt.grid_import_w),
          badge(`+${number(pt.hourly_savings_vnd)}`, pt.hourly_savings_vnd > 0 ? "good" : "gray")
        ])
      );

      dispatchContainer.replaceChildren(
        notice(
          `Giải thuật tối ưu hóa EMHASS độc lập đã nạp ${plan.usable_capacity_kwh} kWh pin khả dụng, ưu tiên sạc đầy vào giờ trưa/thấp điểm và xả công suất tối đa trong 2 khung giờ cao điểm EVN (09:30-11:30 và 17:00-20:00).`,
          `Independent EMHASS dispatch algorithm allocated ${plan.usable_capacity_kwh} kWh battery reserve, prioritizing solar self-consumption and peak shaving during EVN high-tariff windows.`
        ),
        kpis,
        dispatchTable
      );
    } catch (err) {
      dispatchContainer.replaceChildren(p(err.message, "bad"));
    }
  });

  dispatchCard.append(
    p(l("Lập lịch sạc/xả pin lưu trữ tự động theo 3 khung giá EVN để triệt tiêu phụ thu giờ cao điểm và tối đa hóa tỷ lệ tự dùng.",
      "Automated battery dispatch optimization under EVN 3-tier tariffs to eliminate peak charges and maximize self-consumption.")),
    loadDispatchBtn,
    dispatchContainer
  );
  root.append(dispatchCard);

  // 3. EVN TARIFF & CIRCULAR 15 POWER FACTOR ANALYSIS
  const tariffContainer = div("stack");
  const tariffCard = card(l("Phân tích Biểu giá EVN & Cảnh báo phạt Cos(phi)", "EVN Tariff & Circular 15 Power Factor Evaluation"));

  const loadTariffBtn = btn(l("Đánh giá chi phí điện & Hệ số Cos(phi)", "Evaluate Electricity Costs & Cos(phi)"), async () => {
    if (!currentSiteId) return;
    tariffContainer.replaceChildren(p(l("Đang tải dữ liệu biểu giá...", "Loading tariff analysis...")));
    try {
      const data = await api(`/sites/${encodeURIComponent(currentSiteId)}/tariff-analysis`);
      const pf = data.power_factor_analysis;
      const ps = data.peak_shaving_opportunity;

      const pfBadge = badge(`cos φ = ${pf.cos_phi}`, pf.is_compliant ? "good" : "bad");
      const pfAlert = pf.is_compliant
        ? notice(pf.advice, pf.advice)
        : div("banner bad", e("b", l("CẢNH BÁO PHẠT CÔNG SUẤT PHẢN KHÁNG (TT 15/2014/TT-BCT):", "REACTIVE POWER SURCHARGE WARNING:")), p(pf.advice));

      const costTable = table(
        [l("Khung giờ EVN", "EVN Tier"), l("Sản lượng tiêu thụ (kWh)", "Consumption (kWh)"), l("Chi phí ước tính (VNĐ)", "Estimated Cost (VND)")],
        [
          [l("Giờ cao điểm (Peak)", "Peak Hours"), number(data.energy_consumption_kwh.peak_kwh), number(data.energy_cost_vnd.peak_vnd)],
          [l("Giờ bình thường (Normal)", "Normal Hours"), number(data.energy_consumption_kwh.normal_kwh), number(data.energy_cost_vnd.normal_vnd)],
          [l("Giờ thấp điểm (Off-peak)", "Off-peak Hours"), number(data.energy_consumption_kwh.off_peak_kwh), number(data.energy_cost_vnd.off_peak_vnd)],
          [e("b", l("Tổng cộng", "Total")), e("b", number(data.total_active_energy_kwh)), e("b", `${number(data.total_active_bill_vnd)} VNĐ`)],
        ]
      );

      const psCard = card(l("Cơ hội cắt đỉnh phụ tải (Peak Shaving)", "Peak Shaving Opportunity"),
        div("overview-kpis",
          div("fact", e("span", l("Công suất đỉnh cực đại:", "Max Demand Peak:")), e("b", `${ps.max_demand_peak_kw} kW`)),
          div("fact", e("span", l("Đề xuất xả pin cắt đỉnh:", "Recommended Battery Discharge:")), e("b", `${ps.recommended_battery_discharge_kw} kW`, "good-text")),
          div("fact", e("span", l("Chênh lệch giá cao/thấp điểm:", "Arbitrage Spread:")), e("b", `${number(ps.price_spread_vnd_per_kwh)} VNĐ/kWh`)),
          div("fact", e("span", l("Tiết kiệm chênh lệch giá/tháng:", "Monthly Arbitrage Savings:")), badge(`${number(ps.estimated_monthly_arbitrage_vnd)} VNĐ`, "good"))
        ),
        p(ps.peak_hours_definition, "small muted")
      );

      tariffContainer.replaceChildren(
        pfAlert,
        div("row", pfBadge, badge(data.voltage_tier, "blue"), badge(data.customer_class, "gray")),
        costTable,
        psCard
      );
    } catch (err) {
      tariffContainer.replaceChildren(p(err.message, "bad"));
    }
  });

  tariffCard.append(
    p(l("Kiểm tra sự tuân thủ Thông tư 15/2014/TT-BCT của Bộ Công Thương về mua bán công suất phản kháng và cơ cấu tiền điện theo biểu giá EVN.",
      "Verify compliance with Circular 15/2014/TT-BCT on reactive energy surcharge and EVN multi-tier electricity cost structure.")),
    loadTariffBtn,
    tariffContainer
  );
  root.append(tariffCard);

  // 4. MULTI-VENDOR COMPATIBILITY
  const intents = [...new Set((state.fleet.devices||[]).flatMap(d=>(d.capabilities||[]).map(c=>c.intent)))];
  const intent = select((intents.length?intents:['SET_RESERVE_SOC','SET_ZERO_EXPORT','SET_TOU']).map(id=>[id,t(id)]));
  const result = div("stack");
  const assess = btn(l("Kiểm tra khả năng từng thiết bị","Assess each device"),async()=>{
    const ids = (state.fleet.sites||[]).filter(s=>!state.site||s.id===state.site).map(s=>s.id);
    if(!ids.length) {result.replaceChildren(p(l("Chưa có nhà máy.","No plants.")));return;}
    const data = await api('/ems/batch-assess',{site_ids:ids,intents:[intent.value]});
    result.replaceChildren(table([t('plants'),t('status'),l('Thiết bị / lý do','Device / reason')],data.sites.map(s=>[
      s.name,s.status,s.targets.map(d=>d.device_id+': '+d.state+' · '+d.reason).join('; ')||l('Chưa có thiết bị','No devices')])));
  });
  root.append(card(l("Tương thích đa hãng","Multi-vendor compatibility"),field(l("Chức năng","Intent"),intent),assess,result));

  // 5. HISTORICAL BASELINE FORECAST
  const forecastDevices = (state.fleet.devices||[]).filter(d=>!state.site||d.site_id===state.site);
  const forecastDevice = select(forecastDevices.map(d=>[d.id,d.name||d.id]));
  const forecastResult = div("stack");
  root.append(card(l("Dự báo theo lịch sử", "Historical baseline forecast"),
    p(l("Học theo ngày trong tuần và giờ từ dữ liệu W đã xác minh. Cần tối thiểu 3 ngày, 24 giờ đủ mẫu. Kết quả để tham khảo; không tự gửi lệnh.",
      "Learn weekday/hour patterns from verified W observations. Requires at least 3 dates and 24 sufficiently sampled hours. Advisory results do not dispatch commands.")),
    field(l("Thiết bị dự báo", "Forecast device"),forecastDevice),
    btn(l("Tính dự báo 24 giờ", "Calculate 24-hour baseline"),async()=>{
      if(!forecastDevice.value) {forecastResult.replaceChildren(p(l("Chọn thiết bị trước.","Choose a device first.")));return;}
      try {
        const value=await api(`/devices/${encodeURIComponent(forecastDevice.value)}/forecast-baseline`);
        forecastResult.replaceChildren(...Object.entries(value.metrics).map(([metric,data])=>card(metric,
          p(`${data.status} · ${data.training_days} ${l("ngày", "dates")} · ${data.training_hours} h`),
          table([l("Giờ địa phương","Local time"),"W",l("Cơ sở dự báo","Basis")],data.points.map(point=>[
            date(point.local_time),point.value_w===null?"—":Math.round(point.value_w).toString(),point.method])))));
      } catch(err) {forecastResult.replaceChildren(p(err.message,"bad"));}
    }),forecastResult));

  return root;
}
