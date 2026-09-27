// Administration views share persisted accounts, site metadata and discovery.
import { icon } from "./icons.js";
import { l, t, date, number } from "./i18n.js";

export async function renderSettingsWorkspace(ctx) {
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
    admin,
    go,
    siteName,
    sites,
    toast,
    userForm,
    accessForm,
    resetPasswordForm,
    integrationForm,
  } = ctx;

  const activeTab = state.tab || (admin() ? "users" : "vendors");

  const navTabs = [
    ["users", l("Người dùng & phân quyền", "Users & RBAC"), "user"],
    ["vendors", l("Tài khoản hãng & kết nối", "Vendor accounts"), "cloud"],
    ["site_config", l("Cấu hình nhà máy", "Site configuration"), "settings"],
    ["device_onboarding", l("Liên kết thiết bị mới", "Device onboarding"), "device"],
    ["security", l("Nhật ký bảo mật", "Security log"), "shield"],
    ["evidence", l("Tài liệu & tương thích", "Compatibility & evidence"), "report"],
  ];

  const visibleTabs = navTabs.filter(([key]) => {
    if (!admin()) {
      return ["vendors", "evidence"].includes(key);
    }
    return true;
  });

  const root = div("stack settings-workspace-root");

  // Top header with title, subtitle, and subtabs
  const headerCard = div(
    "card settings-header-card",
    div(
      "row space-between align-center",
      div(
        "stack gap-xs",
        div(
          "row align-center gap-sm",
          icon("settings"),
          e("h2", l("Cài đặt hệ thống & Quản trị người dùng", "System Settings & Administration"), "workspace-title"),
          badge(admin() ? l("Quản trị cấp cao (Admin)", "Administrator") : l("Chế độ kỹ thuật", "Technical Mode"), "blue"),
        ),
        p(
          l(
            "Quản lý định danh người dùng, ma trận phân quyền RBAC, kết nối API Cloud các hãng biến tần, cấu hình nhà máy và liên kết thiết bị theo tiêu chuẩn SCADA.",
            "Manage user identities, RBAC matrix, inverter vendor API connections, plant configuration, and device commissioning records.",
          ),
          "text-muted text-sm",
        ),
      ),
      div(
        "row gap-sm align-center",
        btn(
          l("Tải lại dữ liệu", "Refresh"),
          async () => {
            if (refresh) await refresh();
          },
          "secondary",
        ),
      ),
    ),
    div("divider-line"),
    tabs(
      visibleTabs.map(([key, label]) => [key, label]),
      activeTab,
      (key) => go("settings", key),
    ),
  );
  root.append(headerCard);

  // Tab router
  if (activeTab === "users" && admin()) {
    root.append(await renderUsersTab());
  } else if (activeTab === "vendors" || activeTab === "connections") {
    root.append(await renderVendorsTab());
  } else if (activeTab === "site_config" && admin()) {
    root.append(await renderSiteConfigTab());
  } else if (activeTab === "device_onboarding" && admin()) {
    root.append(await renderDeviceOnboardingTab());
  } else if (activeTab === "security" && admin()) {
    root.append(await renderSecurityTab());
  } else if (activeTab === "evidence") {
    root.append(await renderEvidenceTab());
  } else {
    root.append(await renderVendorsTab());
  }

  return root;

  // --------------------------------------------------------------------------
  // SUBTAB 1: USERS & RBAC MATRIX (Mockup #19)
  // --------------------------------------------------------------------------
  async function renderUsersTab() {
    const container = div("stack gap-md");

    const [summary, usersData, rRes, cRes, sRes] = await Promise.all([
      api('/admin/summary'), api('/admin/users?limit=25'), api('/admin/roles-matrix'),
      api('/admin/cloud-accounts'), api('/admin/security-log?limit=5'),
    ]);
    const rolesMatrix=rRes.roles, cloudAccounts=cRes.items, securityLogs=sRes.entries;

    // 4 KPI Cards Grid
    const kpiGrid = div(
      "grid grid-4 gap-md settings-kpi-grid",
      div(
        "card kpi-card",
        div("row space-between align-center", div("stack", e("span", l("Tổng người dùng", "Total Users"), "kpi-label"), e("b", String(summary.total_users), "kpi-value")), div("kpi-icon-wrap blue", icon("user"))),
        div("kpi-meta text-xs text-muted", `${summary.active_users} ${l("đang hoạt động", "active")}, ${summary.total_users - summary.active_users} ${l("tạm khóa", "disabled")}`),
      ),
      div(
        "card kpi-card",
        div("row space-between align-center", div("stack", e("span", l("Nhóm vai trò RBAC", "RBAC Role Groups"), "kpi-label"), e("b", String(summary.roles_count), "kpi-value")), div("kpi-icon-wrap orange", icon("shield"))),
        div("kpi-meta text-xs text-muted", l("Vai trò ứng dụng; quyền thiết bị được kiểm tra riêng", "Application roles; device permissions checked separately")),
      ),
      div(
        "card kpi-card",
        div("row space-between align-center", div("stack", e("span", l("Tài khoản Cloud liên kết", "Linked Cloud Accounts"), "kpi-label"), e("b", String(summary.linked_cloud_accounts), "kpi-value")), div("kpi-icon-wrap green", icon("cloud"))),
        div("kpi-meta text-xs text-muted", l("Kết nối đồng bộ đa hãng", "Multi-vendor sync connections")),
      ),
      div(
        "card kpi-card",
        div("row space-between align-center", div("stack", e("span", l("Quyền nhạy cảm được cấp", "Sensitive Privileges"), "kpi-label"), e("b", String(summary.sensitive_perms_count), "kpi-value")), div("kpi-icon-wrap red", icon("lock"))),
        div("kpi-meta text-xs text-muted", l("Yêu cầu kiểm toán định kỳ", "Requires periodic audit log review")),
      ),
    );
    container.append(kpiGrid);

    // 2-Column Main Layout (Left: Users Table with search/filters/pagination, Right: RBAC Matrix & Org accounts)
    const mainCols = div("row gap-md settings-2col-layout");

    // Left Column: User Management Table
    const leftCol = div("stack gap-md flex-6");
    const userTableCard = div("card stack gap-sm");

    // Table Header with search, filters, actions
    const tableHeader = div(
      "row space-between align-center wrap gap-sm",
      div(
        "row align-center gap-sm",
        icon("user"),
        e("b", l("Danh sách người dùng hệ thống", "System Users Directory"), "card-title"),
        badge(`${usersData.items.length} ${l("tài khoản", "accounts")}`, "gray"),
      ),
      div(
        "row gap-sm align-center",
        btn(
          l("+ Thêm người dùng", "+ Add User"),
          () => {
            if (userForm) userForm();
          },
          "primary",
        ),
        btn(
          l("Xuất CSV", "Export CSV"),
          () => {
            window.location.href = "/api/admin/export-users";
          },
          "secondary",
        ),
      ),
    );

    // Search and Filter Bar
    const searchInput = input("text", "", l("Tìm kiếm theo tên, tài khoản, email…", "Search name, user ID, email…"));
    searchInput.classList.add("input-search");

    const roleFilter = select([['',l('Tất cả vai trò','All roles')],
      ...rolesMatrix.map(r=>[r.role,l(r.name_vi,r.role)])]);

    const statusFilter = select([
      ["", l("Tất cả trạng thái", "All status")],
      ["active", l("Đang hoạt động", "Active")],
      ["disabled", l("Tạm khóa", "Disabled")],
    ]);

    const filterBar = div("row gap-sm align-center wrap", div("flex-grow", searchInput), roleFilter, statusFilter);

    // Dynamic User Table container
    const tableContainer = div("table-responsive");

    function renderUserRows(items) {
      if (!items || items.length === 0) {
        return div("empty-state text-center p-lg", p(l("Không tìm thấy người dùng nào phù hợp", "No matching users found"), "text-muted"));
      }

      return table(
        [
          l("Tài khoản / Định danh", "Account / Identity"),
          l("Vai trò RBAC", "RBAC Role"),
          l("Phạm vi trạm", "Scope"),
          l("Trạng thái", "Status"),
          l("Xác thực 2FA", "2FA Security"),
          l("Đăng nhập cuối", "Last Login"),
          l("Thao tác", "Actions"),
        ],
        items.map((u) => {
          const roleBadgeColor =
            u.role === "admin" ? "blue" : u.role === "engineer" ? "cyan" : u.role === "installer" ? "green" : u.role === "operator" ? "orange" : "gray";

          const isMe = state.me && state.me.user && state.me.user.id === u.id;

          const actionRow = isMe
            ? div("badge gray", l("Tài khoản hiện tại", "Current session"))
            : div(
                "row gap-xs",
                btn(
                  l("Phân quyền", "Access"),
                  () => {
                    if (accessForm) accessForm(u);
                  },
                  "small-btn secondary",
                ),
                btn(
                  l("Đổi mật khẩu", "Reset pwd"),
                  () => {
                    if (resetPasswordForm) resetPasswordForm(u);
                  },
                  "small-btn secondary",
                ),
                btn(
                  u.active ? l("Khóa", "Disable") : l("Mở", "Enable"),
                  async () => {
                    try {
                      await api(`/users/${encodeURIComponent(u.id)}/enabled`, { enabled: !u.active });
                      if (toast) toast(l(`Đã cập nhật trạng thái ${u.id}`, `Updated status for ${u.id}`));
                      if (refresh) await refresh();
                    } catch (err) {
                      showDialog(l("Lỗi cập nhật", "Update error"), p(err.message));
                    }
                  },
                  u.active ? "small-btn danger" : "small-btn success",
                ),
              );

          return [
            div(
              "stack gap-none",
              e("b", u.id, "user-name"),
              u.name ? e("span", u.name, "text-xs text-muted") : null,
            ),
            badge(l(u.role_name_vi || u.role, u.role), roleBadgeColor),
            u.site_ids && u.site_ids.includes("*")
              ? badge(l("Toàn bộ trạm", "All sites"), "blue-soft")
              : div("text-xs text-muted", (u.site_names || []).join(", ") || (u.site_ids || []).join(", ") || "—"),
            badge(u.active ? l("Đang hoạt động", "Active") : l("Tạm khóa", "Disabled"), u.active ? "green" : "red"),
            badge(l("Chưa triển khai", "Not implemented")),
            div("text-xs text-muted", u.last_login_at ? date(u.last_login_at) : l("Chưa đăng nhập", "Never")),
            actionRow,
          ];
        }),
      );
    }

    // Filter event handler
    async function applyUserFilters() {
      const q = searchInput.value.trim();
      const r = roleFilter.value;
      const s = statusFilter.value;
      try {
        const queryParams = new URLSearchParams();
        if (q) queryParams.set("q", q);
        if (r) queryParams.set("role", r);
        if (s) queryParams.set("status", s);
        const filtered = await api(`/admin/users?${queryParams.toString()}`);
        tableContainer.replaceChildren(renderUserRows(filtered.items || []));
      } catch (err) {
        tableContainer.replaceChildren(p(err.message, "bad"));
      }
    }

    searchInput.addEventListener("input", () => applyUserFilters());
    roleFilter.addEventListener("change", () => applyUserFilters());
    statusFilter.addEventListener("change", () => applyUserFilters());

    tableContainer.append(renderUserRows(usersData.items || []));

    userTableCard.append(
      tableHeader,
      filterBar,
      div("divider-line"),
      tableContainer,
      notice(
        "Vai trò quản trị viên quản lý danh sách tài khoản và phân quyền nhà máy. Các quyền can thiệp phần cứng nhạy cảm (như mở khóa lưới điện hoặc nạp xả cưỡng bức) cần khả năng thiết bị đã nghiệm thu, phân quyền và đọc lại; chuỗi kiểm toán cục bộ có thể kiểm tra.",
        "Administrators manage accounts and plant permissions. Sensitive hardware control operations (e.g. grid code unlock, forced dispatch) require an accepted device capability, authorization and readback; the local audit chain can be verified.",
      ),
    );
    leftCol.append(userTableCard);

    // Right Column: Roles Matrix & Org-level Cloud Accounts
    const rightCol = div("stack gap-md flex-4");

    // Card 1: RBAC Roles & Permissions Matrix
    const rbacCard = div(
      "card stack gap-sm",
      div(
        "row space-between align-center",
        div("row align-center gap-xs", icon("shield"), e("b", l("Ma trận vai trò & quyền hạn (RBAC)", "Roles & Permissions Matrix"), "card-title")),
        badge(`${rolesMatrix.length} ${l("vai trò", "roles")}`, "blue-soft"),
      ),
      p(
        l(
          "Phân quyền theo nguyên tắc đặc quyền tối thiểu (PoLP). Không có tài khoản nào được tự ý vượt quyền nếu thiếu khóa ủy quyền.",
          "Principle of Least Privilege (PoLP) enforced across all telemetry and control dispatch routes.",
        ),
        "text-xs text-muted",
      ),
      div(
        "table-responsive",
        table(
          [
            l("Vai trò", "Role"),
            l("Xem", "View"),
            l("Lệnh", "Ctrl"),
            l("Soạn TOU", "TOU draft"),
            l("Lưới", "Grid"),
            l("Soạn lệnh loạt", "Bulk draft"),
            l("Khóa", "Keys"),
            l("Log", "Log"),
          ],
          rolesMatrix.map((r) => {
            const p = r.permissions || {};
            const cell = (val) => (val ? icon("check") : icon("close"));
            return [
              div("stack gap-none", e("b", l(r.name_vi, r.role), "text-xs"), e("span", r.role, "text-xs text-muted")),
              cell(p.view_data),
              cell(p.quick_control),
              cell(p.edit_tou),
              cell(p.grid_settings),
              cell(p.bulk_rollout),
              cell(p.manage_credentials),
              cell(p.view_security_log),
            ];
          }),
        ),
      ),
    );
    rightCol.append(rbacCard);

    // Card 2: Org-level Cloud Accounts List
    const cloudCard = div(
      "card stack gap-sm",
      div(
        "row space-between align-center",
        div("row align-center gap-xs", icon("cloud"), e("b", l("Tài khoản Cloud tổ chức", "Org Cloud Accounts"), "card-title")),
        btn(
          l("Quản lý hãng →", "Manage vendors →"),
          () => go("settings", "vendors"),
          "small-btn link",
        ),
      ),
      div(
        "stack gap-xs",
        ...cloudAccounts.slice(0, 5).map((acc) =>
          div(
            "row space-between align-center p-xs border-bottom",
            div(
              "row align-center gap-sm",
              icon("cloud"),
              div(
                "stack gap-none",
                e("b", acc.brand_name || acc.vendor, "text-sm"),
                e("span", acc.account_mask || acc.name, "text-xs text-muted"),
              ),
            ),
            div(
              "row align-center gap-xs",
              badge(`${acc.plants_count || 0} ${l("trạm", "plants")}`, "gray"),
              badge(
                acc.status === "online" ? l("Đang kết nối", "Online") : l("Chưa kết nối", "Disconnected"),
                acc.status === "online" ? "green" : "gray",
              ),
            ),
          ),
        ),
      ),
    );
    rightCol.append(cloudCard);

    // Card 3: Recent Security Audit Log
    const auditCard = div(
      "card stack gap-sm",
      div(
        "row space-between align-center",
        div("row align-center gap-xs", icon("lock"), e("b", l("Nhật ký bảo mật gần đây", "Recent Security Audit"), "card-title")),
        badge(
          summary.hash_chain_valid ? l("SHA-256 Hợp lệ", "SHA-256 Valid") : l("Cần kiểm tra", "Audit Alert"),
          summary.hash_chain_valid ? "green" : "red",
        ),
      ),
      div(
        "stack gap-xs",
        ...securityLogs.map((log) =>
          div(
            "row space-between align-center p-xs border-bottom text-xs",
            div(
              "stack gap-none",
              e("b", log.action_label_vi || log.event || log.action, "text-xs"),
              e("span", `${log.user_id || "system"} · ${date(log.timestamp)}`, "text-muted"),
            ),
            badge(log.ip_address || "127.0.0.1", "gray"),
          ),
        ),
      ),
      btn(
        l("Xem toàn bộ nhật ký kiểm toán →", "View full audit log →"),
        () => go("settings", "security"),
        "small-btn secondary",
      ),
    );
    rightCol.append(auditCard);

    mainCols.append(leftCol, rightCol);
    container.append(mainCols);
    return container;
  }

  // --------------------------------------------------------------------------
  // SUBTAB 2: VENDOR CLOUD ACCOUNTS & DIAGNOSTIC TEST PANEL (Mockup #21)
  // --------------------------------------------------------------------------
  async function renderVendorsTab() {
    return card(l("Tài khoản hãng", "Vendor accounts"),
      btn(l("Mở tài khoản và kết nối", "Open accounts and connections"), () => go("settings", "connections")));
  }

  async function renderSiteConfigTab() {
    const currentSiteId = state.site || sites()[0]?.id;
    if (!currentSiteId) return card(l("Cấu hình nhà máy", "Plant configuration"), p(t("noData")));
    const {config: cfg, checklist} = await api('/admin/site-config/' + encodeURIComponent(currentSiteId));
    const picker = select(sites().map(s => [s.id, s.name]), currentSiteId);
    picker.onchange = async () => {state.site = picker.value; await refresh();};
    const entity = input('text', cfg.ownership.entity_name || '');
    const contract = input('text', cfg.ownership.ppa_code || '');
    const notes = input('text', cfg.ownership.tech_lead || '');
    const f = form(async () => {
      await api('/admin/site-config/' + encodeURIComponent(currentSiteId), {
        site_id:currentSiteId, ownership:{entity_name:entity.value.trim(), ppa_code:contract.value.trim(), tech_lead:notes.value.trim()}
      });
      await refresh();
    });
    f.finish(field(l('Chủ sở hữu', 'Owner'), entity), field(l('Hợp đồng', 'Contract'), contract), field(l('Phụ trách kỹ thuật', 'Technical contact'), notes));
    const planning = await api('/sites/' + encodeURIComponent(currentSiteId) + '/planning-configuration');
    const planningInput = document.createElement('textarea');
    planningInput.rows = 12;
    planningInput.setAttribute('aria-label', 'Advisory planning configuration JSON');
    planningInput.value = JSON.stringify(planning.configuration, null, 2);
    const planningForm = form(async () => {
      await api('/sites/' + encodeURIComponent(currentSiteId) + '/planning-configuration', JSON.parse(planningInput.value));
      await refresh();
    });
    planningForm.finish(planningInput);
    return div('stack', field(t('plants'), picker),
      notice('Thông tin lưu tại đây là hồ sơ nhà máy. Điều khiển, lịch, biểu giá và nguồn dữ liệu dùng các luồng riêng bên dưới.',
        'This page stores plant records. Use the linked workflows for control, schedules, tariffs and data sources.'),
      card(l('Quyền sở hữu và liên hệ', 'Ownership and contacts'), f),
      card(l('Ranh giới đo và cấu hình quy hoạch', 'Measurement boundaries and planning configuration'),
        p(l('Lưu cấu hình tư vấn, không kích hoạt điều khiển. Chỉ quản trị viên được lưu. Biểu giá USD cần 24 giờ UTC liên tiếp và nguồn gốc; thiếu dữ liệu đo vẫn chặn tính toán.',
          'Advisory configuration only; no dispatch enabled. Only administrators can save. USD prices require 24 consecutive UTC hours and provenance; missing observations still block calculation.')),
        p('dispatch_config: capacity_kwh, usable_kwh, max_charge_kw, max_discharge_kw, charge_efficiency, discharge_efficiency, min_soc_pct, max_soc_pct, reserve_soc_pct, replacement_cost_usd, rated_cycle_life, currency, tariff_source, hourly_prices [{timestamp, import_per_kwh, export_per_kwh}]. Set both dispatch_device_id and dispatch_config to null to clear dispatch configuration.'),
        planningForm),
      card(l('Cấu hình vận hành', 'Operating configuration'), div('row wrap',
        btn(l('Biểu giá điện', 'Electricity tariffs'), () => go('reports', '', 'tariff')),
        btn(l('Lịch / TOU', 'Schedules / TOU'), () => go('operations', 'schedules')),
        btn(l('Pin, EPS và giới hạn phát', 'Battery, EPS and export limits'), () => go('operations', 'control')),
        btn(l('Nguồn dữ liệu', 'Data sources'), () => go('settings', '', 'source_policy')),
        btn(l('Chính sách thông báo', 'Notification policies'), () => go('settings', '', 'notification_policy')))),
      card(l('Hồ sơ đã lưu', 'Saved records'), table([l('Hạng mục', 'Section'), t('status')], checklist.map(c=>[c.item,c.status])), raw(l('Chi tiết bản nháp', 'Draft details'), cfg)));
  }

  async function renderDeviceOnboardingTab() {
    const all = state.fleet.devices.filter(d => !state.site || d.site_id === state.site);
    const rename = d => {
      const name = input('text', d.name || d.vendor_id);name.required = true;
      const f = form(async () => {
        await api('/admin/devices/onboard-complete', {site_id:d.site_id, vendor:d.identity.vendor,
          serial_number:d.vendor_id, integration_id:d.integration_id, device_name:name.value.trim()});
        closeDialog(); await refresh();
      });
      f.finish(field(t('name'), name)); showDialog(l('Đặt tên thiết bị', 'Name equipment'), f);
    };
    return div('stack', notice('Kết nối tài khoản hãng rồi đồng bộ danh mục để nhận diện thiết bị. Đặt tên không thay thế nghiệm thu hoặc thay đổi cấu hình điện.',
      'Connect a vendor account and synchronize its inventory to identify equipment. Naming equipment does not commission it or change electrical settings.'),
      card(l('1. Kết nối và nhận diện', '1. Connect and discover'), btn(l('Mở tài khoản hãng', 'Open vendor accounts'),()=>go('settings','connections'))),
      card(l('2. Thiết bị đã được nhận diện', '2. Discovered equipment'), table([t('name'),t('plants'),l('Hãng / Model', 'Vendor / Model'),'Serial',l('Thao tác','Action')],
        all.map(d=>[d.name||d.vendor_id,siteName(d.site_id),d.identity.vendor+' / '+d.identity.model,d.vendor_id,btn(t('edit'),()=>rename(d))]))),
      card(l('3. Kiểm tra và bàn giao', '3. Review and handover'), btn(l('Mở hồ sơ bàn giao', 'Open handover records'),()=>go('operations','','handover'))));
  }

  async function renderSecurityTab() {
    const container = div("stack gap-md");

    const auditData = await api("/admin/security-log?limit=50");

    const bannerCard = div(
      "card row space-between align-center wrap gap-sm",
      div(
        "row align-center gap-sm",
        icon("shield"),
        div(
          "stack gap-none",
          e("b", l("Nhật ký kiểm toán an ninh & Bất biến SHA-256", "Security Audit Journal & Immutable Hash Chain"), "card-title"),
          e("span", l("Mỗi hành vi thay đổi quyền, đổi mật khẩu và lệnh điều khiển phần cứng đều được ký băm mật mã học.", "All credential changes, access grants and hardware writes are cryptographically hash-chained."), "text-xs text-muted"),
        ),
      ),
      badge(
        auditData.hash_chain_valid ? l("Chuỗi băm hợp lệ (SHA-256 Valid)", "Hash Chain Valid") : l("Cảnh báo: Chuỗi kiểm toán bị gián đoạn", "Chain Alert"),
        auditData.hash_chain_valid ? "green" : "red",
      ),
    );
    container.append(bannerCard);

    const logTableCard = div(
      "card stack gap-sm",
      div(
        "row space-between align-center",
        div("row align-center gap-xs", icon("lock"), e("b", l("Bản ghi kiểm toán gần nhất", "Recent Audit Records"), "card-title")),
        badge(`${auditData.entries.length} ${l("bản ghi", "records")}`, "gray"),
      ),
      div(
        "table-responsive",
        table(
          [
            l("Thời gian (UTC)", "Timestamp (UTC)"),
            l("Tài khoản thực hiện", "Operator"),
            l("Hành động / Sự kiện", "Action / Event"),
            l("Địa chỉ IP", "IP Address"),
            l("Chi tiết thao tác", "Details"),
            l("Mã băm SHA-256", "Row Hash Preview"),
          ],
          auditData.entries.map((r) => [
            div("text-xs text-muted", date(r.timestamp)),
            div("font-semibold text-xs", r.user_id || "system"),
            badge(r.action_label_vi || r.event || r.action, "blue-soft"),
            div("text-xs text-muted", r.ip_address || "—"),
            div("text-xs truncate-text", r.details ? JSON.stringify(r.details) : "—"),
            e("code", r.row_hash ? r.row_hash.slice(0, 12) + "…" : "—", "text-xs text-muted"),
          ]),
        ),
      ),
    );
    container.append(logTableCard);
    return container;
  }

  // --------------------------------------------------------------------------
  // SUBTAB 6: EVIDENCE & COMPATIBILITY REGISTRY (Retained from research)
  // --------------------------------------------------------------------------
  async function renderEvidenceTab() {
    const container = div("stack gap-md");

    let data = { sources: [], native: {}, vendors: {} };
    try {
      data = (await api("/research")) || data;
    } catch (err) {
      console.warn("Failed to fetch research evidence:", err);
    }

    container.append(
      notice(
        "Mức tương thích được xác định theo model + datalogger + firmware + vùng + tài khoản. Logo hãng không phải bằng chứng điều khiển được.",
        "Compatibility is defined by exact model, logger, firmware, region and account. A vendor logo does not prove control support.",
      ),
      card(
        l("Hồ sơ nghiên cứu tương thích", "Compatibility Research Registry"),
        div(
          "stack gap-sm",
          ...(data.sources || []).map((s) =>
            div(
              "card stack gap-xs bg-subtle p-sm border-rounded",
              div(
                "row space-between align-center",
                e("b", s.title || s.id, "text-sm"),
                badge(s.evidence_grade || "UNKNOWN", "blue-soft"),
              ),
              p(`${s.publisher || ""} · ${s.retrieved_date || ""}`, "text-xs text-muted"),
              raw(l("Phạm vi & câu hỏi còn mở", "Scope & open questions"), {
                id: s.id,
                products: s.applicable_products,
                claims: s.claims,
                open_questions: s.open_questions,
              }),
            ),
          ),
        ),
      ),
    );
    return container;
  }
}
