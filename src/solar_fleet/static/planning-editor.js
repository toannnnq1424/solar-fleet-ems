import { l } from "./i18n.js";

// Advisory inputs only: this editor never creates commands or commissioning records.
export function planningEditor(ui, siteId, snapshot) {
  const {state, div, p, input, select, field, e, api} = ui;
  const root = div("stack");
  const choices = [["", l("Chưa cấu hình", "Not configured")],
    ...state.fleet.devices.filter(d => d.site_id === siteId).map(d => [d.id, d.name || d.vendor_id || d.id])];
  const cfg = snapshot.configuration;
  // Retain missing references visibly; never silently replace a removed device.
  for (const id of [cfg.billing_meter_device_id, cfg.dispatch_device_id]) {
    if (id && !choices.some(([value]) => value === id)) choices.push([id, id + " (unavailable)"]);
  }
  const meter = select(choices, cfg.billing_meter_device_id || "");
  const device = select(choices, cfg.dispatch_device_id || "");
  root.append(field(l("Thiết bị ranh giới đo", "Measurement boundary device"), meter),
    field(l("Thiết bị lập kế hoạch tư vấn", "Advisory planning device"), device));
  const parameters = [
    ["capacity_kwh", "Dung lượng (kWh)", "Capacity (kWh)"],
    ["usable_kwh", "Dung lượng khả dụng (kWh)", "Usable capacity (kWh)"],
    ["max_charge_kw", "Công suất sạc tối đa (kW)", "Maximum charge (kW)"],
    ["max_discharge_kw", "Công suất xả tối đa (kW)", "Maximum discharge (kW)"],
    ["charge_efficiency", "Hiệu suất sạc (0–1)", "Charge efficiency (0–1)"],
    ["discharge_efficiency", "Hiệu suất xả (0–1)", "Discharge efficiency (0–1)"],
    ["min_soc_pct", "SOC tối thiểu (%)", "Minimum SOC (%)"],
    ["max_soc_pct", "SOC tối đa (%)", "Maximum SOC (%)"],
    ["reserve_soc_pct", "SOC dự phòng (%)", "Reserve SOC (%)"],
    ["replacement_cost_usd", "Chi phí thay thế (USD)", "Replacement cost (USD)"],
    ["rated_cycle_life", "Số chu kỳ định mức", "Rated cycle life"],
  ];
  const controls = new Map();
  for (const [key, vi, en] of parameters) {
    const control = input("number", cfg.dispatch_config?.[key] ?? "");
    control.step = key === "rated_cycle_life" ? "1" : "any";
    controls.set(key, control);
    root.append(field(l(vi, en), control));
  }
  const source = input("text", cfg.dispatch_config?.tariff_source || "");
  const prices = document.createElement("textarea");
  prices.rows = 8;
  prices.value = JSON.stringify(cfg.dispatch_config?.hourly_prices || [], null, 2);
  root.append(field(l("Nguồn biểu giá USD", "USD tariff source"), source),
    p(l("24 giờ UTC liên tiếp; mỗi dòng JSON có timestamp, import_per_kwh, export_per_kwh. Không phải hóa đơn điện.",
      "24 consecutive UTC hours; JSON entries require timestamp, import_per_kwh, export_per_kwh. Not an electricity bill.")),
    field(l("Giá từng giờ (JSON)", "Hourly prices (JSON)"), prices));
  const status = div("stack");
  status.setAttribute("role", "status");
  let revision = snapshot.revision;
  let conflict = false;
  const save = e("button", l("Lưu cấu hình tư vấn", "Save advisory configuration"));
  save.type = "button";
  save.onclick = async () => {
    if (conflict || save.disabled) return;
    save.disabled = true;
    try {
      let dispatch = null;
      if (device.value) {
        dispatch = {currency: "USD", tariff_source: source.value.trim(), hourly_prices: JSON.parse(prices.value)};
        for (const [key, control] of controls) {
          if (!control.value.trim() || !Number.isFinite(Number(control.value))) {
            throw new Error(l("Điền đầy đủ tham số pin hợp lệ.", "Complete all battery parameters with valid numbers."));
          }
          dispatch[key] = Number(control.value);
        }
      }
      const result = await api("/sites/" + encodeURIComponent(siteId) + "/planning-configuration", {
        expected_revision: revision, billing_meter_device_id: meter.value || null,
        dispatch_device_id: device.value || null, dispatch_config: dispatch,
      });
      revision = result.revision;
      status.replaceChildren(p(l("Đã lưu cấu hình tư vấn; không gửi lệnh.", "Advisory configuration saved; no commands sent.")));
    } catch (error) {
      conflict = error.message.includes("planning_configuration_changed_reload_required");
      status.replaceChildren(p(conflict ? l("Cấu hình đã thay đổi. Tải lại trang để xem bản mới; bản nhập chưa bị xóa.",
        "Configuration changed. Reload the page to review the latest version; your inputs have been retained.") : error.message, "bad"));
    } finally { save.disabled = conflict; }
  };
  root.append(save, status);
  return root;
}