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

  // 6. GRID CODE REGULATOR & ANTI-ISLANDING (P(V), Q(V), P(f), NA003)
  const gridCodeContainer = div("stack");
  const voltageInp = ui.input("number", "255.0");
  voltageInp.step = "0.5";
  const freqInp = ui.input("number", "50.15");
  freqInp.step = "0.01";
  const powerInp = ui.input("number", "10.0");
  powerInp.step = "0.1";

  const evaluateGridCodeBtn = btn(l("Đánh giá quy chuẩn lưới điện", "Evaluate Grid Code Compliance"), async () => {
    gridCodeContainer.replaceChildren(p(l("Đang tính toán đáp ứng điều tần và điều áp...", "Evaluating Volt-Watt, Volt-Var, and Freq-Watt curves...")));
    try {
      const data = await api("/grid-code/evaluate", {
        voltage_v: Number(voltageInp.value),
        frequency_hz: Number(freqInp.value),
        current_power_kw: Number(powerInp.value),
      });

      const stBadge = badge(data.state, data.is_compliant ? "good" : "bad");
      const kpis = div("overview-kpis",
        div("fact", e("span", l("Giới hạn P(V) Volt-Watt:", "Volt-Watt Limit P(V):")), e("b", `${number(data.volt_watt?.power_limit_kw)} kW`), badge(data.volt_watt?.is_curtailed ? l("Cắt giảm phát", "Curtailed") : l("Bình thường", "Normal"), data.volt_watt?.is_curtailed ? "warn" : "good")),
        div("fact", e("span", l("Hỗ trợ Q(V) Volt-Var:", "Volt-Var Support Q(V):")), e("b", `${number(data.volt_var?.reactive_power_kvar)} kVAR`), badge(data.volt_var?.mode || "NORMAL", "blue")),
        div("fact", e("span", l("Đáp ứng tần số P(f):", "Frequency Droop P(f):")), e("b", `${number(data.freq_watt?.power_limit_kw)} kW`), badge(data.freq_watt?.mode || "NORMAL", "gray")),
        div("fact", e("span", l("Chống tách lưới NA003:", "Anti-Islanding NA003:")), badge(data.anti_islanding?.is_tripped ? l("NGẮT BẢO VỆ", "TRIPPED") : l("AN TOÀN", "SECURE"), data.anti_islanding?.is_tripped ? "bad" : "good")),
        div("fact", e("span", l("Công suất cho phép cuối cùng:", "Final Allowed Dispatch:")), e("b", `${number(data.final_dispatched_kw)} kW`, "good-text"))
      );

      gridCodeContainer.replaceChildren(
        notice(data.action_summary, data.action_summary),
        div("row", stBadge, badge(`${voltageInp.value} V`, "gray"), badge(`${freqInp.value} Hz`, "gray")),
        kpis
      );
    } catch (err) {
      gridCodeContainer.replaceChildren(p(err.message, "bad"));
    }
  });

  root.append(card(
    l("Bộ điều phối Quy chuẩn lưới điện (Grid-Code Regulator)", "Grid-Code Regulation Engine (P(V), Q(V), P(f), NA003)"),
    p(l("Mô phỏng đường cong Volt-Watt P(V) chống quá áp, Volt-Var Q(V) hỗ trợ công suất phản kháng, Freq-Watt P(f) sa thải phụ tải khi biến thiên tần số và bảo vệ chống tách đảo NA003.",
        "Simulates Volt-Watt active curtailment, Volt-Var reactive support, Frequency-Watt droop curves, and NA003 anti-islanding trip relay.")),
    div("form-grid",
      field(l("Điện áp lưới (V)", "Grid Voltage (V)"), voltageInp),
      field(l("Tần số lưới (Hz)", "Grid Frequency (Hz)"), freqInp),
      field(l("Công suất phát danh định (kW)", "Active Power (kW)"), powerInp)
    ),
    evaluateGridCodeBtn,
    gridCodeContainer
  ));

  // 7. FORTESCUE 3-PHASE SYMMETRICAL COMPONENTS & BALANCER (IEC 61000-4-30)
  const balancerContainer = div("stack");
  const pL1 = ui.input("number", "4.2"); pL1.step = "0.1";
  const pL2 = ui.input("number", "1.8"); pL2.step = "0.1";
  const pL3 = ui.input("number", "0.5"); pL3.step = "0.1";

  const evaluateBalancerBtn = btn(l("Phân tích mất cân bằng 3 pha", "Analyze 3-Phase Unbalance & Dispatch"), async () => {
    balancerContainer.replaceChildren(p(l("Đang phân tích thành phần đối xứng Fortescue...", "Computing Fortescue symmetrical components...")));
    try {
      const data = await api("/phase-balancer/dispatch", {
        p_l1: Number(pL1.value),
        p_l2: Number(pL2.value),
        p_l3: Number(pL3.value),
      });

      const unb = data.unbalance_metrics || {};
      const sp = data.dispatch_setpoints || {};
      const vufBadge = badge(`VUF: ${unb.vuf_pct || 0}%`, (unb.vuf_pct || 0) <= 2.0 ? "good" : "bad");
      const cufBadge = badge(`CUF: ${unb.cuf_pct || 0}%`, (unb.cuf_pct || 0) <= 10.0 ? "good" : "warn");

      const kpis = div("overview-kpis",
        div("fact", e("span", l("Hệ số mất cân bằng áp (VUF):", "Voltage Unbalance (VUF):")), e("b", `${unb.vuf_pct || 0}%`), vufBadge),
        div("fact", e("span", l("Hệ số mất cân bằng dòng (CUF):", "Current Unbalance (CUF):")), e("b", `${unb.cuf_pct || 0}%`), cufBadge),
        div("fact", e("span", l("Thành phần thứ tự nghịch (I₂):", "Negative Sequence (I₂):")), e("b", `${number(unb.i_neg_a)} A`)),
        div("fact", e("span", l("Thành phần thứ tự không (I₀):", "Zero Sequence (I₀):")), e("b", `${number(unb.i_zero_a)} A`))
      );

      const dispatchTable = table(
        [l("Pha", "Phase"), l("Công suất tải (kW)", "Load Power (kW)"), l("Công suất điều độ Inverter (kW)", "Inverter Dispatch (kW)"), l("Bù phản kháng (kVAR)", "Reactive Var (kVAR)")],
        [
          ["L1", pL1.value, `${number(sp.p_l1_kw || 0)} kW`, `${number(sp.q_l1_kvar || 0)} kVAR`],
          ["L2", pL2.value, `${number(sp.p_l2_kw || 0)} kW`, `${number(sp.q_l2_kvar || 0)} kVAR`],
          ["L3", pL3.value, `${number(sp.p_l3_kw || 0)} kW`, `${number(sp.q_l3_kvar || 0)} kVAR`],
          [e("b", l("Tổng cộng", "Total")), e("b", `${(Number(pL1.value) + Number(pL2.value) + Number(pL3.value)).toFixed(1)} kW`), e("b", `${number(sp.total_p_kw || 0)} kW`), e("b", `${number(sp.total_q_kvar || 0)} kVAR`)]
        ]
      );

      balancerContainer.replaceChildren(
        notice(
          `Giải thuật Fortescue IEC 61000-4-30 tính toán phân phối công suất độc lập từng pha. Giữ cho độ lệch điện áp giữa các pha dưới ngưỡng 2% để bảo vệ động cơ và thiết bị 3 pha.`,
          `Fortescue IEC 61000-4-30 algorithm dispatches asymmetric power per phase to mitigate unbalance below the 2.0% threshold.`
        ),
        kpis,
        dispatchTable
      );
    } catch (err) {
      balancerContainer.replaceChildren(p(err.message, "bad"));
    }
  });

  root.append(card(
    l("Cân bằng pha & Thành phần đối xứng Fortescue (IEC 61000-4-30)", "3-Phase Fortescue Symmetrical Components & Asymmetric Balancer"),
    p(l("Phân tích thành phần thứ tự thuận/nghịch/không và điều độ phát công suất bất đối xứng từng pha trên biến tần 3 pha để triệt tiêu lệch áp trung tính.",
        "Decomposes unbalanced phase currents into positive/negative/zero sequences and calculates per-phase asymmetric inverter injection.")),
    div("form-grid",
      field(l("Tải pha L1 (kW)", "Phase L1 Load (kW)"), pL1),
      field(l("Tải pha L2 (kW)", "Phase L2 Load (kW)"), pL2),
      field(l("Tải pha L3 (kW)", "Phase L3 Load (kW)"), pL3)
    ),
    evaluateBalancerBtn,
    balancerContainer
  ));

  // 8. THERMAL LOAD & SG-READY HEAT PUMP
  const thermalContainer = div("stack");
  const ambTemp = ui.input("number", "10.0"); ambTemp.step = "0.5";
  const pvSurplus = ui.input("number", "3.2"); pvSurplus.step = "0.1";
  const tankTemp = ui.input("number", "46.0"); tankTemp.step = "0.5";

  const evaluateThermalBtn = btn(l("Tính toán Carnot COP & Chế độ SG-Ready", "Calculate Carnot COP & SG-Ready Mode"), async () => {
    thermalContainer.replaceChildren(p(l("Đang tính toán chu trình Carnot và lưu trữ nhiệt...", "Evaluating Carnot thermodynamic efficiency and buffer tank...")));
    try {
      const [copRes, sgRes] = await Promise.all([
        api(`/thermal/heat-pump-cop?ambient_temp_c=${encodeURIComponent(ambTemp.value)}&supply_temp_c=35.0`),
        api("/thermal/sg-ready-evaluate", {
          pv_surplus_kw: Number(pvSurplus.value),
          grid_price: 0.15,
          tank_temp_c: Number(tankTemp.value),
        }),
      ]);

      const stateLabels = {
        1: l("Trạng thái 1: Khóa đỉnh tải EVN", "State 1: Grid Operator Lock"),
        2: l("Trạng thái 2: Tiêu chuẩn năng lượng", "State 2: Normal Standard Operation"),
        3: l("Trạng thái 3: Tận dụng điện mặt trời dư thừa", "State 3: PV Surplus Storage Mode"),
        4: l("Trạng thái 4: Nạp nhiệt cưỡng bức tối đa", "State 4: Forced Maximum Storage"),
      };

      const sgBadge = badge(stateLabels[sgRes.sg_ready_state] || `State ${sgRes.sg_ready_state}`, sgRes.sg_ready_state >= 3 ? "good" : "blue");

      const kpis = div("overview-kpis",
        div("fact", e("span", l("Hệ số hiệu quả nhiệt COP:", "Heat Pump Carnot COP:")), e("b", `${number(copRes.cop)}`)),
        div("fact", e("span", l("Công suất điện tiêu thụ:", "Electric Draw:")), e("b", `${number(copRes.electric_kw)} kW`)),
        div("fact", e("span", l("Nhiệt năng sinh ra:", "Thermal Output:")), e("b", `${number(copRes.thermal_kw)} kWth`)),
        div("fact", e("span", l("Nhiệt độ bồn nước nóng:", "DHW Tank Temp:")), e("b", `${tankTemp.value} °C`)),
        div("fact", e("span", l("Dung lượng đệm nhiệt khả dụng:", "Thermal Buffer Headroom:")), e("b", `${number(sgRes.surplus_headroom_kwh)} kWh`))
      );

      thermalContainer.replaceChildren(
        notice(
          `Tiêu chuẩn SG-Ready DIN EN 14511: Tự động kích hoạt nung nóng bồn trữ nước nóng khi công suất điện mặt trời dư thừa vượt ngưỡng 1.8 kW, biến bồn nước thành pin nhiệt lưu trữ miễn phí.`,
          `SG-Ready DIN EN 14511 standard: Automatically raises thermal storage temperature using solar surplus > 1.8 kW, acting as a zero-cost thermal battery.`
        ),
        div("row", sgBadge, badge(`COP: ${copRes.cop}`, "good")),
        kpis
      );
    } catch (err) {
      thermalContainer.replaceChildren(p(err.message, "bad"));
    }
  });

  root.append(card(
    l("Quản lý phụ tải nhiệt & Bơm nhiệt SG-Ready (DIN EN 14511)", "Thermal Load & SG-Ready Heat Pump Manager"),
    p(l("Tính toán hệ số hiệu năng nhiệt động Carnot COP theo nhiệt độ môi trường và điều khiển 4 trạng thái SG-Ready nạp bồn nhiệt khi dư thừa điện mặt trời.",
        "Evaluates temperature-dependent Carnot COP and regulates 4-state SG-Ready heat pumps to absorb solar surplus into domestic hot water buffers.")),
    div("form-grid",
      field(l("Nhiệt độ môi trường (°C)", "Ambient Temp (°C)"), ambTemp),
      field(l("Điện mặt trời dư thừa (kW)", "Solar Surplus (kW)"), pvSurplus),
      field(l("Nhiệt độ bồn nước nóng (°C)", "DHW Tank Temp (°C)"), tankTemp)
    ),
    evaluateThermalBtn,
    thermalContainer
  ));

  // 9. EV FLEET DYNAMIC LOAD MANAGEMENT (DLM)
  const dlmContainer = div("stack");
  const breakerLimit = ui.input("number", "40.0"); breakerLimit.step = "1.0";
  const evSurplus = ui.input("number", "15.0"); evSurplus.step = "0.5";
  const baseLoad = ui.input("number", "12.0"); baseLoad.step = "0.5";

  const evaluateDlmBtn = btn(l("Tối ưu hóa phân bổ sạc xe điện (DLM)", "Optimize Dynamic EV Fleet DLM"), async () => {
    dlmContainer.replaceChildren(p(l("Đang giải bài toán phân bổ động trạm sạc...", "Computing dynamic load allocation and 1p3p switching...")));
    try {
      const data = await api("/ev-fleet/optimize-dlm", {
        site_breaker_limit_kw: Number(breakerLimit.value),
        available_solar_surplus_kw: Number(evSurplus.value),
        building_base_load_kw: Number(baseLoad.value),
        chargers: [
          { id: "cp1", name: "Trạm sạc 01 (Fleet Van)", vehicle_id: "van-01", soc_pct: 45.0, target_soc_pct: 80.0, mode: "pv", priority: 1 },
          { id: "cp2", name: "Trạm sạc 02 (Giám đốc)", vehicle_id: "car-02", soc_pct: 60.0, target_soc_pct: 80.0, mode: "pv_plus_min", priority: 2 },
          { id: "cp3", name: "Trạm sạc 03 (Khách)", vehicle_id: "guest-03", soc_pct: 82.0, target_soc_pct: 80.0, mode: "pv", priority: 3 }
        ]
      });

      const alloc = data.allocations || [];
      const dlmTable = table(
        [l("Trạm sạc", "Charger"), l("Xe kết nối", "Vehicle"), l("SOC hiện tại", "Current SOC"), l("Chế độ", "Mode"), l("Pha (1p/3p)", "Phases"), l("Dòng cấp (A)", "Current (A)"), l("Công suất (kW)", "Power (kW)"), t("status")],
        alloc.map(a => [
          a.charger_id,
          a.connected_vehicle_id,
          `${a.current_soc_pct}%`,
          badge(a.mode, "blue"),
          badge(a.phases === 3 ? "3-Pha (3P)" : "1-Pha (1P)", a.phases === 3 ? "good" : "gray"),
          `${number(a.allocated_current_amps)} A`,
          `${number(a.allocated_power_kw)} kW`,
          badge(a.is_charging ? l("Đang sạc", "Charging") : l("Ngắt 80% SOC", "80% Cutoff"), a.is_charging ? "good" : "gray")
        ])
      );

      const kpis = div("overview-kpis",
        div("fact", e("span", l("Tổng công suất sạc EV:", "Total EV Power:")), e("b", `${number(data.total_ev_power_kw)} kW`)),
        div("fact", e("span", l("Phụ tải toàn nhà máy:", "Total Site Load:")), e("b", `${number(data.total_site_load_kw)} kW`)),
        div("fact", e("span", l("Dung lượng Aptomat còn lại:", "Breaker Headroom:")), e("b", `${number(data.available_breaker_headroom_kw)} kW`, "good-text")),
        div("fact", e("span", l("Công suất PV dư thừa:", "Solar Surplus Utilized:")), e("b", `${number(evSurplus.value)} kW`))
      );

      dlmContainer.replaceChildren(
        notice(
          `Giải thuật DLM điều phối trạm sạc: Giữ tổng phụ tải không vượt quá Aptomat tổng ${breakerLimit.value} kW, tự động chuyển mạch 1 pha (1.4 kW - 3.7 kW) sang 3 pha (4.1 kW - 22 kW) khi nắng to và ngắt ở ngưỡng 80% SOC để bảo vệ tuổi thọ pin xe điện.`,
          `DLM regulates charger currents under the ${breakerLimit.value} kW breaker limit with automatic 1p/3p phase switching and 80% SOC battery longevity cutoff.`
        ),
        kpis,
        dlmTable
      );
    } catch (err) {
      dlmContainer.replaceChildren(p(err.message, "bad"));
    }
  });

  root.append(card(
    l("Điều phối trạm sạc xe điện động (EV Fleet DLM & Chuyển mạch 1p3p)", "EV Fleet Dynamic Load Management (DLM & 1p/3p Phase Switching)"),
    p(l("Phân bổ dòng sạc thời gian thực cho dàn trạm sạc xe điện theo công suất dư thừa điện mặt trời, tự động đảo pha 1p/3p và ngắt sạc ở 80% SOC để kéo dài tuổi thọ cell pin.",
        "Dynamically allocates EV charging currents to track solar surplus, switches between 1-phase and 3-phase, and enforces 80% SOC cutoff.")),
    div("form-grid",
      field(l("Giới hạn Aptomat tổng trạm (kW)", "Main Breaker Limit (kW)"), breakerLimit),
      field(l("Điện mặt trời dư thừa (kW)", "Solar Surplus Available (kW)"), evSurplus),
      field(l("Phụ tải cơ sở tòa nhà (kW)", "Base Building Load (kW)"), baseLoad)
    ),
    evaluateDlmBtn,
    dlmContainer
  ));

  return root;
}
