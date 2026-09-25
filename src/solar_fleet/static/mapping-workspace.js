import { l, t, date } from "./i18n.js";

const metricNames = {
  pv_w: ["Công suất mặt trời", "Solar power"],
  load_w: ["Công suất tiêu thụ", "Load power"],
  grid_import_w: ["Công suất mua từ lưới", "Grid import power"],
  grid_export_w: ["Công suất phát lên lưới", "Grid export power"],
  battery_charge_w: ["Công suất sạc pin", "Battery charging power"],
  battery_discharge_w: ["Công suất xả pin", "Battery discharging power"],
  soc_pct: ["Dung lượng pin còn lại", "Battery state of charge"],
  pv_total_wh: ["Tổng điện mặt trời", "Total solar energy"],
  load_total_wh: ["Tổng điện tiêu thụ", "Total load energy"],
  grid_import_total_wh: ["Tổng điện mua từ lưới", "Total grid import energy"],
  grid_export_total_wh: ["Tổng điện phát lên lưới", "Total grid export energy"],
  battery_charge_total_wh: ["Tổng điện sạc pin", "Total battery charge energy"],
  battery_discharge_total_wh: ["Tổng điện xả pin", "Total battery discharge energy"],
  grid_voltage_v: ["Điện áp lưới", "Grid voltage"],
  grid_frequency_hz: ["Tần số lưới", "Grid frequency"],
  battery_voltage_v: ["Điện áp pin", "Battery voltage"],
  inverter_temperature_c: ["Nhiệt độ biến tần", "Inverter temperature"],
  battery_temperature_c: ["Nhiệt độ pin", "Battery temperature"],
};
const messages = {
  DRAFT: ["Bản nháp", "Draft"],
  REVIEWED: ["Đã duyệt bản nháp", "Draft reviewed"],
  CHANGES_REQUESTED: ["Cần chỉnh sửa", "Changes requested"],
  MATCHED: ["Định danh và kết nối còn khớp", "Identity and connection match"],
  mapping_identity_changed: ["Định danh thiết bị đã đổi", "Device identity changed"],
  mapping_binding_not_available: ["Kết nối đã bị thu hồi hoặc tắt", "Connection revoked or disabled"],
  CANDIDATE_ONLY: ["Giá trị thử, chưa nghiệm thu", "Candidate only, not commissioned"],
  source_missing: ["Chưa có trường dữ liệu này", "Source field missing"],
  source_missing_or_unit_mismatch: ["Thiếu giá trị hoặc đơn vị đã đổi", "Value missing or unit changed"],
  source_stale_or_invalid: ["Dữ liệu quá hạn hoặc không hợp lệ", "Source stale or invalid"],
  ambiguous_source: ["Có nhiều mẫu trùng trường và nguồn", "Multiple samples match this source"],
  source_not_finite: ["Giá trị không phải số hữu hạn", "Value is not a finite number"],
  negative_value_requires_direction_evidence: ["Giá trị âm cần đối chiếu chiều đo", "Negative value needs direction evidence"],
  percentage_out_of_range: ["Phần trăm nằm ngoài 0–100", "Percentage outside 0–100"],
};
const label = key => messages[key] ? l(...messages[key]) : key;
const metricLabel = key => metricNames[key] ? l(...metricNames[key]) : key;
const reading = (value, unit) => value == null ? "—" : `${Number(value).toLocaleString(l("vi-VN", "en-US"), {maximumFractionDigits: 6})} ${unit || ""}`;

export async function renderMappingWorkspace(ui, siteId) {
  const { state, e, div, p, btn, card, table, field, input, select, notice,
    form, raw, api, showDialog, closeDialog, refresh } = ui;
  const root = div("stack");
  const data = await api("/data-workspace");
  const devices = state.fleet.devices.filter(d => d.site_id === siteId);
  const rows = data.mappings.filter(row => row.site_id === siteId);
  const principal = state.me.user;
  const canEdit = ["Installer", "Senior Engineer", "Administrator"].includes(principal.role);
  const path = row => "/mappings/" + encodeURIComponent(row.id);
  const deviceName = id => devices.find(d => d.id === id)?.name || id;
  const boundary = () => notice(
    "Bản nháp và kết quả mô phỏng không thay đổi số liệu vận hành. Sau khi duyệt, kỹ sư vẫn cần nghiệm thu đúng model, firmware, đơn vị và chiều đo trước khi đưa vào sử dụng.",
    "Drafts and simulations do not change operational readings. Review still requires commissioning against the exact model, firmware, units and measurement direction before use.",
  );

  async function simulate(row) {
    const result = await api(path(row) + "/simulate", {});
    showDialog(l("Kết quả mô phỏng", "Simulation results"), div("stack",
      p(`${row.name} · ${l("Phiên bản", "Revision")} ${result.revision}`), boundary(),
      table([l("Trường gốc", "Source field"), l("Giá trị gốc", "Source reading"), l("Đo lúc", "Measured at"),
        l("Chỉ số đích", "Target metric"), l("Giá trị thử", "Candidate reading"), t("status")],
      result.results.map(r => [r.mapping.source_key, reading(r.source?.value, r.source?.unit),
        date(r.source?.source_timestamp), metricLabel(r.mapping.metric), reading(r.value, r.unit), label(r.result)])),
      raw(l("Thông tin đối chiếu", "Comparison details"), result),
      btn(t("close"), closeDialog),
    ));
  }

  async function history(row) {
    const versions = await api(path(row) + "/versions");
    showDialog(l("Lịch sử ánh xạ", "Mapping history"), div("stack",
      p(row.name), table([l("Phiên bản", "Revision"), t("status"), l("Người sửa", "Author"),
        l("Thời điểm", "Time"), l("Người duyệt", "Reviewer"), l("Chi tiết", "Details")],
      versions.slice().reverse().map(v => [v.revision, label(v.state), v.author, date(v.updated_at),
        v.review?.reviewer || "—", raw(l("Xem bản đã lưu", "Saved revision"), v)])),
      boundary(), btn(t("close"), closeDialog),
    ));
  }

  function review(row) {
    const outcome = select([["REVIEWED", l("Duyệt bản nháp", "Review draft")],
      ["CHANGES_REQUESTED", l("Yêu cầu sửa", "Request changes")]], "REVIEWED");
    const notes = e("textarea"); notes.required = true; notes.minLength = 10; notes.maxLength = 3000;
    const f = form(async () => {
      await api(path(row) + "/review", {revision: row.revision, outcome: outcome.value, notes: notes.value.trim()});
      closeDialog(); await refresh();
    }, l("Lưu đánh giá", "Save review"));
    f.finish(p(`${row.name} · ${l("Phiên bản", "Revision")} ${row.revision}`), boundary(),
      raw(l("Nội dung cần đối chiếu", "Draft to review"), row),
      field(l("Kết luận", "Outcome"), outcome), field(l("Nhận xét kỹ thuật", "Technical review notes"), notes));
    showDialog(l("Duyệt độc lập", "Independent review"), f);
  }

  async function edit(row = null, selectedId = null) {
    const deviceId = row?.device_id || selectedId || devices[0]?.id;
    if (!deviceId) return;
    const context = await api("/devices/" + encodeURIComponent(deviceId) + "/mapping-context");
    if (!context.can_edit) throw new Error(l("Bạn chỉ có quyền xem ánh xạ.", "You have read-only mapping access."));
    const device = select(devices.map(d => [d.id, d.name]), deviceId);
    device.disabled = Boolean(row);
    const name = input("text", row?.name || ""); name.required = true; name.maxLength = 120;
    const notes = e("textarea"); notes.value = row?.notes || ""; notes.maxLength = 3000;
    const bindingOptions = context.bindings.map(b => [b.id, b.name]);
    if (row && !context.bindings.some(b => b.id === row.binding_id)) {
      bindingOptions.unshift([row.binding_id, `${row.binding_id} · ${label("mapping_binding_not_available")}`]);
    }
    const binding = select([["", l("Chọn kết nối", "Choose connection")], ...bindingOptions], row?.binding_id || context.bindings[0]?.id || "");
    binding.required = true;
    let mappings = row ? structuredClone(row.mappings) : [];
    const evidenceIds = new Set(row?.evidence_ids || []);
    const mappingList = div("stack"), sourceInfo = div("stack"), evidenceList = div("stack");
    const validation = e("p", "", "muted");
    let dirty = false;
    const available = () => context.channels.filter(c => c.binding_id === binding.value);

    function drawEvidence() {
      evidenceList.replaceChildren(...[...evidenceIds].map(id => {
        const source = context.evidence.find(item => item.id === id);
        const link = e("a", source?.title || id);
        if (source?.url?.startsWith("https://")) { link.href = source.url; link.target = "_blank"; link.rel = "noreferrer noopener"; }
        return div("toolbar", link, p(`${id} · ${source?.evidence_grade || "?"}`),
          btn(l("Bỏ nguồn", "Remove evidence"), () => { dirty = true; evidenceIds.delete(id); drawEvidence(); }));
      }));
    }
    const evidence = select([["", l("Chọn tài liệu đối chiếu", "Choose supporting document")],
      ...context.evidence.map(item => [item.id, `${item.title} · ${item.id}`])]);
    const addEvidence = btn(l("Thêm tài liệu", "Add evidence"), () => {
      if (evidence.value && evidenceIds.size < 30) { dirty = true; evidenceIds.add(evidence.value); drawEvidence(); }
    });

    function drawMappings() {
      const channels = available();
      // Distinct selectors retain ambiguous observations for simulation to reject.
      const choices = new Map();
      channels.filter(c => c.selectable).forEach(c => choices.set(`${c.metric}\n${c.unit}`, c));
      sourceInfo.replaceChildren(p(l("Dữ liệu đã thu thập từ kết nối đang chọn", "Observed data from the selected connection")),
        table([l("Tên trường", "Field"), l("Giá trị", "Reading"), l("Đo lúc", "Measured at"), l("Chất lượng", "Quality")],
          channels.map(c => [c.label, reading(c.value, c.unit), date(c.source_timestamp),
            c.stale ? label("source_stale_or_invalid") : c.quality])));
      mappingList.replaceChildren();
      mappings.forEach((mapping, index) => {
        const currentKey = mapping.source_key ? `${mapping.source_key}\n${mapping.source_unit}` : "";
        const options = [["", l("Chọn trường gốc", "Choose source field")],
          ...[...choices].map(([key, c]) => [key, `${c.label} (${c.unit}) · ${c.metric}`])];
        if (currentKey && !choices.has(currentKey)) options.push([currentKey,
          `${mapping.source_key} (${mapping.source_unit}) · ${l("chưa thấy trong dữ liệu mới", "absent from latest data")}`]);
        const source = select(options, currentKey); source.required = true;
        const dimension = context.unit_dimensions[mapping.source_unit];
        const target = select([["", l("Chọn chỉ số đích", "Choose target metric")],
          ...Object.entries(context.metrics).filter(([, unit]) => unit === dimension)
            .map(([key, unit]) => [key, `${metricLabel(key)} (${unit})`])], mapping.metric);
        target.required = true;
        const directions = [["nonnegative", l("Số không âm", "Nonnegative value")]];
        if (dimension === "W") directions.push(
          ["positive", l("Phần dương: max(0, giá trị)", "Positive part: max(0, value)")],
          ["negative", l("Đổi phần âm: max(0, −giá trị)", "Negative part: max(0, −value)")]);
        if (dimension === "°C") directions.push(["signed", l("Giữ cả âm và dương", "Keep signed value")]);
        const direction = select(directions, mapping.direction);
        source.onchange = () => {
          dirty = true;
          const channel = choices.get(source.value);
          mapping.source_key = channel?.metric || ""; mapping.source_unit = channel?.unit || "";
          mapping.metric = ""; mapping.direction = "nonnegative"; drawMappings();
        };
        target.onchange = () => { dirty = true; mapping.metric = target.value; };
        direction.onchange = () => { dirty = true; mapping.direction = direction.value; };
        mappingList.append(card(`${l("Ánh xạ", "Mapping")} ${index + 1}`,
          div("form-grid", field(l("Trường gốc", "Source field"), source),
            field(l("Chỉ số đích", "Target metric"), target), field(l("Chiều đo", "Measurement direction"), direction)),
          btn(l("Xóa dòng", "Remove row"), () => { dirty = true; mappings.splice(index, 1); drawMappings(); })));
      });
      validation.textContent = channels.length ? l("Chỉ chọn chỉ số cùng đơn vị đo. Chiều sạc/xả và nhập/xuất phải được đối chiếu tài liệu.",
        "Only compatible measurement units can be mapped. Confirm charge/discharge and import/export direction against documentation.") :
        l("Chưa có dữ liệu tại kết nối này. Đồng bộ thiết bị hoặc chọn kết nối khác trước khi thêm ánh xạ.",
          "No readings for this connection. Synchronize the device or choose another connection before adding mappings.");
    }

    binding.onchange = () => { dirty = true; drawMappings(); };
    // Changing a new draft's device explicitly discards it; never reuse another device's sources.
    device.onchange = () => {
      const nextId = device.value;
      if (!dirty && !name.value && !notes.value && !mappings.length) {
        edit(null, nextId).catch(err => { device.value = deviceId; validation.textContent = err.message; });
        return;
      }
      device.value = deviceId;
      showDialog(l("Đổi thiết bị", "Change device"),
        p(l("Bản nháp chưa lưu sẽ bị bỏ khi đổi thiết bị.", "Changing device discards this unsaved draft.")),
        btn(l("Giữ bản nháp", "Keep draft"), () => showDialog(l("Tạo ánh xạ", "Create mapping"), f)),
        btn(l("Đổi thiết bị", "Change device"), () => edit(null, nextId), "primary"));
    };
    const f = form(async () => {
      const title = name.value.trim();
      if (!title || !mappings.length || mappings.some(m => !m.source_key || !m.metric))
        throw new Error(l("Điền tên và ít nhất một ánh xạ đầy đủ.", "Enter a name and at least one complete mapping."));
      if (new Set(mappings.map(m => m.metric)).size !== mappings.length)
        throw new Error(l("Mỗi chỉ số đích chỉ được ánh xạ một lần.", "Each target metric can only be mapped once."));
      if (!context.bindings.some(b => b.id === binding.value))
        throw new Error(l("Chọn kết nối còn hoạt động.", "Choose an active connection."));
      await api(row ? path(row) : "/mappings", {device_id: deviceId, name: title,
        binding_id: binding.value, mappings, evidence_ids: [...evidenceIds], notes: notes.value.trim(), revision: row?.revision || 0});
      closeDialog(); await refresh();
    }, l("Lưu bản nháp", "Save draft"));
    f.finish(boundary(), div("form-grid", field(t("devices"), device), field(l("Tên ánh xạ", "Mapping name"), name),
      field(l("Kết nối dữ liệu", "Data connection"), binding)),
      raw(l("Định danh dùng để đối chiếu", "Identity for validation"), context.identity),
      sourceInfo, validation, mappingList, btn(l("Thêm ánh xạ", "Add mapping row"), () => {
        if (mappings.length < 100) { dirty = true; mappings.push({source_key: "", source_unit: "", metric: "", direction: "nonnegative"}); drawMappings(); }
      }),
      field(l("Tài liệu đối chiếu", "Supporting document"), evidence), addEvidence, evidenceList,
      field(l("Ghi chú đơn vị và chiều đo", "Unit and direction notes"), notes));
    drawMappings(); drawEvidence();
    showDialog(row ? l("Chỉnh sửa ánh xạ", "Edit mapping") : l("Tạo ánh xạ", "Create mapping"), f);
  }

  root.append(boundary());
  const actions = div("toolbar");
  if (canEdit && devices.length) actions.append(btn(l("Tạo ánh xạ", "Create mapping"), () => edit(), "primary"));
  actions.append(btn(l("Tải lại ánh xạ", "Reload mappings"), refresh));
  root.append(card(l("Ánh xạ dữ liệu thiết bị", "Device data mappings"), actions,
    rows.length ? table([t("name"), t("devices"), l("Phiên bản", "Revision"), t("status"),
      l("Khả năng áp dụng", "Applicability"), l("Thao tác", "Actions")], rows.map(row => {
      const buttons = div("toolbar");
      if (canEdit) buttons.append(btn(l("Chỉnh sửa", "Edit"), () => edit(row)));
      buttons.append(btn(l("Mô phỏng", "Simulate"), () => simulate(row)), btn(l("Lịch sử", "History"), () => history(row)));
      if (principal.role === "Senior Engineer" && principal.id !== row.author && row.state === "DRAFT" && row.applicability === "MATCHED")
        buttons.append(btn(l("Duyệt độc lập", "Independent review"), () => review(row)));
      return [row.name, deviceName(row.device_id), row.revision, label(row.state), label(row.applicability), buttons];
    })) : p(l("Chưa có bản nháp. Chọn thiết bị và trường dữ liệu đã thu thập để bắt đầu.",
      "No drafts yet. Start with a device and its observed data fields."))));
  return root;
}
