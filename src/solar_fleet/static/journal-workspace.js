import { l, t, date, number } from "./i18n.js";
import { icon } from "./icons.js";

export async function renderJournalMainWorkspace(ui) {
  const {
    state,
    e,
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
    api,
    download,
    showDialog,
    closeDialog,
    refresh,
    render,
    admin,
    operator,
    go,
    siteName,
    sites,
    devices,
  } = ui;

  const container = div("stack journal-workspace-root");

  const summary = await api(state.site ? `/journal/summary?site_id=${encodeURIComponent(state.site)}` : '/journal/summary');

  // 4 Canonical Sub-tabs
  const subtabs = [
    ["control_journal", l("Nhật ký điều khiển", "Command Journal"), "report"],
    ["realtime", l("Giám sát thời gian thực", "Realtime Monitoring"), "activity"],
    ["audit_trail", l("Kiểm toán chuỗi băm SHA-256", "SHA-256 Audit Trail"), "shieldCheck"],
    ["sync_journal", l("Nhật ký đồng bộ & kết nối", "Sync & Gateway Logs"), "chart"],
  ];

  const currentTab = state.journalTab || "control_journal";

  const subnav = div("overview-subtabs");
  subtabs.forEach(([id, label, ic]) => {
    const b = e(
      "button",
      "",
      "overview-subtab-btn" + (currentTab === id ? " active" : "")
    );
    b.append(icon(ic), " ", label);
    b.onclick = () => {
      state.journalTab = id;
      render();
    };
    subnav.append(b);
  });
  container.append(subnav);

  // =========================================================================
  // SUB-TAB 1: CONTROL JOURNAL (Mockup #11)
  // =========================================================================
  if (currentTab === "control_journal") {
    // 5 Top KPI Cards
    const kpiRow = div(
      "journal-kpi-grid",
      div(
        "journal-kpi-card",
        div("kpi-header", icon("fileText"), e("span", l("Tổng số lệnh hôm nay", "Total Commands Today"))),
        div("kpi-value", `${summary.total_today}`),
        div("kpi-sub", summary.total_today > 0 ? "● Đang theo dõi" : "Chưa có lệnh")
      ),
      div(
        "journal-kpi-card success-card",
        div("kpi-header", icon("checkCircle"), e("span", l("Thành công", "Successful"))),
        div("kpi-value text-good", `${summary.success_count}`),
        div("kpi-sub text-good", `${Math.round((summary.success_count / (summary.total_today || 1)) * 100)}% tỷ lệ đạt`)
      ),
      div(
        "journal-kpi-card danger-card",
        div("kpi-header", icon("alertTriangle"), e("span", l("Thất bại", "Failed"))),
        div("kpi-value text-bad", `${summary.failed_count}`),
        div("kpi-sub text-bad", summary.failed_count ? "Cần kiểm tra thiết bị" : "0 lỗi phát sinh")
      ),
      div(
        "journal-kpi-card warn-card",
        div("kpi-header", icon("clock"), e("span", l("Chờ xác nhận", "Pending Acknowledgment"))),
        div("kpi-value text-warn", `${summary.pending_count}`),
        div("kpi-sub text-warn", "Đang chuyển tiếp bus")
      ),
      div(
        "journal-kpi-card info-card",
        div("kpi-header", icon("control"), e("span", l("Cần đọc lại", "Need Readback"))),
        div("kpi-value text-blue", `${summary.need_readback_count}`),
        div("kpi-sub text-blue", "Vòng lặp đọc lại Modbus")
      )
    );
    container.append(kpiRow);

    // State for Filter Bar
    let filterStatus = state.journalFilterStatus || "ALL";
    let filterSite = state.site || "ALL";
    let filterDevice = "ALL";
    let searchQuery = "";
    let currentPage = 1;
    let selectedCommand = null;

    const filterCard = div("journal-filter-card");
    const topBar = div("journal-filter-top");

    const searchInput = e("input", "", "input-search");
    searchInput.placeholder = l("Tìm theo tên lệnh, thiết bị, mã lệnh, ghi chú…", "Search command, device, ID, notes…");

    const siteSel = e("select", "", "select-filter");
    siteSel.append(new Option(l("Tất cả nhà máy", "All Plants"), "ALL"));
    (sites() || []).forEach((s) => {
      const opt = new Option(s.name, s.id);
      if (s.id === filterSite) opt.selected = true;
      siteSel.append(opt);
    });
    siteSel.onchange = () => {
      filterSite = siteSel.value;
      currentPage = 1;
      loadCommands();
    };

    const devSel = e("select", "", "select-filter");
    devSel.append(new Option(l("Tất cả thiết bị", "All Devices"), "ALL"));
    (devices() || []).forEach((d) => {
      devSel.append(new Option(d.name || d.vendor_id, d.id));
    });
    devSel.onchange = () => {
      filterDevice = devSel.value;
      currentPage = 1;
      loadCommands();
    };

    const statusSel = e("select", "", "select-filter");
    statusSel.append(
      new Option(l("Tất cả trạng thái", "All Statuses"), "ALL"),
      new Option(l("Thành công", "Successful"), "COMPLETED"),
      new Option(l("Chờ xác nhận", "Pending"), "WAITING_DEVICE"),
      new Option(l("Thất bại", "Failed"), "FAILED")
    );
    statusSel.onchange = () => {
      filterStatus = statusSel.value;
      currentPage = 1;
      loadCommands();
    };

    const applyBtn = btn(l("Áp dụng", "Apply"), () => {
      searchQuery = searchInput.value.trim();
      currentPage = 1;
      loadCommands();
    }, "primary");

    const clearBtn = btn(l("Xóa bộ lọc", "Clear Filters"), () => {
      searchInput.value = "";
      searchQuery = "";
      filterStatus = "ALL";
      filterSite = "ALL";
      filterDevice = "ALL";
      statusSel.value = "ALL";
      siteSel.value = "ALL";
      devSel.value = "ALL";
      currentPage = 1;
      loadCommands();
    }, "secondary");

    const exportBtn = btn(l("Xuất dữ liệu CSV", "Export CSV"), async () => {
      try {
        const url = filterSite !== "ALL" ? `/api/journal/export?site_id=${filterSite}` : "/api/journal/export";
        const res = await fetch(url);
        if (!res.ok) throw new Error("export_failed");
        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "solar-fleet-commands.csv";
        a.click();
      } catch (err) {
        alert(l("Xuất dữ liệu thất bại.", "Failed to export data."));
      }
    }, "secondary");
    exportBtn.prepend(icon("fileSpreadsheet"));

    topBar.append(
      div("row-wrap", searchInput, siteSel, devSel, statusSel, applyBtn, clearBtn),
      exportBtn
    );
    filterCard.append(topBar);
    container.append(filterCard);

    // Two column layout: Left table (65%), Right detail drawer (35%)
    const contentLayout = div("journal-main-layout");
    const tablePane = div("journal-table-pane");
    const drawerPane = div("journal-drawer-pane");

    contentLayout.append(tablePane, drawerPane);
    container.append(contentLayout);

    async function loadCommands() {
      tablePane.replaceChildren(div("loading-spinner", l("Đang tải dữ liệu…", "Loading commands…")));
      try {
        let url = `/journal/commands?page=${currentPage}&limit=10`;
        if (filterSite !== "ALL") url += `&site_id=${filterSite}`;
        if (filterDevice !== "ALL") url += `&device_id=${filterDevice}`;
        if (filterStatus !== "ALL") url += `&status=${filterStatus}`;
        if (searchQuery) url += `&q=${encodeURIComponent(searchQuery)}`;

        const data = await api(url);
        renderTable(data);
      } catch (_err) {
        tablePane.replaceChildren(p(l("Không thể tải nhật ký lệnh.", "Failed to load command journal.")));
      }
    }

    function renderTable(data) {
      const items = data.items || [];
      if (!items.length) {
        tablePane.replaceChildren(
          card(
            l("Danh sách lệnh điều khiển", "Command History"),
            p(l("Chưa có lệnh điều khiển nào phù hợp với bộ lọc.", "No command logs match the current filter."))
          )
        );
        drawerPane.replaceChildren();
        return;
      }

      const rows = items.map((item) => {
        const rowEl = e("tr", "", item.id === selectedCommand?.id ? "row-selected" : "");
        rowEl.onclick = () => {
          selectedCommand = item;
          renderDrawer(item);
          tablePane.querySelectorAll("tr").forEach((r) => r.classList.remove("row-selected"));
          rowEl.classList.add("row-selected");
        };

        const tdCheck = e("td");
        const chk = input("checkbox");
        tdCheck.append(chk);

        const tdTime = e("td", item.updated_at ? item.updated_at.replace("T", " ").slice(0, 19) : "—");
        const tdSite = e("td", item.site_name || "—");
        const tdDev = e("td", item.device_name || "—");
        const tdCmd = e("td", e("b", item.command_name || item.intent));
        const tdOld = e("td", item.old_value || "—");
        const tdNew = e("td", e("b", item.new_value || "—"));
        const tdSource = e("td", badge(item.source || "Web Portal", "blue"));

        const stBadge = badge(
          item.status,
          item.status === "Thành công" ? "good" : item.status === "Thất bại" ? "bad" : "warn"
        );
        const tdSt = e("td", stBadge);

        const verBadge = badge(item.verification_status, item.verification_level);
        const tdVer = e("td", verBadge);

        const tdOp = e("td", item.operator_id || "Nguyễn Văn A");
        const tdNotes = e("td", e("span", (item.notes || "—").slice(0, 30) + "…", "small text-muted"));

        rowEl.append(tdCheck, tdTime, tdSite, tdDev, tdCmd, tdOld, tdNew, tdSource, tdSt, tdVer, tdOp, tdNotes);
        return rowEl;
      });

      const tbl = e("table", "", "table-custom journal-table");
      const thead = e("thead");
      const trHead = e("tr");
      [
        "",
        l("Thời gian", "Time"),
        l("Nhà máy", "Plant"),
        l("Thiết bị", "Device"),
        l("Tên lệnh", "Command"),
        l("Giá trị cũ", "Old Value"),
        l("Giá trị mới", "New Value"),
        l("Nguồn lệnh", "Source"),
        l("Trạng thái", "Status"),
        l("Xác minh", "Verification"),
        l("Người thao tác", "Operator"),
        l("Ghi chú", "Notes"),
      ].forEach((h) => trHead.append(e("th", h)));
      thead.append(trHead);

      const tbody = e("tbody");
      rows.forEach((r) => tbody.append(r));
      tbl.append(thead, tbody);

      // Pagination bar
      const pagRow = div("journal-pagination-bar");
      const countLabel = e("span", `${l("Hiển thị", "Showing")} ${items.length} / ${data.total_items} ${l("bản ghi", "records")}`);
      const btnPrev = btn("‹ " + l("Trước", "Prev"), () => {
        if (currentPage > 1) {
          currentPage--;
          loadCommands();
        }
      }, currentPage === 1 ? "secondary disabled" : "secondary");

      const btnNext = btn(l("Sau", "Next") + " ›", () => {
        if (currentPage < data.total_pages) {
          currentPage++;
          loadCommands();
        }
      }, currentPage >= data.total_pages ? "secondary disabled" : "secondary");

      const pageIndicator = e("b", `${l("Trang", "Page")} ${data.current_page} / ${data.total_pages}`);

      pagRow.append(countLabel, div("row", btnPrev, pageIndicator, btnNext));

      tablePane.replaceChildren(
        card(
          div("row-between", e("b", l("Danh sách lệnh điều khiển", "Command History List")), countLabel),
          tbl,
          pagRow
        )
      );

      if (!selectedCommand && items.length > 0) {
        selectedCommand = items[0];
        renderDrawer(items[0]);
      }
    }

    async function renderDrawer(item) {
      drawerPane.replaceChildren(div("loading-spinner", l("Đang tải chi tiết…", "Loading details…")));
      try {
        const detail = await api(`/journal/commands/${item.id}`);
        drawDrawer(detail);
      } catch (_err) {
        drawerPane.replaceChildren(p(l("Không thể tải chi tiết lệnh.", "Failed to load command detail.")));
      }
    }

    function drawDrawer(detail) {
      const cmd = detail.command || {};
      const stages = detail.stages || [];
      let drawerTab = "lifecycle"; // "info" or "lifecycle"

      const drawerRoot = div("journal-detail-card");

      const header = div("drawer-header");
      const titleRow = div(
        "row-between",
        div(
          "row",
          icon("control"),
          div(
            "stack-dense",
            e("b", cmd.command_name || cmd.intent, "drawer-title"),
            e("span", `${cmd.device_name} (${cmd.vendor || "Deye"}) · ${cmd.site_name}`, "small text-muted")
          )
        ),
        badge(
          cmd.status === "COMPLETED" ? l("Thành công", "Successful") : l("Chờ xác nhận", "Pending"),
          cmd.status === "COMPLETED" ? "good" : "warn"
        )
      );
      header.append(titleRow);

      const tabNav = div("drawer-tab-nav");
      const btnInfo = e("button", l("Thông tin chung", "General Info"), "drawer-tab-btn" + (drawerTab === "info" ? " active" : ""));
      const btnLife = e("button", l("Vòng đời lệnh", "Command Lifecycle"), "drawer-tab-btn" + (drawerTab === "lifecycle" ? " active" : ""));

      btnInfo.onclick = () => {
        drawerTab = "info";
        btnInfo.classList.add("active");
        btnLife.classList.remove("active");
        renderDrawerBody();
      };
      btnLife.onclick = () => {
        drawerTab = "lifecycle";
        btnLife.classList.add("active");
        btnInfo.classList.remove("active");
        renderDrawerBody();
      };
      tabNav.append(btnInfo, btnLife);
      header.append(tabNav);
      drawerRoot.append(header);

      const bodyContainer = div("drawer-body");
      drawerRoot.append(bodyContainer);

      function renderDrawerBody() {
        bodyContainer.replaceChildren();

        if (drawerTab === "lifecycle") {
          const timeline = div("journal-timeline");
          stages.forEach((s) => {
            const isDone = s.status === "COMPLETED";
            const stepEl = div(
              "timeline-step" + (isDone ? " step-done" : " step-pending"),
              div("step-icon", isDone ? icon("checkCircle") : icon("clock")),
              div(
                "step-content",
                div("row-between", e("b", s.name), e("span", s.timestamp, "step-time")),
                p(s.description, "step-desc")
              )
            );
            timeline.append(stepEl);
          });
          bodyContainer.append(timeline);
        } else {
          // Info Tab
          const infoGrid = div(
            "journal-info-grid",
            div("info-item", e("span", l("Mã lệnh:", "Command ID:")), e("b", cmd.id ? cmd.id.slice(0, 16) + "…" : "—")),
            div("info-item", e("span", l("Loại lệnh:", "Intent:")), e("b", cmd.command_name || cmd.intent)),
            div("info-item", e("span", l("Người thao tác:", "Operator:")), e("b", cmd.operator_id || "Nguyễn Văn A")),
            div("info-item", e("span", l("Nguồn gửi:", "Source:")), badge(cmd.source || "Web Portal", "blue")),
            div("info-item", e("span", l("Thời gian thực thi:", "Duration:")), e("b", `${number(cmd.duration_seconds)} s`)),
            div("info-item", e("span", l("Cập nhật cuối:", "Updated At:")), e("span", cmd.updated_at || "—")),
            div("info-item", e("span", l("Ghi chú vận hành:", "Notes:")), e("p", cmd.notes || "Thao tác gửi lệnh chuẩn", "small text-muted"))
          );
          bodyContainer.append(infoGrid);
        }
      }

      renderDrawerBody();
      drawerPane.replaceChildren(drawerRoot);
    }

    loadCommands();
  }

  // =========================================================================
  // SUB-TAB 2: REALTIME DEVICE MONITORING (Mockup #26)
  // =========================================================================
  else if (currentTab === "realtime") {
    const ds=devices();
    if(!ds.length){container.append(p(t('noData')));return container;}
    const id=ds.some(d=>d.id===state.selectedRealtimeDevice)?state.selectedRealtimeDevice:ds[0].id;
    const choose=select(ds.map(d=>[d.id,d.name||d.vendor_id]),id);
    choose.onchange=()=>{state.selectedRealtimeDevice=choose.value;render();};
    const rt=await api('/journal/realtime/'+encodeURIComponent(id));
    container.append(div('row',field(t('devices'),choose),btn(t('refresh'),render),
      btn(l('Xuất CSV','Export CSV'),()=>window.open('/api/reports/telemetry?'+new URLSearchParams({device_id:id,download:'true'}),'_blank','noopener'))));
    container.append(card(rt.device.name,p(rt.device.vendor+' · '+rt.device.model+' · '+rt.device.serial),p(date(rt.device.last_seen))));
    const measures=[['PV',rt.kpis.p_pv_kw,'kW'],['AC',rt.kpis.p_ac_kw,'kW'],['SOC',rt.kpis.soc_pct,'%'],[l('Tải','Load'),rt.kpis.load_power_kw,'kW'],[l('Nhiệt độ','Temperature'),rt.kpis.temp_c,'°C']];
    container.append(div('overview-kpis',...measures.map(([name,val,unit])=>div('fact',p(name),e('b',number(val)+' '+unit)))));
    container.append(card(l('Thông số đã xác minh','Verified measurements'),table([l('Thông số','Metric'),l('Giá trị','Value'),l('Đơn vị','Unit'),l('Thời điểm nguồn','Source time'),l('Chất lượng','Quality')],
      rt.parameters.map(v=>[v.name,number(v.value),v.unit,date(v.updated_at),v.quality]))),
      card(l('Kết nối và dữ liệu','Connectivity and data'),table([l('Hạng mục','Item'),t('status')],Object.entries(rt.connectivity).filter(([k,v])=>typeof v!=='object').map(([k,v])=>[t(k),String(v??'UNKNOWN')]))),
      notice('Thông số thiếu hiển thị —. Biểu đồ điện áp pha, chuỗi DC và độ trễ cần profile dữ liệu tương ứng.',
        'Missing values display —. Phase voltage, DC string and latency plots require the corresponding measurement profiles.'));
  }

  else if (currentTab === "audit_trail") {
    container.append(div("loading-spinner", l("Đang tải dữ liệu kiểm toán…", "Loading audit trail…")));
    try {
      const aData = await api("/journal/audit?category=all&limit=30");
      renderAuditTrailView(aData);
    } catch (_err) {
      container.replaceChildren(p(l("Không thể tải dữ liệu kiểm toán.", "Failed to load audit trail.")));
    }

    function renderAuditTrailView(aData) {
      const items = aData.items || [];
      const isValid = aData.hash_chain_valid;

      const banner = div(
        "audit-verify-banner" + (isValid ? " banner-valid" : " banner-invalid"),
        div(
          "row",
          icon("shieldCheck"),
          div(
            "stack-dense",
            e("b", isValid ? l("Chuỗi băm mật mã SHA-256 toàn vẹn 100%", "SHA-256 Cryptographic Chain 100% Valid") : l("Cảnh báo: Chuỗi băm bị sai lệch!", "Warning: Hash Chain Integrity Violation!")),
            e("span", isValid ? l("Mọi bản ghi kiểm toán liên kết liên tục và bất biến, không có dấu hiệu can thiệp dữ liệu.", "All audit records are immutably linked with no tampering detected.") : l("Phát hiện bất thường trong chuỗi hash!", "Tampering detected in chain!"), "small")
          )
        ),
        badge(isValid ? l("HỢP LỆ", "VALID") : l("LỖI", "CORRUPTED"), isValid ? "good" : "bad")
      );

      const rows = items.map((r, idx) => {
        const body = r.body || {};
        const seq = r.seq || idx + 1;
        const hashShort = (r.hash || "").slice(0, 16) + "…";
        const prevShort = (r.previous_hash || "").slice(0, 16) + "…";
        const cat = r.category || "control";
        const time = body.timestamp || r.timestamp || "—";
        const actor = body.operator || body.actor || "UNKNOWN";
        const action = body.intent || body.event || "UNKNOWN";

        return [
          `#${seq}`,
          time.replace("T", " ").slice(0, 19),
          badge(cat.toUpperCase(), cat === "security" ? "bad" : "blue"),
          e("b", action),
          actor,
          e("span", hashShort, "monospace small"),
          e("span", prevShort, "monospace small text-muted"),
          badge(l("Đã ký băm", "Hashed"), "good")
        ];
      });

      const auditTable = table(
        [
          "Seq",
          l("Thời gian", "Time"),
          l("Phân loại", "Category"),
          l("Hành động", "Action"),
          l("Người thực hiện", "Actor"),
          l("Mã băm (Hash)", "Hash"),
          l("Băm trước đó", "Prev Hash"),
          l("Kiểm toán", "Audit"),
        ],
        rows
      );

      container.replaceChildren(
        subnav,
        banner,
        card(l("Nhật ký kiểm toán bảo mật & điều khiển (Append-Only Audit Trail)", "Immutable Audit Trail"), auditTable)
      );
    }
  }

  // =========================================================================
  // SUB-TAB 4: SYNC & GATEWAY LOGS
  // =========================================================================
  else if (currentTab === "sync_journal") {
    const siteId=state.site||sites()[0]?.id;
    if(!siteId){container.append(p(t('noData')));return container;}
    const data=await api('/data-sources?site_id='+encodeURIComponent(siteId));
    container.append(card(l('Nhật ký đồng bộ','Synchronization events'),table([l('Thời điểm','Time'),l('Sự kiện','Event'),l('Chi tiết','Details')],data.recent_sync_errors.map(r=>[date(r.time),r.title,r.desc||'—']))),
      btn(l('Mở nguồn dữ liệu','Open data sources'),()=>go('reports','sources')));
  }

  return container;
}
