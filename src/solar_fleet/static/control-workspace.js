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
  return root;
}
