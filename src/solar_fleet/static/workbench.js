import { createDataWorkspace, ownsDataWorkspaceRoute } from "./data-workspace.js";
import { createIncidentCenter } from "./incident-center.js";
import { createSchedulePlanner } from "./schedule-planner.js";
import { createMaintenanceWorkspace } from "./maintenance-workspace.js";
import { l, t, date, number } from "./i18n.js";

export const maintenanceSections = new Set(["health", "jobs", "work_orders", "plans", "service-calendar", "maintenance_plan", "firmware", "firmware_request"]);

// Reuses the shell, authentication, dialogs and site scope of the main workspace.
export function createWorkbench(ui) {
  const dataWorkspace = createDataWorkspace(ui);
  const incidentCenter = createIncidentCenter(ui);
  const schedulePlanner = createSchedulePlanner(ui);
  const maintenanceWorkspace = createMaintenanceWorkspace(ui);
  const {
    state,
    e,
    add,
    div,
    p,
    btn,
    badge,
    card,
    raw,
    input,
    select,
    field,
    fact,
    notice,
    table,
    tabs,
    form,
    api,
    download,
    showDialog,
    closeDialog,
    refresh,
    render,
    admin,
    operator,
    siteName,
    sites,
    devices,
    siteSelect,
    deviceDetail,
    toast,
    go,
    scheduleForm,
  } = ui;
  const technical = () =>
    ["Installer", "Senior Engineer"].includes(state.me.user.role);
  const work = () => state.work || {};
  const rows = (kind) =>
    (work()[kind] || []).filter(
      (r) =>
        !r.archived &&
        (!state.site ||
          r.site_id === state.site ||
          r.site_ids?.includes(state.site)),
    );
  const deviceName = (id) =>
    state.fleet.devices.find((d) => d.id === id)?.name ||
    state.fleet.devices.find((d) => d.id === id)?.vendor_id ||
    id;
  const labels = () => ({
    customer: l("Khách hàng", "Customers"),
    topology: l("Sơ đồ thiết bị", "Device topology"),
    source_policy: l("Nguồn dữ liệu", "Data sources"),
    tariff: l("Biểu giá điện", "Electricity tariffs"),
    maintenance_plan: l("Kế hoạch bảo trì", "Maintenance plans"),
    network_profile: l("Logger & mạng", "Loggers & network"),
    firmware_request: l("Firmware", "Firmware"),
    notification_policy: l("Chính sách thông báo", "Notification policies"),
    document: l("Tài liệu", "Documents"),
  });
  const sections = (page) => page === "incidents" && maintenanceSections.has(state.section) ? [
    ["health", l("Sức khỏe hệ thống", "System health")],
    ["jobs", l("Phiếu công tác", "Work orders")],
    ["plans", l("Kế hoạch định kỳ", "Maintenance plans")],
    ["firmware", l("Firmware & OTA", "Firmware & OTA")],
  ] :
    ({
      overview: [
        ["main", l("Tình hình chung", "Fleet overview")],
        ["inbox", l("Việc cần chú ý", "Attention inbox")],
      ],
      plants: [
        ["main", l("Danh sách", "Directory")],
        ["map", l("Bản đồ vị trí", "Location map")],
        ["plant", l("Chi tiết nhà máy", "Plant workspace")],
        ["customer", labels().customer],
      ],
      devices: [
        ["main", l("Danh mục", "Inventory")],
        ["topology", labels().topology],
        ["network_profile", labels().network_profile],
        ["firmware_request", "Firmware"],
        ["document", labels().document],
      ],
      operations: [
        ["main", l("Điều khiển & lịch", "Control & schedules")],
        ["rollouts", l("Triển khai hàng loạt", "Fleet rollout")],
        ["schedule-plans", l("Biên dịch lịch", "Schedule compilation")],
        ["handover", l("Bàn giao", "Handover")],
      ],
      incidents: [
        ["main", l("Trung tâm cảnh báo", "Incident center")],
        ["records", l("Công việc & hồ sơ", "Work orders & records")],
        ["playbooks", l("Hướng dẫn xử lý", "Playbooks")],
        ["sla", l("Chính sách SLA", "SLA policies")],
      ],
      reports: [
        ["quality", l("Tổng quan dữ liệu", "Data overview")],
        ["mapping", l("Bản đồ dữ liệu", "Data mapping")],
        ["collection", l("Cấu hình thu thập", "Collection")],
        ["sync", l("Nhật ký đồng bộ", "Sync status")],
        ["main", l("Dữ liệu đo", "Measurements")],
        ["source_policy", labels().source_policy],
        ["cloud", l("Tài khoản cloud", "Cloud accounts")],
        ["agents", "Local Agent"],
        ["analytics", l("Báo cáo nhà máy", "Plant reports")],
        ["tariff", labels().tariff],
      ],
      settings: [
        ["main", l("Kết nối & tài khoản", "Connections & accounts")],
        ["agents", "Local Agent"],
        ["source_policy", labels().source_policy],
        ["notification_policy", labels().notification_policy],
      ],
    })[page] || [];
  function setSection(key) {
    return go(state.page, state.tab, key);
  }
  async function wrap(page, base) {
    // Data owns its tabs once; legacy /reports/mapping and /reports/sync links
    // resolve through the same route definition as /reports/main/<tab>.
    if (ownsDataWorkspaceRoute(state)) return await dataWorkspace.view();
    const options = sections(page),
      key = options.some(([k]) => k === state.section) ? state.section : "main";
    const accountPage =
      page === "settings" &&
      key === "main" &&
      ["", "connections", "vendors", "users", "site_config", "device_onboarding", "security", "evidence"].includes(state.tab);
    const root = div(
      "stack",
      accountPage ? null : tabs(options, key, setSection),
    );
    if (key === "main") {
      if (page === "devices" && technical())
        root.append(
          btn(
            l("+ Đăng ký thiết bị", "+ Register equipment"),
            assetForm,
            "primary",
          ),
        );
      if (page === "operations") root.append(await operationsTools());
      root.append(page === "incidents" ? await incidentCenter.center() : await base());
    } else if (page === "incidents" && key === "records") {
      root.append(await base());
    } else if (page === "incidents" && key === "playbooks") {
      root.append(await incidentCenter.books());
    } else if (page === "incidents" && key === "sla") {
      root.append(await incidentCenter.policies());
    } else if (page === "incidents" && key === "health") {
      root.append(await maintenanceWorkspace.health());
    } else if (page === "incidents" && (key === "jobs" || key === "work_orders")) {
      root.append(await maintenanceWorkspace.jobs());
    } else if (page === "incidents" && (key === "plans" || key === "maintenance_plan" || key === "service-calendar")) {
      root.append(await maintenanceWorkspace.plans());
    } else if (page === "incidents" && (key === "firmware" || key === "firmware_request")) {
      root.append(await maintenanceWorkspace.firmware());
    } else if (["quality", "mapping", "collection", "sync"].includes(key))
      root.append(await dataWorkspace.view(key));
    else if (labels()[key]) root.append(entityView(key));
    else if (key === "map") root.append(mapView());
    else if (key === "plant") root.append(await plantView());
    else if (key === "agents") root.append(agentsView());
    else if (key === "cloud")
      root.append(
        card(
          l("Tài khoản hãng dùng chung", "Shared vendor accounts"),
          p(
            l(
              "Quản lý tài khoản và kiểm tra kết nối tại trang thông tin truy cập.",
              "Manage accounts and connection checks in the access workspace.",
            ),
          ),
          btn(
            l("Mở tài khoản hãng", "Open vendor accounts"),
            () => go("settings", "connections"),
            "primary",
          ),
        ),
      );
    else if (key === "rollouts") root.append(rolloutsView());
    else if (key === "schedule-plans") root.append(await schedulePlanner.view());
    else if (key === "handover") root.append(await handoverView());
    else if (key === "analytics") root.append(await base());
    else if (key === "inbox") root.append(inboxView());
    return root;
  }
  function schemas() {
    const text = (key, vi, en, required = false) => ({
      key,
      label: l(vi, en),
      required,
    });
    const num = (key, vi, en, min, max, value = 0) => ({
      key,
      label: l(vi, en),
      type: "number",
      min,
      max,
      value,
    });
    const opt = (key, vi, en, choices) => ({ key, label: l(vi, en), choices });
    return {
      customer: [
        text("group", "Nhóm khách hàng", "Customer group"),
        text("contact", "Người liên hệ", "Contact person"),
        text("phone", "Điện thoại", "Phone"),
        { ...text("email", "Email", "Email"), type: "email" },
        text("notes", "Ghi chú", "Notes"),
      ],
      source_policy: [
        num(
          "max_age_seconds",
          "Dữ liệu mới tối đa (giây)",
          "Maximum reading age (seconds)",
          5,
          300,
          300,
        ),
        num(
          "max_skew_seconds",
          "Lệch thời gian tối đa (giây)",
          "Maximum timestamp skew (seconds)",
          0,
          60,
          5,
        ),
        num(
          "disagreement_percent",
          "Ngưỡng sai khác (%)",
          "Disagreement threshold (%)",
          0,
          100,
          5,
        ),
        text("notes", "Ghi chú", "Notes"),
      ],
      tariff: [
        opt("currency", "Đồng tiền", "Currency", ["VND", "USD", "EUR"]),
        {
          key: "effective_from",
          label: l("Áp dụng từ", "Effective from"),
          type: "date",
          value: new Date().toISOString().slice(0, 10),
          required: true,
        },
        num(
          "import_per_kwh",
          "Giá mua cơ bản / kWh",
          "Base import price / kWh",
          0,
          1000000,
        ),
        num(
          "export_per_kwh",
          "Giá bán / kWh",
          "Export price / kWh",
          0,
          1000000,
        ),
        {
          ...num(
            "carbon_kg_per_kwh",
            "Hệ số phát thải (kg/kWh)",
            "Emission factor (kg/kWh)",
            0,
            10,
          ),
          nullable: true,
          value: "",
        },
        text(
          "reference",
          "Nguồn biểu giá / hợp đồng",
          "Tariff source / contract",
          true,
        ),
      ],
      maintenance_plan: [
        {
          key: "device_id",
          label: l("Thiết bị (tùy chọn)", "Equipment (optional)"),
          device: true,
          nullable: true,
        },
        num(
          "interval_days",
          "Chu kỳ (ngày)",
          "Repeat interval (days)",
          1,
          3650,
          30,
        ),
        {
          key: "next_due",
          label: l("Ngày đến hạn", "Next due date"),
          type: "date",
          required: true,
          value: new Date().toISOString().slice(0, 10),
        },
        {
          ...text(
            "instructions",
            "Hướng dẫn công việc",
            "Work instructions",
            true,
          ),
          textarea: true,
        },
        opt("severity", "Ưu tiên", "Priority", [
          "critical",
          "high",
          "medium",
          "low",
        ]),
        {
          key: "enabled",
          label: l("Tạo phiếu khi đến hạn", "Create work order when due"),
          type: "checkbox",
          value: true,
        },
      ],
      network_profile: [
        {
          key: "device_id",
          label: l("Logger / thiết bị", "Logger / device"),
          device: true,
          required: true,
        },
        opt("connection", "Kết nối", "Connection", [
          "Ethernet",
          "Wi-Fi",
          "4G",
          "RS485",
          "Modbus TCP",
          "CAN",
        ]),
        text(
          "address",
          "Địa chỉ IP hoặc cổng tại máy",
          "IP address or local port",
        ),
        {
          ...num("port", "Cổng TCP", "TCP port", 1, 65535),
          value: "",
          nullable: true,
        },
        {
          ...num("slave_id", "Địa chỉ Modbus", "Modbus unit ID", 1, 247),
          value: "",
          nullable: true,
        },
        {
          ...opt(
            "baud",
            "Tốc độ RS485",
            "RS485 baud rate",
            [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200],
          ),
          numeric: true,
          value: 9600,
        },
        opt("parity", "Parity", "Parity", ["none", "even", "odd"]),
        { key: "dhcp", label: "DHCP", type: "checkbox", value: true },
        text("notes", "Ghi chú lắp đặt", "Installation notes"),
      ],
      firmware_request: [
        {
          key: "device_id",
          label: l("Thiết bị", "Device"),
          device: true,
          required: true,
        },
        text("target_version", "Phiên bản đích", "Target version", true),
        {
          ...text(
            "sha256",
            "SHA-256 của gói firmware",
            "Firmware package SHA-256",
            true,
          ),
          pattern: "[a-fA-F0-9]{64}",
        },
        text(
          "release_reference",
          "Tài liệu phát hành của hãng",
          "Vendor release reference",
          true,
        ),
        {
          key: "maintenance_window",
          label: l(
            "Giờ bảo trì (múi giờ máy đang dùng)",
            "Maintenance time (this computer timezone)",
          ),
          type: "datetime-local",
          required: true,
        },
        text(
          "notes",
          "Ghi chú / điều kiện triển khai",
          "Notes / deployment conditions",
        ),
      ],
      notification_policy: [
        opt("minimum_severity", "Mức cảnh báo tối thiểu", "Minimum severity", [
          "critical",
          "high",
          "medium",
          "low",
        ]),
        num(
          "escalation_minutes",
          "Nhắc khi chưa xử lý sau (phút)",
          "Escalate unresolved after (minutes)",
          1,
          10080,
          30,
        ),
        opt("channel", "Kênh", "Channel", [
          "in_app",
          "email",
          "sms",
          "zalo",
          "webhook",
        ]),
        text("destination", "Địa chỉ nhận", "Destination"),
        {
          key: "enabled",
          label: l("Bật chính sách", "Enable policy"),
          type: "checkbox",
          value: true,
        },
      ],
      document: [
        opt("category", "Loại tài liệu", "Category", [
          "manual",
          "installation",
          "handover",
          "evidence",
          "other",
        ]),
        text(
          "reference",
          "Đường dẫn / mã hồ sơ",
          "Document link / reference",
          true,
        ),
        {
          ...text("sha256", "SHA-256 (nếu có)", "SHA-256 (optional)"),
          pattern: "(?:[a-fA-F0-9]{64})?",
        },
        {
          ...text("notes", "Nội dung / ghi chú", "Content / notes"),
          textarea: true,
        },
      ],
      topology: [
        {
          ...text("notes", "Ghi chú sơ đồ thực tế", "As-built topology notes"),
          textarea: true,
        },
      ],
    };
  }
  function entityView(kind) {
    const data = rows(kind),
      title = labels()[kind],
      allowed =
        operator() &&
        (![
          "topology",
          "source_policy",
          "network_profile",
          "firmware_request",
        ].includes(kind) ||
          technical());
    const descriptions = {
      topology: l(
        "Ghi lại dây nguồn và đường truyền thông. Sơ đồ do kỹ thuật viên xác nhận, không suy đoán từ tên hãng.",
        "Document power and communication links. Topology is recorded by a technician, never inferred from vendor branding.",
      ),
      source_policy: l(
        "Cấu hình ưu tiên cho màn hình dòng năng lượng. Mẫu chưa xác minh vẫn được giữ nguyên chất lượng gốc.",
        "Set source priority for the energy view. Unverified readings keep their original quality.",
      ),
      network_profile: l(
        "Hồ sơ kết nối tại công trình. Lưu hồ sơ chưa thay đổi mạng hoặc quét logger; cần driver đúng model để áp dụng.",
        "Site connection profiles. Saving does not change networking or scan a logger; applying requires its model-specific driver.",
      ),
      firmware_request: l(
        "Lập yêu cầu nâng cấp với phiên bản, checksum và cửa sổ bảo trì. Chưa có driver OTA được nghiệm thu để gửi gói xuống thiết bị.",
        "Plan upgrades with versions, checksums and maintenance windows. An accepted OTA driver is required to transfer firmware.",
      ),
      maintenance_plan: l(
        "Controller tự tạo một phiếu khi đến hạn. Những kỳ bỏ lỡ được gộp thành một việc quá hạn để tránh tạo trùng.",
        "The controller creates a due work order. Missed periods are coalesced into one overdue job.",
      ),
      notification_policy: l(
        "Thông báo trong ứng dụng hoạt động khi controller chạy. Email, SMS, Zalo và webhook cần nhà cung cấp đã cấu hình.",
        "In-app notifications run with the controller. Email, SMS, Zalo and webhooks require a configured provider.",
      ),
      tariff: l(
        "Giá do bạn nhập theo hợp đồng thực tế, có ngày hiệu lực và khung giờ. Không dùng giá trong ảnh mockup.",
        "Enter your actual contractual rates with effective dates and time bands. Mockup prices are not used.",
      ),
      document: l(
        "Lưu danh mục hồ sơ và đường dẫn tham chiếu; ứng dụng không tự tải hoặc gửi tài liệu ra ngoài.",
        "Maintain document references; documents are not automatically fetched or sent externally.",
      ),
    };
    const root = div(
      "stack",
      p(
        descriptions[kind] ||
          l(
            "Hồ sơ theo từng nhà máy, hỗ trợ tìm kiếm và chỉnh sửa.",
            "Plant-scoped records with search and editing.",
          ),
      ),
    );
    if (allowed)
      root.append(
        btn(
          l("+ Thêm hồ sơ", "+ Add record"),
          () => entityForm(kind),
          "primary",
        ),
      );
    const search = input("search");
    search.placeholder = l(
      "Tìm tên, nhà máy, thông tin…",
      "Search names, plants, details…",
    );
    search.setAttribute("aria-label", search.placeholder);
    const list = div("");
    const draw = () => {
      const filtered = data.filter((r) =>
        JSON.stringify(r).toLowerCase().includes(search.value.toLowerCase()),
      );
      list.replaceChildren(
        filtered.length
          ? table(
              [
                t("name"),
                t("plants"),
                l("Thông tin", "Summary"),
                l("Cập nhật", "Updated"),
                l("Thao tác", "Actions"),
              ],
              filtered.map((r) => [
                r.name,
                siteName(r.site_id),
                r.state ||
                  r.delivery_state ||
                  (kind === "maintenance_plan"
                    ? `${r.next_due} · ${r.interval_days} ${l("ngày", "days")}`
                    : r.group ||
                      r.connection ||
                      r.currency ||
                      r.category ||
                      "—"),
                date(r.updated_at),
                div(
                  "row",
                  btn(t("details"), () => entityDetail(kind, r)),
                  allowed
                    ? btn(l("Sửa", "Edit"), () => entityForm(kind, r))
                    : null,
                ),
              ]),
            )
          : p(t("noData")),
      );
    };
    search.oninput = draw;
    draw();
    root.append(card(title, search, list));
    if (kind === "maintenance_plan") {
      const due = (state.ops.work_order || [])
        .filter(
          (j) =>
            (!state.site || j.site_id === state.site) &&
            j.due_date &&
            !["resolved", "closed"].includes(j.status),
        )
        .sort((a, b) => a.due_date.localeCompare(b.due_date));
      root.append(
        card(
          l("Lịch công việc sắp tới", "Upcoming work"),
          due.length
            ? table(
                [
                  l("Hạn", "Due"),
                  l("Công việc", "Work"),
                  t("plants"),
                  t("status"),
                ],
                due.map((j) => [
                  j.due_date,
                  j.title,
                  siteName(j.site_id),
                  t(j.status),
                ]),
              )
            : p(t("noData")),
        ),
      );
    }
    return root;
  }
  function entityDetail(kind, row) {
    const root = div("stack", fact(t("plants"), siteName(row.site_id)));
    if (kind === "topology")
      root.append(
        topologyDiagram(row),
        table(
          [l("Từ", "From"), l("Đến", "To"), l("Kết nối", "Connection")],
          row.edges.map((x) => [
            deviceName(x.source),
            deviceName(x.target),
            x.connection,
          ]),
        ),
      );
    for (const spec of schemas()[kind])
      root.append(
        fact(
          spec.label,
          spec.device
            ? deviceName(row[spec.key])
            : typeof row[spec.key] === "boolean"
              ? row[spec.key]
                ? l("Bật", "On")
                : l("Tắt", "Off")
              : (row[spec.key] ?? "—"),
        ),
      );
    if (kind === "tariff")
      root.append(
        table(
          [
            l("Ngày", "Day"),
            l("Từ", "From"),
            l("Đến", "To"),
            l("Giá / kWh", "Price / kWh"),
          ],
          row.slots.map((s) => [s.day + 1, s.start, s.end, number(s.price)]),
        ),
      );
    if (row.state) root.append(badge(row.state));
    root.append(
      raw(l("Lịch sử phiên bản hiện tại", "Current record metadata"), {
        revision: row.revision,
        updated_by: row.updated_by,
        updated_at: row.updated_at,
      }),
    );
    if (
      operator() &&
      (![
        "topology",
        "source_policy",
        "network_profile",
        "firmware_request",
      ].includes(kind) ||
        technical())
    )
      root.append(
        btn(l("Lưu trữ hồ sơ này", "Archive this record"), () => {
          const confirm = div(
            "stack",
            p(
              l(
                "Hồ sơ sẽ được ẩn khỏi danh sách đang dùng. Dữ liệu lịch sử vẫn được giữ.",
                "This record will leave the active list. Historical data is retained.",
              ),
            ),
            btn(
              l("Xác nhận lưu trữ", "Confirm archive"),
              async () => {
                await api(`/workbench/${kind}/${row.id}/archive`, {
                  revision: row.revision,
                });
                closeDialog();
                await refresh();
              },
              "primary",
            ),
          );
          showDialog(l("Lưu trữ hồ sơ", "Archive record"), confirm);
        }),
      );
    showDialog(row.name, root);
  }
  function entityForm(kind, existing = null) {
    if (!state.fleet.sites.length) {
      toast(l("Thêm nhà máy trước.", "Add a plant first."));
      return;
    }
    const name = input("text", existing?.name || ""),
      site = siteSelect(existing?.site_id);
    name.required = true;
    name.maxLength = 160;
    site.disabled = !!existing;
    const controls = {},
      specs = schemas()[kind],
      fields = div(
        "form-grid",
        field(t("name"), name),
        field(t("plants"), site),
      );
    const devOptions = () => [
      ["", l("Chọn thiết bị", "Select device")],
      ...state.fleet.devices
        .filter((d) => d.site_id === site.value)
        .map((d) => [d.id, `${d.name || d.vendor_id} · ${d.type}`]),
    ];
    for (const spec of specs) {
      let value = existing?.[spec.key] ?? spec.value ?? "",
        control;
      if (spec.type === "datetime-local" && value) {
        const d = new Date(value);
        value = new Date(d.getTime() - d.getTimezoneOffset() * 60000)
          .toISOString()
          .slice(0, 16);
      }
      if (spec.device) control = select(devOptions(), value);
      else if (spec.choices)
        control = select(
          spec.choices.map((c) => [String(c), t(String(c))]),
          String(value),
        );
      else if (spec.textarea) {
        control = e("textarea");
        control.value = value;
        control.rows = 3;
        control.maxLength = 2000;
      } else control = input(spec.type || "text", value);
      if (spec.type === "checkbox") control.checked = !!value;
      if (spec.min !== undefined) control.min = spec.min;
      if (spec.max !== undefined) control.max = spec.max;
      if (spec.type === "number") control.step = spec.numeric ? "1" : "any";
      if (spec.pattern) control.pattern = spec.pattern;
      control.required = !!spec.required;
      controls[spec.key] = control;
      fields.append(field(spec.label, control));
    }
    const extra = div("stack"),
      entries = [];
    const addArray = (values = {}) => {
      const r = div("array-row"),
        entry = {};
      if (kind === "topology") {
        entry.source = select(devOptions(), values.source);
        entry.target = select(devOptions(), values.target);
        entry.connection = select(
          ["AC", "DC", "RS485", "LAN", "WIRELESS", "CAN", "OTHER"].map((c) => [
            c,
            c,
          ]),
          values.connection,
        );
        entry.source.required = entry.target.required = true;
        r.append(
          field(l("Thiết bị nguồn", "Source device"), entry.source),
          field(l("Thiết bị đích", "Target device"), entry.target),
          field(l("Đường kết nối", "Connection"), entry.connection),
        );
      } else if (kind === "tariff") {
        entry.day = select(
          Array.from({ length: 7 }, (_, i) => [
            String(i),
            l(
              [
                "Thứ 2",
                "Thứ 3",
                "Thứ 4",
                "Thứ 5",
                "Thứ 6",
                "Thứ 7",
                "Chủ nhật",
              ][i],
              [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
              ][i],
            ),
          ]),
          String(values.day ?? 0),
        );
        entry.start = input("time", values.start || "00:00");
        entry.end = input("text", values.end || "24:00");
        entry.end.pattern = "(?:(?:[01][0-9]|2[0-3]):[0-5][0-9]|24:00)";
        entry.price = input("number", values.price ?? 0);
        entry.price.min = 0;
        entry.price.max = 1000000;
        entry.price.step = "any";
        for (const [key, label] of [
          ["day", l("Ngày", "Day")],
          ["start", l("Từ", "From")],
          ["end", l("Đến", "To")],
          ["price", l("Giá / kWh", "Price / kWh")],
        ]) {
          entry[key].required = true;
          r.append(field(label, entry[key]));
        }
      }
      entries.push(entry);
      r.append(
        btn("×", () => {
          entries.splice(entries.indexOf(entry), 1);
          r.remove();
        }),
      );
      extra.append(r);
    };
    if (kind === "topology" || kind === "tariff") {
      for (const value of existing?.[kind === "topology" ? "edges" : "slots"] ||
        [])
        addArray(value);
      extra.append(btn(l("+ Thêm dòng", "+ Add row"), () => addArray()));
    }
    let priorities = [];
    if (kind === "source_policy") {
      priorities = (
        existing?.priority || ["LOCAL", "SITE_AGENT", "VENDOR_CLOUD"]
      ).slice();
      const priorityBox = div("stack");
      function redraw() {
        priorityBox.replaceChildren(
          ...priorities.map((source, index) =>
            div(
              "priority-row",
              badge(String(index + 1), "blue"),
              e("b", source),
              btn("↑", () => {
                if (index) {
                  [priorities[index - 1], priorities[index]] = [
                    priorities[index],
                    priorities[index - 1],
                  ];
                  redraw();
                }
              }),
            ),
          ),
        );
      }
      redraw();
      extra.append(card(l("Thứ tự ưu tiên", "Source priority"), priorityBox));
    }
    site.onchange = () => {
      for (const spec of specs.filter((s) => s.device)) {
        const n = controls[spec.key];
        n.replaceChildren(
          ...devOptions().map(([value, label]) => {
            const o = e("option", label);
            o.value = value;
            return o;
          }),
        );
      }
      entries.splice(0);
      if (kind === "topology") {
        extra.replaceChildren(
          btn(l("+ Thêm đường kết nối", "+ Add connection"), () => addArray()),
        );
      }
    };
    const f = form(async () => {
      const data = { site_id: site.value, name: name.value };
      for (const spec of specs) {
        const c = controls[spec.key];
        data[spec.key] =
          spec.type === "checkbox"
            ? c.checked
            : spec.nullable && c.value === ""
              ? null
              : spec.type === "number" || spec.numeric
                ? Number(c.value)
                : spec.type === "datetime-local"
                  ? new Date(c.value).toISOString()
                  : c.value;
      }
      if (kind === "topology")
        data.edges = entries.map((r) =>
          Object.fromEntries(Object.entries(r).map(([k, c]) => [k, c.value])),
        );
      if (kind === "tariff")
        data.slots = entries.map((r) => ({
          day: Number(r.day.value),
          start: r.start.value,
          end: r.end.value,
          price: Number(r.price.value),
        }));
      if (kind === "source_policy") data.priority = priorities;
      await api("/workbench/" + kind, {
        id: existing?.id || null,
        revision: existing?.revision || null,
        data,
      });
      closeDialog();
      await refresh();
    });
    f.finish(fields, extra);
    showDialog(
      (existing ? l("Sửa · ", "Edit · ") : l("Thêm · ", "Add · ")) +
        labels()[kind],
      f,
    );
  }
  function assetForm() {
    const name = input(),
      vendor = input(),
      serial = input(),
      model = input(),
      site = siteSelect(),
      type = select(
        [
          "INVERTER",
          "BATTERY",
          "LOGGER",
          "METER",
          "CT",
          "UPS",
          "ATS",
          "GENERATOR",
          "EV_CHARGER",
          "LOAD",
          "OTHER",
        ].map((v) => [v, t(v)]),
      );
    name.required = vendor.required = serial.required = site.required = true;
    name.maxLength = 160;
    vendor.maxLength = 80;
    serial.maxLength = 100;
    model.maxLength = 120;
    const f = form(async () => {
      await api("/assets", {
        site_id: site.value,
        name: name.value,
        vendor: vendor.value,
        serial: serial.value,
        model: model.value,
        type: type.value,
      });
      closeDialog();
      await refresh();
    });
    f.finish(
      notice(
        "Đăng ký tài sản trước, sau đó cấp phạm vi cho Local Agent hoặc nối nguồn hãng. Thiết bị chưa có dữ liệu sẽ hiện chưa kết nối.",
        "Register equipment first, then scope a Local Agent or connect a vendor source. Equipment without readings remains disconnected.",
      ),
      div(
        "form-grid",
        field(t("plants"), site),
        field(t("name"), name),
        field(t("vendor"), vendor),
        field(l("Loại thiết bị", "Equipment type"), type),
        field("Serial", serial),
        field("Model", model),
      ),
    );
    showDialog(l("Đăng ký thiết bị", "Register equipment"), f);
  }
  function mapView() {
    const root = div(
        "stack",
        p(
          l(
            "Bản đồ tọa độ ngoại tuyến; vị trí không gửi tới dịch vụ bản đồ bên ngoài.",
            "Offline coordinate map; locations are not sent to an external map service.",
          ),
        ),
      ),
      found = sites().filter((s) => s.latitude != null && s.longitude != null),
      search = input("search"),
      out = div("map-layout");
    search.placeholder = l(
      "Tìm nhà máy / khách hàng",
      "Search plant / customer",
    );
    search.setAttribute("aria-label", search.placeholder);
    function draw() {
      const selected = found.filter((s) =>
        `${s.name} ${s.customer || ""} ${s.address || ""}`
          .toLowerCase()
          .includes(search.value.toLowerCase()),
      );
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("viewBox", "0 0 800 470");
      svg.setAttribute("role", "img");
      svg.setAttribute(
        "aria-label",
        l("Vị trí các nhà máy theo tọa độ", "Plant coordinates"),
      );
      svg.classList.add("geo-map");
      const make = (tag, attrs, text = "") => {
        const n = document.createElementNS(svg.namespaceURI, tag);
        for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
        n.textContent = text;
        svg.append(n);
        return n;
      };
      make("rect", {
        x: 0,
        y: 0,
        width: 800,
        height: 470,
        rx: 16,
        fill: "#eaf3f8",
      });
      let minLat = -90,
        maxLat = 90,
        minLon = -180,
        maxLon = 180;
      if (selected.length) {
        minLat = Math.min(...selected.map((s) => s.latitude)) - 1;
        maxLat = Math.max(...selected.map((s) => s.latitude)) + 1;
        minLon = Math.min(...selected.map((s) => s.longitude)) - 1;
        maxLon = Math.max(...selected.map((s) => s.longitude)) + 1;
      }
      for (let i = 0; i <= 5; i++) {
        const x = 60 + i * 136,
          y = 35 + i * 78;
        make("path", {
          d: `M${x},35V425 M60,${y}H740`,
          stroke: "#ccdde9",
          fill: "none",
        });
        make(
          "text",
          {
            x,
            y: 454,
            fill: "#526881",
            "font-size": 11,
            "text-anchor": "middle",
          },
          `${(minLon + ((maxLon - minLon) * i) / 5).toFixed(2)}°`,
        );
        make(
          "text",
          { x: 8, y: y + 3, fill: "#526881", "font-size": 11 },
          `${(maxLat - ((maxLat - minLat) * i) / 5).toFixed(2)}°`,
        );
      }
      const detail = div("stack");
      const show = (s) => {
        const ds = state.fleet.devices.filter((d) => d.site_id === s.id);
        detail.replaceChildren(
          e("h2", s.name),
          p(s.address || "—"),
          fact(l("Khách hàng", "Customer"), s.customer || "—"),
          fact(
            l("Công suất lắp đặt", "Installed capacity"),
            s.capacity_kwp == null ? "—" : number(s.capacity_kwp) + " kWp",
          ),
          fact(l("Thiết bị", "Equipment"), ds.length),
          fact(l("Tọa độ", "Coordinates"), `${s.latitude}, ${s.longitude}`),
          btn(
            l("Mở nhà máy", "Open plant"),
            () => {
              state.site = s.id;
              state.page = "plants";
              state.section = "plant";
              return render();
            },
            "primary",
          ),
        );
      };
      for (const s of selected) {
        const x = 60 + ((s.longitude - minLon) / (maxLon - minLon)) * 680,
          y = 35 + ((maxLat - s.latitude) / (maxLat - minLat)) * 390,
          ds = state.fleet.devices.filter((d) => d.site_id === s.id),
          color =
            ds.length && ds.every((d) => d.online && !d.stale)
              ? "#25a56a"
              : "#f0a836";
        const c = make("circle", {
          cx: x,
          cy: y,
          r: 9,
          fill: color,
          stroke: "#fff",
          "stroke-width": 3,
          tabindex: 0,
          role: "button",
          "aria-label": s.name,
        });
        c.onclick = () => show(s);
        c.onkeydown = (ev) => {
          if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            show(s);
          }
        };
        make(
          "text",
          { x: x + 13, y: y + 4, fill: "#183351", "font-size": 12 },
          s.name.slice(0, 25),
        );
      }
      if (selected.length) show(selected[0]);
      else
        detail.append(
          p(
            l(
              "Thêm tọa độ trong hồ sơ nhà máy để hiển thị vị trí.",
              "Add coordinates to a plant profile to show its location.",
            ),
          ),
        );
      out.replaceChildren(svg, card("", detail));
    }
    search.oninput = draw;
    draw();
    root.append(
      search,
      out,
      table(
        [t("name"), l("Địa chỉ", "Address"), l("Tọa độ", "Coordinates")],
        sites().map((s) => [
          s.name,
          s.address || "—",
          s.latitude == null
            ? l("Chưa khai báo", "Not configured")
            : `${s.latitude}, ${s.longitude}`,
        ]),
      ),
    );
    return root;
  }
  function topologyDiagram(row) {
    const ids = [...new Set(row.edges.flatMap((r) => [r.source, r.target]))];
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", `0 0 760 ${Math.max(300, ids.length * 75)}`);
    svg.classList.add("topology-svg");
    svg.setAttribute("role", "img");
    svg.setAttribute(
      "aria-label",
      l("Sơ đồ thiết bị đã khai báo", "Recorded equipment topology"),
    );
    const node = (tag, attrs, text = "") => {
      const n = document.createElementNS(svg.namespaceURI, tag);
      for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
      n.textContent = text;
      svg.append(n);
      return n;
    };
    const points = Object.fromEntries(
      ids.map((id, i) => [
        id,
        { x: i % 2 ? 475 : 35, y: 30 + Math.floor(i / 2) * 130 },
      ]),
    );
    for (const edge of row.edges) {
      const a = points[edge.source],
        b = points[edge.target];
      node("path", {
        d: `M${a.x + 125},${a.y + 65} L${b.x + 125},${b.y + 32}`,
        fill: "none",
        stroke: edge.connection === "DC" ? "#2dac68" : "#526cff",
        "stroke-width": 2,
      });
      node(
        "text",
        {
          x: (a.x + b.x) / 2 + 130,
          y: (a.y + b.y) / 2 + 55,
          fill: "#5c6e87",
          "font-size": 11,
        },
        edge.connection,
      );
    }
    for (const id of ids) {
      const { x, y } = points[id];
      const dev = state.fleet.devices.find((d) => d.id === id);
      const devType = (dev?.type || '').toUpperCase();
      const accent = devType.includes('INV') ? '#3b82f6' :
                     devType.includes('BAT') ? '#8b5cf6' :
                     devType.includes('PV') || devType.includes('SOLAR') ? '#10b981' :
                     devType.includes('MET') || devType.includes('GRID') ? '#f59e0b' : '#64748b';
      node("rect", {
        x,
        y,
        width: 250,
        height: 68,
        rx: 10,
        fill: "var(--surface)",
        stroke: "var(--line)",
        "stroke-width": 1.5,
      });
      node("rect", {
        x,
        y,
        width: 6,
        height: 68,
        rx: 3,
        fill: accent,
      });
      const n = node(
        "text",
        {
          x: x + 16,
          y: y + 27,
          fill: "var(--text)",
          "font-size": 13,
          "font-weight": "700",
          tabindex: 0,
          role: "button",
          "aria-label": deviceName(id),
        },
        deviceName(id).slice(0, 26),
      );
      n.onclick = () => deviceDetail(id);
      n.onkeydown = (ev) => {
        if (ev.key === "Enter") deviceDetail(id);
      };
      node(
        "text",
        { x: x + 16, y: y + 49, fill: "var(--muted)", "font-size": 11 },
        `${dev?.type || "DEVICE"} · ${dev?.status || "UNKNOWN"}`,
      );
    }
    return svg;
  }
  function requireSite() {
    const pick = siteSelect();
    const root = card(
      l("Chọn nhà máy", "Choose a plant"),
      field(t("plants"), pick),
      btn(
        l("Mở", "Open"),
        () => {
          state.site = pick.value;
          return render();
        },
        "primary",
      ),
    );
    return root;
  }
  async function plantView() {
    if (!state.site) return requireSite();
    const site = sites()[0];
    if (!site) return requireSite();
    const [energy, diagnostics] = await Promise.all([
      api(`/sites/${site.id}/energy`),
      api(`/sites/${site.id}/diagnostics`),
    ]);
    const root = div(
      "stack",
      card(
        site.name,
        p(site.address || ""),
        div(
          "facts",
          fact(l("Khách hàng", "Customer"), site.customer || "—"),
          fact(
            l("Công suất", "Capacity"),
            site.capacity_kwp == null
              ? "—"
              : number(site.capacity_kwp) + " kWp",
          ),
          fact(l("Múi giờ", "Timezone"), site.timezone || "—"),
        ),
      ),
    );
    const layout = div("plant-grid"),
      flow = div("energy-flow");
    for (const [metric, vi, en, icon] of [
      ["pv_w", "Điện mặt trời", "Solar PV", "☀"],
      ["load_w", "Tải tiêu thụ", "Consumption", "⌂"],
      ["grid_import_w", "Nhập từ lưới", "Grid import", "↓"],
      ["grid_export_w", "Xuất lên lưới", "Grid export", "↑"],
      ["battery_charge_w", "Sạc pin", "Battery charge", "+"],
      ["battery_discharge_w", "Xả pin", "Battery discharge", "−"],
    ]) {
      const m = energy.metrics[metric];
      flow.append(
        div(
          "energy-node",
          e("span", icon, "energy-symbol"),
          e("span", l(vi, en)),
          e("strong", m.value == null ? "—" : number(m.value / 1000) + " kW"),
          e(
            "small",
            m.value == null
              ? l("Cần dữ liệu đã xác minh", "Verified data required")
              : l("Đã đo", "Measured"),
            "muted",
          ),
        ),
      );
    }
    layout.append(
      card(
        l("Dòng năng lượng", "Energy flow"),
        flow,
        p(
          l(
            "Mỗi đại lượng dùng một nguồn đo rõ ràng. Thiếu số đo hoặc chưa xác định meter sẽ hiển thị —.",
            "Each value needs an explicit measurement source. Missing or ambiguous meter readings display —.",
          ),
        ),
      ),
    );
    layout.append(
      card(
        l("Tình trạng thiết bị", "Equipment health"),
        table(
          [
            t("name"),
            l("Dữ liệu mới", "Fresh readings"),
            l("Cần xử lý", "Next step"),
          ],
          diagnostics.devices.map((d) => [
            btn(d.name, () => deviceDetail(d.device_id)),
            `${d.fresh_samples}/${d.sample_count}`,
            stepLabel(d.next_step),
          ]),
        ),
      ),
    );
    root.append(layout);
    if (energy.topology)
      root.append(
        card(l("Sơ đồ kết nối", "Topology"), topologyDiagram(energy.topology)),
      );
    root.append(
      div(
        "row",
        btn(l("Lịch / TOU", "Schedules / TOU"), () =>
          go("operations", "schedules"),
        ),
        btn(l("Xem sự cố", "View incidents"), () => go("incidents")),
        btn(l("Báo cáo", "Reports"), () => {
          state.page = "reports";
          state.section = "analytics";
          return render();
        }),
      ),
    );
    return root;
  }
  function stepLabel(key) {
    return (
      {
        RECONCILE_COMMAND: l(
          "Đối chiếu lệnh chưa rõ kết quả",
          "Reconcile uncertain command",
        ),
        CHECK_CONNECTION: l("Kiểm tra đường kết nối", "Check connection"),
        VERIFY_MAPPING: l(
          "Đối chiếu thông số của hãng",
          "Verify vendor metric mapping",
        ),
        MONITOR: l("Theo dõi bình thường", "Continue monitoring"),
      }[key] || key
    );
  }
  function agentsView() {
    const root = div(
      "stack",
      notice(
        "Local Agent gửi dữ liệu ra controller, không mở đường điều khiển từ Internet. Token chỉ hiện một lần; dữ liệu chưa có profile đo lường được giữ là chưa xác minh.",
        "Local Agent sends outbound readings to the controller. Tokens display once; measurements without a reviewed profile remain unverified.",
      ),
    );
    if (admin())
      root.append(
        btn(
          l("+ Đăng ký Local Agent", "+ Enroll Local Agent"),
          agentForm,
          "primary",
        ),
      );
    root.append(
      card(
        "Local Agents",
        table(
          [
            t("name"),
            t("plants"),
            l("Lần nhận cuối", "Last received"),
            l("Thiết bị", "Devices"),
            t("status"),
            l("Thao tác", "Actions"),
          ],
          rows("agent").map((r) => [
            r.name,
            siteName(r.site_id),
            date(r.last_seen),
            r.device_ids.length,
            r.enabled
              ? r.last_seen
                ? l("Đã nhận dữ liệu", "Has received data")
                : l("Chờ kết nối", "Awaiting connection")
              : l("Đã thu hồi", "Revoked"),
            r.enabled && admin()
              ? btn(l("Thu hồi token", "Revoke token"), () =>
                  showDialog(
                    l("Thu hồi kết nối", "Revoke connection"),
                    p(
                      l(
                        "Agent này sẽ không thể gửi thêm dữ liệu với token hiện tại.",
                        "This agent will no longer be able to send data with its current token.",
                      ),
                    ),
                    btn(
                      l("Xác nhận thu hồi", "Confirm revocation"),
                      async () => {
                        await api(`/agents/${r.id}/revoke`, {});
                        closeDialog();
                        await refresh();
                      },
                      "primary",
                    ),
                  ),
                )
              : "—",
          ]),
        ),
      ),
    );
    root.append(
      card(
        l("Kết nối tại công trình", "Site connection"),
        p(
          l(
            "1. Đăng ký thiết bị tại Thiết bị. 2. Cấp Agent đúng phạm vi. 3. Cấu hình collector và đường hầm tới controller. 4. Gửi mẫu, kiểm tra thời gian và đơn vị.",
            "1. Register equipment. 2. Enroll an agent with its device scope. 3. Configure a collector and a controller tunnel. 4. Send readings and verify timestamps and units.",
          ),
        ),
        raw(l("Lệnh CLI cho kỹ thuật viên", "Technician CLI"), {
          enqueue:
            "solar-fleet-agent --spool agent.db enqueue --agent-id ID --file readings.json",
          flush:
            "solar-fleet-agent --spool agent.db flush --controller http://127.0.0.1:8765",
          credential: "SOLAR_AGENT_TOKEN environment variable",
          driver: l(
            "Collector theo đúng protocol hãng; không tự đoán thanh ghi.",
            "Use a vendor-specific collector; never infer registers.",
          ),
        }),
      ),
    );
    return root;
  }
  function agentForm() {
    const name = input(),
      site = siteSelect(),
      list = div("checklist");
    name.required = true;
    let choices = [];
    function fill() {
      choices = state.fleet.devices
        .filter((d) => d.site_id === site.value)
        .map((d) => ({ d, box: input("checkbox") }));
      list.replaceChildren(
        ...choices.map(({ d, box }) =>
          add(e("label", "", "check"), box, e("span", deviceName(d.id))),
        ),
      );
    }
    fill();
    site.onchange = fill;
    const f = form(async () => {
      const result = await api("/agents", {
        name: name.value,
        site_id: site.value,
        device_ids: choices.filter((r) => r.box.checked).map((r) => r.d.id),
      });
      await refresh();
      const secret = e("textarea");
      secret.value = result.token;
      secret.readOnly = true;
      secret.rows = 3;
      showDialog(
        l("Lưu token một lần", "Save this one-time token"),
        p(
          l(
            "Lưu vào kho bí mật của máy chạy Agent. Khi đóng, UI sẽ không đọc lại được token.",
            "Store this in the agent machine’s secret store. The UI cannot retrieve it after closing.",
          ),
        ),
        fact("Agent ID", result.id),
        field("Token", secret),
      );
    });
    f.finish(field(t("name"), name), field(t("plants"), site), list);
    showDialog(l("Đăng ký Local Agent", "Enroll Local Agent"), f);
  }
  function inboxView() {
    const data = rows("notification").sort((a, b) =>
      b.created_at.localeCompare(a.created_at),
    );
    return card(
      l("Thông báo vận hành", "Operational notifications"),
      data.length
        ? table(
            [
              l("Nội dung", "Message"),
              t("plants"),
              l("Thời gian", "Time"),
              l("Trạng thái", "Status"),
            ],
            data.map((r) => [
              r.title,
              siteName(r.site_id),
              date(r.created_at),
              r.read_by.includes(state.me.user.id)
                ? badge(l("Đã đọc", "Read"), "good")
                : btn(l("Đánh dấu đã đọc", "Mark read"), async () => {
                    await api(`/notifications/${r.id}/read`, {});
                    await refresh();
                  }),
            ]),
          )
        : p(
            l(
              "Chưa có thông báo cần xử lý.",
              "No operational notifications yet.",
            ),
          ),
    );
  }
  async function operationsTools() {
    if (state.tab === "schedules")
      return card(
        l("Chỉnh sửa lịch đã lưu", "Edit a saved schedule"),
        ...(state.ops.schedule || [])
          .filter((s) => !state.site || s.site_id === state.site)
          .map((r) =>
            div(
              "row between",
              e("b", r.name),
              div(
                "row",
                operator()
                  ? btn(l("Sửa lịch", "Edit schedule"), () => scheduleForm(r))
                  : null,
                btn(l("Xem phiên bản", "Versions"), async () => {
                  const v = await api(`/schedules/${r.id}/versions`);
                  showDialog(
                    r.name,
                    table(
                      [
                        l("Phiên bản", "Revision"),
                        l("Số khung", "Slots"),
                        t("status"),
                      ],
                      v.map((x) => [x.revision || 1, x.slots.length, x.state]),
                    ),
                  );
                }),
                btn(l("Lịch hôm nay", "Today’s timeline"), async () => {
                  const today = new Intl.DateTimeFormat("en-CA", {
                    timeZone: r.timezone,
                    year: "numeric",
                    month: "2-digit",
                    day: "2-digit",
                  }).format(new Date());
                  const data = await api(
                    `/schedules/${r.id}/timeline?day=${today}`,
                  );
                  showDialog(
                    r.name,
                    table(
                      [
                        l("Bắt đầu", "Start"),
                        l("Kết thúc", "End"),
                        l("Chế độ", "Mode"),
                      ],
                      data.slots.map((s) => [
                        date(s.start_at),
                        date(s.end_at),
                        t(s.mode),
                      ]),
                    ),
                  );
                }),
              ),
            ),
          ),
      );
    if (state.tab === "rules")
      return card(
        l("Theo dõi quy tắc tự động", "Automatic rule monitoring"),
        p(
          l(
            "Theo dõi điều kiện liên tục, giữ ngưỡng theo thời gian và giãn cách thông báo. Lệnh đề xuất cần xem trước và xác nhận qua Điều khiển hoặc Triển khai hàng loạt.",
            "Continuously evaluate conditions with hold periods and notification cooldowns. Proposed commands require preview and confirmation through Control or Fleet rollout.",
          ),
        ),
        operator()
          ? btn(
              l("+ Quy tắc nhiều điều kiện", "+ Multi-condition rule"),
              () => ruleEditor(),
              "primary",
            )
          : null,
        table(
          [
            t("name"),
            l("Theo dõi", "Monitoring"),
            l("Điều kiện gần nhất", "Last conditions"),
            l("Thao tác", "Actions"),
          ],
          (state.ops.rule || [])
            .filter((r) => !state.site || r.site_id === state.site)
            .map((r) => {
              const m = (work().rule_monitor || []).find((x) => x.id === r.id);
              return [
                r.name,
                m?.enabled
                  ? l("Đang theo dõi", "Monitoring")
                  : l("Tạm dừng", "Paused"),
                m?.condition_state || "—",
                operator()
                  ? div(
                      "row",
                      btn(l("Sửa", "Edit"), () => ruleEditor(r)),
                      btn(
                        m?.enabled
                          ? l("Dừng", "Pause")
                          : l("Bật theo dõi", "Monitor"),
                        () => monitorForm(r, m),
                      ),
                    )
                  : "—",
              ];
            }),
        ),
      );
    return div("");
  }
  function monitorForm(rule, current) {
    if (current?.enabled)
      return api(`/rules/${rule.id}/monitor`, {
        enabled: false,
        hold_seconds: current.hold_seconds,
        cooldown_seconds: current.cooldown_seconds,
      }).then(refresh);
    const hold = input("number", current?.hold_seconds ?? 60),
      cool = input("number", current?.cooldown_seconds ?? 900);
    hold.min = 0;
    hold.max = 86400;
    cool.min = 60;
    cool.max = 604800;
    hold.required = cool.required = true;
    const f = form(async () => {
      await api(`/rules/${rule.id}/monitor`, {
        enabled: true,
        hold_seconds: Number(hold.value),
        cooldown_seconds: Number(cool.value),
      });
      closeDialog();
      await refresh();
    });
    f.finish(
      field(
        l("Điều kiện giữ liên tục (giây)", "Continuous hold (seconds)"),
        hold,
      ),
      field(
        l("Khoảng cách thông báo (giây)", "Notification cooldown (seconds)"),
        cool,
      ),
      notice(
        "Chế độ theo dõi chỉ tạo thông báo và lịch sử đánh giá, chưa tự gửi lệnh xuống thiết bị.",
        "Monitoring creates notifications and evaluation history; it does not send device commands.",
      ),
    );
    showDialog(rule.name, f);
  }
  function ruleEditor(existing = null) {
    const name = input("text", existing?.name || ""),
      description = e("textarea"),
      site = siteSelect(existing?.site_id);
    description.value = existing?.description || "";
    name.required = true;
    site.disabled = !!existing;
    name.maxLength = 120;
    description.maxLength = 2000;
    const conditions = [],
      actions = [],
      conditionList = div("stack"),
      actionList = div("stack");
    const opts = () =>
      state.fleet.devices
        .filter((d) => d.site_id === site.value)
        .map((d) => [d.id, deviceName(d.id)]);
    const addCondition = (values = {}) => {
      const entry = {
        device_id: select(opts(), values.device_id),
        metric: input("text", values.metric || ""),
        unit: input("text", values.unit || ""),
        comparison: select(
          ["lt", "lte", "gt", "gte", "eq"].map((v, i) => [
            v,
            ["<", "≤", ">", "≥", "="][i],
          ]),
          values.comparison || "lt",
        ),
        threshold: input("number", values.threshold ?? 0),
        max_age_seconds: input("number", values.max_age_seconds ?? 300),
      };
      entry.threshold.step = "any";
      entry.max_age_seconds.min = 1;
      entry.max_age_seconds.max = 300;
      const row = div("array-row");
      for (const [k, label] of [
        ["device_id", l("Thiết bị", "Device")],
        ["metric", l("Thông số", "Metric")],
        ["unit", l("Đơn vị", "Unit")],
        ["comparison", l("So sánh", "Compare")],
        ["threshold", l("Ngưỡng", "Threshold")],
        ["max_age_seconds", l("Tuổi mẫu (s)", "Sample age (s)")],
      ]) {
        entry[k].required = true;
        row.append(field(label, entry[k]));
      }
      conditions.push(entry);
      row.append(
        btn("×", () => {
          conditions.splice(conditions.indexOf(entry), 1);
          row.remove();
        }),
      );
      conditionList.append(row);
    };
    const addAction = (values = {}) => {
      const entry = {
        device_id: select(opts(), values.device_id),
        intent: select(
          [
            "SET_RESERVE_SOC",
            "SET_EXPORT_LIMIT",
            "SET_MAX_CHARGE_CURRENT",
            "SET_MAX_DISCHARGE_CURRENT",
            "SET_WORK_MODE",
            "ENABLE_GRID_CHARGE",
            "DISABLE_GRID_CHARGE",
          ].map((v) => [v, t(v)]),
          values.intent,
        ),
        value: input("number", values.parameters?.value ?? 30),
      };
      entry.value.step = "any";
      const row = div(
        "array-row",
        field(l("Thiết bị", "Device"), entry.device_id),
        field(l("Mục tiêu", "Intent"), entry.intent),
        field(l("Giá trị (theo profile)", "Value (per profile)"), entry.value),
      );
      actions.push(entry);
      row.append(
        btn("×", () => {
          actions.splice(actions.indexOf(entry), 1);
          row.remove();
        }),
      );
      actionList.append(row);
    };
    for (const value of existing?.conditions || [{}]) addCondition(value);
    for (const value of existing?.actions || [{}]) addAction(value);
    site.onchange = () => {
      conditions.splice(0);
      actions.splice(0);
      conditionList.replaceChildren();
      actionList.replaceChildren();
      addCondition();
      addAction();
    };
    const f = form(async () => {
      const data = {
        site_id: site.value,
        name: name.value,
        description: description.value,
        conditions: conditions.map((r) => ({
          device_id: r.device_id.value,
          metric: r.metric.value,
          unit: r.unit.value,
          comparison: r.comparison.value,
          threshold: Number(r.threshold.value),
          max_age_seconds: Number(r.max_age_seconds.value),
        })),
        actions: actions.map((r) => ({
          device_id: r.device_id.value,
          intent: r.intent.value,
          parameters: ["ENABLE_GRID_CHARGE", "DISABLE_GRID_CHARGE"].includes(
            r.intent.value,
          )
            ? {}
            : { value: Number(r.value.value) },
        })),
      };
      await api(
        existing ? `/rules/${existing.id}/edit` : "/rules",
        existing
          ? { id: existing.id, revision: existing.revision || 1, data }
          : data,
      );
      closeDialog();
      await refresh();
    });
    f.finish(
      div("form-grid", field(t("name"), name), field(t("plants"), site)),
      field(l("Mô tả", "Description"), description),
      notice(
        "Tất cả điều kiện phải đúng và dùng số đo mới, đã xác minh, đúng đơn vị. Chỉnh sửa sẽ tạm dừng theo dõi để bạn xem lại.",
        "All conditions must match fresh, verified readings with exact units. Editing pauses monitoring for review.",
      ),
      e("h3", l("Khi tất cả điều kiện đúng", "When all conditions match")),
      conditionList,
      btn(l("+ Điều kiện", "+ Condition"), () => addCondition()),
      e("h3", l("Hành động đề xuất", "Proposed actions")),
      actionList,
      btn(l("+ Hành động", "+ Action"), () => addAction()),
    );
    showDialog(l("Soạn quy tắc EMS", "EMS rule editor"), f);
  }
  function rolloutsView() {
    const root = div(
      "stack",
      notice(
        "Mỗi thiết bị có kết quả riêng. Xem trước, chạy một thiết bị đầu tiên, xác minh rồi mới triển khai phần còn lại. Hủy chỉ dừng các lệnh chưa gửi.",
        "Each target has its own result. Preview, run one canary, verify it, then release the remaining targets. Cancellation only stops unsent commands.",
      ),
    );
    if (operator())
      root.append(
        btn(
          l("+ Tạo đợt triển khai", "+ Create rollout"),
          rolloutForm,
          "primary",
        ),
      );
    root.append(
      card(
        l("Các đợt triển khai", "Rollouts"),
        table(
          [
            t("name"),
            l("Số thiết bị", "Targets"),
            t("status"),
            l("Thời gian", "Created"),
            t("details"),
          ],
          rows("rollout").map((r) => [
            r.name,
            r.targets.length,
            r.state,
            date(r.created_at),
            btn(t("details"), () => rolloutDetail(r)),
          ]),
        ),
      ),
    );
    return root;
  }
  function rolloutForm() {
    const name = input(),
      intent = select(
        [
          "SET_RESERVE_SOC",
          "SET_EXPORT_LIMIT",
          "SET_MAX_CHARGE_CURRENT",
          "SET_MAX_DISCHARGE_CURRENT",
          "ENABLE_GRID_CHARGE",
          "DISABLE_GRID_CHARGE",
        ].map((v) => [v, t(v)]),
      ),
      value = input("number", 30),
      note = e("textarea");
    value.step = "any";
    name.required = true;
    name.maxLength = 160;
    note.maxLength = 2000;
    const choices = devices().map((d) => ({ d, box: input("checkbox") }));
    const f = form(async () => {
      const selected = choices.filter((c) => c.box.checked);
      const result = await api("/rollouts", {
        name: name.value,
        note: note.value,
        actions: selected.map(({ d }) => ({
          device_id: d.id,
          intent: intent.value,
          parameters: ["ENABLE_GRID_CHARGE", "DISABLE_GRID_CHARGE"].includes(
            intent.value,
          )
            ? {}
            : { value: Number(value.value) },
        })),
      });
      await refresh();
      rolloutDetail(result);
    });
    f.finish(
      field(t("name"), name),
      div(
        "form-grid",
        field(l("Mục tiêu", "Intent"), intent),
        field(l("Giá trị theo profile", "Value per profile"), value),
      ),
      field(l("Ghi chú triển khai", "Deployment note"), note),
      div(
        "checklist",
        ...choices.map(({ d, box }) =>
          add(
            e("label", "", "check"),
            box,
            e("span", `${deviceName(d.id)} · ${siteName(d.site_id)}`),
          ),
        ),
      ),
      p(
        l(
          "Tối đa 20 thiết bị mỗi đợt. Đánh giá sẽ chỉ rõ thiết bị bị chặn.",
          "Up to 20 targets per rollout. Assessment identifies blocked devices.",
        ),
      ),
    );
    showDialog(l("Cấu hình hàng loạt", "Bulk configuration"), f);
  }
  async function rolloutDetail(row) {
    const root = div(
      "stack",
      fact(t("status"), row.state),
      p(row.note || ""),
      table(
        [
          l("Thiết bị", "Device"),
          l("Mục tiêu", "Intent"),
          t("status"),
          l("Lý do", "Reason"),
        ],
        row.targets.map((tg) => [
          deviceName(tg.device_id),
          t(tg.intent),
          tg.status,
          tg.reason || "—",
        ]),
      ),
    );
    for (const target of row.targets.filter((t) => t.plan))
      root.append(
        card(
          deviceName(target.device_id),
          table(
            [l("Thông số", "Field"), l("Trước", "Before"), l("Sau", "After")],
            Object.entries(target.plan.expected).map(([k, v]) => [
              k,
              JSON.stringify(target.plan.previous[k]),
              JSON.stringify(v),
            ]),
          ),
          fact(
            l("Hết hạn xem trước", "Preview expires"),
            date(target.plan.expires_at),
          ),
        ),
      );
    const reload = async () => {
      await refresh();
      const current = work().rollout.find((r) => r.id === row.id);
      if (current) rolloutDetail(current);
    };
    root.append(btn(l("Cập nhật kết quả", "Refresh results"), reload));
    if (operator() && row.owner_id === state.me.user.id) {
      if (["DRAFT", "PREVIEWED", "CANARY_VERIFIED"].includes(row.state))
        root.append(
          btn(
            l("Đọc hiện tại & xem trước", "Read current settings & preview"),
            async () =>
              rolloutDetail(await api(`/rollouts/${row.id}/preview`, {})),
            "primary",
          ),
        );
      if (
        ["PREVIEWED", "CANARY_VERIFIED"].includes(row.state) &&
        row.digest &&
        row.targets
          .filter((t) => !t.command_id)
          .every((t) => t.status === "READY")
      ) {
        const checked = input("checkbox"),
          button = btn(
            row.state === "PREVIEWED"
              ? l("Gửi tới thiết bị đầu tiên", "Send canary")
              : l("Triển khai phần còn lại", "Release remaining targets"),
            async () => {
              if (!checked.checked) return;
              const result = await api(`/rollouts/${row.id}/confirm`, {
                digest: row.digest,
                stage: row.state === "PREVIEWED" ? "canary" : "remaining",
              });
              await refresh();
              rolloutDetail(result);
            },
            "primary",
          );
        button.disabled = true;
        checked.onchange = () => (button.disabled = !checked.checked);
        root.append(
          add(
            e("label", "", "check"),
            checked,
            e(
              "span",
              l(
                "Tôi đã kiểm tra mục tiêu và thay đổi nêu trên.",
                "I reviewed the targets and changes above.",
              ),
            ),
          ),
          button,
        );
      }
      if (!["VERIFIED", "CANCELLED_UNSENT_ONLY"].includes(row.state))
        root.append(
          btn(l("Dừng phần chưa gửi", "Cancel unsent targets"), async () => {
            const result = await api(`/rollouts/${row.id}/cancel`, {});
            await refresh();
            rolloutDetail(result);
          }),
        );
    }
    showDialog(row.name, root);
  }
  async function handoverView() {
    if (!state.site) return requireSite();
    const result = await api(`/sites/${state.site}/handover`),
      root = div("stack");
    root.append(
      card(
        l("Sẵn sàng bàn giao", "Handover readiness"),
        badge(
          result.ready
            ? l("Đủ checklist", "Checklist complete")
            : l("Cần hoàn tất kiểm tra", "Inspections required"),
          result.ready ? "good" : "warn",
        ),
        table(
          [
            l("Hạng mục", "Check"),
            l("Kết quả", "Result"),
            l("Bằng chứng", "Evidence"),
          ],
          result.checks.map((c) => [t(c.check), t(c.result), c.evidence]),
        ),
        p(
          l("Cảnh báo nghiêm trọng đang mở: ", "Open critical incidents: ") +
            result.blocking_incidents.length,
        ),
      ),
    );
    if (technical() && result.ready)
      root.append(
        btn(
          l("Ghi nhận bàn giao", "Record handover"),
          () => {
            const inspector = input("text", state.me.user.id),
              customer = input(),
              notes = e("textarea"),
              ack = input("checkbox");
            inspector.required = customer.required = ack.required = true;
            const f = form(async () => {
              await api("/handovers", {
                site_id: state.site,
                inspector_name: inspector.value,
                customer_name: customer.value,
                acknowledgement: ack.checked,
                notes: notes.value,
              });
              closeDialog();
              await refresh();
            });
            f.finish(
              field(l("Người kiểm tra", "Inspector"), inspector),
              field(
                l("Đại diện khách hàng", "Customer representative"),
                customer,
              ),
              field(l("Ghi chú", "Notes"), notes),
              add(
                e("label", "", "check"),
                ack,
                e(
                  "span",
                  l(
                    "Ghi nhận việc bàn giao dựa trên checklist hiện tại. Tên nhập không phải chữ ký số.",
                    "Record handover against the current checklist. Typed names are not digital signatures.",
                  ),
                ),
              ),
            );
            showDialog(l("Biên bản bàn giao", "Handover record"), f);
          },
          "primary",
        ),
      );
    root.append(
      btn(l("Mở báo cáo để in / PDF", "Open printable / PDF report"), () =>
        window.open(
          `/api/sites/${state.site}/report?format=html`,
          "_blank",
          "noopener",
        ),
      ),
    );
    root.append(
      card(
        l("Biên bản đã lưu", "Recorded handovers"),
        table(
          [
            l("Thời gian", "Time"),
            l("Kỹ thuật viên", "Inspector"),
            l("Khách hàng", "Customer"),
          ],
          rows("handover").map((r) => [
            date(r.created_at),
            r.inspector_name,
            r.customer_name,
          ]),
        ),
      ),
    );
    return root;
  }
  function analyticsView() {
    if (!state.site) return requireSite();
    const start = input(
        "date",
        new Date(Date.now() - 86400000).toISOString().slice(0, 10),
      ),
      end = input("date", new Date().toISOString().slice(0, 10)),
      out = div("stack");
    const fetchReport = async () => {
      const data = await api(
        `/sites/${state.site}/analytics?start=${encodeURIComponent(start.value + "T00:00:00Z")}&end=${encodeURIComponent(end.value + "T00:00:00Z")}`,
      );
      out.replaceChildren(
        card(
          l("Năng lượng theo bộ đếm", "Counter-based energy"),
          table(
            [l("Chỉ số", "Metric"), "kWh", l("Chất lượng", "Quality")],
            Object.entries(data.energy).map(([key, r]) => [
              key,
              r.wh == null ? "—" : number(r.wh / 1000),
              r.reason === "COUNTER_DELTA"
                ? l("Chênh lệch bộ đếm đã xác minh", "Verified counter delta")
                : l(
                    "Chưa đủ bộ đếm / độ phủ thời gian",
                    "Counter or period coverage required",
                  ),
            ]),
          ),
        ),
        card(
          l("Xử lý sự cố", "Incident response"),
          fact(
            l("Sự cố trong kỳ", "Incidents in period"),
            data.incidents.count,
          ),
          fact(
            l("Thời gian phản hồi trung bình", "Mean response time"),
            data.incidents.mean_response_seconds == null
              ? "—"
              : number(data.incidents.mean_response_seconds / 60) +
                  " " +
                  l("phút", "minutes"),
          ),
        ),
        notice(
          "Khoảng thời gian trên dùng UTC. Năng lượng cần bộ đếm tích lũy có nguồn rõ ràng; thiếu dữ liệu không thay bằng 0. Tiết kiệm và CO₂ cần phân bổ nguồn năng lượng đúng trước khi tính.",
          "The period above uses UTC. Energy needs traceable cumulative counters; missing readings are not zero. Savings and CO₂ require verified energy attribution.",
        ),
      );
    };
    return div(
      "stack",
      card(
        l("Báo cáo vận hành", "Operations report"),
        div(
          "toolbar",
          field(l("Từ ngày (UTC)", "From (UTC)"), start),
          field(l("Đến ngày, không gồm (UTC)", "Until, exclusive (UTC)"), end),
          btn(l("Tổng hợp", "Calculate"), fetchReport, "primary"),
        ),
        div(
          "row",
          btn(l("Xuất hồ sơ CSV", "Export records CSV"), () =>
            download(
              `/sites/${state.site}/report?format=csv`,
              "site-report.csv",
            ),
          ),
          btn(l("In / PDF", "Print / PDF"), () =>
            window.open(
              `/api/sites/${state.site}/report?format=html`,
              "_blank",
              "noopener",
            ),
          ),
        ),
      ),
      out,
    );
  }
  return { wrap, entityForm, plantView };
}
