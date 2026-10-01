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

      evnContainer.replaceChildren(
        kpis,
        card(l("Kế hoạch điều độ 24 giờ", "24-Hour Dispatch Plan"), tableSlots),
        card(l("Chương trình 6 Slot TOU tương thích phần cứng biến tần (Deye/Sunsynk/Solis/Growatt)", "Inverter Hardware 6-Slot TOU Programme"),
          p(l("Lịch nạp/xả này có thể truyền trực tiếp vào các thanh ghi Modbus của biến tần thông qua Unified Adapter.",
            "This schedule can be compiled and written directly into inverter Modbus holding registers via the Unified Adapter.")),
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
      l("Tối ưu hóa Chi phí Tiền điện theo Biểu giá EVN (3 Giá QĐ 2699/QĐ-BCT)", "EVN Time-of-Use Tariff Arbitrage Optimization"),
      p(l(
        "Thuật toán tối ưu hóa điều độ sạc xả pin dựa trên 3 khung giờ của EVN: Tự động nạp đầy pin trong giờ thấp điểm (đơn giá ~1.100 đ/kWh) và xả công suất cực đại vào 2 khung giờ cao điểm (sáng 09:30-11:30 và tối 17:00-20:00, đơn giá ~3.200 - 4.900 đ/kWh) để triệt tiêu phụ tải đỉnh.",
        "Algorithm optimizes battery charge/discharge based on EVN 3-tier tariff: auto-charges during off-peak hours (~1,100 VND/kWh) and discharges during morning and evening peak hours (~3,200 - 4,900 VND/kWh) to eliminate peak demand charges."
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
  const targetPowerInput = input("number", 15); targetPowerInput.min = "1"; targetPowerInput.max = "500";
  const modeSelect = select([
    ["charge", l("Nạp sạc (Charge)", "Charge")],
    ["discharge", l("Xả tải (Discharge)", "Discharge")],
  ], "charge");

  const runBalanceBtn = btn(l("Phân bổ công suất cân bằng pin", "Compute Balanced Allocation"), async () => {
    if (!state.site) return;
    runBalanceBtn.disabled = true;
    try {
      const res = await ui.api(`/sites/${encodeURIComponent(state.site)}/fleet-balance`, {
        target_total_kw: Number(targetPowerInput.value),
        mode: modeSelect.value,
      });

      const rows = Object.entries(res.allocations || {}).map(([devId, kw]) => [
        devId,
        `${kw} kW`,
        `${res.projected_socs?.[devId] ?? "—"}%`,
      ]);

      balanceContainer.replaceChildren(
        notice(l(
          `Đã phân bổ tổng ${res.target_total_kw} kW ở chế độ ${res.mode.toUpperCase()}. Các pin có mức SOC lệch nhau được cấp dòng bù để cân bằng suy hao cell.`,
          `Allocated ${res.target_total_kw} kW in ${res.mode.toUpperCase()} mode. SOC differences are balanced to prevent single-pack degradation.`
        )),
        table([l("Mã biến tần", "Inverter ID"), l("Công suất phân bổ", "Allocated Power"), l("SOC dự kiến sau 1h", "Projected SOC (1h)")], rows)
      );
    } catch (err) {
      balanceContainer.replaceChildren(p(err.message, "bad"));
    } finally {
      runBalanceBtn.disabled = false;
    }
  });

  root.append(
    card(
      l("Cân bằng Công suất Đa Biến tần (Multi-Inverter Fleet Balancing)", "Multi-Inverter Fleet Balancing"),
      p(l(
        "Kế thừa từ batpred/inverter.py: Khi trạm có nhiều biến tần hybrid chạy song song, thuật toán phân bổ công suất theo tỷ lệ SOC để tránh chai lệch pin và bảo đảm tất cả các pack pin đạt trạng thái cân bằng đồng thời.",
        "Derived from batpred/inverter.py: Balances power across parallel hybrid inverters based on real-time SOC to prevent uneven battery wear and synchronize full charge states."
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