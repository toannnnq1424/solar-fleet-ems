import { l, number, date } from "./i18n.js";

export function importTariffEditor(ui, siteId, snapshot) {
  const {div, p, input, field, e, api, table} = ui;
  const root = div("stack");
  root.append(p(l("Giá khai báo VND, không phải giá EVN đã xác minh. Phiên bản chỉ thêm, không chồng lấn; chưa hỗ trợ sửa/xóa. Thời gian ISO có múi giờ, ví dụ +00:00. Không gồm thuế/phí.",
    "Declared VND rates, not verified EVN tariffs. Append-only, non-overlapping versions; editing/deletion not supported. Use ISO timestamps with timezone, e.g. +00:00. Taxes/fees excluded.")));
  const start = input("text", ""), end = input("text", ""), rate = input("number", ""), source = input("text", "");
  rate.step = "any";
  root.append(field(l("Bắt đầu hiệu lực (ISO)", "Effective start (ISO)"), start),
    field(l("Kết thúc hiệu lực (ISO)", "Effective end (ISO)"), end),
    field(l("Giá nhập (VND/kWh)", "Import rate (VND/kWh)"), rate),
    field(l("Nguồn giá nhập", "Import rate source"), source));
  const history = div("stack"), status = p("");
  status.setAttribute("role", "log");
  status.setAttribute("aria-label", "Import tariff status");
  const draw = versions => history.replaceChildren(table([
    l("Bắt đầu", "Start"), l("Kết thúc", "End"), "VND/kWh", l("Nguồn", "Source"), l("Phiên bản", "Version")
  ], versions.map(v => [date(v.effective_start), date(v.effective_end), number(v.import_vnd_per_kwh), v.source, v.id])));
  draw(snapshot.versions);
  let revision = snapshot.revision, conflict = false;
  const save = e("button", l("Thêm phiên bản giá nhập", "Add import rate version"));
  save.type = "button";
  save.onclick = async () => {
    if (save.disabled || conflict) return;
    save.disabled = true;
    try {
      if (!rate.value.trim() || !Number.isFinite(Number(rate.value))) throw new Error(l("Cần giá hợp lệ.", "A valid rate is required."));
      const result = await api(`/sites/${encodeURIComponent(siteId)}/import-tariffs`, {
        effective_start: start.value, effective_end: end.value, import_vnd_per_kwh: Number(rate.value),
        source: source.value, currency: "VND", expected_revision: revision,
      });
      revision = result.revision;
      draw(result.versions);
      status.textContent = l("Đã lưu giá khai báo; không tạo hóa đơn hoặc lệnh.", "Declared rate saved; no invoice or command created.");
    } catch (err) {
      conflict = err.status === 409;
      status.textContent = conflict ? l("Cấu hình đã đổi. Giữ bản nhập; tải lại trước khi lưu.", "Configuration changed. Inputs preserved; reload before saving.") : err.message;
    } finally { save.disabled = conflict; }
  };
  root.append(save, status, history);
  return root;
}