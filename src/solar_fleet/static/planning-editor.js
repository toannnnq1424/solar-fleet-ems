import { l } from "./i18n.js";
import { hourlyPriceEditor } from './hourly-price-editor.js';

// Advisory inputs only: this editor never creates commands or commissioning records.
export function planningEditor(ui, siteId, snapshot) {
  const {state, div, p, input, select, field, e, api, card} = ui;
  const root = div("stack planning-editor");
  const devices = div('form-grid');
  const choices = [["", l("Chưa cấu hình", "Not configured")],
    ...state.fleet.devices.filter(d => d.site_id === siteId).map(d => [
      d.id,
      `${d.name || d.vendor_id || l("Thiết bị", "Device")} · ${d.brand || d.identity?.vendor || "Solar"} (${d.serial || d.vendor_id || d.id.slice(0, 8)})`
    ])];
  const cfg = snapshot.configuration;
  // Retain missing references visibly; never silently replace a removed device.
  for (const id of [cfg.billing_meter_device_id, cfg.dispatch_device_id]) {
    if (id && !choices.some(([value]) => value === id)) choices.push([id, id + " (unavailable)"]);
  }
  const meter = select(choices, cfg.billing_meter_device_id || "");
  const device = select(choices, cfg.dispatch_device_id || "");
  devices.append(field(l("Thiết bị ranh giới đo", "Measurement boundary device"), meter),
    field(l("Thiết bị lập kế hoạch tư vấn", "Advisory planning device"), device));
  root.append(card(l('Thiết bị dùng để tính toán','Equipment for calculations'),devices));
  root.append(p(l('Chọn “Chưa cấu hình” cho thiết bị tư vấn để xóa cấu hình pin và giá khi lưu; không thay đổi quyền điều khiển.',
    'Select “Not configured” for the advisory device to clear battery and price settings when saving; control permissions are unchanged.')));
  const battery = div('form-grid planning-battery-fields');
  const parameters = [
    ["capacity_kwh", "Dung lượng (kWh)", "Capacity (kWh)"],
    ["usable_kwh", "Dung lượng khả dụng (kWh)", "Usable capacity (kWh)"],
    ["max_charge_kw", "Công suất sạc tối đa (kW)", "Maximum charge (kW)"],
    ["max_discharge_kw", "Công suất xả tối đa (kW)", "Maximum discharge (kW)"],
    ["charge_efficiency", "Hiệu suất sạc (%)", "Charge efficiency (%)"],
    ["discharge_efficiency", "Hiệu suất xả (%)", "Discharge efficiency (%)"],
    ["min_soc_pct", "Mức pin tối thiểu (%)", "Minimum battery level (%)"],
    ["max_soc_pct", "Mức pin tối đa (%)", "Maximum battery level (%)"],
    ["reserve_soc_pct", "Mức pin dự phòng (%)", "Reserve battery level (%)"],
    ["replacement_cost_usd", "Chi phí thay thế (USD)", "Replacement cost (USD)"],
    ["rated_cycle_life", "Số chu kỳ định mức", "Rated cycle life"],
  ];
  const controls = new Map();
  for (const [key, vi, en] of parameters) {
    const value=cfg.dispatch_config?.[key];
    const efficiency=key.endsWith('_efficiency');
    const control = input("number", value==null ? '' : efficiency ? value*100 : value);
    control.step = key === "rated_cycle_life" ? "1" : "any";
    if (efficiency) {control.min='0.01';control.max='100';}
    controls.set(key, control);
    battery.append(field(l(vi, en), control));
  }
  const batteryCard=card(l('Thông số pin lưu trữ','Battery specifications'),
    p(l('Dùng thông số trên hồ sơ pin. Mức pin là phần trăm năng lượng còn lại; các giá trị này chỉ dùng tính toán, không gửi xuống thiết bị.',
      'Use the battery specifications. Battery level is the remaining energy percentage; these inputs are for calculations, not device commands.'),'field-help'),battery);
  const source = input("text", cfg.dispatch_config?.tariff_source || "");
  const prices = hourlyPriceEditor(ui, cfg.dispatch_config?.hourly_prices || []);
  root.append(div('planning-sections',batteryCard,card(l('Giá điện dùng cho kế hoạch','Planning electricity prices'),
    field(l("Nguồn biểu giá USD", "USD tariff source"), source),prices.element)));
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
        if (!source.value.trim()) throw new Error(l('Nhập nguồn biểu giá để có thể đối chiếu.', 'Enter the tariff source for verification.'));
        dispatch = {currency: "USD", tariff_source: source.value.trim(), hourly_prices: prices.read()};
        for (const [key, control] of controls) {
          if (!control.value.trim() || !Number.isFinite(Number(control.value))) {
            throw new Error(l("Điền đầy đủ tham số pin hợp lệ.", "Complete all battery parameters with valid numbers."));
          }
          if (key.endsWith('_efficiency') && (Number(control.value)<=0 || Number(control.value)>100)) {
            throw new Error(l('Hiệu suất phải lớn hơn 0% và không quá 100%.','Efficiency must be above 0% and at most 100%.'));
          }
          dispatch[key] = Number(control.value) / (key.endsWith('_efficiency') ? 100 : 1);
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
