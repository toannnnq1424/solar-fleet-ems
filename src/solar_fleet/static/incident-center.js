import { l, t, date, number, language } from "./i18n.js";

export function createIncidentCenter(ui) {
  const { state, e, div, p, btn, badge, card, input, select, field, fact,
    notice, table, tabs, form, api, showDialog, closeDialog, operator,
    siteName, siteSelect, deviceDetail, go } = ui;
  const levels = () => [["critical", l("Nguy cấp", "Critical")], ["high", l("Cao", "High")],
    ["medium", l("Trung bình", "Medium")], ["low", l("Thấp", "Low")]];
  const statuses = () => [["open", l("Chưa tiếp nhận", "Open")], ["acknowledged", l("Đã tiếp nhận", "Acknowledged")],
    ["in_progress", l("Đang xử lý", "In progress")], ["resolved", l("Đã giải quyết", "Resolved")], ["closed", l("Đã đóng", "Closed")]];
  const categories = () => [["connectivity", l("Kết nối", "Connectivity")], ["inverter", l("Biến tần", "Inverter")],
    ["battery", l("Pin / BMS", "Battery / BMS")], ["meter", l("Đo lường", "Meter")],
    ["grid", l("Lưới điện", "Grid")], ["yield", l("Sản lượng", "Yield")], ["other", l("Khác", "Other")]];
  const textArea = (value = "", required = true, maxLength = 2000) => {
    const node = e("textarea"); node.value = value; node.rows = 3; node.required = required; node.maxLength = maxLength; return node;
  };
  const levelLabel = (value) => levels().find(([key]) => key === value)?.[1] || value;
  const stateLabel = (value) => statuses().find(([key]) => key === value)?.[1] || value;
  const scope = () => new URLSearchParams(state.site ? { site_id: state.site } : {});
  const technical = () => ["Administrator", "Installer", "Senior Engineer"].includes(state.me.user.role);
  const duration = (seconds) => seconds == null ? "—" : number(seconds / 60, 0) + l(" phút", " min");

  async function center() {
    let offset = 0, selected = state.tab || "", current = null, activeTab = "overview";
    const search = input("search"), severity = select([["", t("all")], ...levels()]),
      status = select([["", t("all")], ...statuses()]),
      assignment = select([["", l("Mọi phân công", "All assignments")], ["unassigned", l("Chưa phân công", "Unassigned")], ["mine", l("Của tôi", "Assigned to me")]]),
      sla = select([["", l("Mọi SLA", "All SLAs")], ["breached", l("Đã quá hạn", "Breached")]]),
      list = div("record-list"), detail = div("stack"), actions = div("stack"),
      metrics = div("grid four"), analytics = div("grid three"), pager = div("toolbar");
    search.placeholder = l("Tên cảnh báo, mã lỗi, thiết bị…", "Alert, error code, device…");
    search.maxLength = 200;
    async function reload() {
      const query = scope(); query.set("offset", offset); query.set("limit", 20);
      if (search.value.trim()) query.set("q", search.value.trim());
      if (severity.value) query.set("severity", severity.value);
      if (status.value) query.set("status", status.value);
      if (assignment.value === "mine") query.set("assigned_to", state.me.user.id);
      if (assignment.value === "unassigned") query.set("unassigned", "true");
      if (sla.value) query.set("only_breached", "true");
      const [page, summary] = await Promise.all([api("/incidents?" + query), api("/incidents/summary?" + scope())]);
      metrics.replaceChildren(...[[l("Cảnh báo đang mở", "Open alerts"), summary.open], [l("Nguy cấp", "Critical"), summary.critical],
        [l("Đang xử lý", "In progress"), summary.in_progress], [l("Giải quyết hôm nay", "Resolved today"), summary.resolved_today]]
        .map(([label, value]) => card(label, e("strong", number(value, 0), "metric-value"))));
      list.replaceChildren(...page.items.map((row) => {
        const button = btn("", async () => { selected = row.id; activeTab = "overview"; await open(row.id); }, "record-button" + (row.id === selected ? " selected" : ""));
        button.append(div("row", badge(levelLabel(row.severity), row.severity === "critical" ? "bad" : "warn"), e("strong", row.title)),
          p(siteName(row.site_id)), div("row", badge(stateLabel(row.status)), e("small", date(row.updated_at))),
          p(row.description.slice(0, 130)));
        button.setAttribute("aria-pressed", String(row.id === selected));
        button.dataset.recordId = row.id;
        return button;
      }));
      if (!page.items.length) list.append(p(l("Không có cảnh báo phù hợp bộ lọc.", "No alerts match these filters.")));
      pager.replaceChildren(btn(l("Trước", "Previous"), async () => { offset = Math.max(0, offset - 20); await reload(); }),
        p(`${page.total ? offset + 1 : 0}–${Math.min(offset + 20, page.total)} / ${page.total}`),
        btn(l("Sau", "Next"), async () => { if (offset + 20 < page.total) { offset += 20; await reload(); } }));
      pager.firstElementChild.disabled = offset === 0;
      pager.lastElementChild.disabled = offset + 20 >= page.total;
      analytics.replaceChildren(card(l("Thời gian xử lý • 7 ngày", "Response times • 7 days"),
        fact(l("Phản hồi trung bình", "Mean response"), duration(summary.mean_response_seconds)),
        fact(l("Giải quyết trung bình", "Mean resolution"), duration(summary.mean_resolution_seconds)),
        p(l("Chỉ tính sự cố có mốc thời gian thực tế.", "Only incidents with recorded completion times are counted."))),
      card(l("Tuân thủ SLA", "SLA performance"),
        fact(l("Đúng hạn", "Met"), summary.sla_met_percent == null ? "—" : number(summary.sla_met_percent, 1) + "%"),
        fact(l("Mẫu hoàn thành", "Completed sample"), summary.sla_completed_sample),
        fact(l("Đang quá hạn", "Open breaches"), summary.sla_breached_open), p(l("Thời gian liên tục 24/7, UTC.", "Elapsed time, 24/7, UTC."))),
      card(l("Phân nhóm nguyên nhân", "Categories"), ...categories().map(([key, label]) => fact(label, summary.by_category[key] || 0))));
      if (!selected || !page.items.some((r) => r.id === selected)) selected = page.items[0]?.id || "";
      if (selected) await open(selected); else { detail.replaceChildren(p(l("Chọn một cảnh báo để xử lý.", "Select an alert to investigate."))); actions.replaceChildren(); }
    }
    async function mutate(path, values) { await api(path, values); closeDialog(); await reload(); }
    async function open(id) {
      current = await api(`/incidents/${encodeURIComponent(id)}/detail`);
      const row = current.incident;
      list.querySelectorAll(".record-button").forEach((node) => {
        node.classList.toggle("selected", node.dataset.recordId === id);
        node.setAttribute("aria-pressed", String(node.dataset.recordId === id));
      });
      const content = div("stack");
      const draw = async (key) => {
        activeTab = key;
        const nav = tabs([["overview", l("Tổng quan", "Overview")], ["timeline", l("Lịch sử", "Timeline")],
          ["playbook", l("Hướng dẫn xử lý", "Playbook")], ["related", l("Liên quan", "Related")]], key, draw);
        if (key === "overview") content.replaceChildren(nav,
          card(l("Mô tả sự cố", "Incident description"), p(row.description || "—"),
            fact(l("Nguồn", "Source"), row.source), fact(l("Mã cảnh báo", "Alarm code"), row.alarm_code || "—"),
            fact(l("Lần đầu ghi nhận", "First recorded"), date(row.first_observed_at || row.created_at)),
            fact(l("Ghi nhận gần nhất", "Last observed"), date(row.last_observed_at || row.updated_at)),
            fact(l("Số lần xuất hiện", "Occurrences"), row.occurrences || 1),
            fact(l("Thiết bị", "Equipment"), row.equipment_state === "ACTIVE" ? l("Vẫn có lỗi", "Fault active") : row.equipment_state === "RECOVERED" ? l("Đã phục hồi", "Recovered") : l("Chưa xác minh", "Unknown")),
            fact(l("Nguyên nhân đã ghi nhận", "Recorded cause"), row.root_cause || l("Chưa xác định", "Not determined")),
            div("row", ...(row.tags || []).map((tag) => badge(tag))),
            operator() ? btn(l("Phân loại / ghi nguyên nhân", "Triage / record cause"), () => triage(row, mutate)) : null),
          ...(operator() ? [noteForm(row, mutate)] : []));
        else if (key === "timeline") {
          const history = div("stack");
          const load = async (after = 0) => {
            const page = await api(`/incidents/${row.id}/history?after=${after}`);
            history.querySelector(".load-more")?.remove();
            history.append(...[...page.legacy_timeline, ...page.items].map((item) => div("timeline-item",
              div("row", badge(item.kind || item.status), e("strong", item.actor), e("small", date(item.at))), p(item.note))));
            if (page.next_cursor) history.append(btn(l("Xem tiếp", "Load more"), () => load(page.next_cursor), "load-more"));
          };
          await load(); content.replaceChildren(nav, history);
        } else if (key === "playbook") content.replaceChildren(nav, playbookPanel(row, current.playbooks, mutate));
        else content.replaceChildren(nav,
          card(l("Thiết bị & kết nối", "Equipment & sources"),
            row.device_id ? btn(l("Mở thiết bị", "Open equipment"), () => deviceDetail(row.device_id)) : p(l("Chưa gắn thiết bị.", "No equipment linked.")),
            table([l("Nguồn", "Source"), l("Trạng thái lỗi", "Fault state"), l("Thời gian nguồn", "Source time")], current.sources.map((s) => [s.binding_id, s.active ? l("Đang lỗi", "Active") : l("Đã phục hồi", "Recovered"), date(s.source_timestamp)]))),
          card(l("Công việc bảo trì liên quan", "Linked work orders"), table([t("name"), t("status"), l("Phụ trách", "Assignee")], current.work_orders.map((job) => [job.title, stateLabel(job.status), job.assigned_to || "—"])),
            btn(l("Mở quản lý bảo trì", "Open maintenance"), () => go("incidents", "", "jobs"))));
      };
      detail.replaceChildren(card(row.title, div("row", badge(levelLabel(row.severity), row.severity === "critical" ? "bad" : "warn"),
        badge(stateLabel(row.status)), p(siteName(row.site_id)))), content);
      actions.replaceChildren(actionPanel(row, current.assignees, mutate),
        card(l("Thời hạn xử lý", "SLA deadlines"),
          fact(l("Tiếp nhận trước", "Respond by"), date(row.sla_status.response_due_at)),
          fact(l("Giải quyết trước", "Resolve by"), date(row.sla_status.resolution_due_at)),
          fact(l("Đã tiếp nhận", "Acknowledged"), date(row.acknowledged_at)),
          fact(l("Đã giải quyết", "Resolved"), date(row.resolved_at)),
          badge(row.sla_status.state === "BREACHED" ? l("Quá hạn", "Breached") : row.sla_status.state === "MET" ? l("Đúng hạn", "Met") : l("Đang theo dõi", "Tracking"), row.sla_status.state === "BREACHED" ? "bad" : "good"),
          p(l("SLA được chụp tại thời điểm mở sự cố; thay chính sách không xóa lịch sử quá hạn.", "SLA targets are captured when an incident opens; policy changes do not erase breaches."))));
      await draw(activeTab);
    }
    const root = div("stack", div("toolbar", p(l("Theo dõi, phân công và xử lý sự cố trên các nhà máy.", "Monitor, assign and resolve incidents across plants.")),
      operator() ? btn(l("+ Tạo cảnh báo", "+ Create alert"), () => createManual(reload), "primary") : null), metrics,
      div("form-grid", field(l("Tìm kiếm", "Search"), search), field(l("Mức độ", "Severity"), severity),
        field(t("status"), status), field(l("Phân công", "Assignment"), assignment), field("SLA", sla),
        btn(l("Lọc cảnh báo", "Apply filters"), async () => { offset = 0; selected = ""; await reload(); })),
      div("workbench-layout", card(l("Danh sách cảnh báo", "Alert list"), list, pager), detail, actions), analytics);
    await reload(); return root;
  }

  function actionPanel(row, people, mutate) {
    const who = select([["", l("Chưa phân công", "Unassigned")], ...people.map((person) => [person.id, person.id])], row.assigned_to);
    const permitted = {open:["open","acknowledged","in_progress"], acknowledged:["acknowledged","in_progress","resolved"],
      in_progress:["in_progress","resolved"], resolved:["resolved","closed","open"], closed:["closed","open"]};
    const status = select(statuses().filter(([key]) => permitted[row.status].includes(key)), row.status), note = textArea();
    if (!operator()) return card(l("Phân công & xử lý", "Assignment & response"), fact(l("Phụ trách", "Assignee"), row.assigned_to || "—"));
    const f = form(() => mutate(`/incidents/${row.id}/transition`, {revision: row.revision, status: status.value, assigned_to: who.value, note: note.value}), l("Lưu xử lý", "Save response"));
    f.finish(field(l("Người phụ trách", "Assignee"), who), field(l("Trạng thái xử lý", "Workflow status"), status), field(l("Nội dung xử lý", "Response note"), note));
    return card(l("Phân công & xử lý", "Assignment & response"), f,
      row.equipment_state === "ACTIVE" ? notice("Thiết bị vẫn báo lỗi. Tiếp nhận không đồng nghĩa đã khắc phục.", "The device still reports a fault. Acknowledgement does not mean recovery.", true) : null,
      btn(l("Tạo phiếu bảo trì", "Create work order"), () => workOrder(row, people, mutate)));
  }
  function noteForm(row, mutate) {
    const text = textArea("", true, 4000), f = form(() => mutate(`/incidents/${row.id}/notes`, {revision: row.revision, text: text.value}), l("Thêm ghi chú", "Add note"));
    f.finish(field(l("Ghi chú điều tra", "Investigation note"), text));
    return card(l("Ghi chú", "Notes"), f);
  }
  function triage(row, mutate) {
    const severity = select(levels(), row.severity), category = select(categories(), row.category || "other"),
      cause = textArea(row.root_cause || "", false), tags = input("text", (row.tags || []).join(", ")), note = textArea();
    const f = form(() => mutate(`/incidents/${row.id}/triage`, {revision: row.revision, severity: severity.value, category: category.value,
      root_cause: cause.value, tags: tags.value.split(",").map((s) => s.trim()).filter(Boolean), note: note.value}));
    f.finish(field(l("Mức độ", "Severity"), severity), field(l("Nhóm", "Category"), category),
      field(l("Nguyên nhân có bằng chứng", "Evidence-based cause"), cause), field(l("Thẻ (phân cách dấu phẩy)", "Tags (comma separated)"), tags), field(l("Lý do cập nhật", "Reason for change"), note));
    showDialog(l("Phân loại sự cố", "Triage incident"), f);
  }
  function workOrder(row, people, mutate) {
    const title = input("text", row.title, true), instructions = textArea(row.description, true, 4000), due = input("date"),
      assigned = select([["", l("Chưa phân công", "Unassigned")], ...people.map((u) => [u.id, u.id])], row.assigned_to);
    const f = form(() => mutate(`/incidents/${row.id}/work-order`, {revision: row.revision, title: title.value, instructions: instructions.value,
      assigned_to: assigned.value, due_date: due.value || null}));
    f.finish(field(t("name"), title), field(l("Hướng dẫn công việc", "Work instructions"), instructions), field(l("Phụ trách", "Assignee"), assigned), field(l("Ngày đến hạn", "Due date"), due));
    showDialog(l("Tạo phiếu bảo trì", "Create work order"), f);
  }
  function createManual(reload) {
    const site = siteSelect(), title = input("text", "", true), description = textArea("", true, 4000), severity = select(levels(), "medium");
    const f = form(async () => { await api("/records/incident", {site_id: site.value, title: title.value, description: description.value, severity: severity.value}); closeDialog(); await reload(); });
    f.finish(field(t("plants"), site), field(t("name"), title), field(l("Mô tả", "Description"), description), field(l("Mức độ", "Severity"), severity));
    showDialog(l("Ghi nhận cảnh báo", "Record alert"), f);
  }
  function playbookPanel(row, books, mutate) {
    const root = div("stack");
    if (operator()) {
      const selected = select(books.map((b) => [b.id, `${b.name} · v${b.revision}`]));
      const use = btn(l("Áp dụng hướng dẫn", "Attach playbook"), () => mutate(`/incidents/${row.id}/playbook`, {revision: row.revision, playbook_id: selected.value}));
      use.disabled = !books.length || ["resolved", "closed"].includes(row.status);
      root.append(div("toolbar", field(l("Chọn hướng dẫn", "Select playbook"), selected), use));
    }
    if (!row.playbook) { root.append(p(l("Chưa có hướng dẫn được gắn. Kỹ thuật viên có thể tạo tại tab Hướng dẫn xử lý.", "No playbook attached. A technician can create one in the Playbooks tab."))); return root; }
    root.append(p(`${row.playbook.name} · v${row.playbook.revision}`));
    for (const step of row.playbook.steps) {
      const result = row.playbook_results?.[step.id], outcome = select([["pending", l("Chưa thực hiện", "Pending")], ["pass", l("Đạt", "Pass")], ["fail", l("Không đạt", "Fail")], ["not_applicable", l("Không áp dụng", "Not applicable")]], result?.outcome || "pending"),
        note = textArea(result?.note || "", false);
      const panel = card(language === "vi" ? step.instruction_vi : step.instruction_en,
        fact(l("Kết quả đã ghi", "Recorded outcome"), result?.outcome || "—"));
      if (operator() && !["resolved", "closed"].includes(row.status)) {
        const f = form(() => mutate(`/incidents/${row.id}/check`, {revision: row.revision, step_id: step.id, outcome: outcome.value, note: note.value}));
        f.finish(field(l("Kết quả", "Outcome"), outcome), field(l("Bằng chứng / lý do", "Evidence / reason"), note)); panel.append(f);
      }
      root.append(panel);
    }
    return root;
  }

  async function policies() {
    if (!state.site) return card(l("Chính sách SLA", "SLA policies"), p(l("Chọn nhà máy ở thanh trên để cấu hình.", "Select a plant in the top bar to configure its policy.")));
    const policy = await api("/incident-policies/" + encodeURIComponent(state.site)), name = input("text", policy.name, true), fields = {};
    const f = form(async () => {
      const targets = Object.fromEntries(Object.entries(fields).map(([key, value]) => [key, {response_minutes: Number(value.response.value), resolution_minutes: Number(value.resolution.value)}]));
      await api("/incident-policies", {site_id: state.site, revision: policy.revision, name: name.value, targets, escalation_roles: policy.escalation_roles});
      await ui.refresh();
    });
    f.append(field(t("name"), name));
    for (const [key, label] of levels()) {
      const target = policy.targets[key], response = input("number", target.response_minutes, true), resolution = input("number", target.resolution_minutes, true);
      response.min = resolution.min = 1; response.max = 43200; resolution.max = 129600;
      fields[key] = {response, resolution}; f.append(card(label, div("form-grid", field(l("Tiếp nhận trong (phút)", "Respond within (min)"), response), field(l("Giải quyết trong (phút)", "Resolve within (min)"), resolution))));
    }
    if (technical()) f.finish(); else f.querySelectorAll("input").forEach((node) => node.disabled = true);
    return card(l("Mục tiêu SLA theo mức độ", "SLA targets by severity"), notice("Áp dụng cho sự cố mở mới. Thông báo quá hạn ở trong ứng dụng; chưa gửi email/SMS.", "Applies to new incidents. Escalations are in-app; email/SMS is not sent."), f);
  }
  async function books() {
    const rows = await api("/incident-playbooks?" + scope());
    return card(l("Hướng dẫn xử lý", "Playbooks"), technical() ? btn(l("+ Tạo hướng dẫn", "+ Create playbook"), () => editBook(), "primary") : null,
      table([t("name"), t("plants"), l("Phiên bản", "Revision"), l("Số bước", "Steps"), t("status"), ""], rows.map((r) => [r.name, siteName(r.site_id), r.revision, r.steps.length,
        r.enabled ? l("Đang dùng", "Enabled") : l("Tạm ngừng", "Disabled"), technical() ? btn(l("Chỉnh sửa", "Edit"), () => editBook(r)) : "—"])));
  }
  function editBook(row) {
    let steps = [];
    const site = siteSelect(row?.site_id || state.site), name = input("text", row?.name || "", true), description = textArea(row?.description || "", false),
      category = select(categories(), row?.category || "other"), enabled = select([["yes", l("Đang dùng", "Enabled")], ["no", l("Tạm ngừng", "Disabled")]], row?.enabled === false ? "no" : "yes"), list = div("stack");
    if (row) site.disabled = true;
    function addStep(value = {}) {
      const vi = textArea(value.instruction_vi || ""), en = textArea(value.instruction_en || ""), proof = input("checkbox"); proof.checked = value.requires_evidence !== false;
      const item = {id: value.id || crypto.randomUUID().replaceAll("-", ""), vi, en, proof};
      const panel = card(l("Bước xử lý", "Investigation step"), field("Tiếng Việt", vi), field("English", en), field(l("Yêu cầu ghi bằng chứng", "Require evidence note"), proof),
        btn(l("Bỏ bước", "Remove step"), () => { steps = steps.filter((s) => s !== item); panel.remove(); }));
      steps.push(item); list.append(panel);
    }
    (row?.steps || [{}]).forEach(addStep);
    const f = form(async () => {
      await api("/incident-playbooks" + (row ? "/" + row.id : ""), {site_id: site.value, revision: row?.revision || 0,
        name: name.value, description: description.value, category: category.value, enabled: enabled.value === "yes", alarm_codes: row?.alarm_codes || [],
        steps: steps.map((s) => ({id: s.id, instruction_vi: s.vi.value, instruction_en: s.en.value, requires_evidence: s.proof.checked}))});
      closeDialog(); await ui.refresh();
    });
    f.finish(field(t("plants"), site), field(t("name"), name), field(l("Mô tả", "Description"), description), field(l("Nhóm", "Category"), category), field(t("status"), enabled), list,
      btn(l("+ Thêm bước", "+ Add step"), () => { if (steps.length < 30) addStep(); }),
      notice("Hướng dẫn chỉ ghi kết quả người xử lý. Không tự gửi lệnh hoặc xác nhận an toàn điện.", "Playbooks record operator findings. They do not send device commands or certify electrical safety."));
    showDialog(l("Soạn hướng dẫn xử lý", "Edit playbook"), f);
  }
  return {center, policies, books};
}
