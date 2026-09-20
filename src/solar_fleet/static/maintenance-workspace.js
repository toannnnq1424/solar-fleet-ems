import { l, t, date, number } from "./i18n.js";

// Content only: navigation, forms, dialogs and styles belong to the shared workspace.
export function createMaintenanceWorkspace(ui) {
  const { state, e, div, p, btn, badge, card, input, select, field, fact,
    notice, table, tabs, form, api, showDialog, closeDialog, operator,
    siteName, siteSelect, deviceDetail, go } = ui;
  const technical = () => ["Installer", "Senior Engineer"].includes(state.me.user.role);
  const scope = () => new URLSearchParams(state.site ? { site_id: state.site } : {});
  const statuses = () => [
    ["open", l("Mới tạo", "Open")],
    ["acknowledged", l("Đã tiếp nhận", "Acknowledged")],
    ["in_progress", l("Đang thực hiện", "In progress")],
    ["resolved", l("Đã hoàn tất", "Resolved")],
    ["closed", l("Đã đóng", "Closed")],
  ];
  const outcomes = () => [
    ["pending", l("Chưa thực hiện", "Pending")],
    ["pass", l("Đạt", "Pass")],
    ["fail", l("Chưa đạt", "Fail")],
    ["not_applicable", l("Không áp dụng (cần lý do)", "Not applicable (reason required)")],
  ];
  const stages = () => ({
    UNPLANNED: l("Chưa lập kế hoạch", "Unplanned"),
    PLANNED: l("Đã lập kế hoạch", "Planned"),
    IN_PROGRESS: l("Đang thực hiện", "In progress"),
    AWAITING_REVIEW: l("Chờ kiểm tra độc lập", "Awaiting independent review"),
    CHANGES_REQUESTED: l("Cần bổ sung", "Changes requested"),
    APPROVED: l("Đã được duyệt", "Approved"),
  });
  const statusLabel = (value) => statuses().find(([key]) => key === value)?.[1] || value;
  const outcomeLabel = (value) => outcomes().find(([key]) => key === value)?.[1] || value;
  const editable = (row) => !["resolved", "closed"].includes(row.status);
  const area = (value = "", required = true) => {
    const control = e("textarea");
    control.value = value;
    control.rows = 3;
    control.required = required;
    control.maxLength = 2000;
    return control;
  };
  const requiredInput = (type, value = "") => {
    const control = input(type, value);
    control.required = true;
    return control;
  };
  const browserZone = () => Intl.DateTimeFormat().resolvedOptions().timeZone;
  const localInputValue = (value) => {
    if (!value) return "";
    const at = new Date(value);
    return new Date(at.getTime() - at.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  };
  const timeHint = () => p(l("Giờ nhập theo trình duyệt: ", "Input times use your browser timezone: ") + browserZone());
  const reasonLabel = (value, plan) => {
    const [code, id] = value.split(":");
    const label = {
      work_execution_plan_required: l("Cần lập kế hoạch và checklist.", "An execution plan and checklist are required."),
      required_step_incomplete: l("Chưa hoàn tất bước bắt buộc", "Required step incomplete"),
      failed_step: l("Bước kiểm tra chưa đạt", "Failed checklist step"),
      evidence_unavailable: l("Tài liệu bằng chứng không còn khả dụng", "Evidence document no longer available"),
      evidence_changed: l("Tài liệu đã đổi phiên bản; cần kiểm tra lại", "Evidence version changed; review the step again"),
      work_time_entry_required: l("Cần ghi thời gian thực hiện.", "Record the time spent on this work."),
    }[code] || value;
    return label + (id ? ": " + (plan?.steps.find((step) => step.id === id)?.title || id) : "");
  };

  async function health() {
    const result = await api("/maintenance/health?" + scope());
    const rows = result.items;
    const attention = rows.filter((row) => row.state === "NEEDS_ATTENTION");
    const reasons = {
      connectivity_or_data_stale: l("Mất kết nối hoặc dữ liệu cũ", "Offline or stale data"),
      open_incidents: l("Có cảnh báo chưa giải quyết", "Unresolved incidents"),
      no_verified_telemetry: l("Chưa có dữ liệu đã xác minh", "No verified measurements"),
    };
    return div("stack",
      div("row between", p(l("Quan sát tại ", "Observed at ") + date(result.as_of)),
        btn(l("Mở công việc bảo trì", "Open maintenance work"), () => go("incidents", "", "jobs"), "primary")),
      div("grid four",
        card(l("Thiết bị trong phạm vi", "Devices in scope"), e("strong", number(rows.length, 0), "metric-value")),
        card(l("Cần chú ý", "Need attention"), e("strong", number(attention.length, 0), "metric-value")),
        card(l("Có dữ liệu mới", "Fresh measurements"), e("strong", number(rows.filter((row) => row.fresh_channels > 0).length, 0), "metric-value")),
        card(l("Có công việc đang mở", "With open work"), e("strong", number(rows.filter((row) => row.open_work_orders > 0).length, 0), "metric-value"))),
      card(l("Kết nối, dữ liệu và công việc", "Connectivity, measurements and work"),
        notice("Trạng thái dựa trên kết nối, độ mới dữ liệu và cảnh báo. Chưa có kết luận sức khỏe điện hoặc phiên bản firmware mới nhất khi thiếu dữ liệu xác minh.",
          "Status reflects connectivity, data freshness and alerts. Electrical health and latest firmware are unavailable without verified evidence."),
        table([t("devices"), t("plants"), t("status"), l("Dữ liệu mới / đã xác minh", "Fresh / verified channels"),
          l("Cảnh báo / công việc mở", "Open alerts / work"), l("Firmware ghi nhận", "Reported firmware"), l("Cập nhật cuối", "Last seen")],
        rows.map((row) => [btn(row.name, () => deviceDetail(row.device_id)), siteName(row.site_id),
          div("stack", badge(row.state === "OBSERVABLE" ? l("Có dữ liệu quan sát", "Observable") : l("Cần chú ý", "Needs attention"), row.state === "OBSERVABLE" ? "good" : "warn"),
            ...row.reasons.map((reason) => e("small", reasons[reason] || reason))),
          `${row.fresh_channels} / ${row.verified_channels}`, `${row.open_incidents} / ${row.open_work_orders}`,
          row.firmware || l("Chưa biết", "Unknown"), date(row.last_seen)])),
        rows.length ? null : p(l("Chưa có thiết bị trong phạm vi này.", "No devices in this scope."))),
      div("grid three",
        card(l("Lịch dịch vụ", "Service calendar"), p(l("Xem lịch đã lập và kỳ bảo trì sắp tới.", "Review planned work and upcoming maintenance occurrences.")),
          btn(l("Xem lịch", "View calendar"), () => go("incidents", "", "service-calendar"))),
        card(l("Firmware", "Firmware"), p(l("Lập yêu cầu nâng cấp, phiên bản và cửa sổ bảo trì.", "Prepare upgrade requests, versions and maintenance windows.")),
          btn(l("Mở yêu cầu firmware", "Open firmware requests"), () => go("incidents", "", "firmware_request"))),
        card(l("Kế hoạch định kỳ", "Recurring plans"), p(l("Thiết lập chu kỳ và hướng dẫn công việc.", "Configure recurrence and work instructions.")),
          btn(l("Quản lý kế hoạch", "Manage plans"), () => go("incidents", "", "maintenance_plan")))));
  }

  async function jobs() {
    let selected = state.tab || "", offset = 0, activeTab = "execution", openEpoch = 0;
    const search = input("search"), status = select([["", t("all")], ...statuses()]);
    const late = select([["", l("Tất cả thời hạn", "All deadlines")], ["yes", l("Chỉ quá hạn", "Overdue only")]]);
    search.maxLength = 200;
    const list = div("record-list"), detail = div("stack"), actions = div("stack"), pager = div("toolbar");
    async function reload() {
      const query = scope();
      query.set("offset", offset); query.set("limit", 20);
      if (search.value.trim()) query.set("q", search.value.trim());
      if (status.value) query.set("status", status.value);
      if (late.value) query.set("overdue", "true");
      const page = await api("/maintenance/work-orders?" + query);
      if (!selected) selected = page.items[0]?.id || "";
      list.replaceChildren(...page.items.map((row) => {
        const item = btn("", async () => { selected = row.id; activeTab = "execution"; await open(row.id); }, "record-button");
        item.dataset.recordId = row.id;
        item.append(e("strong", row.title), p(siteName(row.site_id)),
          div("row", badge(statusLabel(row.status)), badge(stages()[row.execution_state])),
          p(l("Checklist: ", "Checklist: ") + `${row.checklist_completed}/${row.checklist_total}`),
          p(l("Người phụ trách: ", "Assignee: ") + (row.assigned_to || "—")),
          p(l("Hạn hoàn tất: ", "Due: ") + (row.due_date || "—")));
        if (row.overdue) item.append(badge(l("Quá hạn", "Overdue"), "bad"));
        return item;
      }));
      if (!page.items.length) list.append(p(l("Không có công việc phù hợp.", "No work matches these filters.")));
      const previous = btn(l("Trước", "Previous"), async () => { offset = Math.max(0, offset - 20); selected = ""; await reload(); });
      const next = btn(l("Sau", "Next"), async () => { offset += 20; selected = ""; await reload(); });
      previous.disabled = offset === 0; next.disabled = offset + 20 >= page.total;
      pager.replaceChildren(previous, p(`${page.total ? offset + 1 : 0}–${Math.min(offset + 20, page.total)} / ${page.total}`), next);
      if (selected) await open(selected);
      else { detail.replaceChildren(p(l("Chọn công việc để xem chi tiết.", "Select work to see its details."))); actions.replaceChildren(); }
    }
    async function changed(path, body) {
      await api(path, body);
      closeDialog();
      await reload();
    }
    async function open(id) {
      const epoch = ++openEpoch;
      const data = await api(`/maintenance/work-orders/${encodeURIComponent(id)}`);
      if (epoch !== openEpoch) return;
      if (state.site && data.work_order.site_id !== state.site) {
        detail.replaceChildren(p(l("Công việc thuộc nhà máy khác. Đổi phạm vi để xem.", "This work belongs to another plant. Change the scope to view it.")));
        actions.replaceChildren();
        return;
      }
      const row = data.work_order, plan = data.execution;
      list.querySelectorAll(".record-button").forEach((node) => {
        const active = node.dataset.recordId === id;
        node.classList.toggle("selected", active); node.setAttribute("aria-pressed", String(active));
      });
      const content = div("stack");
      const draw = async () => {
        content.replaceChildren(tabs([
          ["execution", l("Thực hiện", "Execution")], ["time", l("Thời gian", "Time entries")], ["history", l("Lịch sử", "History")],
        ], activeTab, async (key) => { activeTab = key; await draw(); }));
        if (activeTab === "execution") content.append(executionPanel(data, changed));
        if (activeTab === "time") content.append(timePanel(data, changed));
        if (activeTab === "history") {
          const box = div("stack"); content.append(box);
          let cursor = 0;
          const more = btn(l("Xem thêm lịch sử", "Load more history"), loadHistory);
          async function loadHistory() {
            const page = await api(`/maintenance/work-orders/${row.id}/events?after=${cursor}`);
            cursor = page.next_cursor;
            box.append(...page.items.map((item) => card(eventLabel(item.kind),
              p(date(item.at) + " · " + item.actor), p(item.note),
              ui.raw(l("Bằng chứng đã lưu", "Saved evidence"), item.details))));
            more.disabled = page.items.length < 50;
          }
          box.append(p(l("Các lần thay đổi trạng thái", "Status changes")),
            table([l("Lúc", "At"), l("Người thực hiện", "Actor"), t("status"), l("Ghi chú", "Note")],
              row.timeline.filter((item) => !item.kind).map((item) => [date(item.at), item.actor, statusLabel(item.status), item.note])));
          await loadHistory(); content.append(more);
        }
      };
      detail.replaceChildren(card(row.title, div("row", badge(statusLabel(row.status)), badge(stages()[plan?.state || "UNPLANNED"])),
        p(row.description || "—"), content));
      actions.replaceChildren(card(l("Thông tin công việc", "Work details"),
        fact(t("plants"), siteName(row.site_id)), fact(l("Hạn hoàn tất", "Due date"), row.due_date || "—"),
        fact(l("Người phụ trách", "Assignee"), row.assigned_to || "—"), fact(l("Phiên bản phiếu", "Work revision"), row.revision),
        fact(l("Thời gian đã ghi", "Recorded time"), number(data.total_minutes, 0) + l(" phút", " min")),
        card(l("Điều kiện hoàn tất", "Completion requirements"),
          data.completion.ready ? p(l("Đủ checklist và thời gian thực hiện.", "Checklist and work time are recorded.")) :
            div("stack", ...data.completion.reasons.map((reason) => p(reasonLabel(reason, plan)))),
          p(plan?.review?.decision === "approve" ? l("Đã có kiểm tra độc lập.", "Independent review is recorded.") : l("Cần người khác kiểm tra trước khi hoàn tất.", "Another technician must review before completion.")),
          ...(operator() ? [btn(l("Cập nhật trạng thái / phân công", "Update status / assignment"), () => editStatus(data, changed))] : [])));
      if (row.incident_id) actions.append(btn(l("Mở cảnh báo liên quan", "Open linked incident"), () => go("incidents", row.incident_id, "main")));
      if (row.device_id) actions.append(btn(l("Mở thiết bị", "Open device"), () => deviceDetail(row.device_id)));
      await draw();
    }
    const filter = form(async () => { selected = ""; offset = 0; await reload(); }, l("Lọc công việc", "Filter work"));
    filter.finish(div("form-grid", field(l("Tìm công việc", "Search work"), search), field(t("status"), status), field(l("Thời hạn", "Deadline"), late)));
    const root = div("stack",
      div("row between", e("h2", l("Công việc bảo trì", "Maintenance work")),
        operator() ? btn(l("+ Tạo phiếu bảo trì", "+ Create work order"), () => newJob(async (row) => { selected = row.id; await reload(); }), "primary") : null),
      filter, div("workbench-layout", card(l("Danh sách công việc", "Work list"), list, pager), detail, actions));
    await reload();
    return root;
  }

  function newJob(done) {
    const site = siteSelect(state.site), title = requiredInput("text"), description = area("", false);
    const device = select([["", l("Toàn nhà máy", "Whole plant")]]), due = input("date");
    title.maxLength = 200;
    function syncDevices() {
      device.replaceChildren(...select([["", l("Toàn nhà máy", "Whole plant")],
        ...state.fleet.devices.filter((row) => row.site_id === site.value).map((row) => [row.id, row.name || row.vendor_id])]).children);
    }
    site.onchange = syncDevices; syncDevices();
    const f = form(async () => {
      const row = await api("/records/work_order", { site_id: site.value, title: title.value.trim(), description: description.value,
        device_id: device.value || null, due_date: due.value || null });
      closeDialog(); await done(row);
    }, l("Tạo phiếu", "Create work order"));
    f.finish(field(t("plants"), site), field(l("Tên công việc", "Work title"), title), field(t("devices"), device),
      field(l("Mô tả công việc", "Work description"), description), field(l("Hạn hoàn tất", "Due date"), due));
    showDialog(l("Phiếu bảo trì mới", "New work order"), f);
  }

  function executionPanel(data, changed) {
    const row = data.work_order, plan = data.execution;
    const root = div("stack");
    if (technical() && editable(row)) root.append(btn(plan ? l("Chỉnh kế hoạch / checklist", "Edit plan / checklist") : l("Lập kế hoạch thực hiện", "Plan this work"),
      () => editPlan(data, changed), "primary"));
    if (!plan) { root.append(p(l("Chưa có kế hoạch thực hiện. Kỹ thuật viên lập checklist trước khi ghi kết quả.", "No execution plan yet. A technician must define the checklist before recording results."))); return root; }
    root.append(card(l("Kế hoạch thực hiện", "Execution plan"),
      fact(l("Dự kiến bắt đầu", "Planned start"), date(plan.planned_start)), fact(l("Dự kiến kết thúc", "Planned end"), date(plan.planned_end)),
      fact(l("Nhóm thực hiện", "Team"), plan.team.join(", ") || "—"), p(plan.safety_note)));
    for (const step of plan.steps) {
      const result = plan.results[step.id];
      root.append(card(step.title, div("row", badge(outcomeLabel(result?.outcome || "pending"), result?.outcome === "pass" ? "good" : result?.outcome === "fail" ? "bad" : "warn"),
        step.required ? e("small", l("Bắt buộc", "Required")) : e("small", l("Tùy chọn", "Optional"))),
        p(step.instructions), result ? p(result.note) : null,
        result ? p(date(result.at) + " · " + result.actor) : null,
        result?.document_ids.length ? p(l("Tài liệu: ", "Documents: ") + result.document_ids.map((id) => data.documents.find((doc) => doc.id === id)?.name || id).join(", ")) : null,
        technical() && editable(row) ? btn(l("Ghi kết quả", "Record result"), () => recordStep(data, step, changed)) : null));
    }
    if (plan.review) root.append(card(l("Kết quả kiểm tra độc lập", "Independent review"),
      p(plan.review.decision === "approve" ? l("Chấp thuận", "Approved") : l("Yêu cầu bổ sung", "Changes requested")),
      p(plan.review.note), p(date(plan.review.at) + " · " + plan.review.reviewer)));
    if (technical() && editable(row) && plan.state !== "AWAITING_REVIEW" && plan.state !== "APPROVED") {
      const submit = btn(l("Gửi kiểm tra độc lập", "Submit for independent review"), () => noteAction(l("Gửi kiểm tra", "Submit for review"),
        (note) => changed(`/maintenance/work-orders/${row.id}/submit`, { revision: row.revision, note })), "primary");
      submit.disabled = !data.completion.ready;
      root.append(submit);
    }
    const ownWork = plan.submitted_by === state.me.user.id || Object.values(plan.results).some((result) => result.actor === state.me.user.id) ||
      data.time_entries.some((entry) => !entry.voided && entry.actor === state.me.user.id);
    if (technical() && editable(row) && plan.state === "AWAITING_REVIEW") {
      if (ownWork) root.append(p(l("Một kỹ thuật viên khác cần kiểm tra công việc này.", "Another technician must review this work.")));
      else root.append(div("row", ...[["approve", l("Duyệt hoàn tất", "Approve completion")], ["return", l("Yêu cầu bổ sung", "Request changes")]].map(([decision, label]) =>
        btn(label, () => noteAction(label, (note) => changed(`/maintenance/work-orders/${row.id}/review`, { revision: row.revision, decision, note })), decision === "approve" ? "primary" : ""))));
    }
    return root;
  }

  function editPlan(data, changed) {
    const row = data.work_order, plan = data.execution;
    const start = input("datetime-local", localInputValue(plan?.planned_start)), end = input("datetime-local", localInputValue(plan?.planned_end));
    const safety = area(plan?.safety_note || ""), note = area(), list = div("stack"), team = [];
    let steps = [];
    const teamPanel = div("form-grid", ...data.assignees.map((person) => {
      const control = input("checkbox"); control.checked = plan?.team.includes(person.id) || false;
      team.push({ id: person.id, control });
      return field(person.id + " · " + t(person.role), control);
    }));
    function addStep(value = {}) {
      const title = requiredInput("text", value.title || ""), instructions = area(value.instructions || "", false), required = input("checkbox");
      title.maxLength = 300; required.checked = value.required !== false;
      const item = { id: value.id || crypto.randomUUID().replaceAll("-", ""), title, instructions, required };
      const panel = card(l("Bước công việc", "Work step"), field(l("Tên bước", "Step title"), title), field(l("Hướng dẫn", "Instructions"), instructions),
        field(l("Bắt buộc hoàn tất", "Required for completion"), required),
        btn(l("Bỏ bước", "Remove step"), () => { steps = steps.filter((step) => step !== item); panel.remove(); }));
      steps.push(item); list.append(panel);
    }
    (plan?.steps || [{}]).forEach(addStep);
    const f = form(async () => {
      await changed(`/maintenance/work-orders/${row.id}/plan`, { revision: row.revision,
        planned_start: start.value ? new Date(start.value).toISOString() : null,
        planned_end: end.value ? new Date(end.value).toISOString() : null,
        safety_note: safety.value, note: note.value, team: team.filter((person) => person.control.checked).map((person) => person.id),
        steps: steps.map((step) => ({ id: step.id, title: step.title.value.trim(), instructions: step.instructions.value, required: step.required.checked })) });
    });
    f.finish(timeHint(), div("form-grid", field(l("Bắt đầu dự kiến", "Planned start"), start), field(l("Kết thúc dự kiến", "Planned end"), end)),
      card(l("Nhóm thực hiện", "Work team"), teamPanel), field(l("Điều kiện và lưu ý an toàn", "Prerequisites and safety notes"), safety), list,
      btn(l("+ Thêm bước", "+ Add step"), () => { if (steps.length < 50) addStep(); }), field(l("Lý do lập / thay đổi kế hoạch", "Reason for this plan or change"), note),
      plan ? notice("Lưu kế hoạch mới sẽ yêu cầu ghi lại toàn bộ kết quả checklist và duyệt lại. Bằng chứng cũ vẫn được giữ trong lịch sử.",
        "Saving a new plan requires fresh checklist results and review. Previous evidence remains in history.", true) : null);
    showDialog(l("Kế hoạch thực hiện", "Execution plan"), f);
  }

  function recordStep(data, step, changed) {
    const row = data.work_order, result = data.execution.results[step.id];
    const outcome = select(outcomes(), result?.outcome || "pending"), note = area(result?.note || ""), documents = [];
    const proof = div("stack", ...data.documents.map((doc) => {
      const checkbox = input("checkbox"); checkbox.checked = result?.document_ids.includes(doc.id) || false;
      documents.push({ id: doc.id, checkbox });
      return field(doc.name, checkbox);
    }));
    const f = form(async () => changed(`/maintenance/work-orders/${row.id}/step`, { revision: row.revision, step_id: step.id,
      outcome: outcome.value, note: note.value, document_ids: documents.filter((doc) => doc.checkbox.checked).map((doc) => doc.id) }));
    f.finish(p(step.instructions), field(l("Kết quả", "Result"), outcome), field(l("Kết quả đo / bằng chứng / lý do", "Measurements / evidence / reason"), note),
      card(l("Tài liệu liên quan", "Related documents"), proof, data.documents.length ? null : p(l("Chưa có hồ sơ tài liệu tại nhà máy.", "No document records for this plant."))));
    showDialog(step.title, f);
  }

  function timePanel(data, changed) {
    const row = data.work_order;
    const root = card(l("Thời gian thực hiện", "Work time"),
      fact(l("Tổng thời gian hợp lệ", "Total active time"), number(data.total_minutes, 0) + l(" phút", " min")),
      table([l("Bắt đầu", "Start"), l("Kết thúc", "End"), l("Người thực hiện", "Actor"), l("Công việc", "Activity"), t("status"), ""],
        data.time_entries.map((entry) => [date(entry.start), date(entry.end), entry.actor, entry.activity,
          entry.voided ? l("Đã hủy", "Voided") : l("Được tính", "Counted"),
          operator() && editable(row) && !entry.voided && entry.actor === state.me.user.id ? btn(l("Hủy ghi nhận", "Void entry"),
            () => noteAction(l("Lý do hủy ghi nhận", "Reason for voiding"), (note) => changed(`/maintenance/work-orders/${row.id}/time/${entry.id}/void`, { revision: row.revision, note }))) : "—"])));
    if (operator() && editable(row)) root.append(btn(l("+ Ghi thời gian", "+ Record work time"), () => {
      const start = requiredInput("datetime-local"), end = requiredInput("datetime-local"), activity = area();
      const f = form(async () => changed(`/maintenance/work-orders/${row.id}/time`, { revision: row.revision,
        start: new Date(start.value).toISOString(), end: new Date(end.value).toISOString(), activity: activity.value }));
      f.finish(timeHint(), field(l("Bắt đầu", "Start"), start), field(l("Kết thúc", "End"), end), field(l("Công việc đã thực hiện", "Work performed"), activity),
        p(l("Mỗi lần ghi tối đa 24 giờ; thời gian của một người không được trùng nhau giữa các phiếu.", "Each entry may span up to 24 hours; a person's time cannot overlap across work orders.")));
      showDialog(l("Ghi thời gian thực hiện", "Record work time"), f);
    }, "primary"));
    return root;
  }

  function editStatus(data, changed) {
    const row = data.work_order;
    const transitions = { open: ["open", "acknowledged", "in_progress"], acknowledged: ["acknowledged", "in_progress", "resolved"],
      in_progress: ["in_progress", "resolved"], resolved: ["resolved", "closed", "open"], closed: ["closed", "open"] };
    const status = select(statuses().filter(([key]) => transitions[row.status].includes(key)), row.status);
    const assignee = select([["", l("Chưa phân công", "Unassigned")], ...data.assignees.map((person) => [person.id, person.id])], row.assigned_to);
    const note = area();
    const f = form(async () => changed(`/records/work_order/${row.id}`, { revision: row.revision, status: status.value, assigned_to: assignee.value, note: note.value }));
    f.finish(field(t("status"), status), field(l("Người phụ trách", "Assignee"), assignee), field(l("Ghi chú thay đổi", "Change note"), note),
      p(l("Hoàn tất / đóng phiếu cần checklist đạt, thời gian thực hiện và kiểm tra độc lập còn hợp lệ. Mở lại sẽ yêu cầu duyệt lại.",
        "Resolving or closing requires completed checks, work time and a valid independent review. Reopening requires another review.")));
    showDialog(l("Trạng thái và phân công", "Status and assignment"), f);
  }

  function noteAction(title, save) {
    const note = area();
    const f = form(async () => save(note.value));
    f.finish(field(l("Ghi chú", "Note"), note));
    showDialog(title, f);
  }

  function eventLabel(kind) {
    return ({ maintenance_plan_saved: l("Lưu kế hoạch", "Plan saved"), maintenance_step_recorded: l("Ghi kết quả checklist", "Checklist result recorded"),
      maintenance_time_recorded: l("Ghi thời gian", "Time recorded"), maintenance_time_voided: l("Hủy ghi nhận thời gian", "Time entry voided"),
      maintenance_submitted: l("Gửi kiểm tra", "Submitted for review"), maintenance_reviewed: l("Kiểm tra độc lập", "Independent review") })[kind] || kind;
  }

  async function calendar() {
    const today = new Date(), later = new Date(today.getTime() + 30 * 86400000);
    const start = requiredInput("date", localInputValue(today).slice(0, 10));
    const end = requiredInput("date", localInputValue(later).slice(0, 10));
    const output = div("stack");
    async function draw() {
      const query = scope(); query.set("start", start.value); query.set("end", end.value);
      const result = await api("/maintenance/calendar?" + query);
      output.replaceChildren(table([l("Ngày tại nhà máy", "Plant local date"), l("Công việc / kế hoạch", "Work / plan"), t("plants"), l("Loại", "Type"), t("status"), ""],
        result.items.map((row) => [row.date, row.title, siteName(row.site_id),
          row.kind === "recurrence" ? l("Kỳ dự kiến", "Projected occurrence") : l("Phiếu đã lập lịch", "Scheduled work"),
          row.kind === "recurrence" ? l("Dự kiến · chưa phải phiếu", "Projection · not a work order") : statusLabel(row.status),
          btn(l("Mở", "Open"), () => go("incidents", row.kind === "work_order" ? row.id : "", row.kind === "work_order" ? "jobs" : "maintenance_plan"))])));
      if (!result.items.length) output.append(p(l("Không có lịch trong khoảng đã chọn.", "No planned work in this date range.")));
    }
    const f = form(draw, l("Xem lịch", "Show calendar"));
    f.finish(div("form-grid", field(l("Từ ngày", "From date"), start), field(l("Đến trước ngày", "Until date (exclusive)"), end)));
    await draw();
    return card(l("Lịch dịch vụ", "Service calendar"),
      notice("Xem tối đa 93 ngày. Kỳ dự kiến dựa trên kế hoạch định kỳ; phiếu thực tế và lịch thực hiện được hiển thị riêng.",
        "View up to 93 days. Projected occurrences come from recurring plans; actual work orders and their execution times are shown separately."), f, output);
  }

  return { health, jobs, calendar };
}
