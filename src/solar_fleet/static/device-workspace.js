import { l, t, date, number, language } from "./i18n.js";
import { icon } from "./icons.js";
import { renderModelLibrary } from "./model-workspace.js";
import { equipmentPower } from './device-report.js';

export async function renderDevicesMainWorkspace(ui) {
  const { state, e, div, p, btn, badge, card, table, select, input, field, fact, notice, showDialog, closeDialog, api, go, sites, deviceDetail } = ui;
  const button = (...args) => btn(...args);
  const container = div("stack device-workspace-container");

  const scopeQuery = state.site ? '?site_id=' + encodeURIComponent(state.site) : '';
  const overviewData = await api('/fleet/devices-overview' + scopeQuery);

  const protocolTabs = [
    ["solis_mqtt", l("Solis MQTT & HA (Cầu nối)", "Solis MQTT & HA Bridge")],
    ["goodwe_sems", l("GoodWe SEMS Portal (Cloud)", "GoodWe SEMS Portal (Cloud)")],
    ["growatt_sph", l("Growatt SPH Hybrid (TOU & BMS)", "Growatt SPH Hybrid (TOU & BMS)")],
    ["solis_hybrid", l("Solis Hybrid S6 (Lưu trữ & TOU)", "Solis Hybrid S6 (Storage & TOU)")],
    ["deye_hybrid", l("Deye Hybrid SUN (Lưu trữ & 6-Slot TOU)", "Deye Hybrid SUN (Storage & 6-Slot TOU)")],
    ["solarman_v5", l("Solarman V5 (Cổng 8899)", "Solarman V5 Protocol (Port 8899)")],
    ["smartess_local", l("SmartESS / Eybond (Wifi & P17)", "SmartESS / Eybond (Wifi & P17)")],
    ["growatt_cloud", l("Growatt Cloud (OpenAPI V1)", "Growatt Cloud (OpenAPI V1)")],
    ["eybond_esp", l("ESP EyeBond (Bridge & PI30)", "ESP EyeBond (Bridge & PI30)")],
    ["goodwe_local", l("GoodWe Modbus UDP (Local)", "GoodWe Modbus UDP (Local)")],
    ["huawei_sun2000", l("Huawei SUN2000 (LUNA2000 & TOU)", "Huawei SUN2000 (LUNA2000 & TOU)")],
    ["solarman_profiles", l("Hồ sơ Solarman (Đa hãng)", "Solarman Profiles (Multi-Vendor)")],
    ["sungrow_shx", l("Sungrow SHx Hybrid (Modbus TCP)", "Sungrow SHx Hybrid (Modbus TCP)")],
    ["deye_mqtt", l("Deye & SunSynk (Cầu nối MQTT)", "Deye & SunSynk (MQTT Bridge)")],
    ["community_optimizer", l("Tối ưu hóa khối Modbus (10 Profile)", "Modbus Block Optimizer (10 Profiles)")],
  ];
  const protocolKeys = new Set(protocolTabs.map(([k]) => k));

  const primaryTabs = [
    ["inventory", l("Danh mục thiết bị", "Device Inventory")],
    ["inspector", l("Kiểm tra kỹ thuật", "Technical inspection")],
    ["protocols", l("Công cụ kỹ sư", "Engineering tools")],
    ["native_config", l("Tham số theo thiết bị", "Device parameters")],
    ["health", l("Sức khỏe & Độ tin cậy", "Health & Reliability")],
    ["firmware", l("Phần mềm thiết bị", "Equipment software")],
    ["network_profile", l("Bộ thu thập & mạng", "Collectors & network")],
    ["document", l("Tài liệu", "Documents")],
  ];

  const rawTab = state.deviceTab || "inventory";
  const isProtocolTab = protocolKeys.has(rawTab) || rawTab === "protocols";
  const activePrimaryTab = isProtocolTab ? "protocols" : rawTab;
  const activeProtocolKey = protocolKeys.has(rawTab) ? rawTab : (state.selectedProtocol || "solis_mqtt");
  const currentTab = isProtocolTab ? activeProtocolKey : rawTab;

  const subnav = div("overview-subtabs");
  primaryTabs.forEach(([id, label]) => {
    const b = e("button", label, "overview-subtab-btn" + (activePrimaryTab === id ? " active" : ""));
    b.onclick = () => {
      if (["network_profile", "document"].includes(id)) return go("devices", "", id);
      if (id === "protocols") {
        state.deviceTab = activeProtocolKey;
      } else {
        state.deviceTab = id;
      }
      ui.render();
    };
    subnav.append(b);
  });
  container.append(subnav);

  if (activePrimaryTab === "protocols") {
    const protoSelect = e("select", "", "select-filter protocol-selector");
    protocolTabs.forEach(([k, label]) => {
      const opt = new Option(label, k);
      if (k === activeProtocolKey) opt.selected = true;
      protoSelect.append(opt);
    });
    protoSelect.setAttribute('aria-label', l('Giao thức cần kiểm tra','Protocol to inspect'));
    protoSelect.onchange = () => {
      state.deviceTab = protoSelect.value;
      state.selectedProtocol = protoSelect.value;
      ui.render();
    };

    const protoToolbar = div("protocol-subbar row align-center gap-sm wrap",
      icon("activity"),
      e("b", l("Công cụ kiểm định & giao thức hãng:", "Vendor Protocol & Lab Tool:")),
      protoSelect,
      badge(l("Phòng lab kỹ sư", "Engineering Lab"), "blue")
    );
    container.append(protoToolbar);
  }

  const summary = overviewData.summary || {};
  const deviceList = overviewData.devices || [];

  // TOP KPI STATS
  const kpiRow = div("overview-kpis",
    div("fact", e("span", l("Tổng số thiết bị", "Total Devices")), e("b", `${summary.total_devices || deviceList.length}`)),
    div("fact", e("span", l("Đang kết nối", "Connected Online")), badge(`${summary.online_count || 0} ${l("Online", "Online")}`, "good")),
    div("fact", e("span", l("Cảnh báo hoạt động", "Active Warnings")), badge(summary.warning_count == null ? '—' : String(summary.warning_count), summary.warning_count ? "warn" : summary.warning_count === 0 ? "good" : "")),
    div("fact", e("span", l("Đã nghiệm thu", "Commissioned")), badge(`${summary.commissioned_count || 0}`, "blue")),
    div("fact", e("span", l("Chưa xác định kết nối", "Connection unknown")), e("b", `${summary.unknown_connectivity_count ?? 0}`, "muted")),
  );
  container.append(kpiRow);

  if (isProtocolTab) {
    const vendorByTool={solis_mqtt:'Solis',goodwe_sems:'GoodWe',growatt_sph:'Growatt',solis_hybrid:'Solis',deye_hybrid:'Deye',solarman_v5:'SOLARMAN',smartess_local:'Eybond',growatt_cloud:'Growatt',eybond_esp:'Eybond',goodwe_local:'GoodWe',huawei_sun2000:'Huawei',sungrow_shx:'Sungrow',deye_mqtt:'Deye'};
    const vendor=vendorByTool[currentTab];
    const matching=deviceList.filter(d=>!vendor||[d.vendor,d.brand].some(v=>String(v||'').toLowerCase()===vendor.toLowerCase()));
    container.append(div('protocol-reference-layout',
      card(l('Thiết bị trong phạm vi','Equipment in scope'),
        p(l('Chỉ hiển thị danh mục đã đồng bộ. Chọn công cụ không tạo kết nối hoặc chứng minh thiết bị tương thích.','Synchronized inventory only. Selecting a tool neither connects equipment nor establishes compatibility.'),'field-help'),
        table([t('name'),l('Hãng / Model','Vendor / Model'),l('Thao tác','Action')],matching.map(d=>[
          d.name||d.serial,[d.vendor,d.model].filter(Boolean).join(' / ')||'—',btn(l('Mở thiết bị','Open equipment'),()=>deviceDetail(d.id))]))),
      card(l('Kiểm tra theo đúng thiết bị','Equipment-specific checks'),
        div('quick-action-list',
          btn(l('Chọn model và giải mã số đo','Select model and decode readings'),()=>{state.deviceTab='inspector';return ui.render();}),
          btn(l('Quản lý tài khoản hãng','Manage vendor accounts'),()=>go('settings','connections')),
          btn(l('Bộ thu thập tại trạm','On-site collection'),()=>go('reports','agent','main')),
          btn(l('Điều khiển có kiểm tra','Reviewed controls'),()=>go('operations','control'))),
        notice('Công cụ trình diễn cũ đã được gỡ. Chưa có phép thử trực tiếp cho đường giao thức được chọn; dùng hồ sơ model có nguồn tham chiếu để xem kế hoạch đọc hoặc giải mã số đo do bạn cung cấp.',
          'Legacy demonstration tools have been removed. This selected protocol has no verified live test here; use a sourced model profile to preview a read plan or decode supplied observations.',true))));
    return container;
  }

  // SUB-TAB 1: INVENTORY
  if (currentTab === "inventory") {
    let viewMode = "table";
    let searchQuery = "";
    let filterType = "ALL";
    let filterVendor = "ALL";
    let filterStatus = "ALL";

    const filterBar = div("gis-controls-bar");

    const searchInput = e("input", "", "input-search");
    searchInput.setAttribute('aria-label', l('Tìm thiết bị','Find equipment'));
    searchInput.placeholder = l("Tìm theo tên, model, số serial thiết bị…", "Search name, model, serial number…");

    const selType = e("select", "", "select-filter");
    selType.append(
      new Option(l("Tất cả loại thiết bị", "All Device Types"), "ALL"),
      ...[...new Set(deviceList.map(d => d.type).filter(Boolean))].sort()
        .map(type => new Option(t(type), type))
    );
    selType.setAttribute('aria-label', l('Loại thiết bị','Equipment type'));
    selType.onchange = () => { filterType = selType.value; renderFilteredDevices(); };

    const selVendor = e("select", "", "select-filter");
    selVendor.append(
      new Option(l("Tất cả hãng sản xuất", "All Vendors"), "ALL"),
      ...[...new Set(deviceList.flatMap(d => [d.vendor, d.brand]).filter(Boolean))]
        .sort().map(name => new Option(name, name))
    );
    selVendor.setAttribute('aria-label', l('Hãng thiết bị','Equipment vendor'));
    selVendor.onchange = () => { filterVendor = selVendor.value; renderFilteredDevices(); };

    const cardBtn = btn(l("Dạng thẻ", "Cards"), () => { viewMode = "card"; renderFilteredDevices(); }, viewMode === "card" ? "primary" : "secondary");
    cardBtn.prepend(icon("grid"));
    const tableBtn = btn(l("Dạng bảng", "Table"), () => { viewMode = "table"; renderFilteredDevices(); }, viewMode === "table" ? "primary" : "secondary");
    tableBtn.prepend(icon("report"));
    const viewSwitcher = div("row", cardBtn, tableBtn);

    filterBar.append(
      div("row",
        searchInput,
        div("field-inline", e("label", l("Loại:", "Type:")), selType),
        div("field-inline", e("label", l("Hãng:", "Vendor:")), selVendor)
      ),
      viewSwitcher
    );
    container.append(filterBar);

    const listContainer = div("stack");

    function renderFilteredDevices() {
      const q = searchInput.value.toLowerCase().trim();
      const filtered = deviceList.filter((d) => {
        const matchSearch = !q || (d.name || "").toLowerCase().includes(q) || (d.model || "").toLowerCase().includes(q) || (d.serial || "").toLowerCase().includes(q);
        const matchType = filterType === "ALL" || d.type === filterType;
        const matchVendor = filterVendor === "ALL" || [d.vendor, d.brand].includes(filterVendor);
        return matchSearch && matchType && matchVendor;
      });

      if (viewMode === "card") {
        const grid = div("plant-card-grid");
        filtered.forEach((d) => {
          const cardEl = div("plant-visual-card",
            div("row justify-between",
              div("row",
                div("plant-type-badge", icon(d.type === "INVERTER" ? "device" : d.type === "BATTERY" ? "activity" : "chart")),
                div("",
                  e("b", d.name || t(d.type), "plant-card-title"),
                  e("p", `${d.brand || d.vendor} · ${d.model || "—"}`, "small muted")
                )
              ),
              badge(d.online === true ? t('online') : d.online === false ? t('offline') : t('UNKNOWN'), d.online === true ? "good" : d.online === false ? 'warn' : "gray")
            ),
            div("plant-card-metrics",
              div("fact", e("span", l("Số Serial:", "Serial:")), e("span", d.serial || "—", "monospace small")),
              div("fact", e("span", l("Công suất:", "Power:")), equipmentPower(ui, d)),
              div("fact", e("span", l("Nhiệt độ:", "Temp:")), e("span", `${d.temp_c ?? "—"} °C`)),
              div("fact", e("span", l("Sức khỏe:", "Health Score:")), badge(d.health_score == null ? l("Chưa đánh giá", "Not assessed") : `${d.health_score}/100`))
            ),
            div("row",
              btn(l("Chi tiết & thông số gốc", "Detail & native readings"), () => deviceDetail(d.id)),
              btn(l("Giám sát Realtime", "Realtime"), () => {
                state.page = "operations";
                state.tab = "journal";
                state.journalTab = "realtime";
                state.selectedRealtimeDevice = d.id;
                ui.render();
              }, "primary"),
              btn(l("Profile / thanh ghi", "Profiles / registers"), () => {
                state.deviceTab = "inspector";
                state.selectedInspectorDevice = d.id;
                ui.render();
              }, "secondary"),
              btn(l("Tham số Native", "Native"), () => {
                state.deviceTab = "native_config";
                state.selectedInspectorDevice = d.id;
                ui.render();
              }, "secondary"),
              btn(l("Sức khỏe", "Health"), () => {
                state.deviceTab = "health";
                state.selectedInspectorDevice = d.id;
                ui.render();
              }, "secondary"),
              btn(l("Điều khiển →", "Control →"), () => {
                state.page = "operations";
                state.section = "main";
                state.tab = "control";
                state.selectedControlDevice = d.id;
                ui.render();
              }, "secondary")
            )
          );
          grid.append(cardEl);
        });
        listContainer.replaceChildren(filtered.length ? grid : div("notice-box", e("p", l("Không tìm thấy thiết bị phù hợp bộ lọc.", "No devices match the filter."))));
      } else {
        listContainer.replaceChildren(
          table(
            [l("Tên thiết bị", "Device Name"), l("Loại", "Type"), l("Hãng sản xuất", "Vendor"), l("Model", "Model"), l("Số Serial", "Serial Number"), l("Công suất (kW)", "Power (kW)"), t("status"), l("Hành động", "Actions")],
            filtered.map((d) => [
              e("b", d.name || t(d.type)),
              badge(t(d.type), "blue"),
              d.brand || d.vendor,
              d.model || "—",
              e("span", d.serial || "—", "monospace"),
              equipmentPower(ui, d),
              badge(d.online === true ? t('online') : d.online === false ? t('offline') : t('UNKNOWN'), d.online === true ? "good" : d.online === false ? 'warn' : "gray"),
              div("row",
                btn(l("Chi tiết & thông số gốc", "Detail & native readings"), () => deviceDetail(d.id)),
                btn(l("Realtime", "Realtime"), () => {
                  state.page = "operations";
                  state.tab = "journal";
                  state.journalTab = "realtime";
                  state.selectedRealtimeDevice = d.id;
                  ui.render();
                }, "primary"),
                btn(l("Profile / thanh ghi", "Profiles / registers"), () => {
                  state.deviceTab = "inspector";
                  state.selectedInspectorDevice = d.id;
                  ui.render();
                }, "secondary"),
                btn(l("Tham số", "Params"), () => {
                  state.deviceTab = "native_config";
                  state.selectedInspectorDevice = d.id;
                  ui.render();
                }, "secondary"),
                btn(l("Điều khiển →", "Control →"), () => {
                  state.page = "operations";
                  state.section = "main";
                  state.tab = "control";
                  state.selectedControlDevice = d.id;
                  ui.render();
                }, "secondary")
              )
            ])
          )
        );
      }
    }

    searchInput.oninput = renderFilteredDevices;
    container.append(listContainer);
    renderFilteredDevices();
  }

  // Versioned model candidates; no brand-only presets or automatic network reads.
  if (currentTab === "inspector") {
    container.append(await renderModelLibrary(ui, deviceList));
  }

  // SUB-TAB 3: 9 NATIVE PARAMETER GROUPS
  if (currentTab === "native_config") {
    const targetDeviceId = deviceList.find(d => d.id === state.selectedInspectorDevice)?.id || deviceList[0]?.id;
    if (!targetDeviceId) {
      container.append(p(l("Chưa có thiết bị trong phạm vi đã chọn.", "No devices in the selected scope.")));
      return container;
    }
    const configData = await api(`/devices/${encodeURIComponent(targetDeviceId)}/native-config-groups`);
    const targetPicker=select(deviceList.map(d=>[d.id,d.name||d.serial||d.id]),targetDeviceId);
    targetPicker.onchange=()=>{state.selectedInspectorDevice=targetPicker.value;return ui.render();};
    container.append(field(l('Thiết bị cần xem thông số','Equipment parameters to inspect'),targetPicker));

    const groupsList = div("plant-card-grid");
    (configData.groups || []).forEach((g) => {
      const gCard = div("plant-visual-card",
        div("row justify-between",
          e("b", typeof g.title === 'object' ? g.title?.[language] || g.title?.en || g.id : g.title || g.id, "plant-card-title"),
          badge(l("Khóa an toàn nghiệm thu", "Locked"), "warn")
        ),
        p(l("Cần kỹ thuật viên kiểm tra đúng thiết bị và hoàn tất nghiệm thu trước khi thay đổi thông số.", "A technician must verify this equipment and complete commissioning before changing parameters."), "small muted"),
        div("plant-card-metrics",
           ...(g.fields || []).map((f) => div("fact", e("span", (typeof f === "string" ? f : f.name) + ":"), e("b", typeof f === "string" ? "—" : f.current ?? "—")))
        ),
        btn(l("Mở hồ sơ nghiệm thu", "Open commissioning records"), () => {
          state.site = deviceList.find(d => d.id === targetDeviceId).site_id;
          return go("operations", "", "handover");
        }, "secondary")
      );
      groupsList.append(gCard);
    });

    container.append(
      notice("Thông số được nhóm theo chức năng của thiết bị. Chỉ mở chỉnh sửa khi đã xác minh khả năng hỗ trợ và nghiệm thu kết nối.", "Parameters are grouped by equipment function. Editing requires verified support and a commissioned connection."),
      groupsList
    );
  }

  // SUB-TAB 4: HEALTH & RELIABILITY
  if (currentTab === "health") {
    const healthGrid = div("plant-card-grid");

    // Fetch site battery health summary if available
    let siteHealthMap = {};
    if (state.site) {
      try {
        const siteHealth = await api(`/sites/${encodeURIComponent(state.site)}/battery-health`);
        (siteHealth.batteries || []).forEach(b => { siteHealthMap[b.device_id] = b; });
      } catch (_e) {}
    }

    for (const d of deviceList) {
      let bHealth = siteHealthMap[d.id];
      if (!bHealth && (d.type === 'BATTERY' || d.type === 'INVERTER' || d.has_battery)) {
        try {
          bHealth = await api(`/devices/${encodeURIComponent(d.id)}/battery-health`);
        } catch (_e) {}
      }

      const hCard = div("plant-visual-card",
        div("row justify-between",
          div("row",
            div("plant-type-badge", icon(d.type === "BATTERY" ? "battery" : "activity")),
            div("",
              e("b", d.name, "plant-card-title"),
              e("p", `${d.vendor} · ${d.model}`, "small muted")
            )
          ),
          bHealth?.soh_percent != null ? badge(`SOH ${bHealth.soh_percent}%`, bHealth.soh_percent >= 80 ? "good" : "warn") :
            badge(d.health_score == null ? l("Chưa đánh giá", "Not assessed") : `${d.health_score}/100`)
        ),
        div("plant-card-metrics",
          div("fact", e("span", l("Nhiệt độ cell / vỏ:", "Cell / Case Temp:")), e("b", `${number(bHealth?.operating_temp_c)} °C`)),
          div("fact", e("span", l("Chu kỳ tương đương (EFC):", "Equivalent Cycles:")), e("b", number(bHealth?.equivalent_full_cycles))),
          div("fact", e("span", l("Hệ số lão hóa nhiệt:", "Thermal Stress:")), e("b", number(bHealth?.temperature_stress_factor), bHealth && bHealth.temperature_stress_factor > 1.2 ? "bad-text" : "")),
          div("fact", e("span", l("Tuổi thọ ước tính còn lại:", "Estimated Life:")), e("b", number(bHealth?.estimated_remaining_years), "good-text"))
        ),
        div("stack",
          div("fact", e("span", l("Tình trạng bảo hành:", "Warranty Status:")),
            bHealth?.warranty_status && bHealth.warranty_status !== "UNKNOWN" ? badge(bHealth.warranty_status === "WITHIN_WARRANTY" ? l("Trong hạn bảo hành", "In Warranty") : l("Hết hạn bảo hành", "Expired"), bHealth.warranty_status === "WITHIN_WARRANTY" ? "good" : "bad") :
            e("span", l("Chưa xác định", "Unknown"))),
          div("fact", e("span", l("Chu kỳ bảo hành còn lại:", "Warranty Remaining:")),
            e("span", bHealth?.warranty_remaining_days != null ? `${number(bHealth.warranty_remaining_cycles)} / ${bHealth.warranty_remaining_days} ${l("ngày", "days")}` : l("Chưa nghiệm thu", "Not accepted")))
        )
      );
      if (bHealth && bHealth.recommendations && bHealth.recommendations.length > 0) {
        hCard.append(p(bHealth.recommendations[0], "small muted"));
      }
      healthGrid.append(hCard);
    }

    container.append(
      notice("Mô hình suy giảm dung lượng (Degradation Model) đánh giá đồng thời: chu kỳ nạp/xả EFC, độ sâu xả DOD, lão hóa lịch theo căn bậc hai thời gian, và hệ số gia tốc nhiệt Arrhenius.",
             "Battery degradation model evaluates EFC cycles, DoD stress, square-root calendar aging, and Arrhenius thermal acceleration."),
      card(l("Sức khỏe & Độ tin cậy thiết bị hạm đội", "Equipment Condition & Battery Health"), healthGrid)
    );
  }

  // SUB-TAB 5: FIRMWARE MATRIX
  if (currentTab === "firmware") {
    const fwData = await api("/fleet/firmware-matrix" + scopeQuery);

    const fwTable = table(
      [l("Thiết bị", "Device"), l("Hãng", "Vendor"), l("Model", "Model"), l("Phiên bản hiện tại", "Installed Version"), l("Bản mới nhất", "Latest Release"), l("Đánh giá tuân thủ", "Compliance Status"), l("Ngày phát hành", "Release Date"), l("Mã băm SHA-256", "SHA-256 Hash"), l("Hành động", "Actions")],
      (fwData.devices || []).map((r) => [
        e("b", r.device_name),
        r.vendor,
        r.model,
        badge(r.current_firmware ?? "—", "blue"),
        e("b", r.latest_firmware ?? "—"),
        badge(r.compliance_status === "COMPLIANT" ? l("Đạt chuẩn", "Compliant") : l("Chưa xác minh", "Unverified"), r.compliance_status === "COMPLIANT" ? "good" : "warn"),
        r.release_date ?? "—",
        e("span", r.sha256_hash ? r.sha256_hash.slice(0, 16) + "…" : "—", "monospace small"),
        btn(l("Mở hồ sơ bảo trì", "Open maintenance records"), () => {state.site = r.site_id; return go('incidents', '', 'health');}, "secondary")
      ])
    );

    container.append(
      notice("Ma trận tuân thủ firmware toàn hạm đội. Mọi gói cập nhật OTA đều bắt buộc xác minh mã băm SHA-256 của nhà sản xuất trước khi nạp vào hàng đợi.", "Fleet firmware compliance matrix. All OTA packages must verify manufacturer SHA-256 hash before entering deployment queue."),
      card(l("Bảng ma trận firmware & kiểm định an toàn phần mềm nhúng", "Firmware Compliance Matrix & Safety Verification"), fwTable)
    );
  }

  return container;
}

// Backward compatibility wrapper
export function createDeviceWorkspace(ui) {
  return {
    openRegisterInspector: (d) => {
      ui.state.deviceTab = "inspector";
      ui.state.selectedInspectorDevice = d.id;
      ui.render();
    },
    openDeviceHealthDrawer: (d) => {
      ui.state.deviceTab = "health";
      ui.state.selectedInspectorDevice = d.id;
      ui.render();
    },
  };
}
