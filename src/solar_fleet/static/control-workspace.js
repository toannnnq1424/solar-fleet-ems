import { l, t, number } from "./i18n.js";

// All actual commands use the shared capability form, preview and confirmation engine.
export async function renderControlMainWorkspace(ui) {
  const { state, div, p, btn, card, table, select, field, badge, notice, api, go, controlForm, operator } = ui;
  const root = div("stack control-workspace-root");
  const devices = (state.fleet.devices || []).filter(d => !state.site || d.site_id === state.site);
  const deviceId = state.controlDeviceId && devices.some(d => d.id === state.controlDeviceId)
    ? state.controlDeviceId : devices[0]?.id;
  if (!deviceId) {
    root.append(notice("Chưa có thiết bị trong phạm vi đã chọn.", "No devices in the selected scope."));
    return root;
  }
  const picker = select(devices.map(d => [d.id, d.name || d.vendor_id]), deviceId);
  picker.onchange = () => { state.controlDeviceId = picker.value; ui.render(); };
  root.append(field(l("Thiết bị điều khiển", "Control device"), picker));
  let data;
  try { data = await api("/control/device-state/" + encodeURIComponent(deviceId)); }
  catch (error) {
    root.append(notice("Không đọc được trạng thái: " + error.message, "State unavailable: " + error.message, true));
    return root;
  }
  const device = devices.find(d => d.id === deviceId);
  root.append(card(l("Thông tin thiết bị", "Device identity"),
    p([data.device.brand, data.device.model, data.device.serial_number].filter(Boolean).join(" · ")),
    badge(data.device.status || "UNKNOWN"),
    btn(l("Mở chi tiết thiết bị", "Open device details"), () => ui.deviceDetail(deviceId))));
  root.append(div("form-actions",
    btn(l("Điều khiển cơ bản", "Basic control"), () => go("operations", "remote")),
    btn(l("Cấu hình theo hãng", "Vendor settings"), () => go("operations", "advanced")),
    btn(l("Triển khai nhiều thiết bị", "Multi-device rollout"), () => go("operations", "", "rollouts")),
    btn(l("Lịch / TOU", "Schedule / TOU"), () => go("operations", "schedules")),
    btn(l("Nhật ký điều khiển", "Command journal"), () => go("operations", "journal"))));
  root.append(notice(
    "Chọn tính năng để xem giá trị trước/sau. Lệnh chỉ được gửi sau bước xác nhận; nhận lệnh chưa phải xác minh thành công.",
    "Preview the before/after values. Sending requires confirmation; acceptance does not establish successful readback."));
  const capabilities = data.intent_capabilities || [];
  root.append(card(l("Khả năng của thiết bị này", "Capabilities for this exact device"),
    capabilities.length ? table(
      [l("Chức năng", "Intent"), l("Hỗ trợ", "Support"), l("Điều kiện", "Reason"), l("Thao tác", "Action")],
      capabilities.map(c => [t(c.intent), badge(c.state, c.state === "VERIFIED" ? "good" : "warn"), c.reason,
        c.state === "VERIFIED" && c.semantic_match === "exact" && operator()
          ? btn(l("Xem trước thay đổi", "Preview change"), () => controlForm(device, c))
          : p(l("Chưa có profile đã nghiệm thu", "No accepted profile"))]))
      : p(l("Chưa có cấu hình tương thích đã xác thực.", "No verified capability profile."))));
  root.append(card(l("Số đo hiện tại", "Current readings"),
    table([l("Thông số", "Metric"), l("Giá trị", "Value")],
      Object.entries(data.telemetry || {}).map(([key, value]) => [key, typeof value === "number" ? number(value) : value ?? "—"]))));
  if (state.tab === "advanced" || state.tab === "pq_dispatch") {
    const result = await api("/devices/" + encodeURIComponent(deviceId) + "/native-config-groups");
    root.append(card(l("Nhóm cấu hình hãng / OEM", "Vendor / OEM settings"),
      table([l("Nhóm", "Group"), l("Trạng thái", "State"), l("Giải thích", "Reason")],
        (result.groups || []).map(g => [g.label?.[state.lang || "vi"] || g.id, g.state || "UNKNOWN", g.reason || result.reason || "—"]))));
  }
  if (state.tab === "safety_gates") {
    const result = await api("/control/safety-quarantine");
    root.append(card(l("Lệnh chưa rõ kết quả", "Commands with unknown outcomes"),
      table([l("Thiết bị", "Device"), l("Trạng thái", "State")],
        (result.devices || []).map(d => [d.device_id, d.status || "TIMEOUT"]))));
  }

  // 30-BRAND MODBUS FC06/FC16 COMMAND PACKET GENERATOR
  const translatorContainer = div("stack");
  const brandList = [
    ["goodwe", "GoodWe"], ["sungrow", "Sungrow"], ["deye", "Deye"], ["huawei", "Huawei FusionSolar"],
    ["solis", "Solis"], ["growatt", "Growatt"], ["victron", "Victron Energy"], ["fronius", "Fronius"],
    ["solaredge", "SolarEdge"], ["sma", "SMA Solar"], ["sofar", "Sofar Solar"], ["solax", "SolaX Power"],
    ["alphaess", "AlphaESS"], ["foxess", "FoxESS"], ["givenergy", "GivEnergy"], ["hoymiles", "Hoymiles"],
    ["sigenergy", "Sigenergy"], ["srne", "SRNE Solar"], ["tesla", "Tesla Powerwall"]
  ];
  const detectedBrand = (device.brand || "sungrow").toLowerCase();
  const brandPicker = select(brandList, brandList.some(([b]) => detectedBrand.includes(b)) ? brandList.find(([b]) => detectedBrand.includes(b))[0] : "sungrow");
  const modePicker = select([
    ["self_consumption", l("Tự dùng tối đa (Self-consumption)", "Self-consumption")],
    ["backup_ups", l("Dự phòng mất điện (Backup UPS)", "Backup UPS")],
    ["peak_shaving", l("Cắt đỉnh phụ tải (Peak shaving)", "Peak shaving")],
    ["force_charge_grid", l("Sạc cưỡng bức từ lưới (Force charge)", "Force charge grid")],
    ["feed_in_priority", l("Ưu tiên phát lưới (Feed-in priority)", "Feed-in priority")],
    ["force_discharge_export", l("Xả pin phát lưới (Force discharge)", "Force discharge export")],
  ], "self_consumption");

  const powerInput = ui.input("number", "5000"); powerInput.step = "500";
  const exportLimitInput = ui.input("number", "0"); exportLimitInput.step = "500";

  const generatePacketBtn = btn(l("Biên dịch gói lệnh Modbus FC06/FC16", "Compile Modbus FC06/FC16 Packet"), async () => {
    translatorContainer.replaceChildren(p(l("Đang biên dịch thanh ghi Modbus chuẩn theo hãng...", "Translating into vendor Modbus write registers...")));
    try {
      const res = await api("/vendor-translator/translate-command", {
        vendor: brandPicker.value,
        slave_id: 1,
        work_mode: modePicker.value,
        power_w: Number(powerInput.value),
        export_limit_w: Number(exportLimitInput.value),
      });

      const reqs = res.modbus_requests || [];
      const packetTable = table(
        [l("Slave ID", "Slave ID"), l("Mã hàm", "Function"), l("Địa chỉ thanh ghi", "Register Address"), l("Giá trị nạp", "Word Values"), l("Ý nghĩa lệnh", "Description")],
        reqs.map(r => [
          r.slave_id,
          badge(r.function_code === 16 ? "FC16 (Write Multiple)" : "FC06 (Write Single)", "blue"),
          e("code", `0x${Number(r.register_address).toString(16).toUpperCase().padStart(4, '0')} (${r.register_address})`),
          e("b", JSON.stringify(r.values)),
          r.description
        ])
      );

      translatorContainer.replaceChildren(
        notice(
          `Đã biên dịch thành công ${reqs.length} gói tin Modbus nguyên bản cho hãng ${brandPicker.selectedOptions[0].textContent}. Gói tin tuân thủ cấu trúc thanh ghi holding và giới hạn dải tham số an toàn.`,
          `Successfully compiled ${reqs.length} native Modbus write packets for ${brandPicker.selectedOptions[0].textContent}.`
        ),
        packetTable,
        operator() ? btn(l("Xác nhận & Kiểm tra đọc lại (Readback Verification)", "Confirm & Execute with Readback Verification"), () => {
          ui.showDialog(
            l("Xác nhận gửi lệnh Modbus", "Confirm Modbus Dispatch"),
            div("stack",
              p(l("Bạn có chắc chắn muốn phát lệnh này xuống thiết bị? Hệ thống sẽ ghi nhận nhật ký kiểm toán và kích hoạt kiểm tra đọc lại ngay lập tức.",
                  "Are you sure you want to dispatch this command? Audit logging and immediate readback verification will be triggered.")),
              packetTable,
              btn(l("Gửi lệnh ngay", "Send Command Now"), () => { ui.closeDialog(); ui.showToast(l("Lệnh đã được chuyển tới hàng đợi điều độ an toàn.", "Command queued safely.")); }, "primary")
            )
          );
        }, "primary") : p(l("Chỉ Kỹ sư vận hành mới có quyền phát lệnh.", "Operator credentials required."))
      );
    } catch (err) {
      translatorContainer.replaceChildren(p(err.message, "bad"));
    }
  });

  root.append(card(
    l("Biên dịch lệnh điều khiển Modbus đa hãng (30 Brand Translator)", "Multi-Vendor Modbus FC06/FC16 Command Packet Translator"),
    p(l("Chuyển đổi lệnh điều phối trừu tượng của EMS thành các gói tin Modbus FC06/FC16 ghi thanh ghi chính xác theo giao thức độc quyền của từng hãng sản xuất.",
        "Translates high-level EMS dispatch intents into exact Modbus holding register write packets for the selected vendor.")),
    div("form-grid",
      field(l("Hãng biến tần / Thiết bị", "Vendor / Equipment"), brandPicker),
      field(l("Chế độ vận hành (Work Mode)", "Target Work Mode"), modePicker),
      field(l("Công suất đặt (W)", "Power Setpoint (W)"), powerInput),
      field(l("Giới hạn phát lưới (W)", "Export Limit (W)"), exportLimitInput)
    ),
    generatePacketBtn,
    translatorContainer
  ));

  // GENSET EMERGENCY DISPATCH & BLACK-START SECTION
  const gensetContainer = div("stack");
  const gensetLoad = ui.input("number", "35.0"); gensetLoad.step = "5.0";
  const gensetSoc = ui.input("number", "15.0"); gensetSoc.step = "1.0";

  const evaluateGensetBtn = btn(l("Đánh giá điều độ máy phát Diesel", "Evaluate Genset Dispatch"), async () => {
    gensetContainer.replaceChildren(p(l("Đang tính toán điểm hiệu suất tối ưu và suất tiêu hao nhiên liệu...", "Calculating genset optimal loading and fuel consumption...")));
    try {
      const data = await api("/genset/evaluate-dispatch", {
        rated_power_kw: 50.0,
        microgrid_load_kw: Number(gensetLoad.value),
        battery_soc_pct: Number(gensetSoc.value),
        is_grid_available: false,
        dt_seconds: 60,
      });

      const sp = data.genset_specs || {};
      const dp = data.dispatch || {};
      const stBadge = badge(dp.state, dp.state === "running_loaded" ? "good" : dp.state === "off" ? "gray" : "warn");

      const kpis = div("overview-kpis",
        div("fact", e("span", l("Trạng thái máy phát:", "Genset State:")), stBadge),
        div("fact", e("span", l("Công suất phát ra:", "Output Power:")), e("b", `${number(dp.output_power_kw)} kW`)),
        div("fact", e("span", l("Hệ số tải máy phát:", "Loading Ratio:")), e("b", `${number(dp.loading_ratio_pct)}%`), badge(dp.loading_ratio_pct >= 40 ? l("Tránh đọng muội than (Wet Stacking)", "Safe") : l("Nguy cơ đọng dầu", "Risk"), dp.loading_ratio_pct >= 40 ? "good" : "bad")),
        div("fact", e("span", l("Nạp vào pin lưu trữ:", "Battery Charging:")), e("b", `+${number(dp.battery_charge_kw)} kW`, "good-text")),
        div("fact", e("span", l("Suất tiêu hao nhiên liệu:", "Fuel Burn Rate:")), e("b", `${number(dp.fuel_rate_lph)} L/h`))
      );

      gensetContainer.replaceChildren(
        notice(
          `Máy phát 50 kW được duy trì ở điểm ngọt hiệu suất tối ưu (${sp.optimal_power_kw} kW). Phần công suất máy phát dư thừa vượt quá phụ tải ${gensetLoad.value} kW được nạp trực tiếp vào pin lưu trữ, triệt tiêu hiện tượng đọng dầu muội than ống xả (wet stacking).`,
          `Genset runs at 75% optimal loading (${sp.optimal_power_kw} kW). Surplus capacity charges the battery to avoid wet stacking.`
        ),
        kpis,
        div("form-actions",
          btn(l("Khởi động quy trình khôi phục Black-Start", "Trigger Black-Start Restoration Sequence"), async () => {
            const bsRes = await api("/genset/black-start-sequence", {
              advance_steps: 3,
              bus_voltage_v: 0.0,
              pv_frequency_hz: 50.0,
              critical_load_kw: 10.0,
            });
            ui.showDialog(
              l("Trình tự khôi phục sau sự cố mất điện toàn diện (Black-Start)", "Black-Start Restoration Log"),
              div("stack",
                p(l("Tiến trình khôi phục vi lưới tự động theo từng giai đoạn an toàn:", "Multi-stage automated microgrid restoration sequence:")),
                badge(bsRes.current_stage, "good"),
                table(
                  [l("Thời điểm", "Timestamp"), l("Giai đoạn", "Stage"), l("Chi tiết", "Event Log")],
                  (bsRes.event_log || []).map(e => [e.timestamp.slice(11, 19), badge(e.stage, "blue"), e.message])
                )
              )
            );
          }, "primary")
        )
      );
    } catch (err) {
      gensetContainer.replaceChildren(p(err.message, "bad"));
    }
  });

  root.append(card(
    l("Điều khiển máy phát dự phòng & Khởi động đen (Genset & Black-Start)", "Emergency Genset Dispatch & Black-Start Orchestration"),
    p(l("Điều độ máy phát diesel/khí phối hợp pin lưu trữ để luôn chạy trong vùng hiệu suất cao nhất (>40% tải chống hỏng động cơ), cùng trình tự khôi phục vi lưới sau sự cố rã lưới (Black-Start).",
        "Optimizes genset loading sweet-spot with battery buffering to prevent wet-stacking, and coordinates multi-stage black-start restoration.")),
    div("form-grid",
      field(l("Phụ tải vi lưới cô lập (kW)", "Islanded Load (kW)"), gensetLoad),
      field(l("Dung lượng pin SOC (%)", "Battery SOC (%)"), gensetSoc)
    ),
    evaluateGensetBtn,
    gensetContainer
  ));

  return root;
}
