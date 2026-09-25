import { l, t, date, number } from "./i18n.js";
import { icon } from "./icons.js";

// Maintenance & Work Orders Workspace (Mockup #23)
// 4 canonical sub-tabs: Sức khỏe (health), Phiếu công tác (jobs/work_orders), Kế hoạch định kỳ (plans), Firmware & OTA (firmware).
export function createMaintenanceWorkspace(ui) {
  const {
    state, e, div, p, btn, badge, card, input, select, field, fact,
    notice, table, tabs, form, api, showDialog, closeDialog, operator,
    siteName, siteSelect, deviceDetail, go,
  } = ui;

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

  const severities = () => [
    ["critical", l("Khẩn cấp", "Critical")],
    ["high", l("Cao", "High")],
    ["medium", l("Trung bình", "Medium")],
    ["low", l("Thấp", "Low")],
  ];

  const statusLabel = (value) => statuses().find(([key]) => key === value)?.[1] || value;
  const outcomeLabel = (value) => outcomes().find(([key]) => key === value)?.[1] || value;
  const severityLabel = (value) => severities().find(([key]) => key === value)?.[1] || value;
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

  // KPI Header Component
  async function kpiHeader(summaryData) {
    const dev = summaryData?.devices || { total: 0, attention: 0, fresh: 0, healthy: 0 };
    const wo = summaryData?.work_orders || { total: 0, open: 0, in_progress: 0, overdue: 0, awaiting_review: 0, resolved: 0 };
    const pl = summaryData?.plans || { total: 0, active: 0, due_soon: 0 };
    const fw = summaryData?.firmware || { total_requests: 0, pending_requests: 0 };

    const grid = div("grid four maintenance-kpi-grid");

    const c1 = card(l("Sức khỏe thiết bị", "Device Health"),
      div("row between",
        e("strong", number(dev.total, 0), "metric-value"),
        dev.attention > 0 ? badge(`${dev.attention} ` + l("cần chú ý", "need attention"), "warn") : badge(l("Bình thường", "Normal"), "good")
      ),
      p(l("Quan sát: ", "Observable: ") + `${dev.healthy}/${dev.total} · ` + l("Có dữ liệu mới: ", "Fresh: ") + `${dev.fresh}`)
    );

    const c2 = card(l("Phiếu công tác O&M", "Work Orders"),
      div("row between",
        e("strong", number(wo.total, 0), "metric-value"),
        wo.overdue > 0 ? badge(`${wo.overdue} ` + l("quá hạn", "overdue"), "bad") : badge(l("Đúng hạn", "On track"), "good")
      ),
      p(l("Đang mở: ", "Open: ") + `${wo.open} · ` + l("Đang làm: ", "In progress: ") + `${wo.in_progress} · ` + l("Chờ duyệt: ", "Review: ") + `${wo.awaiting_review}`)
    );

    const c3 = card(l("Kế hoạch định kỳ", "Preventive Plans"),
      div("row between",
        e("strong", number(pl.total, 0), "metric-value"),
        pl.due_soon > 0 ? badge(`${pl.due_soon} ` + l("đến hạn 7 ngày", "due in 7d"), "warn") : badge(l("Đang kích hoạt", "Active"), "good")
      ),
      p(l("Đang chạy: ", "Enabled: ") + `${pl.active}/${pl.total}`)
    );

    const c4 = card(l("Firmware & Nâng cấp OTA", "Firmware & OTA"),
      div("row between",
        e("strong", number(fw.total_requests, 0), "metric-value"),
        fw.pending_requests > 0 ? badge(`${fw.pending_requests} ` + l("trong hàng đợi", "queued"), "blue") : badge(l("Đã cập nhật", "Up to date"), "good")
      ),
      p(l("Tổng thời gian kỹ thuật: ", "Total logged labor: ") + number(summaryData?.total_labor_minutes || 0, 0) + l(" phút", " min"))
    );

    grid.append(c1, c2, c3, c4);
    return grid;
  }

  // 1. SUBTAB: HEALTH & RELIABILITY
  async function health() {
    const [summaryResult, healthResult] = await Promise.all([
      api("/maintenance/summary?" + scope()),
      api("/maintenance/health?" + scope()),
    ]);

    const rows = healthResult.items;

    const reasons = {
      connectivity_or_data_stale: l("Mất kết nối hoặc dữ liệu cũ", "Offline or stale data"),
      open_incidents: l("Có cảnh báo chưa giải quyết", "Unresolved incidents"),
      no_verified_telemetry: l("Chưa có dữ liệu đã xác minh", "No verified measurements"),
    };

    const typeFilter = select([
      ["", l("Tất cả loại thiết bị", "All equipment types")],
      ["INVERTER", l("Biến tần (Inverter)", "Inverter")],
      ["BATTERY", l("Pin lưu trữ (Battery)", "Battery")],
      ["METER", l("Công tơ (Meter)", "Meter")],
      ["LOGGER", l("Bộ thu thập (Logger)", "Logger")],
    ]);

    const stateFilter = select([
      ["", l("Tất cả trạng thái", "All health states")],
      ["NEEDS_ATTENTION", l("Cần chú ý", "Needs attention")],
      ["OBSERVABLE", l("Có dữ liệu quan sát", "Observable")],
    ]);

    const tableBox = div("stack");

    function renderTable() {
      const filtered = rows.filter((r) => {
        if (typeFilter.value && r.type !== typeFilter.value) return false;
        if (stateFilter.value && r.state !== stateFilter.value) return false;
        return true;
      });

      tableBox.replaceChildren(
        table(
          [
            t("devices"),
            t("plants"),
            l("Loại", "Type"),
            t("status"),
            l("Dữ liệu mới / đã xác minh", "Fresh / verified channels"),
            l("Cảnh báo / công việc mở", "Open alerts / work"),
            l("Firmware ghi nhận", "Reported firmware"),
            l("Cập nhật cuối", "Last seen"),
            "",
          ],
          filtered.map((row) => [
            btn(row.name, () => deviceDetail(row.device_id)),
            siteName(row.site_id),
            badge(row.type, "gray"),
            div("stack",
              badge(row.state === "OBSERVABLE" ? l("Bình thường", "Observable") : l("Cần chú ý", "Needs attention"), row.state === "OBSERVABLE" ? "good" : "warn"),
              ...row.reasons.map((reason) => e("small", reasons[reason] || reason))
            ),
            `${row.fresh_channels} / ${row.verified_channels}`,
            `${row.open_incidents} / ${row.open_work_orders}`,
            row.firmware || l("Chưa biết", "Unknown"),
            date(row.last_seen),
            operator() ? btn(l("+ Lập phiếu", "+ Work order"), () => newJob(() => go("incidents", "", "jobs"), row.site_id, row.device_id)) : "—",
          ])
        )
      );

      if (!filtered.length) {
        tableBox.append(p(l("Không có thiết bị phù hợp với bộ lọc.", "No devices match this filter.")));
      }
    }

    typeFilter.onchange = renderTable;
    stateFilter.onchange = renderTable;
    renderTable();

    return div("stack maintenance-workspace-root",
      await kpiHeader(summaryResult),
      div("row between",
        div("row",
          field(l("Loại thiết bị", "Device type"), typeFilter),
          field(t("status"), stateFilter)
        ),
        btn(l("Mở danh sách phiếu công tác", "Open work orders"), () => go("incidents", "", "jobs"), "primary")
      ),
      card(l("Kết nối, dữ liệu và công việc", "Connectivity, measurements and work"),
        notice(
          "Trạng thái dựa trên kết nối thực tế, độ mới dữ liệu và cảnh báo từ SQLite store. Chưa có kết luận sức khỏe điện hoặc chứng nhận thiết bị khi thiếu dữ liệu xác minh.",
          "Status reflects active connectivity, data freshness and alarms from the SQLite store. Electrical health certification is unavailable without verified evidence."
        ),
        tableBox
      ),
      div("grid three",
        card(l("Phiếu công tác O&M", "Work orders"),
          p(l("Quản lý phiếu giao việc, checklist kiểm tra hiện trường, ghi thời gian và duyệt 4-eyes.", "Manage work orders, field checklists, time logging and 4-eyes review.")),
          btn(l("Xem phiếu công tác", "View work orders"), () => go("incidents", "", "jobs"))
        ),
        card(l("Kế hoạch định kỳ & Lịch", "Preventive plans & Calendar"),
          p(l("Thiết lập chu kỳ bảo trì phòng ngừa (vệ sinh tấm pin, siết ốc, đo cách điện) và xem lịch 90 ngày.", "Configure preventive maintenance intervals (panel cleaning, torque check, insulation test) and 90-day calendar.")),
          btn(l("Quản lý kế hoạch", "Manage plans"), () => go("incidents", "", "plans"))
        ),
        card(l("Firmware & Nâng cấp OTA", "Firmware & OTA"),
          p(l("Kiểm soát phiên bản phần mềm nhúng, kiểm tra điều kiện an toàn pre-flight và hàng đợi OTA.", "Audit embedded firmware versions, pre-flight safety gates and OTA staging queue.")),
          btn(l("Mở Firmware & OTA", "Open Firmware & OTA"), () => go("incidents", "", "firmware"))
        )
      )
    );
  }

  // 2. SUBTAB: WORK ORDERS & EXECUTION
  async function jobs() {
    let selected = state.tab || "", offset = 0, activeTab = "execution", openEpoch = 0;
    const search = input("search");
    search.placeholder = l("Tìm theo tên hoặc mô tả...", "Search by title or description...");
    search.maxLength = 200;

    const status = select([["", t("all")], ...statuses()]);
    const late = select([["", l("Tất cả thời hạn", "All deadlines")], ["yes", l("Chỉ quá hạn", "Overdue only")]]);
    const list = div("record-list"), detail = div("stack"), actions = div("stack"), pager = div("toolbar");

    async function reload() {
      const query = scope();
      query.set("offset", offset);
      query.set("limit", 20);
      if (search.value.trim()) query.set("q", search.value.trim());
      if (status.value) query.set("status", status.value);
      if (late.value) query.set("overdue", "true");

      const page = await api("/maintenance/work-orders?" + query);
      if (!selected) selected = page.items[0]?.id || "";

      list.replaceChildren(...page.items.map((row) => {
        const item = btn("", async () => {
          selected = row.id;
          activeTab = "execution";
          await open(row.id);
        }, "record-button");
        item.dataset.recordId = row.id;

        item.append(
          e("strong", row.title),
          p(siteName(row.site_id)),
          div("row", badge(statusLabel(row.status)), badge(stages()[row.execution_state])),
          p(l("Checklist: ", "Checklist: ") + `${row.checklist_completed}/${row.checklist_total}`),
          p(l("Người phụ trách: ", "Assignee: ") + (row.assigned_to || "—")),
          p(l("Hạn hoàn tất: ", "Due: ") + (row.due_date || "—"))
        );
        if (row.overdue) item.append(badge(l("Quá hạn", "Overdue"), "bad"));
        return item;
      }));

      if (!page.items.length) {
        list.append(p(l("Không có công việc phù hợp với bộ lọc.", "No work matches these filters.")));
      }

      const previous = btn(l("Trước", "Previous"), async () => {
        offset = Math.max(0, offset - 20);
        selected = "";
        await reload();
      });
      const next = btn(l("Sau", "Next"), async () => {
        offset += 20;
        selected = "";
        await reload();
      });
      previous.disabled = offset === 0;
      next.disabled = offset + 20 >= page.total;
      pager.replaceChildren(previous, p(`${page.total ? offset + 1 : 0}–${Math.min(offset + 20, page.total)} / ${page.total}`), next);

      if (selected) await open(selected);
      else {
        detail.replaceChildren(p(l("Chọn công việc để xem chi tiết.", "Select work to see its details.")));
        actions.replaceChildren();
      }
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
        node.classList.toggle("selected", active);
        node.setAttribute("aria-pressed", String(active));
      });

      const content = div("stack");
      const draw = async () => {
        content.replaceChildren(tabs([
          ["execution", l("Thực hiện & Checklist", "Execution & Checklist")],
          ["time", l("Ghi thời gian", "Time entries")],
          ["history", l("Lịch sử kiểm toán", "Audit history")],
        ], activeTab, async (key) => { activeTab = key; await draw(); }));

        if (activeTab === "execution") content.append(executionPanel(data, changed));
        if (activeTab === "time") content.append(timePanel(data, changed));
        if (activeTab === "history") {
          const box = div("stack");
          content.append(box);
          let cursor = 0;
          const more = btn(l("Xem thêm lịch sử", "Load more history"), loadHistory);

          async function loadHistory() {
            const histPage = await api(`/maintenance/work-orders/${row.id}/events?after=${cursor}`);
            cursor = histPage.next_cursor;
            box.append(...histPage.items.map((item) => card(eventLabel(item.kind),
              p(date(item.at) + " · " + item.actor),
              p(item.note),
              ui.raw(l("Bằng chứng đã lưu", "Saved evidence"), item.details))));
            more.disabled = histPage.items.length < 50;
          }

          box.append(p(l("Các lần thay đổi trạng thái", "Status changes")),
            table([l("Lúc", "At"), l("Người thực hiện", "Actor"), t("status"), l("Ghi chú", "Note")],
              row.timeline.filter((item) => !item.kind).map((item) => [date(item.at), item.actor, statusLabel(item.status), item.note])));

          await loadHistory();
          content.append(more);
        }
      };

      detail.replaceChildren(
        card(row.title,
          div("row",
            badge(statusLabel(row.status)),
            badge(stages()[plan?.state || "UNPLANNED"]),
            badge(severityLabel(row.severity || "medium"), row.severity === "critical" ? "bad" : row.severity === "high" ? "warn" : "gray")
          ),
          p(row.description || "—"),
          content
        )
      );

      actions.replaceChildren(
        card(l("Thông tin công việc", "Work details"),
          fact(t("plants"), siteName(row.site_id)),
          fact(l("Mức độ", "Severity"), severityLabel(row.severity || "medium")),
          fact(l("Hạn hoàn tất", "Due date"), row.due_date || "—"),
          fact(l("Người phụ trách", "Assignee"), row.assigned_to || "—"),
          fact(l("Phiên bản phiếu", "Work revision"), row.revision),
          fact(l("Thời gian đã ghi", "Recorded time"), number(data.total_minutes, 0) + l(" phút", " min")),
          card(l("Điều kiện hoàn tất (Safety Gate)", "Completion requirements"),
            data.completion.ready
              ? p(l("Đủ checklist và thời gian thực hiện.", "Checklist and work time are recorded."))
              : div("stack", ...data.completion.reasons.map((reason) => p(reasonLabel(reason, plan)))),
            p(plan?.review?.decision === "approve"
              ? l("Đã có kiểm tra độc lập hợp lệ.", "Independent review is recorded.")
              : l("Cần kỹ thuật viên khác kiểm tra độc lập trước khi hoàn tất.", "Another technician must review before completion.")
            ),
            ...(operator() ? [btn(l("Cập nhật trạng thái / phân công", "Update status / assignment"), () => editStatus(data, changed))] : [])
          )
        )
      );

      if (row.incident_id) {
        actions.append(btn(l("Mở cảnh báo liên quan", "Open linked incident"), () => go("incidents", row.incident_id, "main")));
      }
      if (row.device_id) {
        actions.append(btn(l("Mở thiết bị liên quan", "Open device"), () => deviceDetail(row.device_id)));
      }

      await draw();
    }

    const filter = form(async () => {
      selected = "";
      offset = 0;
      await reload();
    }, l("Lọc công việc", "Filter work"));

    filter.finish(div("form-grid",
      field(l("Tìm công việc", "Search work"), search),
      field(t("status"), status),
      field(l("Thời hạn", "Deadline"), late)
    ));

    const summaryResult = await api("/maintenance/summary?" + scope());

    const root = div("stack maintenance-workspace-root",
      await kpiHeader(summaryResult),
      div("row between",
        e("h2", l("Phiếu công tác O&M", "Maintenance Work Orders")),
        operator() ? btn(l("+ Tạo phiếu bảo trì", "+ Create work order"), () => newJob(async (row) => {
          selected = row.id;
          await reload();
        }), "primary") : null
      ),
      filter,
      div("workbench-layout",
        card(l("Danh sách công việc", "Work list"), list, pager),
        detail,
        actions
      )
    );

    await reload();
    return root;
  }

  function newJob(done, initialSiteId = "", initialDeviceId = "") {
    const site = siteSelect(initialSiteId || state.site);
    const title = requiredInput("text");
    const description = area("", false);
    const device = select([["", l("Toàn nhà máy", "Whole plant")]]);
    const severity = select(severities(), "medium");
    const due = input("date");
    title.maxLength = 200;

    function syncDevices() {
      const devRows = (state.fleet.devices || []).filter((row) => row.site_id === site.value);
      device.replaceChildren(...select([
        ["", l("Toàn nhà máy", "Whole plant")],
        ...devRows.map((row) => [row.id, row.name || row.vendor_id]),
      ]).children);
      if (initialDeviceId && devRows.some((d) => d.id === initialDeviceId)) {
        device.value = initialDeviceId;
      }
    }

    site.onchange = syncDevices;
    syncDevices();

    const f = form(async () => {
      const row = await api("/records/work_order", {
        site_id: site.value,
        title: title.value.trim(),
        description: description.value,
        device_id: device.value || null,
        severity: severity.value,
        due_date: due.value || null,
      });
      closeDialog();
      await done(row);
    }, l("Tạo phiếu", "Create work order"));

    f.finish(
      field(t("plants"), site),
      field(l("Tên công việc", "Work title"), title),
      field(t("devices"), device),
      field(l("Mức độ nghiêm trọng", "Severity"), severity),
      field(l("Mô tả công việc", "Work description"), description),
      field(l("Hạn hoàn tất", "Due date"), due)
    );
    showDialog(l("Phiếu bảo trì mới", "New work order"), f);
  }

  function executionPanel(data, changed) {
    const row = data.work_order, plan = data.execution;
    const root = div("stack");

    if (technical() && editable(row)) {
      root.append(btn(plan ? l("Chỉnh kế hoạch / checklist", "Edit plan / checklist") : l("Lập kế hoạch thực hiện", "Plan this work"),
        () => editPlan(data, changed), "primary"));
    }

    if (!plan) {
      root.append(p(l("Chưa có kế hoạch thực hiện. Kỹ thuật viên lập checklist trước khi ghi kết quả.", "No execution plan yet. A technician must define the checklist before recording results.")));
      return root;
    }

    root.append(card(l("Kế hoạch thực hiện", "Execution plan"),
      fact(l("Dự kiến bắt đầu", "Planned start"), date(plan.planned_start)),
      fact(l("Dự kiến kết thúc", "Planned end"), date(plan.planned_end)),
      fact(l("Nhóm thực hiện", "Team"), plan.team.join(", ") || "—"),
      p(plan.safety_note)
    ));

    for (const step of plan.steps) {
      const result = plan.results[step.id];
      root.append(card(step.title,
        div("row",
          badge(outcomeLabel(result?.outcome || "pending"), result?.outcome === "pass" ? "good" : result?.outcome === "fail" ? "bad" : "warn"),
          step.required ? e("small", l("Bắt buộc", "Required")) : e("small", l("Tùy chọn", "Optional"))
        ),
        p(step.instructions),
        result ? p(result.note) : null,
        result ? p(date(result.at) + " · " + result.actor) : null,
        result?.document_ids?.length ? p(l("Tài liệu: ", "Documents: ") + result.document_ids.map((id) => data.documents.find((doc) => doc.id === id)?.name || id).join(", ")) : null,
        technical() && editable(row) ? btn(l("Ghi kết quả", "Record result"), () => recordStep(data, step, changed)) : null
      ));
    }

    if (plan.review) {
      root.append(card(l("Kết quả kiểm tra độc lập", "Independent review"),
        p(plan.review.decision === "approve" ? l("Chấp thuận", "Approved") : l("Yêu cầu bổ sung", "Changes requested")),
        p(plan.review.note),
        p(date(plan.review.at) + " · " + plan.review.reviewer)
      ));
    }

    if (technical() && editable(row) && plan.state !== "AWAITING_REVIEW" && plan.state !== "APPROVED") {
      const submit = btn(l("Gửi kiểm tra độc lập (4-eyes)", "Submit for independent review"), () => noteAction(
        l("Gửi kiểm tra", "Submit for review"),
        (note) => changed(`/maintenance/work-orders/${row.id}/submit`, { revision: row.revision, note })
      ), "primary");
      submit.disabled = !data.completion.ready;
      root.append(submit);
    }

    const ownWork = plan.submitted_by === state.me.user.id ||
      Object.values(plan.results).some((result) => result.actor === state.me.user.id) ||
      data.time_entries.some((entry) => !entry.voided && entry.actor === state.me.user.id);

    if (technical() && editable(row) && plan.state === "AWAITING_REVIEW") {
      if (ownWork) {
        root.append(notice(
          "Theo nguyên tắc 4-eyes: Bạn đã tham gia thực hiện phiếu này nên không thể tự phê duyệt. Một kỹ thuật viên khác phải kiểm tra độc lập.",
          "4-eyes principle: You participated in this work order and cannot approve your own work. Another technician must independently review.",
          true
        ));
      } else {
        root.append(div("row",
          ...[["approve", l("Duyệt hoàn tất", "Approve completion")], ["return", l("Yêu cầu bổ sung", "Request changes")]].map(([decision, label]) =>
            btn(label, () => noteAction(label, (note) => changed(`/maintenance/work-orders/${row.id}/review`, { revision: row.revision, decision, note })), decision === "approve" ? "primary" : "")
          )
        ));
      }
    }

    return root;
  }

  function editPlan(data, changed) {
    const row = data.work_order, plan = data.execution;
    const start = input("datetime-local", localInputValue(plan?.planned_start));
    const end = input("datetime-local", localInputValue(plan?.planned_end));
    const safety = area(plan?.safety_note || "");
    const note = area();
    const list = div("stack");
    const team = [];
    let steps = [];

    const teamPanel = div("form-grid", ...data.assignees.map((person) => {
      const control = input("checkbox");
      control.checked = plan?.team.includes(person.id) || false;
      team.push({ id: person.id, control });
      return field(person.id + " · " + t(person.role), control);
    }));

    function addStep(value = {}) {
      const title = requiredInput("text", value.title || "");
      const instructions = area(value.instructions || "", false);
      const required = input("checkbox");
      title.maxLength = 300;
      required.checked = value.required !== false;
      const item = { id: value.id || crypto.randomUUID().replaceAll("-", ""), title, instructions, required };
      const panel = card(l("Bước công việc", "Work step"),
        field(l("Tên bước", "Step title"), title),
        field(l("Hướng dẫn thao tác", "Instructions"), instructions),
        field(l("Bắt buộc hoàn tất", "Required for completion"), required),
        btn(l("Bỏ bước", "Remove step"), () => {
          steps = steps.filter((s) => s !== item);
          panel.remove();
        })
      );
      steps.push(item);
      list.append(panel);
    }

    (plan?.steps || [{ title: l("Kiểm tra mắt thường và ngoại quan", "Visual and cosmetic inspection"), instructions: l("Kiểm tra vết nứt, bám bẩn hoặc dấu hiệu phóng điện.", "Inspect for cracks, dirt or arc marks.") }]).forEach(addStep);

    const f = form(async () => {
      await changed(`/maintenance/work-orders/${row.id}/plan`, {
        revision: row.revision,
        planned_start: start.value ? new Date(start.value).toISOString() : null,
        planned_end: end.value ? new Date(end.value).toISOString() : null,
        safety_note: safety.value,
        note: note.value,
        team: team.filter((person) => person.control.checked).map((person) => person.id),
        steps: steps.map((step) => ({
          id: step.id,
          title: step.title.value.trim(),
          instructions: step.instructions.value,
          required: step.required.checked,
        })),
      });
    });

    f.finish(
      timeHint(),
      div("form-grid", field(l("Bắt đầu dự kiến", "Planned start"), start), field(l("Kết thúc dự kiến", "Planned end"), end)),
      card(l("Nhóm thực hiện", "Work team"), teamPanel),
      field(l("Điều kiện và lưu ý an toàn", "Prerequisites and safety notes"), safety),
      list,
      btn(l("+ Thêm bước checklist", "+ Add checklist step"), () => { if (steps.length < 50) addStep(); }),
      field(l("Lý do lập / thay đổi kế hoạch", "Reason for this plan or change"), note),
      plan ? notice("Lưu kế hoạch mới sẽ yêu cầu ghi lại toàn bộ kết quả checklist và duyệt lại. Bằng chứng cũ vẫn được lưu trong lịch sử.",
        "Saving a new plan requires fresh checklist results and review. Previous evidence remains in history.", true) : null
    );
    showDialog(l("Kế hoạch thực hiện", "Execution plan"), f);
  }

  function recordStep(data, step, changed) {
    const row = data.work_order, result = data.execution.results[step.id];
    const outcome = select(outcomes(), result?.outcome || "pending");
    const note = area(result?.note || "");
    const documents = [];

    const proof = div("stack", ...data.documents.map((doc) => {
      const checkbox = input("checkbox");
      checkbox.checked = result?.document_ids?.includes(doc.id) || false;
      documents.push({ id: doc.id, checkbox });
      return field(doc.name, checkbox);
    }));

    const f = form(async () => changed(`/maintenance/work-orders/${row.id}/step`, {
      revision: row.revision,
      step_id: step.id,
      outcome: outcome.value,
      note: note.value,
      document_ids: documents.filter((doc) => doc.checkbox.checked).map((doc) => doc.id),
    }));

    f.finish(
      p(step.instructions),
      field(l("Kết quả", "Result"), outcome),
      field(l("Kết quả đo / bằng chứng / lý do", "Measurements / evidence / reason"), note),
      card(l("Tài liệu liên quan", "Related documents"), proof, data.documents.length ? null : p(l("Chưa có hồ sơ tài liệu tại nhà máy.", "No document records for this plant.")))
    );
    showDialog(step.title, f);
  }

  function timePanel(data, changed) {
    const row = data.work_order;
    const root = card(l("Thời gian thực hiện", "Work time"),
      fact(l("Tổng thời gian hợp lệ", "Total active time"), number(data.total_minutes, 0) + l(" phút", " min")),
      table(
        [l("Bắt đầu", "Start"), l("Kết thúc", "End"), l("Người thực hiện", "Actor"), l("Công việc", "Activity"), t("status"), ""],
        data.time_entries.map((entry) => [
          date(entry.start),
          date(entry.end),
          entry.actor,
          entry.activity,
          entry.voided ? l("Đã hủy", "Voided") : l("Được tính", "Counted"),
          operator() && editable(row) && !entry.voided && entry.actor === state.me.user.id
            ? btn(l("Hủy ghi nhận", "Void entry"), () => noteAction(
                l("Lý do hủy ghi nhận", "Reason for voiding"),
                (note) => changed(`/maintenance/work-orders/${row.id}/time/${entry.id}/void`, { revision: row.revision, note })
              ))
            : "—",
        ])
      )
    );

    if (operator() && editable(row)) {
      root.append(btn(l("+ Ghi thời gian", "+ Record work time"), () => {
        const start = requiredInput("datetime-local");
        const end = requiredInput("datetime-local");
        const activity = area();

        const f = form(async () => changed(`/maintenance/work-orders/${row.id}/time`, {
          revision: row.revision,
          start: new Date(start.value).toISOString(),
          end: new Date(end.value).toISOString(),
          activity: activity.value,
        }));

        f.finish(
          timeHint(),
          field(l("Bắt đầu", "Start"), start),
          field(l("Kết thúc", "End"), end),
          field(l("Công việc đã thực hiện", "Work performed"), activity),
          p(l("Mỗi lần ghi tối đa 24 giờ; thời gian của một người không được trùng nhau giữa các phiếu.", "Each entry may span up to 24 hours; a person's time cannot overlap across work orders."))
        );
        showDialog(l("Ghi thời gian thực hiện", "Record work time"), f);
      }, "primary"));
    }
    return root;
  }

  function editStatus(data, changed) {
    const row = data.work_order;
    const transitions = {
      open: ["open", "acknowledged", "in_progress"],
      acknowledged: ["acknowledged", "in_progress", "resolved"],
      in_progress: ["in_progress", "resolved"],
      resolved: ["resolved", "closed", "open"],
      closed: ["closed", "open"],
    };
    const status = select(statuses().filter(([key]) => transitions[row.status]?.includes(key)), row.status);
    const assignee = select([["", l("Chưa phân công", "Unassigned")], ...data.assignees.map((person) => [person.id, person.id])], row.assigned_to);
    const note = area();

    const f = form(async () => changed(`/records/work_order/${row.id}`, {
      revision: row.revision,
      status: status.value,
      assigned_to: assignee.value,
      note: note.value,
    }));

    f.finish(
      field(t("status"), status),
      field(l("Người phụ trách", "Assignee"), assignee),
      field(l("Ghi chú thay đổi", "Change note"), note),
      p(l("Hoàn tất / đóng phiếu cần checklist đạt, thời gian thực hiện và kiểm tra độc lập còn hợp lệ. Mở lại sẽ yêu cầu duyệt lại.",
        "Resolving or closing requires completed checks, work time and a valid independent review. Reopening requires another review."))
    );
    showDialog(l("Trạng thái và phân công", "Status and assignment"), f);
  }

  function noteAction(title, save) {
    const note = area();
    const f = form(async () => save(note.value));
    f.finish(field(l("Ghi chú", "Note"), note));
    showDialog(title, f);
  }

  function eventLabel(kind) {
    return ({
      maintenance_plan_saved: l("Lưu kế hoạch", "Plan saved"),
      maintenance_step_recorded: l("Ghi kết quả checklist", "Checklist result recorded"),
      maintenance_time_recorded: l("Ghi thời gian", "Time recorded"),
      maintenance_time_voided: l("Hủy ghi nhận thời gian", "Time entry voided"),
      maintenance_submitted: l("Gửi kiểm tra", "Submitted for review"),
      maintenance_reviewed: l("Kiểm tra độc lập", "Independent review"),
      maintenance_plan_triggered: l("Kích hoạt phiếu từ kế hoạch", "Work order triggered from plan"),
      firmware_upgrade_staged: l("Xếp hàng nâng cấp Firmware", "Firmware upgrade staged"),
    })[kind] || kind;
  }

  // 3. SUBTAB: PREVENTIVE PLANS & SERVICE CALENDAR
  async function plans() {
    let mode = "plans"; // "plans" or "calendar"
    const root = div("stack maintenance-workspace-root");

    const [summaryResult, plansResult] = await Promise.all([
      api("/maintenance/summary?" + scope()),
      api("/maintenance/plans?" + scope()),
    ]);

    root.append(await kpiHeader(summaryResult));

    const contentBox = div("stack");

    const subNav = div("row between",
      tabs([
        ["plans", l("Kế hoạch bảo trì phòng ngừa", "Preventive plans")],
        ["calendar", l("Lịch dịch vụ 90 ngày", "90-day service calendar")],
      ], mode, async (key) => {
        mode = key;
        await drawContent();
      }),
      operator() ? btn(l("+ Thêm kế hoạch định kỳ", "+ New preventive plan"), () => newPlan(async () => {
        await plans();
      }), "primary") : null
    );

    root.append(subNav, contentBox);

    async function drawContent() {
      if (mode === "plans") {
        const rows = plansResult.items;
        const tbl = table(
          [
            l("Tên kế hoạch", "Plan title"),
            t("plants"),
            l("Thiết bị", "Equipment"),
            l("Chu kỳ (ngày)", "Interval (days)"),
            l("Hạn kế tiếp", "Next due"),
            l("Mức độ", "Severity"),
            l("Phiếu đã tạo", "Orders created"),
            t("status"),
            "",
          ],
          rows.map((plan) => [
            div("stack",
              e("strong", plan.name),
              e("small", plan.instructions.slice(0, 80) + (plan.instructions.length > 80 ? "…" : ""))
            ),
            siteName(plan.site_id),
            plan.device ? `${plan.device.name} (${plan.device.vendor || "—"})` : l("Toàn nhà máy", "Whole plant"),
            `${plan.interval_days} ` + l("ngày", "days"),
            div("row",
              plan.next_due,
              plan.overdue ? badge(l("Quá hạn", "Overdue"), "bad") : plan.days_until_due <= 7 ? badge(`${plan.days_until_due}d`, "warn") : null
            ),
            badge(severityLabel(plan.severity), plan.severity === "critical" ? "bad" : plan.severity === "high" ? "warn" : "gray"),
            number(plan.work_orders_generated, 0),
            badge(plan.enabled ? l("Đang chạy", "Enabled") : l("Tạm dừng", "Paused"), plan.enabled ? "good" : "gray"),
            div("row",
              operator() ? btn(l("Tạo phiếu ngay", "Trigger now"), async () => {
                await api(`/maintenance/plans/${plan.id}/trigger`, {});
                go("incidents", "", "jobs");
              }) : null,
              operator() ? btn(plan.enabled ? l("Tạm dừng", "Pause") : l("Kích hoạt", "Enable"), async () => {
                await api(`/workbench/maintenance_plan`, {
                  id: plan.id,
                  revision: plan.revision,
                  data: {
                    site_id: plan.site_id,
                    device_id: plan.device_id,
                    name: plan.name,
                    interval_days: plan.interval_days,
                    next_due: plan.next_due,
                    instructions: plan.instructions,
                    severity: plan.severity,
                    enabled: !plan.enabled,
                  },
                });
                const refreshed = await api("/maintenance/plans?" + scope());
                plansResult.items = refreshed.items;
                await drawContent();
              }) : null
            ),
          ])
        );

        contentBox.replaceChildren(
          card(l("Danh mục kế hoạch bảo trì phòng ngừa định kỳ", "Preventive Maintenance Plans"),
            notice("Kế hoạch định kỳ được kiểm tra tự động bởi Controller runtime. Khi đến hạn, hệ thống tự động sinh phiếu công tác với source: MAINTENANCE_PLAN.",
              "Preventive schedules are polled automatically by the controller runtime. When due, work orders are automatically created with source: MAINTENANCE_PLAN."),
            rows.length ? tbl : p(l("Chưa có kế hoạch bảo trì định kỳ nào trong phạm vi này.", "No preventive maintenance plans in this scope."))
          )
        );
      } else {
        contentBox.replaceChildren(await calendarSection());
      }
    }

    await drawContent();
    return root;
  }

  function newPlan(done) {
    const site = siteSelect(state.site);
    const name = requiredInput("text");
    const interval = requiredInput("number", "90");
    interval.min = 1;
    interval.max = 3650;
    const nextDue = requiredInput("date", new Date().toISOString().slice(0, 10));
    const device = select([["", l("Toàn nhà máy", "Whole plant")]]);
    const severity = select(severities(), "medium");
    const instructions = area("", true);
    name.maxLength = 150;

    function syncDevices() {
      const devRows = (state.fleet.devices || []).filter((row) => row.site_id === site.value);
      device.replaceChildren(...select([
        ["", l("Toàn nhà máy", "Whole plant")],
        ...devRows.map((row) => [row.id, row.name || row.vendor_id]),
      ]).children);
    }
    site.onchange = syncDevices;
    syncDevices();

    const f = form(async () => {
      await api("/workbench/maintenance_plan", {
        data: {
          site_id: site.value,
          device_id: device.value || null,
          name: name.value.trim(),
          interval_days: Number(interval.value),
          next_due: nextDue.value,
          severity: severity.value,
          instructions: instructions.value,
          enabled: true,
        },
      });
      closeDialog();
      await done();
    }, l("Tạo kế hoạch", "Create plan"));

    f.finish(
      field(t("plants"), site),
      field(l("Tên kế hoạch bảo trì", "Plan name"), name),
      field(t("devices"), device),
      div("form-grid",
        field(l("Chu kỳ lặp lại (ngày)", "Interval days"), interval),
        field(l("Hạn thực hiện đầu tiên", "First due date"), nextDue)
      ),
      field(l("Mức độ nghiêm trọng", "Severity"), severity),
      field(l("Quy trình / hướng dẫn thực hiện", "Standard operating instructions"), instructions)
    );

    showDialog(l("Kế hoạch bảo trì phòng ngừa mới", "New preventive maintenance plan"), f);
  }

  async function calendarSection() {
    const today = new Date(), later = new Date(today.getTime() + 30 * 86400000);
    const start = requiredInput("date", localInputValue(today).slice(0, 10));
    const end = requiredInput("date", localInputValue(later).slice(0, 10));
    const output = div("stack");

    async function draw() {
      const query = scope();
      query.set("start", start.value);
      query.set("end", end.value);
      const result = await api("/maintenance/calendar?" + query);

      output.replaceChildren(
        table(
          [
            l("Ngày tại nhà máy", "Plant local date"),
            l("Công việc / kế hoạch", "Work / plan"),
            t("plants"),
            l("Loại", "Type"),
            t("status"),
            "",
          ],
          result.items.map((row) => [
            row.date,
            row.title,
            siteName(row.site_id),
            row.kind === "recurrence" ? badge(l("Kỳ dự kiến", "Projected occurrence"), "blue") : badge(l("Phiếu đã lập lịch", "Scheduled work"), "gray"),
            row.kind === "recurrence" ? l("Dự kiến · chưa tạo phiếu", "Projection · not a work order") : statusLabel(row.status),
            btn(l("Mở", "Open"), () => go("incidents", row.kind === "work_order" ? row.id : "", row.kind === "work_order" ? "jobs" : "plans")),
          ])
        )
      );

      if (!result.items.length) {
        output.append(p(l("Không có lịch bảo trì nào trong khoảng thời gian đã chọn.", "No planned work in this date range.")));
      }
    }

    const f = form(draw, l("Xem lịch", "Show calendar"));
    f.finish(div("form-grid", field(l("Từ ngày", "From date"), start), field(l("Đến trước ngày", "Until date (exclusive)"), end)));
    await draw();

    return card(l("Lịch dịch vụ & Bảo trì (Tối đa 93 ngày)", "Service Calendar (Up to 93 days)"),
      notice(
        "Kỳ dự kiến dựa trên các kế hoạch phòng ngừa định kỳ; phiếu công tác thực tế và thời gian thao tác tại hiện trường được hiển thị riêng biệt.",
        "Projected occurrences derive from recurring plans; actual work orders and their execution times are shown separately."
      ),
      f,
      output
    );
  }

  // 4. SUBTAB: FIRMWARE COMPLIANCE & SAFE OTA STAGING
  async function firmware() {
    const root = div("stack maintenance-workspace-root");

    const [summaryResult, fwData] = await Promise.all([
      api("/maintenance/summary?" + scope()),
      api("/maintenance/firmware?" + scope()),
    ]);

    root.append(await kpiHeader(summaryResult));

    const preflight = card(
      l("Điều kiện An Toàn Trước Khi Nâng Cấp Firmware (Pre-flight Prerequisites)", "Pre-flight Safety Prerequisites"),
      notice(
        "Kiểm soát nghiêm ngặt nâng cấp OTA nhằm chống bricking và gián đoạn vận hành. Chỉ thực hiện khi có checksum SHA-256 đối chiếu và đạt đầy đủ 4 điều kiện an toàn.",
        "Strict OTA gating prevents equipment bricking and outage. Only executes with verified SHA-256 checksum and all 4 pre-flight conditions met."
      ),
      div("grid four maintenance-preflight-box",
        div("stack", e("strong", l("1. Kết nối thiết bị", "1. Connectivity")), badge(l("Thiết bị Online & Fresh", "Device online"), "good")),
        div("stack", e("strong", l("2. Cảnh báo hoạt động", "2. Active Alarms")), badge(l("Không có lỗi nguy cấp", "No critical alarms"), "good")),
        div("stack", e("strong", l("3. Dung lượng pin dự phòng", "3. Auxiliary / Battery")), badge(l("Tối thiểu SOC >= 30%", "Min SOC >= 30%"), "good")),
        div("stack", e("strong", l("4. Tính toàn vẹn tệp", "4. Binary Checksum")), badge(l("Mã băm SHA-256 64-hex", "SHA-256 64-hex"), "good"))
      )
    );
    root.append(preflight);

    const header = div("row between",
      e("h3", l("Danh mục Firmware & Hàng đợi OTA", "Firmware Inventory & OTA Queue")),
      technical() ? btn(l("+ Yêu cầu nâng cấp Firmware", "+ Stage OTA Upgrade"), () => stageFirmwareDialog(async () => {
        await firmware();
      }), "primary") : null
    );
    root.append(header);

    // Section: Device Firmware Inventory
    const invRows = fwData.inventory;
    const invTable = table(
      [
        t("devices"),
        t("plants"),
        l("Hãng / Model", "Vendor / Model"),
        l("Serial Number", "Serial"),
        l("Firmware hiện tại", "Current FW"),
        t("status"),
        l("Điều kiện Pre-flight", "Pre-flight"),
        "",
      ],
      invRows.map((d) => [
        btn(d.name, () => deviceDetail(d.device_id)),
        siteName(d.site_id),
        `${d.vendor} ${d.model || ""}`,
        d.serial || "—",
        badge(d.current_firmware, "gray"),
        badge(d.online ? l("Trực tuyến", "Online") : l("Mất kết nối", "Offline"), d.online ? "good" : "bad"),
        d.preflight.passed ? badge(l("Sẵn sàng OTA", "OTA Ready"), "good") : badge(l("Chưa đạt điều kiện", "Blocked"), "bad"),
        technical() ? btn(l("Nâng cấp OTA", "Stage OTA"), () => stageFirmwareDialog(async () => {
          await firmware();
        }, d.site_id, d.device_id)) : "—",
      ])
    );

    root.append(card(l("Danh mục phiên bản Firmware thiết bị", "Device Firmware Inventory"),
      invRows.length ? invTable : p(l("Chưa có thiết bị trong phạm vi này.", "No devices in this scope."))));

    // Section: Staged OTA Requests Queue (live from store!)
    const reqRows = fwData.requests;
    const reqTable = table(
      [
        l("Thiết bị", "Device"),
        l("Hãng", "Vendor"),
        l("Bản hiện tại", "Current FW"),
        l("Bản mục tiêu", "Target FW"),
        l("Mã băm SHA-256", "SHA-256"),
        l("Cửa sổ bảo trì", "Maintenance window"),
        t("status"),
        "",
      ],
      reqRows.map((req) => [
        btn(req.device_name || req.device_id, () => deviceDetail(req.device_id)),
        req.vendor,
        badge(req.current_firmware, "gray"),
        badge(req.target_version, "blue"),
        e("code", req.sha256.slice(0, 12) + "…"),
        date(req.maintenance_window),
        badge(req.state, req.state === "COMPLETED" ? "good" : req.state === "QUEUED_FOR_MAINTENANCE_WINDOW" ? "blue" : "warn"),
        btn(l("Xem chi tiết", "Details"), () => {
          showDialog(
            l("Chi tiết yêu cầu firmware", "Firmware request details"),
            div("stack",
              fact(l("Thiết bị", "Device"), req.device_name || req.device_id),
              fact(l("Phiên bản mục tiêu", "Target version"), req.target_version),
              fact(l("SHA-256 đầy đủ", "Full SHA-256"), req.sha256),
              fact(l("Tài liệu phát hành", "Release reference"), req.release_reference),
              fact(l("Cửa sổ bảo trì", "Maintenance window"), date(req.maintenance_window)),
              fact(l("Trạng thái", "Status"), req.state),
              p(req.notes || l("Không có ghi chú thêm.", "No additional notes."))
            )
          );
        }),
      ])
    );

    root.append(card(l("Hàng đợi nâng cấp Firmware (OTA Staging Queue)", "OTA Upgrade Queue"),
      notice("Hàng đợi OTA được lưu trữ an toàn trong SQLite store. Lệnh nâng cấp chỉ được nạp tới thiết bị trong cửa sổ bảo trì đã xác nhận.",
        "OTA requests are safely stored in the SQLite store. Upgrade commands are only delivered to equipment during the verified maintenance window."),
      reqRows.length ? reqTable : p(l("Chưa có yêu cầu nâng cấp firmware nào đang chờ xử lý.", "No pending firmware upgrade requests."))));

    return root;
  }

  function stageFirmwareDialog(done, initialSiteId = "", initialDeviceId = "") {
    const site = siteSelect(initialSiteId || state.site);
    const device = select([["", l("Chọn thiết bị...", "Select device...")]]);
    const targetVersion = requiredInput("text");
    targetVersion.placeholder = "e.g. v2.1.05";
    const sha256 = requiredInput("text");
    sha256.placeholder = "64 hex characters (e.g. e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855)";
    sha256.pattern = "^[a-fA-F0-9]{64}$";
    const releaseRef = requiredInput("text");
    releaseRef.placeholder = "e.g. REL-2026-Q3-PATCH-2";
    const windowDate = requiredInput("datetime-local", localInputValue(new Date(Date.now() + 86400000)));
    const notes = area("", false);

    function syncDevices() {
      const devRows = (state.fleet.devices || []).filter((row) => row.site_id === site.value);
      device.replaceChildren(...select([
        ["", l("Chọn thiết bị...", "Select device...")],
        ...devRows.map((row) => [row.id, `${row.name || row.vendor_id} (${row.identity?.firmware || "FW ?"})`]),
      ]).children);
      if (initialDeviceId && devRows.some((d) => d.id === initialDeviceId)) {
        device.value = initialDeviceId;
      }
    }
    site.onchange = syncDevices;
    syncDevices();

    const f = form(async () => {
      if (!device.value) {
        showDialog(l("Lỗi", "Error"), p(l("Vui lòng chọn thiết bị cần nâng cấp.", "Please select a target device.")));
        return;
      }
      await api("/api/maintenance/firmware/stage", {
        site_id: site.value,
        device_id: device.value,
        target_version: targetVersion.value.trim(),
        sha256: sha256.value.trim().toLowerCase(),
        release_reference: releaseRef.value.trim(),
        maintenance_window: new Date(windowDate.value).toISOString(),
        notes: notes.value,
      });
      closeDialog();
      await done();
    }, l("Xếp hàng nâng cấp", "Stage upgrade"));

    f.finish(
      timeHint(),
      field(t("plants"), site),
      field(t("devices"), device),
      div("form-grid",
        field(l("Phiên bản mục tiêu", "Target version"), targetVersion),
        field(l("Mã băm SHA-256 (64 ký tự)", "SHA-256 hash (64 hex)"), sha256)
      ),
      field(l("Tài liệu phát hành / URL gói binary", "Release reference"), releaseRef),
      field(l("Cửa sổ bảo trì cho phép", "Maintenance window"), windowDate),
      field(l("Ghi chú an toàn", "Safety notes"), notes),
      notice(
        "Chỉ tải lên gói firmware nhúng đã được kiểm toán và ký số bởi nhà sản xuất thiết bị gốc. Hệ thống sẽ lưu vết kiểm toán bất biến cho hành động này.",
        "Only stage verified embedded packages cryptographically signed by the OEM. The system immutably logs an audit trail event for this action."
      )
    );

    showDialog(l("Yêu cầu nâng cấp Firmware OTA", "Stage Firmware OTA Upgrade"), f);
  }

  // Alias for backward compatibility
  async function calendar() {
    return await calendarSection();
  }

  return { health, jobs, plans, firmware, calendar };
}

// Full page standalone renderer
export async function renderMaintenanceWorkspace(ctx) {
  const ws = createMaintenanceWorkspace(ctx);
  const activeTab = ctx.state.section || "health";
  if (activeTab === "jobs" || activeTab === "work_orders") return await ws.jobs();
  if (activeTab === "plans" || activeTab === "maintenance_plan") return await ws.plans();
  if (activeTab === "firmware" || activeTab === "firmware_request") return await ws.firmware();
  if (activeTab === "service-calendar") return await ws.calendar();
  return await ws.health();
}
