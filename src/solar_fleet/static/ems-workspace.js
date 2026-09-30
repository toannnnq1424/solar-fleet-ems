import { advisoryCalculator } from "./advisory-calculator.js";
import { dispatchPlanCard } from "./dispatch-plan.js";
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
    "Điều độ yêu cầu lịch sử đo đã xác minh và cấu hình pin, giá điện rõ ràng. Kết quả chỉ là ước tính, không phát lệnh; chưa tính hóa đơn EVN hoặc phạt phản kháng.",
    "Dispatch requires verified history and explicit battery and tariff configuration. Results are advisory only, not commands, EVN bills or reactive-energy penalties."
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

  root.append(dispatchPlanCard(ui));

  // 3. EVN TARIFF & CIRCULAR 15 POWER FACTOR ANALYSIS
  const tariffContainer = div("stack");
  const tariffCard = card(l("Điện nhập tại công tơ thanh toán", "Billing meter import observations"));

  const loadTariffBtn = btn(l("Đọc điện nhập và độ phủ dữ liệu", "Read import energy and coverage"), async () => {
    const currentSiteId = state.site;
    if (!currentSiteId) return;
    loadTariffBtn.disabled = true;
    tariffContainer.replaceChildren(p(l("Đang tải dữ liệu điện nhập...", "Loading import observations...")));
    try {
      const data = await api(`/sites/${encodeURIComponent(currentSiteId)}/tariff-analysis`);
      tariffContainer.replaceChildren(
        p(l("Ước tính từ công suất quan sát và giá khai báo, không phải hóa đơn. Không tính khoảng thiếu giá hoặc vượt ranh giới giá; chưa gồm thuế, phí, phản kháng.",
          "Estimate from observed power and declared rates, not a bill. Missing or unaligned tariff intervals excluded; taxes, fees and reactive energy excluded.")),
        table([l("Chỉ số", "Metric"), l("Giá trị", "Value")], [
          [l("Điện nhập đo được (kWh)", "Observed import (kWh)"), number(data.observed_import_kwh)],
          [l("Độ phủ dữ liệu", "Observation coverage"), `${number(data.coverage * 100)}%`],
          [l("Tiền điện", "Bill"), number(data.total_active_bill_vnd)],
          [l("Chi phí nhập ước tính (VND)", "Estimated import cost (VND)"), number(data.estimated_import_cost_vnd)],
          [l("Độ phủ được định giá", "Priced coverage"), `${number(data.priced_coverage * 100)}%`],
          [l("Nguồn giá khai báo", "Declared rate sources"), [...new Set((data.priced_intervals || []).map(v => v.source))].join("; ") || "—"],
          [l("Trạng thái", "Status"), data.status === "PARTIAL_OBSERVATIONS"
            ? l("Số đo chưa đầy đủ", "Partial observations")
            : data.status === "INSUFFICIENT_DATA" ? l("Chưa đủ dữ liệu", "Insufficient data") : t("unknown")]
        ])
      );
    } catch (err) {
      tariffContainer.replaceChildren(p(err.message, "bad"));
    } finally {
      loadTariffBtn.disabled = false;
    }
  });

  tariffCard.append(
    p(l("Cần chọn công tơ thanh toán. Chưa tính tiền điện hoặc xác nhận tuân thủ phản kháng khi thiếu biểu giá và dữ liệu phù hợp.",
      "An explicit billing meter is required. Missing tariffs or observations cannot establish bills or reactive-energy compliance.")),
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

  root.append(advisoryCalculator(ui, "Grid response estimate", "/grid-code/evaluate",
    "voltage_v, frequency_hz, current_power_kw; volt_watt {nominal_voltage_v, v1_v, v2_v, v3_v, v4_v, p_rated_kw, min_power_ratio}; volt_var {nominal_voltage_v, v1_v, v2_v, v3_v, v4_v, q_max_ratio, rated_kva}; freq_watt {nominal_freq_hz, over_freq_threshold_hz, under_freq_threshold_hz, droop_pct, p_rated_kw}; protection {v_min_trip_v, v_max_trip_v, f_min_trip_hz, f_max_trip_hz}"));

  // 7. FORTESCUE 3-PHASE SYMMETRICAL COMPONENTS & BALANCER (IEC 61000-4-30)
  const balancerContainer = div("stack");
  const phaseInput = e("textarea");
  phaseInput.rows = 8;
  phaseInput.setAttribute("aria-label", "Phase measurements and equipment limits JSON");

  const evaluateBalancerBtn = btn(l("Phân tích mất cân bằng 3 pha", "Analyze 3-Phase Unbalance & Dispatch"), async () => {
    balancerContainer.replaceChildren(p(l("Đang phân tích thành phần đối xứng Fortescue...", "Computing Fortescue symmetrical components...")));
    try {
      const payload = JSON.parse(phaseInput.value);
      const data = await api("/phase-balancer/dispatch", payload);
      const measured = payload.measurement;

      const unb = data.unbalance_metrics || {};
      const sp = data.dispatch_setpoints || {};
      const vufBadge = badge(`VUF: ${unb.vuf_pct || 0}%`, (unb.vuf_pct || 0) <= 2.0 ? "good" : "bad");
      const cufBadge = badge(`CUF: ${unb.cuf_pct || 0}%`, (unb.cuf_pct || 0) <= 10.0 ? "good" : "warn");

      const kpis = div("overview-kpis",
        div("fact", e("span", l("Hệ số mất cân bằng áp (VUF):", "Voltage Unbalance (VUF):")), e("b", `${unb.vuf_pct || 0}%`), vufBadge),
        div("fact", e("span", l("Hệ số mất cân bằng dòng (CUF):", "Current Unbalance (CUF):")), e("b", `${unb.cuf_pct || 0}%`), cufBadge),
        div("fact", e("span", l("Dòng trung tính ước tính:", "Estimated neutral current:")), e("b", `${number(unb.i_neutral_amps)} A`))
      );

      const dispatchTable = table(
        [l("Pha", "Phase"), l("Công suất tải (kW)", "Load Power (kW)"), l("Công suất điều độ Inverter (kW)", "Inverter Dispatch (kW)"), l("Bù phản kháng (kVAR)", "Reactive Var (kVAR)")],
        [
          ["L1", measured.p_l1, `${number(sp.p_l1_kw)} kW`, `${number(sp.q_l1_kvar)} kVAR`],
          ["L2", measured.p_l2, `${number(sp.p_l2_kw)} kW`, `${number(sp.q_l2_kvar)} kVAR`],
          ["L3", measured.p_l3, `${number(sp.p_l3_kw)} kW`, `${number(sp.q_l3_kvar)} kVAR`],
          [e("b", l("Tổng cộng", "Total")), number(measured.p_l1 + measured.p_l2 + measured.p_l3), number(sp.total_p_kw), number(sp.total_q_kvar)]
        ]
      );

      balancerContainer.replaceChildren(
        notice(
          `Ước tính với giả định góc lệch pha 120°. Không xác nhận tuân thủ, không gửi lệnh và không bảo đảm giảm lệch áp.`,
          `Estimate assuming 120° phase displacement. Not a compliance assessment; no commands sent or voltage correction guaranteed.`
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
    p(l("Máy tính tư vấn; nhập đầy đủ số đo và giới hạn thiết bị, không tự điền số mẫu.",
        "Advisory calculator; supply all measurements and equipment limits. No sample values supplied.")),
    p("JSON: measurement {v_l1, v_l2, v_l3, i_l1, i_l2, i_l3, p_l1, p_l2, p_l3, q_l1, q_l2, q_l3}; limits {max_total_kw, max_phase_kw, max_phase_kvar, battery_max_charge_kw, battery_max_discharge_kw, allows_independent_phases}"),
    phaseInput,
    evaluateBalancerBtn,
    balancerContainer
  ));

  root.append(advisoryCalculator(ui, "Heat pump estimate", "/thermal/heat-pump-cop",
    "ambient_temp_c, supply_temp_c, required_thermal_kw, carnot_efficiency, min_electric_kw, max_electric_kw"));
  root.append(advisoryCalculator(ui, "SG-ready recommendation", "/thermal/sg-ready-evaluate",
    "pv_surplus_kw, grid_price, is_grid_peak_lock, surplus_threshold_kw, forced_surplus_kw, tank_temp_c, min_temp_c, normal_setpoint_c, boost_setpoint_c"));

  // 9. EV FLEET DYNAMIC LOAD MANAGEMENT (DLM)
  const dlmContainer = div("stack");
  const breakerLimit = ui.input("number", ""); breakerLimit.step = "any";
  const evSurplus = ui.input("number", ""); evSurplus.step = "any";
  const baseLoad = ui.input("number", ""); baseLoad.step = "any";
  const evObservedAt = ui.input("text", "");
  const chargerInputs = e("textarea");
  chargerInputs.rows = 8;
  const requiredNumber = input => {
    if (!input.value.trim() || !Number.isFinite(Number(input.value))) {
      throw new Error(l("Nhập đầy đủ số đo và thông số thực.", "Enter all actual observations and specifications."));
    }
    return Number(input.value);
  };

  const evaluateDlmBtn = btn(l("Tối ưu hóa phân bổ sạc xe điện (DLM)", "Optimize Dynamic EV Fleet DLM"), async () => {
    evaluateDlmBtn.disabled = true;
    dlmContainer.replaceChildren(p(l("Đang tính phân bổ tham khảo...", "Computing advisory allocation with fixed phases...")));
    try {
      const data = await api("/ev-fleet/optimize-dlm", {
        site_breaker_limit_kw: requiredNumber(breakerLimit),
        available_solar_surplus_kw: requiredNumber(evSurplus),
        building_base_load_kw: requiredNumber(baseLoad),
        observed_at: evObservedAt.value.trim() || null,
        chargers: JSON.parse(chargerInputs.value)
      });

      const alloc = data.chargers;
      const dlmTable = table(
        [l("Trạm sạc", "Charger"), l("Xe kết nối", "Vehicle"), l("SOC hiện tại", "Current SOC"), l("Chế độ", "Mode"), l("Pha (1p/3p)", "Phases"), l("Dòng cấp (A)", "Current (A)"), l("Công suất (kW)", "Power (kW)"), t("status")],
        alloc.map(a => [
          a.charger_id,
          a.vehicle_id ?? "—",
          number(a.vehicle_soc),
          badge(a.mode, "blue"),
          badge(a.phases === 3 ? "3-Pha (3P)" : "1-Pha (1P)", a.phases === 3 ? "good" : "gray"),
          `${number(a.allocated_amps)} A`,
          `${number(a.power_kw)} kW`,
          badge(a.is_charging ? l("Đề xuất sạc", "Proposed charging") : l("Không phân bổ", "Not allocated"), "gray")
        ])
      );

      const kpis = div("overview-kpis",
        div("fact", e("span", l("Tổng công suất sạc EV:", "Total EV Power:")), e("b", `${number(data.total_ev_power_kw)} kW`)),
        div("fact", e("span", l("Phụ tải dự kiến:", "Estimated Site Load:")), e("b", `${number(data.building_base_load_kw + data.total_ev_power_kw)} kW`)),
        div("fact", e("span", l("Dư địa trước phân bổ:", "Headroom Before Allocation:")), e("b", `${number(data.available_headroom_kw)} kW`)),
        div("fact", e("span", l("PV dư còn lại:", "Remaining Solar Surplus:")), e("b", `${number(data.remaining_solar_kw)} kW`))
      );

      dlmContainer.replaceChildren(
        notice(
          "Ước tính từ đầu vào người dùng, không phải số đo đã xác minh. Không gửi lệnh sạc hoặc chuyển pha.",
          "Estimated from user-supplied inputs, not verified telemetry. No charging or phase-switch commands are sent."
        ),
        p(data.freshness?.status === "USER_REPORTED_RECENT"
          ? l("Thời điểm khai báo trong 5 phút; chưa xác minh nguồn đo.", "Declared timestamps are within 5 minutes; telemetry remains unverified.")
          : l("Chưa xác định độ mới: thiếu thời điểm đo tại site hoặc trạm sạc.", "Freshness unknown: site or charger observation timestamps are missing.")),
        kpis,
        dlmTable
      );
    } catch (err) {
      dlmContainer.replaceChildren(p(err.message, "bad"));
    } finally {
      evaluateDlmBtn.disabled = false;
    }
  });

  root.append(card(
    l("Điều phối trạm sạc xe điện động (EV Fleet DLM & Chuyển mạch 1p3p)", "EV Fleet Dynamic Load Management (DLM & 1p/3p Phase Switching)"),
    p(l("Tính phân bổ tham khảo từ thông số nhập rõ ràng. Giữ nguyên số pha đã cấu hình, không điều khiển thiết bị.",
        "Calculate advisory allocations from explicit inputs. Configured phases remain fixed; no equipment is controlled.")),
    p("JSON: id, name, vehicle_id, soc_pct, target_soc_pct, mode (off/now/min_pv/pv), priority (1–5), min_current_amps, max_current_amps, voltage_per_phase_v, phases (1/3), observed_at (ISO 8601 with timezone)."),
    p(l("Thời điểm đo là tùy chọn; bỏ trống nghĩa là chưa rõ độ mới. Nếu nhập, phải trong 5 phút và không ở tương lai.",
        "Observation timestamps are optional; blank means unknown freshness. Supplied timestamps must be within 5 minutes and not in the future.")),
    field(l("Thời điểm đo site (ISO 8601 có múi giờ)", "Site observation time (ISO 8601 with timezone)"), evObservedAt),
    field(l("Danh sách trạm sạc thực (JSON)", "Actual charger list (JSON)"), chargerInputs),
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
