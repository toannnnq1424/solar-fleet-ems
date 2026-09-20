import { l, t, date, number, language } from "./i18n.js";

export function createSchedulePlanner(ui) {
  const { state, e, div, p, btn, badge, card, input, select, field, fact,
    notice, table, form, api, operator, go } = ui;
  const reason = (key) => ({
    adapter_schedule_contract_missing: l("Chưa có bộ dịch lịch cho model/adapter này.", "No schedule translator for this model/adapter."),
    schedule_has_uncovered_intervals: l("Lịch tuần còn khoảng giờ chưa cấu hình.", "The weekly schedule has uncovered intervals."),
    schedule_mapping_not_exact: l("Cách áp dụng chưa tương đương hoàn toàn hoặc chưa xác định giờ thiết bị.", "Mapping is not exact or the equipment clock is unknown."),
    capability_or_parameter_unverified: l("Chưa có nghiệm thu năng lực hoặc tham số thiết bị.", "Equipment capability or parameters are not commissioned."),
    device_offline_or_stale: l("Thiết bị ngoại tuyến hoặc dữ liệu đã cũ.", "Equipment is offline or readings are stale."),
    fresh_preview_required: l("Tương thích theo hồ sơ; cần đọc cấu hình trước khi triển khai.", "Profile is compatible; a fresh configuration preview is required."),
    schedule_mapping_evidence_missing: l("Thiếu nguồn xác minh cách ánh xạ lịch.", "Schedule mapping evidence is missing."),
  })[key] || key;
  const minutes = (value) => `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;

  async function view() {
    const schedules = (state.ops.schedule || []).filter((s) => !state.site || s.site_id === state.site),
      schedule = select(schedules.map((s) => [s.id, s.name])),
      start = input("date", new Date().toISOString().slice(0, 10), true), days = input("number", 7, true),
      gap = select([["reject", l("Yêu cầu phủ đủ tuần", "Require a complete week")], ["preserve_device_schedule", l("Giữ cấu hình cũ ở khoảng trống", "Preserve equipment settings in gaps")]]),
      dst = select([["reject", l("Dừng nếu có chuyển giờ DST", "Block DST transitions")], ["earlier", l("Chọn lần sớm khi trùng giờ", "Use earlier repeated time")], ["later", l("Chọn lần muộn khi trùng giờ", "Use later repeated time")]]),
      targets = div("stack"), output = div("stack"), saved = div("stack");
    days.min = 1; days.max = 14;
    let checkboxes = [];
    const drawTargets = () => {
      const source = schedules.find((s) => s.id === schedule.value);
      checkboxes = state.fleet.devices.filter((d) => d.site_id === source?.site_id && d.type === "INVERTER").map((device) => {
        const check = input("checkbox"); check.checked = false;
        return {device, check};
      });
      targets.replaceChildren(...checkboxes.map(({device, check}) => field(`${device.name || device.vendor_id} · ${device.identity.vendor} · ${device.identity.model || "—"}`, check)));
      if (!checkboxes.length) targets.append(p(l("Nhà máy chưa có inverter để kiểm tra lịch.", "This plant has no inverter available for schedule assessment.")));
    };
    const show = (plan) => {
      output.replaceChildren(card(l("Kết quả biên dịch", "Compilation result"),
        div("row", badge(plan.state, plan.state === "COMPATIBLE" ? "good" : "warn"), p(plan.schedule_name)),
        fact(l("Múi giờ nhà máy", "Plant timezone"), plan.timeline.timezone),
        fact(l("Phiên bản lịch", "Schedule revision"), plan.source_revision),
        fact(l("Kế hoạch hết hạn", "Plan expires"), date(plan.expires_at)),
        notice("Đây là cài lịch tuần lên thiết bị. Khoảng ngày bên dưới chỉ để xem trước, không phải ngày tự dừng lịch.", "This installs a weekly equipment schedule. Dates below are a preview window, not an automatic schedule end date."),
        table([t("devices"), l("Nền tảng", "Platform"), l("Tương thích", "Compatibility"), l("Giải thích", "Explanation")], plan.targets.map((target) => [
          target.device_name, target.platform, badge(target.semantics), div("stack", p(reason(target.reason)),
            target.translation ? p(language === "vi" ? target.translation.reason_vi : target.translation.reason_en) : null)])),
        operator() && plan.state === "COMPATIBLE" ? btn(l("Chuẩn bị triển khai hàng loạt", "Prepare fleet rollout"), async () => {
          await api(`/schedule-compilations/${plan.id}/rollout`, {digest: plan.digest});
          await ui.refresh(); await go("operations", "", "rollouts");
        }, "primary") : null),
      card(l("Dòng thời gian dự kiến", "Projected timeline"), table([
        l("Bắt đầu theo giờ nhà máy", "Plant-local start"), l("Kết thúc", "End"), l("Chế độ", "Mode"), "SOC (%)", "kW", l("Thời lượng thực", "Elapsed duration")],
        plan.timeline.windows.map((slot) => [slot.start_local, slot.end_local,
          ({self_use:l("Tự dùng", "Self-use"), charge:l("Sạc", "Charge"), discharge:l("Xả", "Discharge"), hold:l("Giữ", "Hold")})[slot.mode],
          slot.target_soc_pct ?? "—", slot.power_w == null ? "—" : number(slot.power_w / 1000),
          `${number(slot.duration_seconds / 3600, 2)} h${slot.dst_adjusted ? " · DST" : ""}`]))),
      card(l("Khoảng trống trong tuần", "Weekly gaps"), plan.weekly_gaps.length ?
        table([l("Ngày", "Day"), l("Từ", "From"), l("Đến", "Until")], plan.weekly_gaps.map((item) => [item.date, minutes(item.start_minute), minutes(item.end_minute)])) :
        p(l("Lịch đã phủ đủ 7 ngày.", "All seven days are covered."))));
    };
    const loadSaved = async () => {
      const plans = await api("/schedule-compilations?" + new URLSearchParams(state.site ? {site_id: state.site} : {}));
      saved.replaceChildren(table([l("Lịch", "Schedule"), l("Tạo lúc", "Created"), t("status"), l("Thiết bị", "Targets"), ""],
        plans.map((plan) => [plan.schedule_name, date(plan.created_at), badge(plan.state), plan.targets.length,
          btn(l("Xem kết quả", "View compilation"), () => show(plan))])));
    };
    const f = form(async () => {
      const ids = checkboxes.filter((item) => item.check.checked).map((item) => item.device.id);
      if (!ids.length) throw new Error(l("Chọn ít nhất một thiết bị.", "Select at least one device."));
      const plan = await api(`/schedules/${schedule.value}/compile`, {device_ids: ids, start_date: start.value,
        days: Number(days.value), gap_policy: gap.value, dst_policy: dst.value});
      show(plan); await loadSaved();
    }, l("Kiểm tra & biên dịch", "Check & compile"));
    f.finish(field(l("Chọn lịch tuần", "Weekly schedule"), schedule),
      div("form-grid", field(l("Ngày bắt đầu xem trước", "Preview start date"), start), field(l("Số ngày xem trước", "Preview days"), days),
        field(l("Khoảng trống", "Gap policy"), gap), field(l("Chuyển giờ mùa hè", "DST policy"), dst)),
      card(l("Chọn thiết bị triển khai", "Select equipment"), targets));
    schedule.onchange = drawTargets; drawTargets();
    if (!operator() || !schedules.length) f.querySelector('button[type="submit"]').disabled = true;
    await loadSaved();
    return div("stack", notice("Bản biên dịch không gửi lệnh. Bước triển khai dùng cùng kiểm tra quyền, đọc cấu hình, xác nhận canary và readback của bộ điều khiển.",
      "Compilation sends no commands. Rollout uses the controller's permissions, configuration preview, canary confirmation and readback."),
      card(l("Biên dịch lịch đa hãng", "Multi-vendor schedule compiler"), !schedules.length ?
        btn(l("Tạo lịch tuần trước", "Create a weekly schedule"), () => go("operations", "schedules", "main")) : null, f), output,
      card(l("Các lần biên dịch gần đây", "Recent compilations"), saved));
  }
  return {view};
}
