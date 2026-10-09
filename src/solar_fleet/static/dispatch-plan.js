import { l, number, date } from "./i18n.js";

// Both schedule and EMS views consume the same scoped, storage-backed engine.
export function dispatchPlanCard(ui) {
  const {state, div, e, p, btn, badge, card, table, select, field, input, notice} = ui;
  const root = div("stack gap-md");

  // SECTION 1: EVN TOU OPTIMIZATION & ARBITRAGE (VND)
  const evnContainer = div("stack gap-sm");
  const catSelect = select([
    ["MANUFACTURING", l("Sản xuất / Công nghiệp", "Manufacturing")],
    ["COMMERCIAL_BUSINESS", l("Kinh doanh / Thương mại", "Commercial Business")],
    ["ADMINISTRATIVE", l("Hành chính sự nghiệp", "Administrative")],
  ], "MANUFACTURING");
  const voltSelect = select([
    ["LOW_VOLTAGE_UNDER_22KV", l("Hạ thế (< 22 kV)", "Low Voltage (< 22 kV)")],
    ["MEDIUM_VOLTAGE_22_110KV", l("Trung thế (22 - 110 kV)", "Medium Voltage (22 - 110 kV)")],
    ["HIGH_VOLTAGE_110KV", l("Cao thế (≥ 110 kV)", "High Voltage (≥ 110 kV)")],
  ], "LOW_VOLTAGE_UNDER_22KV");

  const runEvnBtn = btn(l("Tối ưu hóa điều độ theo biểu giá EVN (24h)", "Optimize 24h Schedule for EVN TOU"), async () => {
    if (!state.site) {
      evnContainer.replaceChildren(p(l("Vui lòng chọn nhà máy.", "Select a plant first.")));
      return;
    }
    runEvnBtn.disabled = true;
    evnContainer.replaceChildren(p(l("Đang tính toán tối ưu chu kỳ sạc/xả...", "Computing optimal dispatch trajectory...")));
    try {
      const q = `category=${encodeURIComponent(catSelect.value)}&voltage=${encodeURIComponent(voltSelect.value)}`;
      const res = await ui.api(`/sites/${encodeURIComponent(state.site)}/ems-optimization?${q}`);

      const kpis = div("grid grid-4 gap-sm",
        div("card kpi-card",
          div("stack", e("span", l("Chi phí cơ sở (Không pin)", "Baseline Cost (No ESS)"), "kpi-label"),
            e("b", `${number(res.total_baseline_cost_vnd)} đ`, "kpi-value"))),
        div("card kpi-card",
          div("stack", e("span", l("Chi phí sau tối ưu EMS", "Optimized EMS Cost"), "kpi-label"),
            e("b", `${number(res.total_optimized_cost_vnd)} đ`, "kpi-value green"))),
        div("card kpi-card",
          div("stack", e("span", l("Tiết kiệm ròng trong ngày", "Net Daily Savings"), "kpi-label"),
            e("b", `${number(res.net_savings_vnd)} đ`, "kpi-value orange"))),
        div("card kpi-card",
          div("stack", e("span", l("Tỷ lệ giảm hóa đơn", "Bill Reduction"), "kpi-label"),
            e("b", `${res.savings_pct}%`, "kpi-value"))),
      );

      const tableSlots = table(
        [
          l("Giờ", "Hour"),
          l("Khung giá EVN", "EVN Tier"),
          l("Đơn giá", "Tariff"),
          "PV (kW)",
          l("Phụ tải (kW)", "Load (kW)"),
          l("Hành động", "Action"),
          l("Sạc/Xả (kW)", "ESS kW"),
          l("Mua lưới (kW)", "Grid (kW)"),
          "SOC %",
          l("Tiền điện", "Cost"),
        ],
        (res.slots_24h || []).map(s => {
          const tierBadge = s.tier === "PEAK"
            ? badge(l("Cao điểm", "Peak"), "red")
            : s.tier === "OFF_PEAK"
              ? badge(l("Thấp điểm", "Off-Peak"), "green")
              : badge(l("Bình thường", "Normal"), "blue");

          const pEss = s.charge_kw > 0
            ? `+${s.charge_kw} kW`
            : s.discharge_kw > 0
              ? `-${s.discharge_kw} kW`
              : "0 kW";

          return [
            `${s.hour}:00`,
            tierBadge,
            `${number(s.rate_vnd)} đ`,
            s.solar_kw,
            s.load_kw,
            s.action === "GRID_CHARGE"
              ? badge(l("Nạp lưới giờ rẻ", "Grid Charge"), "green")
              : s.action === "PEAK_DISCHARGE"
                ? badge(l("Xả đỉnh giờ đắt", "Peak Shave"), "orange")
                : badge(l("Tự dùng", "Self-Use"), "gray"),
            pEss,
            s.grid_import_kw,
            `${s.battery_soc_pct}%`,
            `${number(s.cost_vnd)} đ`,
          ];
        })
      );

      const touProgTable = table(
        [
          l("Slot", "Slot"),
          l("Giờ bắt đầu", "Start Time"),
          l("Công suất (W)", "Power (W)"),
          l("SOC mục tiêu", "Target SOC"),
          l("Nạp từ lưới", "Grid Charge"),
        ],
        (res.tou_programme?.slots || []).map(ts => [
          `#${ts.index}`,
          ts.time,
          `${ts.power_w} W`,
          `${ts.target_soc}%`,
          ts.grid_charge ? badge(l("Bật", "Enabled"), "green") : badge(l("Tắt", "Disabled"), "gray"),
        ])
      );

      const lowVal = res.scenarios?.low_solar_savings_vnd ?? res.scenarios?.p10_gloomy_savings_vnd;
      const highVal = res.scenarios?.high_solar_savings_vnd ?? res.scenarios?.p90_sunny_savings_vnd;
      const scenarioBar = res.scenarios ? div("row gap-md wrap align-center card",
        e("b", l("Phân tích độ nhạy quang năng (Độ nhạy thời tiết):", "Solar Generation Sensitivity Scenarios:"), "muted"),
        badge(`${l("Kịch bản nắng yếu (-55%):", "Low Solar (-55%):")} ${number(lowVal)} đ`, "warn"),
        badge(`${l("Kịch bản chuẩn:", "Nominal:")} ${number(res.scenarios.nominal_savings_vnd)} đ`, "blue"),
        badge(`${l("Kịch bản nắng mạnh (+35%):", "High Solar (+35%):")} ${number(highVal)} đ`, "good"),
        badge(`${l("Sau hao mòn pin:", "Net after wear:")} ${number(res.net_profit_after_wear_vnd || res.net_savings_vnd)} đ`, "blue-soft"),
      ) : div();

      evnContainer.replaceChildren(
        kpis,
        scenarioBar,
        card(l("Kế hoạch điều độ 24 giờ", "24-Hour Dispatch Plan"), tableSlots),
        card(l("Kế hoạch điều độ năng lượng 6 khung giờ (Universal Energy Plan)", "6-Slot Universal Energy Plan"),
          p(l("Lịch nạp/xả phổ quát này được chuyển dịch qua compiler của từng hãng biến tần để nạp vào thanh ghi phần cứng khi điều độ.",
            "This universal energy plan is translated by vendor-specific compilers to enforce exact hardware registers when dispatched.")),
          touProgTable
        )
      );
    } catch (err) {
      evnContainer.replaceChildren(p(err.message, "bad"));
    } finally {
      runEvnBtn.disabled = false;
    }
  }, "primary");

  root.append(
    card(
      l("Ước tính lịch sạc / xả tiết kiệm điện", "Estimate a cost-saving battery schedule"),
      p(l(
        "Chọn nhóm giá điện phù hợp để tính lịch tham khảo từ số đo và cấu hình pin. Kết quả chưa áp dụng cho thiết bị và không phải hóa đơn. Nhờ đơn vị lắp đặt xác nhận nhóm giá nếu bạn chưa rõ.",
        "Select a tariff category to estimate a schedule from measurements and battery configuration. Results are not sent to equipment and are not a bill. Ask your installer to confirm the category if unsure."
      )),
      div("row gap-sm align-center wrap",
        field(l("Nhóm khách hàng", "Customer Group"), catSelect),
        field(l("Cấp điện áp", "Voltage Level"), voltSelect),
        runEvnBtn
      ),
      evnContainer
    )
  );

  // SECTION 2: MULTI-INVERTER FLEET BALANCING
  const balanceContainer = div("stack gap-sm");
  const targetPowerInput = input("number", ""); targetPowerInput.min = "1"; targetPowerInput.max = "500"; targetPowerInput.required = true;
  const modeSelect = select([
    ["charge", l("Nạp sạc (Charge)", "Charge")],
    ["discharge", l("Xả tải (Discharge)", "Discharge")],
  ], "charge");

  const runBalanceBtn = btn(l("Phân bổ công suất cân bằng pin", "Compute Balanced Allocation"), async () => {
    if (!state.site) { balanceContainer.replaceChildren(p(l("Chọn nhà máy trước khi tính toán.", "Select a plant before calculating."))); return; }
    if (!targetPowerInput.reportValidity()) return;
    runBalanceBtn.disabled = true;
    try {
      const res = await ui.api(`/sites/${encodeURIComponent(state.site)}/fleet-balance`, {
        target_total_kw: Number(targetPowerInput.value),
        mode: modeSelect.value,
      });

      const rows = Object.entries(res.allocations || {}).map(([devId, kw]) => {
        const devObj = (state.fleet.devices || []).find(d => d.id === devId);
        const devLabel = devObj ? `${devObj.name || devObj.vendor_id} · ${devObj.brand || "Solar"}` : devId;
        return [
          devLabel,
          `${kw} kW`,
          `${res.projected_socs?.[devId] ?? "—"}%`,
        ];
      });

      balanceContainer.replaceChildren(
        notice(l(
          `Ước tính phân bổ ${res.target_total_kw} kW. Kết quả chỉ để tham khảo, chưa gửi lệnh tới thiết bị.`,
          `Estimated allocation of ${res.target_total_kw} kW. Advisory only; no equipment command has been sent.`
        )),
        table([l("Biến tần", "Inverter"), l("Công suất phân bổ", "Allocated Power"), l("SOC dự kiến sau 1h", "Projected SOC (1h)")], rows)
      );
    } catch (err) {
      balanceContainer.replaceChildren(p(err.message, "bad"));
    } finally {
      runBalanceBtn.disabled = false;
    }
  });

  root.append(
    card(
      l("Chia công suất giữa các biến tần", "Allocate power across inverters"),
      p(l(
        "Nhập công suất mong muốn để tính phân bổ tham khảo. Cần mức pin đo được và giới hạn công suất của từng thiết bị. Kết quả tính không tự điều khiển thiết bị.",
        "Enter the requested power for an advisory allocation. Measured battery levels and each device's limits are required. Calculations do not control equipment."
      )),
      div("row gap-sm align-center wrap",
        field(l("Tổng công suất mục tiêu (kW)", "Target Total Power (kW)"), targetPowerInput),
        field(l("Chế độ", "Mode"), modeSelect),
        runBalanceBtn
      ),
      balanceContainer
    )
  );

  return root;
}
