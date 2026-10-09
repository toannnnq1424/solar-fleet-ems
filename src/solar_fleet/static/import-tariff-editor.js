import { l, number, date } from "./i18n.js";
import { vietnamToUTC } from './hourly-price-editor.js';

export function importTariffEditor(ui, siteId, snapshot) {
  const {div, p, input, field, e, api, table} = ui;
  const root = div("stack");
  root.append(p(l("Chọn thời gian theo giờ Việt Nam (UTC+7) và giá từ hợp đồng của bạn. Giá khai báo chưa gồm thuế/phí, không phải giá EVN đã xác minh. Mỗi lần lưu thêm một giai đoạn không chồng lấn; chưa hỗ trợ sửa/xóa.",
    "Choose Vietnam time (UTC+7) and the rate in your contract. Declared rates exclude taxes/fees and are not verified EVN tariffs. Each save adds a non-overlapping period; editing/deletion is not supported."),'field-help'));
  const start = input("datetime-local", ""), end = input("datetime-local", ""), rate = input("number", ""), source = input("text", "");
  rate.step = "any";
  root.append(div('form-grid',field(l("Bắt đầu hiệu lực (giờ Việt Nam)", "Effective start (Vietnam time)"), start),
    field(l("Kết thúc hiệu lực (giờ Việt Nam)", "Effective end (Vietnam time)"), end),
    field(l("Giá nhập (VND/kWh)", "Import rate (VND/kWh)"), rate),
    field(l("Nguồn giá nhập", "Import rate source"), source)));
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
        effective_start: vietnamToUTC(start.value), effective_end: vietnamToUTC(end.value), import_vnd_per_kwh: Number(rate.value),
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
