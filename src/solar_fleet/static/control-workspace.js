import { advisoryCalculator } from "./advisory-calculator.js";
import { l, t, number } from "./i18n.js";

// All actual commands use the shared capability form, preview and confirmation engine.
export async function renderControlMainWorkspace(ui) {
  const { state, div, p, e, btn, card, table, select, field, badge, notice, api, go, controlForm, operator } = ui;
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

  const powerInput = ui.input("number", ""); powerInput.step = "500";
  const exportLimitInput = ui.input("number", ""); exportLimitInput.step = "500";

  const generatePacketBtn = btn(l("Biên dịch gói lệnh Modbus FC06/FC16", "Compile Modbus FC06/FC16 Packet"), async () => {
    translatorContainer.replaceChildren(p(l("Đang biên dịch thanh ghi Modbus chuẩn theo hãng...", "Translating into vendor Modbus write registers...")));
    try {
      const res = await api("/vendor-translator/translate-command", {
        vendor: brandPicker.value,
        slave_id: 1,
        work_mode: modePicker.value,
        power_w: powerInput.value.trim() ? Number(powerInput.value) : null,
        export_limit_w: exportLimitInput.value.trim() ? Number(exportLimitInput.value) : null,
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
        p(l("Pa-két tham khảo, chưa gửi tới thiết bị. Điều khiển thật cần tính năng đã xác minh và bước xem trước ở trên.",
          "Reference packets only; not sent. Actual control requires a verified capability and the preview workflow above."))
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

  const generatorFields = "specs {rated_power_kw, min_loading_ratio, optimal_loading_ratio, max_loading_ratio, fuel_idle_liters_per_hour, fuel_slope_liters_per_kwh, crank_time_seconds, warmup_time_seconds, cooldown_time_seconds, min_run_time_seconds, auto_start_soc_threshold, auto_stop_soc_threshold}; ";
  root.append(advisoryCalculator(ui, "Genset dispatch estimate", "/genset/evaluate-dispatch",
    generatorFields + "initial_state, elapsed_in_state_seconds, cumulative_run_seconds, microgrid_load_kw, battery_soc_pct, is_grid_available, battery_max_charge_kw, battery_max_discharge_kw, dt_seconds"));
  root.append(advisoryCalculator(ui, "Black-start scenario", "/genset/black-start-sequence",
    generatorFields + "observations [{bus_voltage_v, pv_frequency_hz, critical_load_kw}]. Scenario only; hardware acknowledgements are not verified."));

  return root;
}
