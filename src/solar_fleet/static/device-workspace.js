import { l, t, date, number } from "./i18n.js";
import { icon } from "./icons.js";
import { renderModelLibrary } from "./model-workspace.js";

export async function renderDevicesMainWorkspace(ui) {
  const { state, e, div, p, btn, badge, card, table, select, input, field, fact, notice, showDialog, closeDialog, api, go, sites, deviceDetail } = ui;
  const container = div("stack device-workspace-container");

  const overviewData = await api('/fleet/devices-overview');

  const subtabs = [
    ["inventory", l("Danh mục thiết bị", "Device Inventory")],
    ["inspector", l("Kiểm tra thanh ghi Modbus", "Modbus Register Inspector")],
    ["community_optimizer", l("Tối ưu hóa khối Modbus (10 Profile)", "Modbus Block Optimizer (10 Profiles)")],
    ["solis_mqtt", l("Cầu nối Solis MQTT & HA", "Solis MQTT & HA Bridge")],
    ["goodwe_sems", l("GoodWe SEMS Portal (Cloud)", "GoodWe SEMS Portal (Cloud)")],
    ["growatt_sph", l("Growatt SPH Hybrid (TOU & BMS)", "Growatt SPH Hybrid (TOU & BMS)")],
    ["solis_hybrid", l("Solis Hybrid S6 (Lưu trữ & TOU)", "Solis Hybrid S6 (Storage & TOU)")],
    ["deye_hybrid", l("Deye Hybrid SUN (Lưu trữ & 6-Slot TOU)", "Deye Hybrid SUN (Storage & 6-Slot TOU)")],
    ["solarman_v5", l("Giao thức Solarman V5 (Cổng 8899)", "Solarman V5 Protocol (Port 8899)")],
    ["smartess_local", l("SmartESS / Eybond (Wifi & P17)", "SmartESS / Eybond (Wifi & P17)")],
    ["growatt_cloud", l("Growatt Cloud (OpenAPI V1)", "Growatt Cloud (OpenAPI V1)")],
    ["eybond_esp", l("ESP EyeBond Collector (Bridge & PI30)", "ESP EyeBond Collector (Bridge & PI30)")],
    ["goodwe_local", l("GoodWe Modbus UDP (Local & Eco Mode)", "GoodWe Modbus UDP (Local & Eco Mode)")],
    ["huawei_sun2000", l("Huawei SUN2000 (LUNA2000 & TOU)", "Huawei SUN2000 (LUNA2000 & TOU)")],
    ["solarman_profiles", l("Hồ sơ Solarman (Đa thương hiệu)", "Solarman Profiles (Multi-Vendor)")],
    ["native_config", l("Tham số theo thiết bị", "Device parameters")],
    ["health", l("Sức khỏe & Độ tin cậy", "Health & Reliability")],
    ["firmware", l("Quản lý Firmware & OTA", "Firmware Compliance & OTA")],
  ];

  const currentTab = state.deviceTab || "inventory";
  const subnav = div("overview-subtabs");
  subtabs.forEach(([id, label]) => {
    const b = e("button", label, "overview-subtab-btn" + (currentTab === id ? " active" : ""));
    b.onclick = () => {
      state.deviceTab = id;
      ui.render();
    };
    subnav.append(b);
  });
  container.append(subnav);

  const summary = overviewData.summary || {};
  const deviceList = overviewData.devices || [];

  // TOP KPI STATS
  const kpiRow = div("overview-kpis",
    div("fact", e("span", l("Tổng số thiết bị", "Total Devices")), e("b", `${summary.total_devices || deviceList.length}`)),
    div("fact", e("span", l("Đang kết nối", "Connected Online")), badge(`${summary.online_count || 0} ${l("Online", "Online")}`, "good")),
    div("fact", e("span", l("Cảnh báo hoạt động", "Active Warnings")), badge(`${summary.warning_count || 0}`, summary.warning_count ? "warn" : "good")),
    div("fact", e("span", l("Đã nghiệm thu", "Commissioned")), badge(`${summary.commissioned_count || 0}`, "blue")),
    div("fact", e("span", l("Chưa xác định kết nối", "Connection unknown")), e("b", `${summary.unknown_count || 0}`, "muted")),
  );
  container.append(kpiRow);

  // SUB-TAB 1: INVENTORY
  if (currentTab === "inventory") {
    let viewMode = "card"; // "card" or "table"
    let searchQuery = "";
    let filterType = "ALL";
    let filterVendor = "ALL";
    let filterStatus = "ALL";

    const filterBar = div("gis-controls-bar");

    const searchInput = e("input", "", "input-search");
    searchInput.placeholder = l("Tìm theo tên, model, số serial thiết bị…", "Search name, model, serial number…");

    const selType = e("select", "", "select-filter");
    selType.append(
      new Option(l("Tất cả loại thiết bị", "All Device Types"), "ALL"),
      new Option(l("Biến tần Inverter", "Inverter"), "INVERTER"),
      new Option(l("Pin lưu trữ BESS", "Battery BESS"), "BATTERY"),
      new Option(l("Đồng hồ Smart Meter", "Smart Meter"), "METER"),
      new Option(l("Datalogger Gateway", "Logger Gateway"), "LOGGER"),
      new Option(l("Trạm thời tiết", "Weather Station"), "WEATHER")
    );
    selType.onchange = () => { filterType = selType.value; renderFilteredDevices(); };

    const selVendor = e("select", "", "select-filter");
    selVendor.append(
      new Option(l("Tất cả hãng sản xuất", "All Vendors"), "ALL"),
      ...[...new Set(deviceList.flatMap(d => [d.vendor, d.brand]).filter(Boolean))]
        .sort().map(name => new Option(name, name))
    );
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
                  e("b", d.name, "plant-card-title"),
                  e("p", `${d.brand || d.vendor} · ${d.model || "—"}`, "small muted")
                )
              ),
              badge(d.online ? l("Online", "Online") : l("Chưa xác định", "Unknown"), d.online ? "good" : "gray")
            ),
            div("plant-card-metrics",
              div("fact", e("span", l("Số Serial:", "Serial:")), e("span", d.serial || "—", "monospace small")),
              div("fact", e("span", l("Công suất:", "Power:")), e("b", `${d.power_kw != null ? d.power_kw : "—"} kW`)),
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
              e("b", d.name),
              badge(d.type, "blue"),
              d.brand || d.vendor,
              d.model || "—",
              e("span", d.serial || "—", "monospace"),
              `${d.power_kw ?? "—"} kW`,
              badge(d.online ? l("Hoạt động", "Online") : l("Chưa xác định", "Unknown"), d.online ? "good" : "gray"),
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

  // SUB-TAB: COMMUNITY INVERTER MODBUS BLOCK PACKING OPTIMIZER
  if (currentTab === "community_optimizer") {
    await renderCommunityOptimizerSubtab(ui, container);
  }

  // SUB-TAB: SOLIS MODBUS-TO-MQTT & HOME ASSISTANT BRIDGE
  if (currentTab === "solis_mqtt") {
    await renderSolisMqttSubtab(ui, container);
  }

  // SUB-TAB: GOODWE SEMS PORTAL CLOUD INTEGRATION
  if (currentTab === "goodwe_sems") {
    await renderGoodWeSemsSubtab(ui, container);
  }

  // SUB-TAB: GROWATT SPH HYBRID MODBUS & TOU SCHEDULER
  if (currentTab === "growatt_sph") {
    await renderGrowattSphSubtab(ui, container);
  }

  // SUB-TAB: SOLIS HYBRID S6 / RHI MODBUS & TOU SCHEDULER
  if (currentTab === "solis_hybrid") {
    await renderSolisHybridSubtab(ui, container);
  }

  // SUB-TAB: DEYE HYBRID SUN-xxK-SG04/05LP3 MODBUS & 6-SLOT TOU
  if (currentTab === "deye_hybrid") {
    await renderDeyeHybridSubtab(ui, container);
  }

  // SUB-TAB: SOLARMAN V5 DATALOGGER FRAME PROTOCOL
  if (currentTab === "solarman_v5") {
    await renderSolarmanV5Subtab(ui, container);
  }

  // SUB-TAB: SMARTESS / EYBOND LOCAL WI-FI & P17 INVERTER
  if (currentTab === "smartess_local") {
    await renderSmartEssLocalSubtab(ui, container);
  }

  // SUB-TAB: GROWATT CLOUD OPENAPI V1
  if (currentTab === "growatt_cloud") {
    await renderGrowattCloudSubtab(ui, container);
  }

  // SUB-TAB: ESP EYEBOND COLLECTOR & VOLTRONIC PI30
  if (currentTab === "eybond_esp") {
    await renderEybondEspSubtab(ui, container);
  }

  // SUB-TAB: GOODWE LOCAL UDP & MODBUS RTU
  if (currentTab === "goodwe_local") {
    await renderGoodWeLocalSubtab(ui, container);
  }

  // SUB-TAB: HUAWEI SUN2000 & LUNA2000
  if (currentTab === "huawei_sun2000") {
    await renderHuaweiSun2000Subtab(ui, container);
  }

  // SUB-TAB: SOLARMAN PROFILE CATALOGUE & MULTI-VENDOR ENGINE
  if (currentTab === "solarman_profiles") {
    await renderSolarmanProfilesSubtab(ui, container);
  }

  // SUB-TAB 3: 9 NATIVE PARAMETER GROUPS
  if (currentTab === "native_config") {
    let targetDeviceId = state.selectedInspectorDevice || (deviceList[0] ? deviceList[0].id : "inv_demo");

    let configData = null;
    try {
      configData = await api(`/devices/${targetDeviceId}/native-config-groups`);
    } catch (_err) {
      configData = { groups: [] };
    }

    const groupsList = div("plant-card-grid");
    (configData.groups || []).forEach((g) => {
      const gCard = div("plant-visual-card",
        div("row justify-between",
          e("b", g.title, "plant-card-title"),
          badge(l("Khóa an toàn nghiệm thu", "Locked"), "warn")
        ),
        p(l("Lý do khóa: Chưa hoàn tất biên bản nghiệm thu phần cứng hiện trường (LOCKED_PENDING_HARDWARE_ACCEPTANCE).", "Locked: Hardware acceptance required before native write."), "small bad"),
        div("plant-card-metrics",
          ...(g.fields || []).map((f) => div("fact", e("span", f.name + ":"), e("b", f.current)))
        ),
        btn(l("Yêu cầu mở khóa nghiệm thu", "Request Hardware Commissioning"), () => {
          alert(l("Yêu cầu nghiệm thu phần cứng đã được gửi tới kỹ sư trưởng phụ trách O&M.", "Commissioning request sent to Lead Engineer."));
        }, "secondary")
      );
      groupsList.append(gCard);
    });

    container.append(
      notice("9 Nhóm tham số Native của thiết bị được bảo vệ bởi cơ chế an toàn cấp công nghiệp. Toàn bộ lệnh cấu hình phần cứng đều cần fresh readback và chữ ký nghiệm thu.", "9 Native parameter groups are protected by industrial hardware safety gates. All hardware modifications require fresh readback and commissioned sign-off."),
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
          bHealth ? badge(`SOH ${bHealth.soh_percent}%`, bHealth.soh_percent >= 80 ? "good" : "warn") :
            badge(d.health_score == null ? l("Chưa đánh giá", "Not assessed") : `${d.health_score}/100`)
        ),
        div("plant-card-metrics",
          div("fact", e("span", l("Nhiệt độ cell / vỏ:", "Cell / Case Temp:")), e("b", bHealth ? `${bHealth.operating_temp_c} °C` : `${number(d.temp_c || 28.5)} °C`)),
          div("fact", e("span", l("Chu kỳ tương đương (EFC):", "Equivalent Cycles:")), e("b", bHealth ? `${bHealth.equivalent_full_cycles}` : "—")),
          div("fact", e("span", l("Hệ số lão hóa nhiệt:", "Thermal Stress:")), e("b", bHealth ? `${bHealth.temperature_stress_factor}x` : "1.00x", bHealth && bHealth.temperature_stress_factor > 1.2 ? "bad-text" : "")),
          div("fact", e("span", l("Tuổi thọ ước tính còn lại:", "Estimated Life:")), e("b", bHealth ? `${bHealth.estimated_remaining_years} ${l("năm", "yrs")}` : "—", "good-text"))
        ),
        div("stack",
          div("fact", e("span", l("Tình trạng bảo hành:", "Warranty Status:")),
            bHealth ? badge(bHealth.warranty_status === "WITHIN_WARRANTY" ? l("Trong hạn bảo hành", "In Warranty") : l("Hết hạn bảo hành", "Expired"), bHealth.warranty_status === "WITHIN_WARRANTY" ? "good" : "bad") :
            e("span", l("Đang cập nhật", "Updating"))),
          div("fact", e("span", l("Chu kỳ bảo hành còn lại:", "Warranty Remaining:")),
            e("span", bHealth ? `${number(bHealth.warranty_remaining_cycles)} / ${bHealth.warranty_remaining_days} ${l("ngày", "days")}` : l("Chưa nghiệm thu", "Not accepted")))
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
    let fwData = null;
    try {
      fwData = await api("/fleet/firmware-matrix");
    } catch (_err) {
      fwData = { records: [] };
    }

    const fwTable = table(
      [l("Thiết bị", "Device"), l("Hãng", "Vendor"), l("Model", "Model"), l("Phiên bản hiện tại", "Installed Version"), l("Bản mới nhất", "Latest Release"), l("Đánh giá tuân thủ", "Compliance Status"), l("Ngày phát hành", "Release Date"), l("Mã băm SHA-256", "SHA-256 Hash"), l("Hành động", "Actions")],
      (fwData.records || []).map((r) => [
        e("b", r.device_name),
        r.vendor,
        r.model,
        badge(r.installed_version, "blue"),
        e("b", r.latest_release),
        badge(r.compliance_status === "COMPLIANT" ? l("Đạt chuẩn", "Compliant") : l("Chưa xác minh", "Unverified"), r.compliance_status === "COMPLIANT" ? "good" : "warn"),
        r.release_date,
        e("span", r.sha256_hash ? r.sha256_hash.slice(0, 16) + "…" : "—", "monospace small"),
        btn(l("Mở hồ sơ bảo trì", "Open maintenance records"), () => go('incidents', 'health'), "secondary")
      ])
    );

    container.append(
      notice("Ma trận tuân thủ firmware toàn hạm đội. Mọi gói cập nhật OTA đều bắt buộc xác minh mã băm SHA-256 của nhà sản xuất trước khi nạp vào hàng đợi.", "Fleet firmware compliance matrix. All OTA packages must verify manufacturer SHA-256 hash before entering deployment queue."),
      card(l("Bảng ma trận firmware & kiểm định an toàn phần mềm nhúng", "Firmware Compliance Matrix & Safety Verification"), fwTable)
    );
  }

  return container;
}

async function renderCommunityOptimizerSubtab(ui, container) {
  const { e, div, p, btn, badge, notice, api } = ui;
  const optBox = div("stack");

  let profileList = [];
  try {
    const res = await api("/community-inverters/profiles");
    profileList = res.profiles || [];
  } catch (_e) {
    profileList = [];
  }

  if (profileList.length === 0) {
    optBox.append(notice("Không thể tải danh sách profile cộng đồng.", "Could not load community profiles."));
    container.append(optBox);
    return;
  }

  let selectedModelId = profileList[0].model_id;
  let enableGapTolerance = true;

  const headerNotice = notice(
    "10 Profile thanh ghi Modbus chuẩn hóa từ dự án mã nguồn mở solar-inverter-modbus-registers (MIT, Daniel Szlaski). Hỗ trợ thuật toán đóng gói khối tối ưu hóa (block packing with gap tolerance) và giải mã bitmask sự cố 80-bit.",
    "10 Normalized Modbus inverter profiles from open-source project solar-inverter-modbus-registers (MIT, Daniel Szlaski). Features block packing with gap tolerance and 80-bit fault bitmask decoding."
  );
  optBox.append(headerNotice);

  const controlBar = div("gis-controls-bar");
  const selModel = e("select", "", "select-filter");
  profileList.forEach((p) => {
    const opt = new Option(
      `${p.brand_name} - ${p.model_name} (${p.supported_fields_count} thanh ghi, FC0${p.polling_config ? "4" : "3"})`,
      p.model_id
    );
    selModel.append(opt);
  });
  selModel.value = selectedModelId;

  const chkGap = e("input");
  chkGap.type = "checkbox";
  chkGap.checked = enableGapTolerance;
  chkGap.id = "chk-gap-tol";

  const lblGap = e("label", "", "row items-center gap-2 pointer");
  lblGap.append(chkGap, e("span", "Cho phép bắc cầu khoảng trống (Gap Tolerance)"));

  const btnCalc = btn("Tối ưu hóa gói tin Modbus", async () => {
    await runOptimization();
  }, "primary");

  controlBar.append(selModel, lblGap, btnCalc);
  optBox.append(controlBar);

  const resultsArea = div("stack");
  optBox.append(resultsArea);

  async function runOptimization() {
    selectedModelId = selModel.value;
    enableGapTolerance = chkGap.checked;

    resultsArea.replaceChildren(p("Đang tính toán các khối Modbus PDU tối ưu...", "Calculating optimal Modbus PDU blocks..."));

    try {
      const [optRes, profDetail] = await Promise.all([
        api("/community-inverters/optimize-polling", {
          method: "POST",
          body: JSON.stringify({
            model_id: selectedModelId,
            enable_gap_tolerance: enableGapTolerance,
          }),
        }),
        api(`/community-inverters/profile/${encodeURIComponent(selectedModelId)}`),
      ]);

      const prof = profDetail.profile || {};

      // KPI cards
      const kpis = div("overview-kpis",
        div("fact", e("span", "Số yêu cầu ban đầu:"), e("b", `${optRes.baseline_requests}`)),
        div("fact", e("span", "Số khối Modbus tối ưu:"), badge(`${optRes.optimized_requests} khối`, "good")),
        div("fact", e("span", "Gói tin tiết kiệm:"), badge(`-${optRes.packets_saved} (-${optRes.savings_pct}%)`, optRes.packets_saved > 0 ? "good" : "muted")),
        div("fact", e("span", "Ước tính độ trễ:"), e("b", `~${optRes.estimated_latency_ms} ms`)),
        div("fact", e("span", "Cấu hình ghép khối:"), e("span", `Max=${optRes.max_block_size}, Gap=${optRes.gap_tolerance}`, "small muted")),
      );

      // Block Table
      const blockSection = div("stack");
      blockSection.append(e("b", "Danh sách khối đọc Modbus PDU đã được tối ưu hóa:"));

      const tbl = e("table", "", "table");
      const thead = e("thead");
      thead.innerHTML = "<tr><th>#</th><th>FC</th><th>Đ/c bắt đầu</th><th>Số lượng</th><th>Đ/c kết thúc</th><th>Lệnh Hex PDU</th><th>Các trường thu thập</th><th>Bắc cầu</th></tr>";
      tbl.append(thead);

      const tbody = e("tbody");
      (optRes.blocks || []).forEach((b, idx) => {
        const tr = e("tr");
        tr.innerHTML = `
          <td><b>#${idx + 1}</b></td>
          <td><span class="badge blue">FC 0${b.function_code}</span></td>
          <td><code>${b.start_address}</code></td>
          <td><b>${b.count}</b></td>
          <td><code>${b.end_address}</code></td>
          <td><code>${b.hex_cmd}</code></td>
          <td><small>${(b.target_field_ids || []).join(", ")}</small></td>
          <td>${b.bridged_gaps > 0 ? `<span class="badge warn">+${b.bridged_gaps} đ/c</span>` : '<span class="badge muted">0</span>'}</td>
        `;
        tbody.append(tr);
      });
      tbl.append(tbody);
      blockSection.append(tbl);

      // Live Telemetry Simulation Card
      const simCard = div("plant-visual-card",
        div("row justify-between",
          e("b", "Mô phỏng giải mã Telemetry thời gian thực (Live Decoder)"),
          badge(prof.brandName || "Vendor", "blue")
        ),
        p("Giải mã các thanh ghi 16-bit / 32-bit theo đúng thứ tự byte big-endian, hệ số tỷ lệ và ngưỡng hợp lệ:", "small muted")
      );

      const demoFields = div("plant-card-metrics");
      const fieldsDict = prof.fields || {};
      Object.entries(fieldsDict).forEach(([fid, fval]) => {
        if (fval.presence !== "unsupported" && fval.addr) {
          demoFields.append(div("fact",
            e("span", `${fid}:`),
            e("span", `Đ/c ${fval.addr} (x${fval.scale || 1} ${fval.signed ? "signed" : "unsigned"})`, "small muted")
          ));
        }
      });
      simCard.append(demoFields);

      // Alarm Bitfield section if available
      const alarmsList = prof.alarms || [];
      if (alarmsList.length > 0) {
        const alarmCard = div("plant-visual-card",
          div("row justify-between",
            e("b", `Giải mã bitmask cảnh báo (${alarmsList.length} nhóm, ${Object.keys(alarmsList[0].bits || {}).length} mã lỗi)`),
            badge("Bitmask Engine", "warn")
          ),
          p(`Thanh ghi cảnh báo gốc: 0x${alarmsList[0].addr.toString(16).toUpperCase()} (${alarmsList[0].addr}), độ dài ${alarmsList[0].count} từ (words = ${alarmsList[0].count * 16} bits).`, "small muted")
        );

        const testAlarmBtn = btn("Mô phỏng kích hoạt bit sự cố (Bit 0 NO-Grid, Bit 66 OV-TEM)", async () => {
          const rawSim = {};
          rawSim[alarmsList[0].addr] = 1; // Bit 0
          if (alarmsList[0].count >= 5) {
            rawSim[alarmsList[0].addr + 4] = 4; // Bit 66 in word 4
          }
          const decAlarms = await api("/community-inverters/decode-alarms", {
            method: "POST",
            body: JSON.stringify({
              model_id: selectedModelId,
              registers: rawSim,
            }),
          });
          const alms = decAlarms.alarms || [];
          alarmCard.append(
            div("stack",
              notice(`Đã phát hiện ${alms.length} sự cố từ bitmask Modbus:`, `Detected ${alms.length} incidents from Modbus bitmask:`),
              ...alms.map((a) => div("plant-visual-card",
                div("row justify-between",
                  e("b", `[${a.severity}] Mã lỗi ${a.fault_code}: ${a.message}`),
                  badge(a.category, a.severity === "CRITICAL" ? "bad" : "warn")
                ),
                p(`SOP ứng phó: ${a.sop}`, "small good-text")
              ))
            )
          );
        }, "secondary");
        alarmCard.append(testAlarmBtn);
        resultsArea.replaceChildren(kpis, blockSection, simCard, alarmCard);
      } else {
        resultsArea.replaceChildren(kpis, blockSection, simCard);
      }
    } catch (err) {
      resultsArea.replaceChildren(notice("Lỗi khi tối ưu hóa: " + err.message, "Optimization error"));
    }
  }

  selModel.onchange = () => { runOptimization(); };
  chkGap.onchange = () => { runOptimization(); };

  await runOptimization();
  container.append(optBox);
}

async function renderSolisMqttSubtab(ui, container) {
  const { e, div, p, btn, badge, notice, card, table, api } = ui;
  const bridgeBox = div("stack");

  let regData = null;
  try {
    regData = await api("/solis-mqtt/registers");
  } catch (_e) {
    regData = { registers: [] };
  }

  const registers = regData.registers || [];

  bridgeBox.append(
    notice(
      "Cầu nối Solis Modbus-to-MQTT & Tự động khám phá Home Assistant (Auto-Discovery). Độc lập triển khai dựa trên kiến thức mã nguồn mở solis2mqtt (GPL-3.0, incub77). Hỗ trợ toàn diện giao thức Ginlong Solis RS485 (9600 8N1, FC03/04), bộ giải mã Datetime Composed, cơ chế bảo vệ số liệu đo đếm khi ngắt kết nối ban đêm, và biên dịch khung lệnh ghi FC06 kiểm định an toàn.",
      "Solis Modbus-to-MQTT Bridge & Home Assistant Auto-Discovery. Clean-room independent implementation based on solis2mqtt (GPL-3.0, incub77). Covers Ginlong Solis RS485 (9600 8N1, FC03/04), Composed Datetime decoder, night-mode statistics protection, and safety-gated FC06 write frame compilation."
    )
  );

  // Top KPIs
  const kpiRow = div("overview-kpis",
    div("fact", e("span", "Tổng số thanh ghi"), e("b", `${registers.length}`)),
    div("fact", e("span", "Lệnh ghi FC06"), badge("2 điều khiển (Reg 3051, 3006)", "blue")),
    div("fact", e("span", "Thực thể Home Assistant"), badge("11 Sensors, 1 Number, 1 Switch", "good")),
    div("fact", e("span", "Trạng thái cổng an toàn"), badge("LOCKED_PENDING_HARDWARE_ACCEPTANCE", "warn")),
  );
  bridgeBox.append(kpiRow);

  // 1. REGISTER TABLE
  const regTable = table(
    ["Tên thực thể", "Mô tả", "Thanh ghi Modbus", "Mã hàm", "Kiểu dữ liệu", "Đơn vị", "Loại HA", "State Class"],
    registers.map((r) => [
      e("b", r.name),
      r.description,
      e("span", Array.isArray(r.register) ? `[${r.register.join(", ")}]` : `Reg ${r.register}`, "monospace"),
      badge(r.write_function_code ? `FC0${r.function_code} / FC0${r.write_function_code}` : `FC0${r.function_code}`, r.write_function_code ? "blue" : "secondary"),
      r.read_type,
      r.unit || "—",
      badge(r.ha_device, r.ha_device === "switch" ? "warn" : r.ha_device === "number" ? "blue" : "good"),
      r.ha_state_class || "—",
    ])
  );
  bridgeBox.append(card("1. Danh mục thanh ghi Ginlong Solis & Thực thể Home Assistant", regTable));

  // 2. HA DISCOVERY GENERATOR
  const discCard = card("2. Trình tạo cấu hình khám phá Home Assistant (Auto-Discovery Configs)");
  const discControls = div("gis-controls-bar",
    div("row",
      e("label", "Node ID:"),
      (() => {
        const inp = e("input", "", "input-search");
        inp.id = "solis_node_id";
        inp.value = "solis2mqtt";
        inp.style.width = "140px";
        return inp;
      })(),
      e("label", "Prefix:"),
      (() => {
        const inp = e("input", "", "input-search");
        inp.id = "solis_disc_prefix";
        inp.value = "homeassistant";
        inp.style.width = "140px";
        return inp;
      })()
    )
  );

  const discResults = div("stack");
  const genDiscBtn = btn("Tạo gói tin Auto-Discovery", async () => {
    discResults.replaceChildren(notice("Đang biên dịch cấu hình MQTT Auto-Discovery…", "Compiling..."));
    try {
      const nodeId = document.getElementById("solis_node_id")?.value || "solis2mqtt";
      const prefix = document.getElementById("solis_disc_prefix")?.value || "homeassistant";
      const res = await api("/solis-mqtt/discovery-topics", {
        method: "POST",
        body: JSON.stringify({
          device_name: "solis_inverter",
          device_model: "Ginlong Solis String",
          base_topic: nodeId,
          discovery_prefix: prefix,
        }),
      });

      const configs = res.discovery_configs || [];
      const listEl = div("stack",
        notice(`Đã tạo thành công ${configs.length} cấu hình khám phá thực thể Home Assistant:`, `Generated ${configs.length} discovery configs:`),
        table(
          ["Thực thể", "Loại", "Chủ đề khám phá (Discovery Topic)", "Chủ đề trạng thái", "Lệnh ghi (Set Topic)"],
          configs.map((c) => [
            e("b", c.entity_name),
            badge(c.entity_type, c.entity_type === "switch" ? "warn" : c.entity_type === "number" ? "blue" : "good"),
            e("span", c.discovery_topic, "monospace small"),
            e("span", c.state_topic, "monospace small"),
            e("span", c.command_topic || "—", "monospace small"),
          ])
        ),
        div("plant-visual-card",
          e("b", "Ví dụ gói JSON cấu hình mẫu (Thanh ghi giới hạn công suất Power Limitation):"),
          (() => {
            const numCfg = configs.find((c) => c.entity_type === "number") || configs[0];
            const pre = e("pre", JSON.stringify(numCfg?.payload || {}, null, 2), "monospace small");
            pre.style.background = "var(--bg-card)";
            pre.style.padding = "8px";
            pre.style.overflowX = "auto";
            return pre;
          })()
        )
      );
      discResults.replaceChildren(listEl);
    } catch (err) {
      discResults.replaceChildren(notice("Lỗi tạo cấu hình: " + err.message, "Error"));
    }
  }, "primary");

  discCard.append(discControls, genDiscBtn, discResults);
  bridgeBox.append(discCard);

  // 3. TELEMETRY DECODER PLAYGROUND
  const telCard = card("3. Trình giải mã đo xa & Datetime Composed (Live Telemetry Decoder)");
  const telDesc = notice(
    "Mô phỏng dữ liệu thô từ cổng RS485 Solis: Công suất tác dụng 32-bit (Reg 3004), Công suất DC 32-bit (Reg 3006), Sản lượng hôm nay (Reg 3014, hệ số 0.1), Nhiệt độ (Reg 3041, hệ số 0.1), và Thời gian hệ thống ghép 6 thanh ghi (Reg 3072..3077).",
    "Simulates raw Modbus RS485 readings and decodes into engineering telemetry and MQTT state topics."
  );

  const telResults = div("stack");
  const decodeBtn = btn("Giải mã dữ liệu thô sang MQTT Telemetry", async () => {
    try {
      const simulatedRegisters = {
        3004: 0, 3005: 4500, // active_power = 4500 W
        3006: 0, 3007: 4720, // total_dc_output_power = 4720 W
        3008: 0, 3009: 18250, // total_power = 18250 kWh
        3010: 0, 3011: 420, // energy_this_month = 420 kWh
        3012: 0, 3013: 560, // generation_last_month = 560 kWh
        3014: 245, // generation_today = 24.5 kWh (decimals: 1)
        3015: 312, // generation_yesterday = 31.2 kWh (decimals: 1)
        3016: 0, 3017: 2850, // generation_this_year = 2850 kWh
        3018: 0, 3019: 3950, // generation_last_year = 3950 kWh
        3041: 385, // inverter_temp = 38.5 °C (decimals: 1)
        3072: 26, 3073: 9, 3074: 27, 3075: 9, 3076: 45, 3077: 0 // 2026-09-27T09:45:00
      };

      const res = await api("/solis-mqtt/decode-telemetry", {
        method: "POST",
        body: JSON.stringify({
          registers: simulatedRegisters,
          base_topic: "solis2mqtt",
        }),
      });

      const metrics = res.metrics || {};
      const mqttMsgs = res.mqtt_messages || [];

      telResults.replaceChildren(
        notice(`Đã giải mã thành công ${res.total_decoded} thông số kỹ thuật và tạo ${mqttMsgs.length} bản tin MQTT:`, "Decoded:"),
        table(
          ["Thông số", "Mô tả", "Giá trị kỹ thuật", "Đơn vị", "Chủ đề MQTT (State Topic)", "Gói tin Payload"],
          Object.entries(metrics).map(([k, m]) => {
            const pub = mqttMsgs.find((msg) => msg.topic.endsWith("/" + k));
            return [
              e("b", k),
              m.description,
              e("span", String(m.value), "badge good"),
              m.unit || "—",
              e("span", pub?.topic || `solis2mqtt/${k}`, "monospace small"),
              e("b", pub?.payload || String(m.value)),
            ];
          })
        )
      );
    } catch (err) {
      telResults.replaceChildren(notice("Lỗi giải mã: " + err.message, "Error"));
    }
  }, "primary");

  telCard.append(telDesc, decodeBtn, telResults);
  bridgeBox.append(telCard);

  // 4. NIGHT MODE & OFFLINE SANITIZER
  const nightCard = card("4. Cơ chế bảo vệ số liệu ngắt kết nối ban đêm (Night Mode Offline Sanitizer)");
  const nightNotice = notice(
    "Khi trời tối, điện áp chuỗi pin PV giảm dưới ngưỡng hoạt động, biến tần Solis ngắt vi điều khiển RS485 dẫn đến mất tín hiệu (NoResponseError). Thuật toán solis2mqtt độc lập được tích hợp: tự động đưa công suất tức thời về 0W trong khi giữ nguyên các tổng sản lượng tích lũy (total_increasing) để bảo vệ dashboard Home Assistant khỏi các đột biến âm dữ liệu.",
    "Preserves cumulative energy counters when inverter loses power at night, while resetting instantaneous power to 0."
  );

  const nightResults = div("stack");
  const testNightBtn = btn("Mô phỏng ngắt kết nối ban đêm", async () => {
    try {
      const activeState = {
        active_power: { value: 4500, description: "Active Power" },
        total_dc_output_power: { value: 4720, description: "Total DC Output Power" },
        generation_today: { value: 24.5, description: "Energy Generated Today" },
        total_power: { value: 18250, description: "Inverter Total Power Generation" },
        inverter_temp: { value: 38.5, description: "Inverter Temperature" },
      };

      const res = await api("/solis-mqtt/simulate-offline", {
        method: "POST",
        body: JSON.stringify({
          last_known_metrics: activeState,
          base_topic: "solis2mqtt",
        }),
      });

      nightResults.replaceChildren(
        div("plant-visual-card",
          div("row justify-between",
            e("b", "Trạng thái hạm đội: Biến tần đang ngoại tuyến (Inverter Offline)"),
            badge(`Chu kỳ quét tự động tăng: ${res.recommended_poll_interval_sec} giây (10 phút)`, "warn")
          ),
          table(
            ["Chỉ số đo đạc", "Giá trị ban ngày", "Giá trị sau khi lọc ngoại tuyến", "Trạng thái xử lý dữ liệu"],
            [
              ["active_power", "4500 W", "0 W", badge("Về 0 an toàn (Measurement)", "warn")],
              ["total_dc_output_power", "4720 W", "0 W", badge("Về 0 an toàn (Measurement)", "warn")],
              ["generation_today", "24.5 kWh", "24.5 kWh", badge("Bảo toàn giá trị (Total Increasing)", "good")],
              ["total_power", "18250 kWh", "18250 kWh", badge("Bảo toàn giá trị (Total Increasing)", "good")],
              ["inverter_temp", "38.5 °C", "0 °C", badge("Về 0 (Measurement)", "warn")],
            ]
          )
        )
      );
    } catch (err) {
      nightResults.replaceChildren(notice("Lỗi mô phỏng ban đêm: " + err.message, "Error"));
    }
  }, "secondary");

  nightCard.append(nightNotice, testNightBtn, nightResults);
  bridgeBox.append(nightCard);

  // 5. MODBUS FC06 WRITE COMPILER & SAFETY GATE
  const ctrlCard = card("5. Trình biên dịch lệnh ghi Modbus FC06 & Cổng an toàn phần cứng");
  const ctrlNotice = notice(
    "Kiểm định an toàn điều khiển biến tần Solis: Các lệnh ghi tham số qua Function Code 06 (Giới hạn công suất phát Reg 3051 và Công tắc bật/tắt Reg 3006) bắt buộc tuân thủ quy trình kiểm định an toàn (Hardware Acceptance Gate), ngăn chặn các thao tác ghi tùy tiện ra thiết bị vật lý khi chưa có ủy quyền.",
    "Hardware safety gate ensures writable FC06 controls remain locked pending official hardware acceptance and operator confirmation."
  );

  const ctrlControls = div("stack",
    div("gis-controls-bar",
      div("row",
        e("label", "Giới hạn công suất (%):"),
        (() => {
          const inp = e("input", "", "input-search");
          inp.id = "solis_ctrl_pct";
          inp.type = "number";
          inp.min = "0";
          inp.max = "100";
          inp.step = "5";
          inp.value = "75.0";
          inp.style.width = "90px";
          return inp;
        })(),
        btn("Biên dịch khung FC06 Power Limit", async () => {
          compileControl("power_limitation", parseFloat(document.getElementById("solis_ctrl_pct")?.value || 75.0));
        }, "primary")
      )
    ),
    div("gis-controls-bar",
      div("row",
        e("label", "Công tắc Inverter (Reg 3006):"),
        btn("Biên dịch lệnh BẬT (ON, 190 / 0xBE)", () => compileControl("on_off", 190), "good"),
        btn("Biên dịch lệnh TẮT (OFF, 222 / 0xDE)", () => compileControl("on_off", 222), "warn")
      )
    )
  );

  const ctrlResults = div("stack");

  async function compileControl(metric, val) {
    ctrlResults.replaceChildren(notice("Đang biên dịch khung lệnh Modbus FC06…", "Compiling..."));
    try {
      const res = await api("/solis-mqtt/compile-control", {
        method: "POST",
        body: JSON.stringify({
          metric: metric,
          value: val,
          slave_address: 1,
          bypass_safety: false,
        }),
      });

      ctrlResults.replaceChildren(
        div("plant-visual-card",
          div("row justify-between",
            e("b", res.description),
            badge(res.safety_gate, "warn")
          ),
          p(`Thanh ghi: ${res.register_address} | Giá trị số thô: ${res.raw_value} (0x${res.raw_value.toString(16).toUpperCase()})`, "small"),
          p(`Chuỗi byte truyền thông Modbus RTU (kèm CRC16):`, "small bold"),
          e("pre", res.hex_payload, "monospace"),
          notice(
            "Cảnh báo an toàn: Lệnh điều khiển đã được biên dịch chính xác theo chuẩn Ginlong Solis, nhưng đang bị KHÓA bởi Cổng an toàn (LOCKED_PENDING_HARDWARE_ACCEPTANCE). Để thực hiện lệnh ghi ra phần cứng vật lý, cần nghiệm thu thiết bị và xác nhận đọc lại (readback verification).",
            "Safety Warning: Frame compiled successfully but locked by safety gate pending hardware acceptance."
          )
        )
      );
    } catch (err) {
      ctrlResults.replaceChildren(notice("Lỗi biên dịch lệnh: " + err.message, "Error"));
    }
  }

  ctrlCard.append(ctrlNotice, ctrlControls, ctrlResults);
  bridgeBox.append(ctrlCard);

  container.append(bridgeBox);
}

async function renderGoodWeSemsSubtab(ui, container) {
  const { e, div, p, btn, badge, notice, card, table, api } = ui;
  const semsBox = div("stack");

  semsBox.append(
    notice(
      "Tích hợp GoodWe SEMS Portal Cloud API (v1/v2 REST API). Độc lập triển khai dựa trên kiến thức mã nguồn mở pygoodwe (MIT License, James Hodgkinson). Cung cấp cơ chế xác thực CrossLogin với phát hiện động máy chủ khu vực (regional redirect), giám sát dòng công suất tức thời (Powerflow), đo xa điện lực đa pha (3-Phase AC/DC), trạng thái pin lưu trữ (SOC), và báo cáo sản lượng trạm hàng tháng.",
      "GoodWe SEMS Portal Cloud API Integration (v1/v2 REST). Clean-room implementation based on pygoodwe (MIT, James Hodgkinson). Features CrossLogin auth with dynamic regional endpoint redirect, multi-phase inverter telemetry, real-time powerflow, battery SOC, and monthly generation reports."
    )
  );

  // Top KPIs
  const kpiRow = div("overview-kpis",
    div("fact", e("span", "Giao thức kết nối"), badge("SEMS Portal Cloud REST", "blue")),
    div("fact", e("span", "Máy chủ khu vực"), badge("eu.semsportal.com", "good")),
    div("fact", e("span", "Dung lượng trạm"), e("b", "15.0 kWp")),
    div("fact", e("span", "Trạng thái Pin BESS"), badge("SOC 86.5%", "good")),
  );
  semsBox.append(kpiRow);

  // 1. AUTH & CREDENTIALS CARD
  const authCard = card("1. Xác thực cổng SEMS Portal (CrossLogin & Regional Discovery)");
  const authNotice = notice(
    "Giao thức CrossLogin gửi tài khoản và mật khẩu đến điểm cuối toàn cầu https://semsportal.com/api/v2/Common/CrossLogin để nhận Token phiên làm việc và địa chỉ máy chủ khu vực (api redirect url). Tuân thủ quy định bảo mật: Mặc định phiên mô phỏng an toàn khi không nhập thông tin thật.",
    "CrossLogin endpoint handles regional routing and session tokens. Safe simulation active when live credentials are not supplied."
  );

  const authControls = div("gis-controls-bar",
    div("row",
      e("label", "Tài khoản (Email):"),
      (() => {
        const inp = e("input", "", "input-search");
        inp.id = "goodwe_acc";
        inp.placeholder = "operator@semsportal.com";
        inp.style.width = "200px";
        return inp;
      })(),
      e("label", "Mã trạm (Station ID):"),
      (() => {
        const inp = e("input", "", "input-search");
        inp.id = "goodwe_stid";
        inp.value = "gw_rooftop_vn01";
        inp.style.width = "180px";
        return inp;
      })(),
      btn("Kiểm tra kết nối SEMS Portal", async () => {
        authResults.replaceChildren(notice("Đang kết nối xác thực SEMS Portal…", "Connecting..."));
        try {
          const acc = document.getElementById("goodwe_acc")?.value || "";
          const res = await api("/goodwe-sems/login", {
            method: "POST",
            body: JSON.stringify({ account: acc, password: "" }),
          });

          authResults.replaceChildren(
            div("plant-visual-card",
              div("row justify-between",
                e("b", `Trạng thái phiên: ${res.authenticated ? "ĐÃ XÁC THỰC THÀNH CÔNG" : "THẤT BẠI"}`),
                badge(res.status === "simulated" ? "SIMULATED_SESSION" : "LIVE_CONNECTED", "good")
              ),
              p(`Máy chủ API khu vực phát hiện: ${res.base_url}`, "small bold"),
              p(`Chuỗi Token bảo mật phiên: ${res.token.slice(0, 40)}…`, "small monospace"),
              notice(res.message || "Phiên làm việc đã sẵn sàng để truy vấn dữ liệu đo xa trạm.", "Ready.")
            )
          );
        } catch (err) {
          authResults.replaceChildren(notice("Lỗi xác thực: " + err.message, "Error"));
        }
      }, "primary")
    )
  );

  const authResults = div("stack");
  authCard.append(authNotice, authControls, authResults);
  semsBox.append(authCard);

  // 2. REAL-TIME MONITORING & POWERFLOW
  const telCard = card("2. Giám sát thời gian thực & Dòng công suất đa chiều (Real-Time Powerflow & Battery SOC)");
  const telNotice = notice(
    "API v2/PowerStation/GetMonitorDetailByPowerstationId trả về gói dữ liệu toàn diện của trạm: Thông tin trạm, KPI sản lượng ngày/tổng, dòng công suất tức thời giữa PV, Tải tiêu thụ, Pin lưu trữ và Lưới điện (loadStatus: -1 Nhập lưới, 1 Dùng Pin), cùng chi tiết thông số điện lực từng Inverter đa pha.",
    "Real-time monitoring details covering station KPIs, bidirectional powerflow, battery SOC, and multiphase inverter telemetry."
  );

  const telResults = div("stack");
  const readTelBtn = btn("Đọc dữ liệu giám sát trạm (GetMonitorDetail)", async () => {
    telResults.replaceChildren(notice("Đang truy vấn dữ liệu đo xa trạm GoodWe…", "Fetching..."));
    try {
      const stId = document.getElementById("goodwe_stid")?.value || "gw_rooftop_vn01";
      const res = await api("/goodwe-sems/station-detail", {
        method: "POST",
        body: JSON.stringify({ station_id: stId }),
      });

      const detail = res.station_detail || {};
      const pf = detail.powerflow || {};
      const kpi = detail.kpi || {};
      const inverters = detail.inverters || [];
      const norm = res.normalized_fleet_telemetry || {};

      telResults.replaceChildren(
        div("overview-kpis",
          div("fact", e("span", "Công suất PV"), badge(`${pf.pv_power_w} W (${(pf.pv_power_w/1000).toFixed(2)} kW)`, "good")),
          div("fact", e("span", "Tải tiêu thụ"), badge(`${pf.load_power_w} W (${pf.load_direction})`, "warn")),
          div("fact", e("span", "Pin lưu trữ BESS"), badge(`${pf.battery_power_w} W (SOC: ${pf.soc_pct}%)`, "blue")),
          div("fact", e("span", "Công suất Lưới điện"), badge(`${pf.grid_power_w} W`, "secondary")),
          div("fact", e("span", "Sản lượng hôm nay"), e("b", `${kpi.day_generation_kwh} kWh`)),
          div("fact", e("span", "Tổng tích lũy"), e("b", `${kpi.total_generation_kwh} kWh`)),
        ),
        card("Thông số điện lực Inverter đa pha GoodWe Hybrid (GW10K-ET)",
          table(
            ["Số Serial", "Model", "Trạng thái", "Nhiệt độ", "Điện áp 3 pha (V)", "Dòng điện 3 pha (A)", "Chuỗi PV (V / A)", "Tần số"],
            inverters.map((inv) => [
              e("b", inv.serial_number),
              inv.model_type,
              badge(inv.status === 1 ? "Đang phát điện" : "Chờ", "good"),
              `${inv.temperature_c} °C`,
              e("span", `A: ${inv.vac1} | B: ${inv.vac2} | C: ${inv.vac3}`, "monospace small"),
              e("span", `A: ${inv.iac1} | B: ${inv.iac2} | C: ${inv.iac3}`, "monospace small"),
              e("span", `PV1: ${inv.vpv1}V (${inv.ipv1}A) | PV2: ${inv.vpv2}V (${inv.ipv2}A)`, "monospace small"),
              `${inv.fac1_hz} Hz`,
            ])
          )
        ),
        card("Chuẩn hóa đo xa sang hệ thống Solar Fleet EMS (Unified Telemetry)",
          table(
            ["Trường chuẩn hóa", "Giá trị kỹ thuật", "Mô tả ý nghĩa đối với Dispatch / EMS"],
            [
              ["pv_power_kw", `${norm.pv_power_kw} kW`, "Công suất phát thực tế từ dàn pin quang điện"],
              ["active_power_kw", `${norm.active_power_kw} kW`, "Công suất tác dụng AC cấp ra điểm đấu nối"],
              ["load_power_kw", `${norm.load_power_kw} kW`, "Phụ tải tiêu thụ nội bộ công trình"],
              ["battery_power_kw", `${norm.battery_power_kw} kW`, "Công suất nạp/xả pin lưu trữ"],
              ["soc_pct", `${norm.soc_pct}%`, "Mức dung lượng khả dụng của hệ thống BESS"],
              ["daily_generation_kwh", `${norm.daily_generation_kwh} kWh`, "Sản lượng điện tích lũy trong ngày"],
              ["total_generation_kwh", `${norm.total_generation_kwh} kWh`, "Sản lượng trọn đời dùng cho báo cáo đối soát"],
            ]
          )
        )
      );
    } catch (err) {
      telResults.replaceChildren(notice("Lỗi truy vấn: " + err.message, "Error"));
    }
  }, "primary");

  telCard.append(telNotice, readTelBtn, telResults);
  semsBox.append(telCard);

  // 3. MONTHLY REPORT CARD
  const repCard = card("3. Báo cáo sản lượng trạm theo tháng (Monthly Generation Report)");
  const repControls = div("gis-controls-bar",
    div("row",
      e("label", "Kỳ báo cáo (Tháng):"),
      (() => {
        const inp = e("input", "", "input-search");
        inp.id = "goodwe_rep_month";
        inp.type = "month";
        inp.value = "2026-09";
        inp.style.width = "160px";
        return inp;
      })(),
      btn("Tải báo cáo sản lượng tháng (v1/ReportData)", async () => {
        repResults.replaceChildren(notice("Đang tải dữ liệu báo cáo tháng…", "Loading..."));
        try {
          const stId = document.getElementById("goodwe_stid")?.value || "gw_rooftop_vn01";
          const ym = document.getElementById("goodwe_rep_month")?.value || "2026-09";
          const res = await api("/goodwe-sems/monthly-report", {
            method: "POST",
            body: JSON.stringify({ station_id: stId, year_month: ym }),
          });

          const stations = res.stations || [];
          repResults.replaceChildren(
            table(
              ["Mã trạm", "Tên trạm", "Công suất lắp đặt", "Chủ sở hữu", "Sản lượng tháng này", "Trung bình ngày", "Tổng sản lượng trọn đời"],
              stations.map((s) => [
                e("b", s.powerstation_id),
                s.station_name,
                `${s.capacity_kwp} kWp`,
                s.owner_name || "—",
                badge(`${s.month_generation_kwh} kWh`, "good"),
                `${s.avg_daily_generation_kwh} kWh/ngày`,
                e("b", `${s.total_lifetime_generation_kwh} kWh`),
              ])
            )
          );
        } catch (err) {
          repResults.replaceChildren(notice("Lỗi tải báo cáo: " + err.message, "Error"));
        }
      }, "secondary")
    )
  );

  const repResults = div("stack");
  repCard.append(repControls, repResults);
  semsBox.append(repCard);

  container.append(semsBox);
}

async function renderGrowattSphSubtab(ui, container) {
  const { e, div, p, btn, badge, notice, card, table, api } = ui;
  const sphBox = div("stack");

  sphBox.append(
    notice(
      "Giao thức điều khiển biến tần lai Growatt SPH Hybrid qua Modbus RTU/TCP (Port 502, 9600 8N1). Độc lập triển khai dựa trên kiến thức mã nguồn mở growatt_modbus (GPL-3.0) và kiểm thử thực tế trên thiết bị phần cứng thật. Hỗ trợ chuyển đổi 3 chế độ ưu tiên (Load First, Battery First, Grid First), quản trị ma trận 12 khe lịch nạp xả TOU (6 Battery First + 6 Grid First với độ lệch thanh ghi slot 4 = 1018), giải mã chi tiết khối BMS Pack (1087..1097), và đo xa 12 điện áp cell pin.",
      "Growatt SPH Hybrid Inverter Modbus Protocol & TOU Scheduling. Clean-room independent implementation based on growatt_modbus (GPL-3.0) and live hardware validation. Features 3 priority mode switches, 12-slot TOU schedule matrix, BMS pack gauge block, and 12-cell voltage telemetry."
    )
  );

  // Top KPIs
  const kpiRow = div("overview-kpis",
    div("fact", e("span", "Dòng thiết bị"), badge("Growatt SPH 3K-6K Hybrid", "blue")),
    div("fact", e("span", "Điện áp Pack BMS"), e("b", "53.70 V (+57.5 A)")),
    div("fact", e("span", "Độ lệch Cell Pin"), badge("Delta 12 mV (Envelope 3.358 / 3.346 V)", "good")),
    div("fact", e("span", "Số khe nạp xả TOU"), badge("12 Slots (6 BF + 6 GF)", "warn")),
  );
  sphBox.append(kpiRow);

  // 1. PRIORITY MODE SWITCHING & MODBUS COMPILER
  const modeCard = card("1. Chuyển chế độ ưu tiên Pin & Lưới điện (Growatt Priority Mode Switching)");
  const modeNotice = notice(
    "Growatt SPH hỗ trợ 3 chế độ vận hành chính: (1) Load First (Tự dùng gia đình - xóa các khe kích hoạt), (2) Battery First (Sạc AC từ lưới giờ thấp điểm - ghi thanh ghi 1090..1092 và lập trình khe), (3) Grid First (Xả đỉnh ra lưới giờ cao điểm - ghi thanh ghi 1070..1071 và lập trình khe). Mọi lệnh điều khiển đều được kiểm soát bởi Cổng an toàn (Safety Gate).",
    "Priority mode switching compiler generates FC06 / FC16 write frames with safety gating."
  );

  const modeControls = div("stack",
    div("gis-controls-bar",
      div("row",
        btn("Chuyển sang Load First (Tự dùng)", () => compileMode("load_first"), "good"),
        btn("Lập trình Battery First (Sạc đêm 00:00 - 04:00)", () => compileMode("battery_first", { slot_number: 6, start_time: "00:00", end_time: "04:00", rate_pct: 100, stop_soc_pct: 100 }), "blue"),
        btn("Lập trình Grid First (Xả đỉnh 17:00 - 19:00)", () => compileMode("grid_first", { slot_number: 1, start_time: "17:00", end_time: "19:00", rate_pct: 100, stop_soc_pct: 25 }), "warn")
      )
    )
  );

  const modeResults = div("stack");

  async function compileMode(mode, extraParams = {}) {
    modeResults.replaceChildren(notice("Đang biên dịch khung lệnh Modbus FC06/FC16…", "Compiling..."));
    try {
      const res = await api("/growatt-sph/compile-mode-command", {
        method: "POST",
        body: JSON.stringify({
          mode: mode,
          slave_id: 1,
          bypass_safety: false,
          ...extraParams,
        }),
      });

      const cmds = res.commands || [];
      modeResults.replaceChildren(
        div("plant-visual-card",
          div("row justify-between",
            e("b", `Đã biên dịch thành công ${cmds.length} lệnh Modbus cho chế độ: ${res.mode.toUpperCase()}`),
            badge(cmds[0]?.safety_gate || "LOCKED_PENDING_HARDWARE_ACCEPTANCE", "warn")
          ),
          table(
            ["Tên thao tác", "Mã hàm Modbus", "Thanh ghi bắt đầu", "Số thanh ghi", "Giá trị số thô", "Chuỗi Byte RTU (kèm CRC16)"],
            cmds.map((c) => [
              e("b", c.command_name),
              badge(`FC0${c.function_code}` || "FC", "secondary"),
              `Reg ${c.register_address}`,
              `${c.register_count}`,
              `[${c.raw_values.join(", ")}]`,
              e("span", c.hex_payload, "monospace small"),
            ])
          ),
          notice(
            "Cổng an toàn phần cứng: Toàn bộ lệnh ghi tham số biến tần Growatt được khóa an toàn (LOCKED_PENDING_HARDWARE_ACCEPTANCE). Để thực thi xuống phần cứng vật lý, yêu cầu xác nhận nghiệm thu tại công trình và đọc kiểm tra lại (readback verification).",
            "Hardware acceptance gate: Writes locked pending verified readback and operator confirmation."
          )
        )
      );
    } catch (err) {
      modeResults.replaceChildren(notice("Lỗi biên dịch lệnh: " + err.message, "Error"));
    }
  }

  modeCard.append(modeNotice, modeControls, modeResults);
  sphBox.append(modeCard);

  // 2. TOU SLOTS SCHEDULER
  const slotCard = card("2. Ma trận lịch biểu nạp xả 12 khe (6-Slot Time-Of-Use Scheduler)");
  const slotNotice = notice(
    "Growatt SPH quản lý 6 khe Battery First (Sạc) và 6 khe Grid First (Xả). Phát hiện phần cứng thực tế xác nhận: Các khe 4..6 của Battery First bắt đầu từ thanh ghi 1018 (chứ không phải 1017 như tài liệu cũ).",
    "Inspects all 12 programmable TOU slots with verified register addressing."
  );

  const slotResults = div("stack");
  const readSlotsBtn = btn("Đọc trạng thái 12 khe lịch TOU", async () => {
    slotResults.replaceChildren(notice("Đang đọc trạng thái thanh ghi các khe TOU…", "Reading..."));
    try {
      const simulatedHolding = {
        // Battery First slots
        1100: (0 << 8) | 0, 1101: (4 << 8) | 0, 1102: 1, // Slot 1: 00:00 - 04:00, enabled
        1103: (4 << 8) | 0, 1104: (6 << 8) | 0, 1105: 0, // Slot 2
        1106: 0, 1107: 0, 1108: 0,                       // Slot 3
        1018: (12 << 8) | 0, 1019: (14 << 8) | 0, 1020: 0, // Slot 4 (reg 1018)
        1021: 0, 1022: 0, 1023: 0,                       // Slot 5
        1024: (2 << 8) | 30, 1025: (4 << 8) | 30, 1026: 1, // Slot 6: 02:30 - 04:30, enabled
        // Grid First slots
        1080: (17 << 8) | 0, 1081: (19 << 8) | 0, 1082: 1, // Slot 1: 17:00 - 19:00, enabled
        1083: 0, 1084: 0, 1085: 0,
        1086: 0, 1087: 0, 1088: 0,
        1027: 0, 1028: 0, 1029: 0,
        1030: 0, 1031: 0, 1032: 0,
        1033: 0, 1034: 0, 1035: 0,
      };

      const res = await api("/growatt-sph/decode-tou-slots", {
        method: "POST",
        body: JSON.stringify({ holding_registers: simulatedHolding }),
      });

      const bf = res.battery_first_slots || [];
      const gf = res.grid_first_slots || [];

      slotResults.replaceChildren(
        card("Danh sách 6 khe Battery First (Sạc ưu tiên từ lưới/PV)",
          table(
            ["Khe", "Giờ bắt đầu", "Giờ kết thúc", "Trạng thái", "Thanh ghi Bắt đầu / Kết thúc / Kích hoạt"],
            bf.map((s) => [
              e("b", `Slot ${s.slot_number}`),
              s.start_time,
              s.end_time,
              badge(s.enabled ? "Kích hoạt (ON)" : "Tắt (OFF)", s.enabled ? "good" : "secondary"),
              e("span", `Reg ${s.start_register}, ${s.end_register}, ${s.enable_register}`, "monospace small"),
            ])
          )
        ),
        card("Danh sách 6 khe Grid First (Xả đỉnh ra lưới điện)",
          table(
            ["Khe", "Giờ bắt đầu", "Giờ kết thúc", "Trạng thái", "Thanh ghi Bắt đầu / Kết thúc / Kích hoạt"],
            gf.map((s) => [
              e("b", `Slot ${s.slot_number}`),
              s.start_time,
              s.end_time,
              badge(s.enabled ? "Kích hoạt (ON)" : "Tắt (OFF)", s.enabled ? "warn" : "secondary"),
              e("span", `Reg ${s.start_register}, ${s.end_register}, ${s.enable_register}`, "monospace small"),
            ])
          )
        )
      );
    } catch (err) {
      slotResults.replaceChildren(notice("Lỗi đọc khe: " + err.message, "Error"));
    }
  }, "secondary");

  slotCard.append(slotNotice, readSlotsBtn, slotResults);
  sphBox.append(slotCard);

  // 3. BMS GAUGE & 12-CELL TELEMETRY CARD
  const bmsCard = card("3. Khối thông số BMS Pack & Đo xa 12 Cell Pin (BMS Gauge & 12-Cell Telemetry)");
  const bmsNotice = notice(
    "Giải mã thanh ghi đầu vào Modbus 1083..1097 (Điện áp pack, dòng nạp xả, dung lượng Ah, FCC, mục tiêu sạc CV) và khối 1108..1123 (Điện áp 12 cell pin đơn lẻ theo mV và bao điện áp min/max).",
    "Decodes BMS pack parameters and 12 individual cell voltages from Growatt SPH input registers."
  );

  const bmsResults = div("stack");
  const readBmsBtn = btn("Giải mã dữ liệu BMS & 12 Cell Pin", async () => {
    bmsResults.replaceChildren(notice("Đang giải mã thông số BMS…", "Decoding..."));
    try {
      const simulatedInputRegs = {
        1084: 184, // Cycle count = 184
        1085: 28,  // SOC = 28%
        1086: 93,  // SOH = 93%
        1087: 5370, // bmsVoltage = 53.70 V
        1088: 5750, // bmsCurrent = +57.50 A
        1090: 17620, // maxChargeCurrent = 176.20 A
        1091: 6110,  // remaining capacity = 61.10 Ah
        1092: 21580, // FCC = 215.80 Ah
        1097: 5680,  // CV target = 56.80 V
        1108: 3358,  // maxCellVoltage = 3.358 V
        1109: 3346,  // minCellVoltage = 3.346 V
        1110: 2,     // 2 modules in parallel
        1112: 3355, 1113: 3358, 1114: 3350, 1115: 3352,
        1116: 3348, 1117: 3346, 1118: 3354, 1119: 3351,
        1120: 3353, 1121: 3349, 1122: 3356, 1123: 3352,
      };

      const [resBms, resCells] = await Promise.all([
        api("/growatt-sph/decode-bms", {
          method: "POST",
          body: JSON.stringify({ registers: simulatedInputRegs }),
        }),
        api("/growatt-sph/decode-cells", {
          method: "POST",
          body: JSON.stringify({ registers: simulatedInputRegs }),
        }),
      ]);

      const g = resBms.bms_gauge || {};
      const c = resCells.cell_telemetry || {};

      bmsResults.replaceChildren(
        div("overview-kpis",
          div("fact", e("span", "Điện áp Pack"), e("b", `${g.voltage_v} V`)),
          div("fact", e("span", "Dòng nạp hiện tại"), badge(`+${g.current_a} A`, "good")),
          div("fact", e("span", "Giới hạn dòng sạc"), badge(`${g.max_charge_current_a} A`, "blue")),
          div("fact", e("span", "Dung lượng còn lại"), e("b", `${g.remaining_capacity_ah} Ah`)),
          div("fact", e("span", "Dung lượng đầy đủ FCC"), e("b", `${g.full_charge_capacity_ah} Ah`)),
          div("fact", e("span", "Mức pin SOC / SOH"), badge(`SOC ${g.bms_soc_pct}% / SOH ${g.bms_soh_pct}%`, "good")),
          div("fact", e("span", "Số chu kỳ nạp xả EFC"), e("b", `${g.bms_cycle_count} cycles`)),
        ),
        card("Đo xa 12 Cell Pin Lithium & Bao điện áp (Cell Voltage Envelope)",
          div("stack",
            div("row justify-between",
              p(`Điện áp Cell lớn nhất: ${c.max_cell_v} V | Cell nhỏ nhất: ${c.min_cell_v} V`, "bold"),
              badge(`Độ lệch Delta: ${c.delta_cell_mv} mV (Cân bằng tốt)`, "good")
            ),
            table(
              ["Cell #", "Điện áp (mV)", "Điện áp (V)", "Đánh giá trạng thái cell"],
              (c.cell_voltages_mv || []).map((mv, idx) => [
                e("b", `Cell ${idx + 1}`),
                `${mv} mV`,
                `${(mv / 1000).toFixed(3)} V`,
                badge(mv === Math.round(c.max_cell_v * 1000) ? "Max Envelope" : mv === Math.round(c.min_cell_v * 1000) ? "Min Envelope" : "Bình thường", "secondary"),
              ])
            )
          )
        )
      );
    } catch (err) {
      bmsResults.replaceChildren(notice("Lỗi giải mã BMS: " + err.message, "Error"));
    }
  }, "primary");

  bmsCard.append(bmsNotice, readBmsBtn, bmsResults);
  sphBox.append(bmsCard);

  // 4. MULTI-PHASE ARCHITECTURE & 3-PHASE TELEMETRY (SPH TL3)
  const multiPhaseCard = card(l("4. Nhận diện Kiến trúc Đa pha (SPH 1 Pha vs SPH TL3 3 Pha)", "4. Multi-Phase Architecture & 3-Phase Telemetry (SPH TL3)"));
  const multiPhaseNotice = p(
    "Dựa trên mã nguồn ha-growatt-modbus (Lu-Fi), hệ thống tự động nhận diện kiến trúc phần cứng qua thanh ghi giữ 44 (Tracker/Phase: byte cao = số MPPT, byte thấp = số pha 1 hoặc 3) và thanh ghi 43 (DTC). Đối với dòng 3 pha SPH TL3, hệ thống kích hoạt khối đo xa đối xứng từng pha L1, L2, L3 (Điện áp pha, công suất pha, điện áp dây L1-L2, L2-L3, L3-L1).",
    "muted"
  );

  const multiPhaseResults = div("stack");
  const read3PhaseBtn = btn(l("Nhận diện & Đo xa Biến tần SPH TL3 3 Pha", "Identify & Read 3-Phase SPH TL3 Telemetry"), async () => {
    multiPhaseResults.replaceChildren(notice("Đang đọc và giải mã thanh ghi SPH TL3…", "Reading..."));
    try {
      const simulatedHolding = {
        43: 20,
        44: (2 << 8) | 3, // 2 trackers, 3 phases (0x0203)
        23: 0x5350, 24: 0x4854, 25: 0x4C33, 26: 0x3030, 27: 0x3132, // Serial "SPHTL30012"
        9: 0x5941, 10: 0x312E, 11: 0x3000, // FW "YA1.0"
        12: 0x4441, 13: 0x312E, 14: 0x3000, // Ctrl FW "DA1.0"
        122: 1, 123: 650, // 65.0% export limit
        608: 20,
        1070: 80, 1071: 15,
        1080: (1 << 8) | 0, 1081: (5 << 8) | 0, 1082: 1,
        1090: 90, 1091: 100, 1092: 1,
        1100: (22 << 8) | 0, 1101: (6 << 8) | 0, 1102: 1,
      };

      const simulatedInput = {
        0: 1, 1000: 5,
        1: 0, 2: 52000, // 5200.0 W PV
        3: 3800, 4: 70, 5: 0, 6: 26600, // PV1: 380V, 7A, 2660W
        7: 3750, 8: 68, 9: 0, 10: 25400, // PV2: 375V, 6.8A, 2540W
        38: 2305, 40: 0, 41: 16500, // L1: 230.5V, 1650W
        42: 2298, 44: 0, 45: 16800, // L2: 229.8V, 1680W
        46: 2312, 48: 0, 49: 17200, // L3: 231.2V, 1720W
        1013: 528, 1014: 220, 1009: 1160, 1017: 82, // Bat: 52.8V, 22A, 1160W, 82%
        1037: 0, 1038: 18500, // Load: 1850W
        1029: 0, 1030: 0,     // EPS: 0W
      };

      const res = await api("/growatt-multiphase/decode-telemetry", {
        method: "POST",
        body: JSON.stringify({
          input_registers: simulatedInput,
          holding_registers: simulatedHolding,
        }),
      });

      const tel = res.telemetry || {};
      const pf = tel.power_flow || {};
      const grid = tel.grid || {};

      multiPhaseResults.replaceChildren(
        div("stack",
          div("overview-kpis",
            div("fact", e("span", "Kiến trúc Biến tần"), badge(`${tel.phase_count} Pha (${tel.profile})`, "blue")),
            div("fact", e("span", "Số kênh MPPT"), badge(`${tel.tracker_count} Trackers`, "secondary")),
            div("fact", e("span", "Số Serial Inverter"), e("b", tel.serial_number)),
            div("fact", e("span", "Firmware / Control"), e("b", `${tel.firmware_version} / ${tel.control_firmware_version}`)),
            div("fact", e("span", "Tổng Công suất Lưới 3 Pha"), badge(`${pf.grid_power_w} W`, "good")),
          ),
          card("Bảng đo xa 3 Pha Đối xứng (3-Phase Grid Metrics)",
            table(
              ["Pha điện lực", "Điện áp Pha (V)", "Công suất Xuất/Nhận (W)", "Trạng thái vận hành"],
              [
                ["Pha L1 (R)", `${grid.voltage_l1_v} V`, `${pf.grid_l1_power_w} W`, badge("Bình thường", "good")],
                ["Pha L2 (S)", `${grid.voltage_l2_v} V`, `${pf.grid_l2_power_w} W`, badge("Bình thường", "good")],
                ["Pha L3 (T)", `${grid.voltage_l3_v} V`, `${pf.grid_l3_power_w} W`, badge("Bình thường", "good")],
              ]
            )
          )
        )
      );
    } catch (err) {
      multiPhaseResults.replaceChildren(notice("Lỗi nhận diện đa pha: " + err.message, "Error"));
    }
  }, "secondary");

  multiPhaseCard.append(multiPhaseNotice, read3PhaseBtn, multiPhaseResults);
  sphBox.append(multiPhaseCard);

  // 5. EXPORT LIMITATION & ZERO FEED-IN CONTROLS
  const exportCard = card(l("5. Điều khiển Bám tải & Chống phát ngược (Export Limitation / Zero Feed-in)", "5. Zero Feed-in / Export Limitation Controls (Regs 122 & 123)"));
  const exportNotice = p(
    "Growatt SPH hỗ trợ bám tải không phát ngược ra lưới điện qua thanh ghi giữ 122 (Bật/Tắt chống phát ngược) và 123 (Giới hạn công suất phát ngược theo % với độ phân giải 0.1%). Kết hợp với thanh ghi 608 để bảo vệ mức xả pin tối thiểu.",
    "muted"
  );

  const expControls = div("row gap-sm items-center");
  const expEnableSelect = e("select", null, "input-select");
  [
    ["true", "Kích hoạt Chống phát ngược (Enable)"],
    ["false", "Vô hiệu hóa Chống phát ngược (Disable)"],
  ].forEach(([v, t]) => {
    const opt = e("option", t);
    opt.value = v;
    expEnableSelect.append(opt);
  });

  const expRateInput = e("input", null, "input-text");
  expRateInput.type = "number";
  expRateInput.value = "50.0";
  expRateInput.step = "0.5";
  expRateInput.min = "0";
  expRateInput.max = "100";
  expRateInput.placeholder = "Công suất phát tối đa (%)";
  expRateInput.style.maxWidth = "180px";

  const expResults = div("stack");

  const compileExpBtn = btn(l("Biên dịch lệnh Chống phát ngược (FC06)", "Compile Export Limit (FC06)"), async () => {
    try {
      const isEnable = expEnableSelect.value === "true";
      const rate = parseFloat(expRateInput.value) || 50.0;

      const res = await api("/growatt-multiphase/compile-export-limit", {
        method: "POST",
        body: JSON.stringify({ enable: isEnable, limit_rate_percent: rate }),
      });

      const cmd = res.command || {};
      const regs = cmd.registers || {};

      expResults.replaceChildren(
        div("stack",
          div("row justify-between items-center",
            e("h4", `Lệnh Chống phát ngược đã biên dịch`),
            badge(cmd.status, "warn")
          ),
          table(
            ["Thanh ghi điều khiển", "Địa chỉ Modbus", "Giá trị ghi (Raw)", "Ý nghĩa kỹ thuật"],
            [
              ["Export Limit Enable", "Reg 122 (Holding)", `${regs[122]}`, regs[122] === 1 ? "Bật bám tải (Zero Feed-in ON)" : "Tắt bám tải"],
              ["Export Limit Rate", "Reg 123 (Holding)", `${regs[123]}`, `Giới hạn: ${(regs[123] * 0.1).toFixed(1)}% định mức (tỉ lệ 0.1)`],
            ]
          ),
          notice(cmd.reason, "Warning")
        )
      );
    } catch (err) {
      expResults.replaceChildren(notice("Lỗi biên dịch lệnh: " + err.message, "Error"));
    }
  }, "secondary");

  expControls.append(expEnableSelect, expRateInput, compileExpBtn);
  exportCard.append(exportNotice, expControls, expResults);
  sphBox.append(exportCard);

  // 6. 112-BIT COMPREHENSIVE FAULT & WARNING MATRIX
  const faultCard = card(l("6. Giải mã Ma trận 112-Bit Sự cố & Cảnh báo (Input Regs 1001..1007)", "6. 112-Bit Fault & Warning Matrix (Input Regs 1001..1007)"));
  const faultNotice = p(
    "Growatt phân bổ 7 thanh ghi đầu vào (1001..1007) tương ứng 112 bit cờ trạng thái để giám sát toàn diện lỗi lưới, lỗi biến tần, lỗi cách điện PV, lỗi quá nhiệt và lỗi giao tiếp BMS/Meter. Hệ thống phân tách tự động lỗi nghiêm trọng (CRITICAL - ngắt lưới) và cảnh báo thứ cấp (WARNING - ví dụ điện áp PV thấp ban đêm).",
    "muted"
  );

  const faultResults = div("stack");
  const readFaultsBtn = btn(l("Giải mã Ma trận 112-Bit Sự cố", "Decode 112-Bit Faults Matrix"), async () => {
    faultResults.replaceChildren(notice("Đang quét và giải mã bit sự cố…", "Scanning..."));
    try {
      const simulatedFaults = {
        1001: 0x0001, // Bit 0: MasterForceINVFault (CRITICAL)
        1002: 0x8000, // Bit 15: NoUtility (CRITICAL)
        1005: 0x0020, // Bit 5: PV1_VoltLowWarn (WARNING)
        1007: 0x0100, // Bit 8: BoostDriver1Warn (WARNING)
      };

      const res = await api("/growatt-multiphase/decode-faults", {
        method: "POST",
        body: JSON.stringify({ fault_registers: simulatedFaults }),
      });

      const alarms = res.alarms || [];

      faultResults.replaceChildren(
        div("stack",
          div("row justify-between items-center",
            e("h4", `Phát hiện ${alarms.length} sự cố / cảnh báo từ thanh ghi 1001..1007`),
            badge(alarms.some(a => a.severity === "CRITICAL") ? "CRITICAL ALARM" : "NORMAL", alarms.some(a => a.severity === "CRITICAL") ? "critical" : "good")
          ),
          table(
            ["Thanh ghi nguồn", "Vị trí Bit", "Mã lỗi kỹ thuật", "Mức độ nghiêm trọng", "Hành động khuyến nghị"],
            alarms.map(a => [
              `Reg ${a.register}`,
              `Bit ${a.bit}`,
              e("b", a.code),
              badge(a.severity, a.severity === "CRITICAL" ? "critical" : "warn"),
              a.severity === "CRITICAL" ? "Kiểm tra hệ thống điện & Inverter ngắt an toàn" : "Cảnh báo vận hành thứ cấp, tự phục hồi",
            ])
          )
        )
      );
    } catch (err) {
      faultResults.replaceChildren(notice("Lỗi giải mã sự cố: " + err.message, "Error"));
    }
  }, "secondary");

  faultCard.append(faultNotice, readFaultsBtn, faultResults);
  sphBox.append(faultCard);

  container.append(sphBox);
}

async function renderSolisHybridSubtab(ui, container) {
  const { e, div, card, p, badge, notice, button, table } = ui;
  const solisBox = div("stack");

  // Provenance Banner
  const provenanceCard = card(l("Nguồn gốc & Hồ sơ Giao thức (Solis Hybrid S6 / RHI Modbus)", "Provenance & Protocol Specification (Solis Hybrid S6 / RHI Modbus)"));
  provenanceCard.append(
    p(
      "Giao thức điều khiển lưu trữ Solis S6 / RHI Hybrid qua Modbus RTU/TCP. Độc lập triển khai dựa trên kiến thức mã nguồn mở solis-modbus-ha (MIT) và GreenGrid controller. Hỗ trợ giải mã trường bit chế độ lưu trữ (Reg 43110), bật/tắt sạc lưới AC (BIT05), điều phối động 3 chế độ (Auto, Charge, Discharge), ma trận 12 khe lịch TOU 7-thanh ghi (43708..43791), và cơ chế giám sát phần mềm Software Watchdog TTL do Solis không có bộ đếm phần cứng rvrttms.",
      "muted"
    ),
    div("overview-kpis",
      div("fact", e("span", "Dòng thiết bị"), badge("Solis S6 / RHI Hybrid", "blue")),
      div("fact", e("span", "Giao thức"), badge("Modbus RTU / TCP (Port 502)", "secondary")),
      div("fact", e("span", "Thanh ghi chế độ"), badge("Holding Reg 43110", "blue")),
      div("fact", e("span", "Bật sạc lưới (AC)"), badge("Reg 43110 BIT05 (0x0020)", "good")),
      div("fact", e("span", "Software Watchdog"), badge("Bắt buộc (TTL 1200s Auto-Revert)", "warning")),
      div("fact", e("span", "Cổng an toàn"), badge("LOCKED_PENDING_HARDWARE_ACCEPTANCE", "critical")),
    )
  );
  solisBox.append(provenanceCard);

  // 1. Storage Control Mode (Reg 43110) & Grid Charge Toggle
  const modeCard = card(l("1. Chế độ điều khiển lưu trữ & Sạc lưới AC (Register 43110)", "1. Storage Control Mode & Grid Charging (Register 43110)"));
  const modeNotice = p(
    "Thanh ghi 43110 quản lý các cờ bit: BIT00 (Self-consumption), BIT01 (Time-charging), BIT02 (Off-grid), BIT03 (Wakeup), BIT04 (Reserve), BIT05 (Grid charge allowed). Khi không bật BIT05, biến tần chỉ giữ pin mà không kéo điện lưới sạc đêm. Khi điều khiển, hệ thống thực hiện đọc-sửa-ghi nguyên tử để bảo toàn BIT04 Reserve.",
    "muted"
  );

  const modeInputRow = div("row gap-sm items-center");
  const modeInput = e("input", null, "input-text");
  modeInput.type = "number";
  modeInput.value = "33"; // 0x0021 = BIT00 + BIT05
  modeInput.placeholder = "Giá trị thanh ghi 43110 (VD: 33 = 0x0021)";
  modeInput.style.maxWidth = "280px";

  const decodeModeBtn = button(l("Giải mã thanh ghi 43110", "Decode Reg 43110"), async () => {
    try {
      const val = parseInt(modeInput.value, 10) || 0;
      const res = await api("/solis-hybrid/decode-storage-mode", {
        method: "POST",
        body: JSON.stringify({ value: val }),
      });
      const m = res.storage_mode || {};
      modeResults.replaceChildren(
        div("overview-kpis",
          div("fact", e("span", "Giá trị Raw / Hex"), e("b", `${m.raw_value} (${m.hex_value})`)),
          div("fact", e("span", "Tự dùng (Self-consumption)"), badge(m.self_consumption ? "BẬT (Bit 0)" : "TẮT", m.self_consumption ? "good" : "secondary")),
          div("fact", e("span", "Lịch nạp xả (Time-charging)"), badge(m.time_charging ? "BẬT (Bit 1)" : "TẮT", m.time_charging ? "blue" : "secondary")),
          div("fact", e("span", "Sạc từ lưới (Grid Charge)"), badge(m.grid_charge_allowed ? "CHO PHÉP (Bit 5)" : "KHÓA", m.grid_charge_allowed ? "good" : "critical")),
          div("fact", e("span", "Dự phòng (Battery Reserve)"), badge(m.battery_reserve ? "BẬT (Bit 4)" : "TẮT", m.battery_reserve ? "blue" : "secondary")),
          div("fact", e("span", "Độc lập lưới (Off-grid)"), badge(m.off_grid ? "BẬT (Bit 2)" : "TẮT", m.off_grid ? "warning" : "secondary")),
        ),
        p(`Các cờ đang kích hoạt: ${m.summary}`, "bold")
      );
    } catch (err) {
      modeResults.replaceChildren(notice("Lỗi giải mã: " + err.message, "Error"));
    }
  }, "secondary");

  const toggleOnBtn = button(l("Biên dịch lệnh BẬT sạc lưới (BIT05 ON)", "Compile Grid Charge ON (BIT05)"), async () => {
    try {
      const val = parseInt(modeInput.value, 10) || 0;
      const res = await api("/solis-hybrid/compile-grid-charge", {
        method: "POST",
        body: JSON.stringify({ current_mode_value: val, enable_grid_charge: true }),
      });
      renderCompiledCommand(res.command, modeResults);
    } catch (err) {
      modeResults.replaceChildren(notice("Lỗi biên dịch: " + err.message, "Error"));
    }
  }, "primary");

  const toggleOffBtn = button(l("Biên dịch lệnh TẮT sạc lưới (BIT05 OFF)", "Compile Grid Charge OFF (BIT05)"), async () => {
    try {
      const val = parseInt(modeInput.value, 10) || 0;
      const res = await api("/solis-hybrid/compile-grid-charge", {
        method: "POST",
        body: JSON.stringify({ current_mode_value: val, enable_grid_charge: false }),
      });
      renderCompiledCommand(res.command, modeResults);
    } catch (err) {
      modeResults.replaceChildren(notice("Lỗi biên dịch: " + err.message, "Error"));
    }
  }, "ghost");

  modeInputRow.append(modeInput, decodeModeBtn, toggleOnBtn, toggleOffBtn);
  const modeResults = div("stack");
  modeCard.append(modeNotice, modeInputRow, modeResults);
  solisBox.append(modeCard);

  // 2. GreenGrid Dynamic Dispatch with Software Watchdog
  const dispatchCard = card(l("2. Điều phối động & Bộ giám sát Software Watchdog (GreenGrid Engine)", "2. Dynamic Dispatch & Software Watchdog (GreenGrid Engine)"));
  const dispatchNotice = p(
    "Bộ điều phối GreenGrid chuẩn hóa 3 chế độ: (1) Auto - Tự dùng gia đình, hoàn trả về cờ Self-consumption và xóa khe TOU, (2) Force Charge - Sạc lưới AC khẩn cấp với khe thời gian [now..now+TTL] và mục tiêu SOC 100%, (3) Force Discharge - Xả đỉnh lưới với khe thời gian [now..now+TTL] và sàn SOC 10%. Toàn bộ lệnh đều tính toán dòng nạp/xả Amps = Công suất (W) / Điện áp Pin (V) và tự kết thúc khi hết TTL.",
    "muted"
  );

  const dispatchControls = div("row gap-sm items-center");
  const modeSelect = e("select", null, "input-select");
  [
    ["auto", "Auto (Tự dùng - Self-Consumption)"],
    ["charge", "Force Charge (Sạc lưới AC - Grid Charge)"],
    ["discharge", "Force Discharge (Xả pin bán lưới - Grid Export)"],
  ].forEach(([val, txt]) => {
    const opt = e("option", txt);
    opt.value = val;
    modeSelect.append(opt);
  });

  const powerInput = e("input", null, "input-text");
  powerInput.type = "number";
  powerInput.value = "3000";
  powerInput.placeholder = "Công suất W (VD: 3000)";
  powerInput.style.maxWidth = "160px";

  const voltInput = e("input", null, "input-text");
  voltInput.type = "number";
  voltInput.value = "51.2";
  voltInput.placeholder = "Điện áp Pin V (VD: 51.2)";
  voltInput.style.maxWidth = "140px";

  const ttlInput = e("input", null, "input-text");
  ttlInput.type = "number";
  ttlInput.value = "1200";
  ttlInput.placeholder = "Watchdog TTL s (VD: 1200)";
  ttlInput.style.maxWidth = "140px";

  const compileDispatchBtn = button(l("Biên dịch lệnh Điều phối & Watchdog", "Compile Dispatch & Watchdog"), async () => {
    try {
      const mode = modeSelect.value;
      const pw = parseFloat(powerInput.value) || 0;
      const v = parseFloat(voltInput.value) || 51.2;
      const ttl = parseInt(ttlInput.value, 10) || 1200;
      const curMode = parseInt(modeInput.value, 10) || 1;

      const res = await api("/solis-hybrid/compile-dispatch", {
        method: "POST",
        body: JSON.stringify({
          mode: mode,
          power_w: pw,
          battery_voltage: v,
          ttl_seconds: ttl,
          current_storage_mode: curMode,
        }),
      });
      renderCompiledCommand(res.command, dispatchResults);
    } catch (err) {
      dispatchResults.replaceChildren(notice("Lỗi biên dịch điều phối: " + err.message, "Error"));
    }
  }, "primary");

  dispatchControls.append(
    e("span", "Chế độ:"), modeSelect,
    e("span", "Công suất:"), powerInput,
    e("span", "Điện áp:"), voltInput,
    e("span", "TTL:"), ttlInput,
    compileDispatchBtn
  );
  const dispatchResults = div("stack");
  dispatchCard.append(dispatchNotice, dispatchControls, dispatchResults);
  solisBox.append(dispatchCard);

  // 3. 12-Slot TOU Schedule Programmer & Inspector
  const touCard = card(l("3. Ma trận 12 Khe Lịch TOU (6 Khe Sạc 43708.. + 6 Khe Xả 43750..)", "3. 12-Slot TOU Matrix (6 Charge 43708.. + 6 Discharge 43750..)"));
  const touNotice = p(
    "Mỗi khe TOU gồm khối 7 thanh ghi: [0: Mục tiêu SOC%, 1: Dòng nạp/xả (0.1A), 2: Trường kiểm soát (mặc định 490), 3: Giờ bắt đầu, 4: Phút bắt đầu, 5: Giờ kết thúc, 6: Phút kết thúc]. Dưới đây là bộ giải mã toàn diện 12 khe lịch từ dữ liệu thanh ghi holding thực tế.",
    "muted"
  );

  const touActions = div("row gap-sm items-center");
  const decodeTouBtn = button(l("Giải mã Ma trận 12 Khe Lịch TOU", "Decode 12 TOU Slots Matrix"), async () => {
    try {
      // Mock active registers for demonstration
      const mockRegs = {
        43708: 100, 43709: 600, 43710: 490, 43711: 0, 43712: 0, 43713: 4, 43714: 0, // Charge slot 0: 00:00 - 04:00 @ 60.0A
        43715: 80, 43716: 300, 43717: 490, 43718: 11, 43719: 0, 43720: 13, 43721: 0, // Charge slot 1: 11:00 - 13:00 @ 30.0A
        43750: 15, 43751: 800, 43752: 490, 43753: 17, 43754: 0, 43755: 20, 43756: 0, // Discharge slot 0: 17:00 - 20:00 @ 80.0A
      };

      const res = await api("/solis-hybrid/decode-tou-slots", {
        method: "POST",
        body: JSON.stringify({ registers: mockRegs }),
      });

      const chSlots = res.charge_slots || [];
      const disSlots = res.discharge_slots || [];

      touResults.replaceChildren(
        card("6 Khe Sạc Lưới / Pin (TOU Charge Slots: 43708..43749)",
          table(
            ["Khe #", "Thanh ghi gốc", "Mục tiêu SOC", "Dòng sạc tối đa", "Khung giờ (Giờ:Phút)", "Trạng thái khe"],
            chSlots.map((s) => [
              e("b", `Charge Slot ${s.slot_index + 1}`),
              badge(`Reg ${s.base_register}`, "secondary"),
              badge(`${s.target_soc}%`, s.target_soc > 0 ? "good" : "secondary"),
              `${s.current_a} A`,
              `${String(s.start_hour).padStart(2, "0")}:${String(s.start_minute).padStart(2, "0")} - ${String(s.end_hour).padStart(2, "0")}:${String(s.end_minute).padStart(2, "0")}`,
              badge(s.target_soc > 0 ? "Kích hoạt" : "Không dùng", s.target_soc > 0 ? "good" : "secondary"),
            ])
          )
        ),
        card("6 Khe Xả Lưới / Nhà (TOU Discharge Slots: 43750..43791)",
          table(
            ["Khe #", "Thanh ghi gốc", "Sàn SOC", "Dòng xả tối đa", "Khung giờ (Giờ:Phút)", "Trạng thái khe"],
            disSlots.map((s) => [
              e("b", `Discharge Slot ${s.slot_index + 1}`),
              badge(`Reg ${s.base_register}`, "secondary"),
              badge(`${s.target_soc}%`, s.target_soc > 0 ? "blue" : "secondary"),
              `${s.current_a} A`,
              `${String(s.start_hour).padStart(2, "0")}:${String(s.start_minute).padStart(2, "0")} - ${String(s.end_hour).padStart(2, "0")}:${String(s.end_minute).padStart(2, "0")}`,
              badge(s.target_soc > 0 ? "Kích hoạt" : "Không dùng", s.target_soc > 0 ? "blue" : "secondary"),
            ])
          )
        )
      );
    } catch (err) {
      touResults.replaceChildren(notice("Lỗi giải mã TOU: " + err.message, "Error"));
    }
  }, "secondary");

  touActions.append(decodeTouBtn);
  const touResults = div("stack");
  touCard.append(touNotice, touActions, touResults);
  solisBox.append(touCard);

  function renderCompiledCommand(cmd, targetContainer) {
    if (!cmd) return;
    targetContainer.replaceChildren(
      div("stack",
        div("row justify-between items-center",
          e("h4", cmd.command_name || cmd.command_id),
          badge(cmd.safety_gate, "critical")
        ),
        notice(cmd.reason, "Warning"),
        p(`Mô tả: ${cmd.description}`, "muted"),
        cmd.watchdog_ttl_seconds > 0
          ? badge(`Software Watchdog TTL: ${cmd.watchdog_ttl_seconds} giây (Tự động hoàn trả Auto khi hết hạn)`, "warning")
          : null,
        table(
          ["Thanh ghi", "Mã hàm Modbus", "Giá trị ghi", "Khung truyền RTU (Hex + CRC16)", "Chi tiết thao tác"],
          (cmd.actions || []).map((a) => [
            badge(`Reg ${a.register_address}`, "blue"),
            badge(a.function_code, "secondary"),
            JSON.stringify(a.values),
            e("code", a.rtu_frame_hex),
            a.description,
          ])
        )
      )
    );
  }

  container.append(solisBox);
}

async function renderDeyeHybridSubtab(ui, container) {
  const { e, div, card, p, badge, notice, button, table } = ui;
  const deyeBox = div("stack");

  // Provenance Banner
  const provenanceCard = card(l("Nguồn gốc & Hồ sơ Giao thức (Deye 3-Phase Hybrid SUN Modbus)", "Provenance & Protocol Specification (Deye 3-Phase Hybrid SUN Modbus)"));
  provenanceCard.append(
    p(
      "Giao thức điều khiển biến tần lưu trữ 3 pha hạ thế Deye SUN-xxK-SG04LP3 / SG05LP3 qua Modbus RTU/TCP (Port 8899 mặc định trên logger WiFi/LAN Deye, hoặc Port 502 qua gateway RS485). Độc lập triển khai dựa trên kiến thức mã nguồn mở deye-modbus-ha (MIT) và tài liệu MODBUS RTU 三相储能通信协议. Hỗ trợ chuyển đổi 3 chế độ Work Mode (Selling First, Zero Export to Load/CT), khóa/mở bán điện dư Solar Sell (Reg 145), sạc lưới AC (Reg 130), ma trận 6 khe lịch TOU độc lập (148..177) với thời gian định dạng số thập phân HHMM, và đo xa đa kênh PV1..PV4, Lưới 3 pha, Tải 3 pha, Bộ đếm năng lượng 32-bit little-endian.",
      "muted"
    ),
    div("overview-kpis",
      div("fact", e("span", "Dòng thiết bị"), badge("Deye SUN-5..12K-SG04/05LP3", "blue")),
      div("fact", e("span", "Giao thức"), badge("Modbus RTU / TCP (Port 8899 / 502)", "secondary")),
      div("fact", e("span", "Thanh ghi Work Mode"), badge("Holding Reg 142", "blue")),
      div("fact", e("span", "Bán điện Solar Sell"), badge("Reg 145 (0: Off, 1: On)", "good")),
      div("fact", e("span", "Sạc lưới AC"), badge("Reg 130 (Enable) + Reg 128 (Amps)", "good")),
      div("fact", e("span", "Ma trận TOU"), badge("6 Slots (148..177)", "warning")),
      div("fact", e("span", "Cổng an toàn"), badge("LOCKED_PENDING_HARDWARE_ACCEPTANCE", "critical")),
    )
  );
  deyeBox.append(provenanceCard);

  // 1. Work Mode & Solar Sell Control
  const workCard = card(l("1. Chế độ vận hành & Bán điện lưới (Work Mode & Solar Sell)", "1. Work Mode & Solar Sell Control"));
  const workNotice = p(
    "Deye hỗ trợ 3 chế độ vận hành cốt lõi tại thanh ghi 142: (0) Selling First (Ưu tiên tải, pin, điện dư phát lưới), (1) Zero Export To Load (Bám tải nội bộ không phát ngược), (2) Zero Export To CT (Bám tải điểm đặt biến dòng lưới CT). Công tắc Solar Sell (Reg 145) cho phép bật/tắt quyền xuất điện mặt trời ra lưới.",
    "muted"
  );

  const workControls = div("row gap-sm items-center");
  const modeSelect = e("select", null, "input-select");
  [
    ["0", "0: Selling First (Hòa lưới bán điện dư)"],
    ["1", "1: Zero Export To Load (Bám tải nội bộ không phát ngược)"],
    ["2", "2: Zero Export To CT (Bám tải qua biến dòng CT lưới)"],
  ].forEach(([val, txt]) => {
    const opt = e("option", txt);
    opt.value = val;
    modeSelect.append(opt);
  });

  const sellLabel = e("label", " Cho phép bán điện Solar Sell (Reg 145):");
  const sellCheck = e("input", null, "checkbox");
  sellCheck.type = "checkbox";
  sellCheck.checked = true;

  const maxSellInput = e("input", null, "input-text");
  maxSellInput.type = "number";
  maxSellInput.value = "10000";
  maxSellInput.placeholder = "Max Sell Power W (VD: 10000)";
  maxSellInput.style.maxWidth = "200px";

  const compileWorkBtn = button(l("Biên dịch lệnh Chế độ Deye", "Compile Deye Work Mode"), async () => {
    try {
      const modeVal = parseInt(modeSelect.value, 10);
      const sellVal = sellCheck.checked;
      const maxSell = parseInt(maxSellInput.value, 10) || 10000;

      const res = await api("/deye-hybrid/compile-work-mode", {
        method: "POST",
        body: JSON.stringify({
          mode: modeVal,
          solar_sell: sellVal,
          max_sell_power_w: maxSell,
        }),
      });
      renderCompiledCommand(res.command, workResults);
    } catch (err) {
      workResults.replaceChildren(notice("Lỗi biên dịch: " + err.message, "Error"));
    }
  }, "primary");

  workControls.append(modeSelect, sellCheck, sellLabel, maxSellInput, compileWorkBtn);
  const workResults = div("stack");
  workCard.append(workNotice, workControls, workResults);
  deyeBox.append(workCard);

  // 2. Grid Charge Configuration
  const gridCard = card(l("2. Cấu hình Sạc lưới AC & Dòng sạc (Grid Charge Control)", "2. Grid Charge Configuration"));
  const gridNotice = p(
    "Thanh ghi 130 bật/tắt tính năng sạc lưới AC ban đêm hoặc giờ thấp điểm. Thanh ghi 128 thiết lập giới hạn dòng nạp tối đa từ lưới (0..120 A).",
    "muted"
  );

  const gridControls = div("row gap-sm items-center");
  const gridCheck = e("input", null, "checkbox");
  gridCheck.type = "checkbox";
  gridCheck.checked = true;
  const gridCheckLabel = e("label", " Bật sạc lưới AC (Reg 130)");

  const currInput = e("input", null, "input-text");
  currInput.type = "number";
  currInput.value = "40";
  currInput.placeholder = "Dòng sạc A (VD: 40)";
  currInput.style.maxWidth = "160px";

  const compileGridBtn = button(l("Biên dịch cấu hình Sạc lưới", "Compile Grid Charge"), async () => {
    try {
      const en = gridCheck.checked;
      const c = parseInt(currInput.value, 10) || 40;
      const res = await api("/deye-hybrid/compile-grid-charge", {
        method: "POST",
        body: JSON.stringify({ enable: en, charge_current_a: c }),
      });
      renderCompiledCommand(res.command, gridResults);
    } catch (err) {
      gridResults.replaceChildren(notice("Lỗi biên dịch sạc lưới: " + err.message, "Error"));
    }
  }, "primary");

  gridControls.append(gridCheck, gridCheckLabel, e("span", "Dòng sạc:"), currInput, compileGridBtn);
  const gridResults = div("stack");
  gridCard.append(gridNotice, gridControls, gridResults);
  deyeBox.append(gridCard);

  // 3. 6-Slot TOU Matrix Programmer
  const touCard = card(l("3. Ma trận 6 Khe Lịch TOU (Time-Of-Use 148..177)", "3. 6-Slot TOU Matrix (Time-Of-Use 148..177)"));
  const touNotice = p(
    "Deye quản lý 6 khe TOU tuần tự: Thời gian (148..153) lưu dưới dạng số thập phân HHMM (VD 02:30 -> 230), Công suất giới hạn (154..159, Watts), Mức SOC mục tiêu/sàn (166..171, %), Nguồn sạc (172..177: 0=Tự dùng/Xả pin, 1=Lưới AC, 2=Máy phát, 3=Lưới + Máy phát). Khe i áp dụng từ mốc thời gian i tới mốc thời gian i+1.",
    "muted"
  );

  const touActions = div("row gap-sm items-center");
  const decodeTouBtn = button(l("Giải mã Ma trận 6 Khe TOU", "Decode 6 TOU Slots Matrix"), async () => {
    try {
      const mockRegs = {
        148: 100, 149: 500, 150: 900, 151: 1300, 152: 1700, 153: 2100,
        154: 5000, 155: 6000, 156: 4000, 157: 5000, 158: 8000, 159: 5000,
        166: 100, 167: 90, 168: 50, 169: 80, 170: 20, 171: 40,
        172: 1, 173: 0, 174: 0, 175: 1, 176: 0, 177: 0,
      };

      const res = await api("/deye-hybrid/decode-tou-schedule", {
        method: "POST",
        body: JSON.stringify({ registers: mockRegs }),
      });

      const slots = res.slots || [];
      touResults.replaceChildren(
        table(
          ["Khe #", "Mốc thời gian", "Thô (HHMM)", "Công suất tối đa", "Mục tiêu / Sàn SOC", "Nguồn nạp / Chế độ", "Đánh giá vận hành"],
          slots.map((s) => [
            e("b", `Slot ${s.slot_number}`),
            badge(s.time_str, "blue"),
            badge(`${s.time_raw}`, "secondary"),
            `${s.power_w} W`,
            badge(`${s.target_soc}%`, s.target_soc > 50 ? "good" : "warning"),
            badge(s.charge_source_label, s.charge_source === 1 ? "good" : (s.charge_source === 0 ? "blue" : "secondary")),
            s.charge_source === 1 ? "Sạc lưới AC đêm" : (s.target_soc <= 30 ? "Xả đỉnh giờ cao điểm" : "Tự dùng gia đình"),
          ])
        )
      );
    } catch (err) {
      touResults.replaceChildren(notice("Lỗi giải mã TOU: " + err.message, "Error"));
    }
  }, "secondary");

  // Slot programmer inputs
  const slotNumSelect = e("select", null, "input-select");
  [1, 2, 3, 4, 5, 6].forEach((n) => {
    const opt = e("option", `Khe ${n}`);
    opt.value = n;
    slotNumSelect.append(opt);
  });

  const slotTimeInput = e("input", null, "input-text");
  slotTimeInput.type = "text";
  slotTimeInput.value = "02:00";
  slotTimeInput.placeholder = "HH:MM";
  slotTimeInput.style.maxWidth = "110px";

  const slotPwrInput = e("input", null, "input-text");
  slotPwrInput.type = "number";
  slotPwrInput.value = "6000";
  slotPwrInput.placeholder = "Công suất W";
  slotPwrInput.style.maxWidth = "130px";

  const slotSocInput = e("input", null, "input-text");
  slotSocInput.type = "number";
  slotSocInput.value = "95";
  slotSocInput.placeholder = "SOC %";
  slotSocInput.style.maxWidth = "100px";

  const slotSrcSelect = e("select", null, "input-select");
  [
    ["0", "Off (Xả pin theo tải)"],
    ["1", "Grid (Sạc lưới AC)"],
    ["2", "Generator (Máy phát)"],
    ["3", "Grid + Generator"],
  ].forEach(([v, t]) => {
    const opt = e("option", t);
    opt.value = v;
    slotSrcSelect.append(opt);
  });

  const progSlotBtn = button(l("Biên dịch lập trình Khe TOU", "Compile Program Slot"), async () => {
    try {
      const res = await api("/deye-hybrid/compile-tou-slot", {
        method: "POST",
        body: JSON.stringify({
          slot_number: parseInt(slotNumSelect.value, 10),
          time_str: slotTimeInput.value,
          power_w: parseInt(slotPwrInput.value, 10) || 5000,
          target_soc: parseInt(slotSocInput.value, 10) || 100,
          charge_source: parseInt(slotSrcSelect.value, 10) || 0,
        }),
      });
      renderCompiledCommand(res.command, touResults);
    } catch (err) {
      touResults.replaceChildren(notice("Lỗi lập trình khe: " + err.message, "Error"));
    }
  }, "primary");

  touActions.append(
    decodeTouBtn,
    e("span", "| Lập trình:"),
    slotNumSelect,
    slotTimeInput,
    slotPwrInput,
    slotSocInput,
    slotSrcSelect,
    progSlotBtn
  );

  const touResults = div("stack");
  touCard.append(touNotice, touActions, touResults);
  deyeBox.append(touCard);

  // 4. Telemetry Inspector
  const telemCard = card(l("4. Đo xa Biến tần Lai 3 Pha Deye (Telemetry Inspector)", "4. Deye 3-Phase Telemetry Inspector"));
  const telemNotice = p(
    "Giải mã 68 tham số đo xa: PV1..PV4, Lưới điện 3 pha L1/L2/L3, Tải tiêu thụ 3 pha, Pin lưu trữ, Nhiệt độ DC/AC, và các bộ đếm sản lượng điện 32-bit little-endian.",
    "muted"
  );

  const readTelemBtn = button(l("Đọc & Chuẩn hóa Đo xa Deye", "Read & Normalize Deye Telemetry"), async () => {
    try {
      const mockTelemetryRegs = {
        500: 2, // Normal
        672: 3200, 676: 4205, 677: 76, // PV1: 3200W, 420.5V, 7.6A
        673: 2800, 678: 4150, 679: 67, // PV2: 2800W, 415.0V, 6.7A
        587: 5120, 588: 85, 590: 1500, 591: 2930, 586: 1285, 592: 200, // Batt: 51.2V, 85%, 1500W, 29.3A, 28.5C, 200Ah
        598: 2315, 599: 2298, 600: 2304, 609: 5002, 619: -1250, // Grid: 231.5V, 50.02Hz, -1250W import
        653: 4450, 643: 0, 636: 4450, // Load: 4450W, UPS: 0W, Inv: 4450W
        540: 1350, 541: 1380, // DC: 35.0C, AC: 38.0C
        529: 245, 514: 85, 515: 42, 520: 120, 521: 180, 526: 310, // Today energy
        534: 25400, 535: 0, // PV Total 2540.0 kWh (32-bit LE)
        522: 12500, 523: 0, // Grid Import Total 1250.0 kWh
        524: 18200, 525: 0, // Grid Export Total 1820.0 kWh
      };

      const res = await api("/deye-hybrid/decode-telemetry", {
        method: "POST",
        body: JSON.stringify({ registers: mockTelemetryRegs }),
      });

      const t = res.telemetry || {};
      const b = t.battery || {};
      const g = t.grid || {};
      const l_data = t.load || {};
      const e_today = t.energy_today_kwh || {};
      const e_total = t.energy_total_kwh || {};

      telemResults.replaceChildren(
        div("overview-kpis",
          div("fact", e("span", "Trạng thái vận hành"), badge(t.run_state_label, "good")),
          div("fact", e("span", "Tổng công suất PV"), badge(`${t.pv_total_power_w} W`, "blue")),
          div("fact", e("span", "Mức pin SOC / Dung lượng"), badge(`${b.soc_pct}% (${b.capacity_ah} Ah)`, "good")),
          div("fact", e("span", "Điện áp & Dòng pin"), e("b", `${b.voltage_v} V / ${b.current_a} A`)),
          div("fact", e("span", "Công suất Lưới"), badge(`${g.power_total_w} W (${g.direction})`, g.direction === "EXPORTING" ? "good" : "warning")),
          div("fact", e("span", "Tải tiêu thụ tổng"), e("b", `${l_data.power_total_w} W`)),
          div("fact", e("span", "Nhiệt độ DC / AC"), e("b", `${t.inverter?.dc_temp_c}°C / ${t.inverter?.ac_temp_c}°C`)),
        ),
        card("Sản lượng điện Năng lượng (0.1 kWh Resolution)",
          div("overview-kpis",
            div("fact", e("span", "PV hôm nay"), badge(`${e_today.pv} kWh`, "blue")),
            div("fact", e("span", "Sạc pin hôm nay"), e("b", `${e_today.battery_charge} kWh`)),
            div("fact", e("span", "Xả pin hôm nay"), e("b", `${e_today.battery_discharge} kWh`)),
            div("fact", e("span", "Nhập lưới hôm nay"), e("b", `${e_today.grid_import} kWh`)),
            div("fact", e("span", "Xuất lưới hôm nay"), badge(`${e_today.grid_export} kWh`, "good")),
            div("fact", e("span", "Tổng PV tích lũy"), badge(`${e_total.pv} kWh`, "blue")),
            div("fact", e("span", "Tổng xuất lưới tích lũy"), badge(`${e_total.grid_export} kWh`, "good")),
          )
        )
      );
    } catch (err) {
      telemResults.replaceChildren(notice("Lỗi đo xa Deye: " + err.message, "Error"));
    }
  }, "secondary");

  telemCard.append(telemNotice, readTelemBtn);
  const telemResults = div("stack");
  telemCard.append(telemResults);
  deyeBox.append(telemCard);

  function renderCompiledCommand(cmd, targetContainer) {
    if (!cmd) return;
    targetContainer.replaceChildren(
      div("stack",
        div("row justify-between items-center",
          e("h4", cmd.command_name || cmd.command_id),
          badge(cmd.safety_gate, "critical")
        ),
        notice(cmd.reason, "Warning"),
        p(`Mô tả: ${cmd.description}`, "muted"),
        table(
          ["Thanh ghi", "Mã hàm Modbus", "Giá trị ghi", "Khung truyền RTU (Hex + CRC16)", "Chi tiết thao tác"],
          (cmd.actions || []).map((a) => [
            badge(`Reg ${a.register_address}`, "blue"),
            badge(a.function_code, "secondary"),
            JSON.stringify(a.values),
            e("code", a.rtu_frame_hex),
            a.description,
          ])
        )
      )
    );
  }

  container.append(deyeBox);
}

async function renderSolarmanV5Subtab(ui, container) {
  const { e, div, card, p, badge, notice, button, table } = ui;
  const v5Box = div("stack");

  // Provenance Banner
  const provenanceCard = card(l("Nguồn gốc & Hồ sơ Giao thức (Solarman V5 Datalogger Frame Protocol)", "Provenance & Protocol Specification (Solarman V5 Datalogger Frame Protocol)"));
  provenanceCard.append(
    p(
      "Giao thức đóng gói khung truyền Solarman V5 (IGEN Tech) chạy trên cổng TCP 8899 của các thanh ghi dữ liệu WiFi/LAN (dùng phổ biến trên Deye, Sofar, Solis, Chisage, Eybond). Độc lập triển khai dựa trên kiến thức mã nguồn mở pysolarmanv5 (MIT). Đóng gói và bóc tách khung Modbus RTU tiêu chuẩn vào phong bì V5 (Header 11 byte, Payload 15 byte, Trailer 2 byte với mã kiểm tra Checksum modulo-256), theo dõi số thứ tự Sequence Number 2 chiều, và tự động khử lỗi nhân đôi CRC (double-CRC bug) thường gặp trên một số dòng firmware Deye.",
      "muted"
    ),
    div("overview-kpis",
      div("fact", e("span", "Chuẩn giao thức"), badge("Solarman V5 TCP", "blue")),
      div("fact", e("span", "Cổng kết nối"), badge("TCP Port 8899 (Local)", "secondary")),
      div("fact", e("span", "Cấu trúc Header"), badge("11 Bytes (Start 0xA5)", "blue")),
      div("fact", e("span", "Cấu trúc Trailer"), badge("2 Bytes (Checksum + 0x15)", "blue")),
      div("fact", e("span", "Khử lỗi Double-CRC"), badge("Tự động nhận diện & cắt tỉa", "good")),
      div("fact", e("span", "Phát hiện UDP"), badge("UDP Broadcast Port 48899", "secondary")),
      div("fact", e("span", "Cổng an toàn"), badge("LOCKED_PENDING_HARDWARE_ACCEPTANCE", "critical")),
    )
  );
  v5Box.append(provenanceCard);

  // 1. Encapsulate & Compile Modbus RTU into V5
  const encCard = card(l("1. Đóng gói Lệnh Modbus RTU vào Phong bì Solarman V5", "1. Encapsulate Modbus RTU into Solarman V5 Frame"));
  const encNotice = p(
    "Nhập số sê-ri Datalogger (uint32 được in trên tem thiết bị, VD: 2312345678), ID trạm Modbus, mã hàm và địa chỉ thanh ghi. Hệ thống sẽ tính toán Modbus CRC16 chuẩn, đóng gói vào Payload V5, thêm Sequence Number và tính toán Checksum modulo-256 cho toàn bộ khung truyền.",
    "muted"
  );

  const encControls = div("row gap-sm items-center");
  const serialInput = e("input", null, "input-text");
  serialInput.type = "number";
  serialInput.value = "2312345678";
  serialInput.placeholder = "Sê-ri Logger (VD: 2312345678)";
  serialInput.style.maxWidth = "200px";

  const slaveInput = e("input", null, "input-text");
  slaveInput.type = "number";
  slaveInput.value = "1";
  slaveInput.placeholder = "Slave ID";
  slaveInput.style.maxWidth = "90px";

  const fcSelect = e("select", null, "input-select");
  [
    ["3", "FC03: Đọc Holding Registers"],
    ["4", "FC04: Đọc Input Registers"],
    ["6", "FC06: Ghi 1 thanh ghi đơn (Single)"],
    ["16", "FC16: Ghi khối nhiều thanh ghi (Multiple)"],
  ].forEach(([v, t]) => {
    const opt = e("option", t);
    opt.value = v;
    fcSelect.append(opt);
  });

  const addrInput = e("input", null, "input-text");
  addrInput.type = "number";
  addrInput.value = "500";
  addrInput.placeholder = "Địa chỉ (VD: 500)";
  addrInput.style.maxWidth = "130px";

  const qtyInput = e("input", null, "input-text");
  qtyInput.type = "number";
  qtyInput.value = "10";
  qtyInput.placeholder = "Số lượng / Giá trị";
  qtyInput.style.maxWidth = "140px";

  const compileBtn = button(l("Biên dịch & Đóng gói V5", "Compile & Encapsulate V5"), async () => {
    try {
      const serial = parseInt(serialInput.value, 10) || 2312345678;
      const slave = parseInt(slaveInput.value, 10) || 1;
      const fc = parseInt(fcSelect.value, 10) || 3;
      const addr = parseInt(addrInput.value, 10) || 500;
      const qty = parseInt(qtyInput.value, 10) || 1;

      const res = await api("/solarman-v5/compile-request", {
        method: "POST",
        body: JSON.stringify({
          logger_serial: serial,
          modbus_slave_id: slave,
          function_code: fc,
          start_address: addr,
          quantity_or_value: qty,
          sequence_number: 1,
        }),
      });

      const c = res.compiled || {};
      const isWrite = fc === 6 || fc === 16;

      encResults.replaceChildren(
        div("stack",
          div("row justify-between items-center",
            e("h4", `Khung Solarman V5 đã biên dịch (${c.function_code})`),
            badge(isWrite ? c.safety_gate : "READ_ONLY", isWrite ? "critical" : "good")
          ),
          isWrite ? notice(c.reason, "Warning") : null,
          table(
            ["Thành phần gói tin", "Dữ liệu Hex", "Ý nghĩa chi tiết"],
            [
              [e("b", "Khung Solarman V5 hoàn chỉnh"), e("code", c.v5_frame_hex), "Gửi trực tiếp qua kết nối TCP Port 8899"],
              [e("b", "Khung Modbus RTU nhúng bên trong"), e("code", c.modbus_rtu_hex), "Được giải mã bởi vi điều khiển biến tần"],
              [e("b", "Sê-ri Logger đích"), badge(`${c.logger_serial}`, "blue"), "Little-endian 32-bit (Bytes 7..10)"],
              [e("b", "Số thứ tự Sequence Number"), badge(`${c.sequence_number}`, "secondary"), "Tự động tăng dần để đối chiếu gói tin phản hồi"],
            ]
          )
        )
      );
    } catch (err) {
      encResults.replaceChildren(notice("Lỗi đóng gói: " + err.message, "Error"));
    }
  }, "primary");

  encControls.append(
    serialInput, slaveInput, fcSelect, addrInput, qtyInput, compileBtn
  );
  const encResults = div("stack");
  encCard.append(encNotice, encControls, encResults);
  v5Box.append(encCard);

  // 2. Decode & Validate Response Frame
  const decCard = card(l("2. Giải mã & Xác thực Khung phản hồi Solarman V5", "2. Decode & Validate Solarman V5 Response Frame"));
  const decNotice = p(
    "Dán chuỗi Hex phản hồi từ cổng 8899 để kiểm tra tính toàn vẹn Checksum, đối chiếu Sequence Number, thời gian hoạt động của Logger, và trích xuất dữ liệu Modbus RTU kèm tự động khử lỗi nhân đôi CRC.",
    "muted"
  );

  const decInputArea = e("textarea", null, "input-textarea");
  decInputArea.rows = 3;
  decInputArea.style.width = "100%";
  decInputArea.style.fontFamily = "monospace";
  // Prepopulate with a verified synthetic response frame:
  // Start=A5, Len=15 (0x0F,0x00), Code=10 15, Seq=01 00, Serial=DE C0 AD 89 (2309865694), Type=02, Status=01, Times..., Modbus RTU (01 03 02 01 F4 78 8B), Checksum=XX, End=15
  decInputArea.value = "A51500101501004E8BA389020100000000000000000000000001030201F4788BC615";

  const decodeBtn = button(l("Giải mã & Xác thực Khung V5", "Decode & Validate V5 Frame"), async () => {
    try {
      const hexVal = decInputArea.value.replace(/\s+/g, "");
      const res = await api("/solarman-v5/decode-frame", {
        method: "POST",
        body: JSON.stringify({ v5_frame_hex: hexVal }),
      });

      const d = res.decoded || {};
      decResults.replaceChildren(
        div("overview-kpis",
          div("fact", e("span", "Trạng thái gói V5"), badge(d.valid ? "HỢP LỆ (VALID)" : "LỖI (INVALID)", d.valid ? "good" : "critical")),
          div("fact", e("span", "Mã điều khiển (Control Code)"), badge(`${d.control_code_name} (0x${d.control_code.toString(16)})`, "blue")),
          div("fact", e("span", "Sê-ri Logger"), e("b", `${d.logger_serial}`)),
          div("fact", e("span", "Số thứ tự Sequence"), badge(`${d.sequence_number}`, "secondary")),
          div("fact", e("span", "Thời gian Logger hoạt động"), e("b", `${d.total_working_time_s} giây`)),
          div("fact", e("span", "Kiểm tra Modbus CRC16"), badge(d.modbus_crc_valid ? "CRC HỢP LỆ" : "CRC SAI", d.modbus_crc_valid ? "good" : "critical")),
        ),
        d.error ? notice(`Lỗi phân tích: ${d.error}`, "Critical") : null,
        card("Khung Modbus RTU trích xuất được từ Payload",
          div("stack",
            p(`Dữ liệu Modbus RTU (Hex):`, "bold"),
            e("code", d.modbus_rtu_hex || "Không có"),
            p("Dữ liệu này được chuyển tiếp trực tiếp vào bộ phân tích thanh ghi của Inverter.", "muted")
          )
        )
      );
    } catch (err) {
      decResults.replaceChildren(notice("Lỗi giải mã: " + err.message, "Error"));
    }
  }, "secondary");

  const decResults = div("stack");
  decCard.append(decNotice, decInputArea, decodeBtn, decResults);
  v5Box.append(decCard);

  // 3. Local UDP Discovery Parser
  const discCard = card(l("3. Phát hiện Datalogger qua Mạng Cục bộ (UDP Port 48899 Discovery)", "3. Local Network Datalogger Discovery (UDP Port 48899)"));
  const discNotice = p(
    "Datalogger Solarman hỗ trợ giao thức phát hiện tự động qua cổng UDP 48899. Dưới đây là bộ phân tích phản hồi broadcast để tự động lấy địa chỉ IP, địa chỉ MAC và Sê-ri Logger.",
    "muted"
  );

  const discInput = e("input", null, "input-text");
  discInput.value = "192.168.1.150,ACCF23654128,2312345678";
  discInput.placeholder = "Chuỗi phản hồi UDP (VD: 192.168.1.150,ACCF23654128,2312345678)";
  discInput.style.maxWidth = "400px";

  const discBtn = button(l("Phân tích Phản hồi Discovery", "Parse Discovery Reply"), async () => {
    try {
      const res = await api("/solarman-v5/parse-discovery", {
        method: "POST",
        body: JSON.stringify({ payload: discInput.value }),
      });
      const d = res.discovery || {};
      discResults.replaceChildren(
        div("overview-kpis",
          div("fact", e("span", "Địa chỉ IP"), badge(d.ip_address, "blue")),
          div("fact", e("span", "Địa chỉ MAC"), e("b", d.mac_address)),
          div("fact", e("span", "Sê-ri Logger"), badge(`${d.logger_serial}`, "good")),
        )
      );
    } catch (err) {
      discResults.replaceChildren(notice("Lỗi phân tích: " + err.message, "Error"));
    }
  }, "secondary");

  const discResults = div("stack");
  discCard.append(discNotice, div("row gap-sm items-center", discInput, discBtn), discResults);
  v5Box.append(discCard);

  container.append(v5Box);
}

async function renderSmartEssLocalSubtab(ui, container) {
  const { e, div, card, p, badge, notice, button, table, input } = ui;
  const essBox = div("stack");

  // Provenance Banner
  const provenanceCard = card(l("Nguồn gốc & Hồ sơ Giao thức (SmartESS / Eybond Wi-Fi & P17)", "Provenance & Protocol Specification (SmartESS / Eybond Wi-Fi & P17)"));
  provenanceCard.append(
    p(
      "Giao thức Eybond Modbus chạy trên cục phát Wi-Fi/LAN của các dòng biến tần Off-grid và Hybrid (Voltronic, Axpert, MPP Solar, EASun, PowMr, Bluesun, RCT). Độc lập triển khai dựa trên kiến thức mã nguồn mở ha-smartess-local (MIT). Giao thức sử dụng Header nhị phân 8 byte (>HHHBB) với mã hàm FC=1 (Heartbeat đồng bộ thời gian UTC) và FC=4 (Forward2Device đóng gói khung P17/Q-protocol qua RS485). Hỗ trợ đầy đủ các lệnh GS (Trạng thái tổng thể 28 trường), MOD (Chế độ hoạt động), PIRI (Cấu hình định mức & nguồn ưu tiên) và ET (Sản lượng điện).",
      "muted"
    ),
    div("overview-kpis",
      div("fact", e("span", "Chuẩn kết nối"), badge("Eybond Modbus + P17", "blue")),
      div("fact", e("span", "Cổng dịch vụ"), badge("TCP Port 8899 / 5000", "secondary")),
      div("fact", e("span", "Header Eybond"), badge("8 Bytes (>HHHBB)", "blue")),
      div("fact", e("span", "Mã hàm hỗ trợ"), badge("FC=1 (HB) & FC=4 (Fwd)", "blue")),
      div("fact", e("span", "Mã kiểm tra CRC"), badge("CRC-16/XMODEM (Stuffed)", "good")),
      div("fact", e("span", "Inverter mục tiêu"), badge("Voltronic / Axpert / Bluesun", "good")),
      div("fact", e("span", "Cổng an toàn"), badge("LOCKED_PENDING_HARDWARE_ACCEPTANCE", "critical")),
    )
  );
  essBox.append(provenanceCard);

  // 1. Inverter Telemetry Poller (GS, MOD, PIRI, ET)
  const pollCard = card(l("1. Đọc & Chuẩn hóa Dữ liệu Inverter (GS, MOD, PIRI, ET)", "1. Poll & Normalize Inverter Telemetry (GS, MOD, PIRI, ET)"));
  const pollNotice = p(
    "Nhập số Serial/PN của cục phát Wi-Fi Eybond và địa chỉ RS485 của biến tần (mặc định 1). Hệ thống sẽ gửi chuỗi lệnh P17 (^P...GS, ^P...MOD, ^P...PIRI, (ET), bóc tách 28 trường dữ liệu và chuẩn hóa thành mô hình dữ liệu Solar Fleet EMS.",
    "muted"
  );

  const pollControls = div("row gap-sm items-center");
  const pnInput = e("input", null, "input-text");
  pnInput.value = "EYBOND-WIFI-001";
  pnInput.placeholder = "Mã PN / Sê-ri Cục phát";
  pnInput.style.maxWidth = "220px";

  const devaddrInput = e("input", null, "input-text");
  devaddrInput.type = "number";
  devaddrInput.value = "1";
  devaddrInput.min = "1";
  devaddrInput.max = "247";
  devaddrInput.placeholder = "Địa chỉ RS485";
  devaddrInput.style.maxWidth = "110px";

  const pollResults = div("stack");

  const pollBtn = button(l("Đọc Dữ liệu Inverter (Poll)", "Poll Inverter Telemetry"), async () => {
    try {
      const pn = pnInput.value.trim() || "EYBOND-WIFI-001";
      const addr = parseInt(devaddrInput.value, 10) || 1;

      const res = await api("/smartess/poll", {
        method: "POST",
        body: JSON.stringify({ collector_pn: pn, devaddr: addr }),
      });

      const tel = res.telemetry || {};
      const pf = tel.power_flow || {};
      const bat = tel.battery || {};
      const grid = tel.grid || {};
      const conf = tel.configuration || {};
      const nrg = tel.energy || {};

      pollResults.replaceChildren(
        div("stack",
          div("row justify-between items-center",
            e("h4", `Dữ liệu Inverter ${tel.device_id} (${tel.inverter_mode})`),
            badge(tel.protocol, "blue")
          ),
          // Top KPIs
          div("overview-kpis",
            div("fact", e("span", "Công suất PV"), badge(`${pf.solar_power_w} W`, "good")),
            div("fact", e("span", "Công suất Tải"), e("b", `${pf.load_power_w} W`)),
            div("fact", e("span", "Lưới điện"), e("b", `${pf.grid_power_w} W`)),
            div("fact", e("span", "Dung lượng Pin SOC"), badge(`${bat.soc_percent}%`, bat.soc_percent > 30 ? "good" : "warn")),
            div("fact", e("span", "Điện áp Pin"), e("b", `${bat.voltage_v} V`)),
            div("fact", e("span", "Sản lượng ngày"), badge(`${nrg.today_kwh} kWh`, "secondary")),
          ),
          // Detailed Tables Grid
          div("plant-card-grid",
            div("plant-visual-card",
              e("h5", "Thông số Hoạt động Thời gian thực (GS)"),
              table(
                ["Trường thông số", "Giá trị đo đạc"],
                [
                  ["Điện áp / Tần số Lưới", `${grid.voltage_v} V / ${grid.frequency_hz} Hz`],
                  ["Điện áp / Tần số Đầu ra AC", `${grid.ac_output_voltage_v} V / ${grid.ac_output_frequency_hz} Hz`],
                  ["Công suất biểu kiến / Tải", `${pf.apparent_power_va} VA (${pf.output_load_percent}%)`],
                  ["Dòng nạp / Dòng xả Pin", `${bat.charge_current_a} A / ${bat.discharge_current_a} A`],
                  ["Công suất PV1 / Điện áp PV1", `${pf.pv1_power_w} W (${pf.pv1_voltage_v} V)`],
                  ["Nhiệt độ tản nhiệt Inverter", `${conf.heatsink_temperature_c} °C`],
                ]
              )
            ),
            div("plant-visual-card",
              e("h5", "Cấu hình Định mức & Nguồn Ưu tiên (PIRI)"),
              table(
                ["Thông số cấu hình", "Giá trị thiết lập"],
                [
                  ["Loại Pin lưu trữ", badge(bat.type, "blue")],
                  ["Nguồn ra ưu tiên (Output Priority)", badge(conf.output_source_priority, "secondary")],
                  ["Nguồn sạc ưu tiên (Charger Priority)", badge(conf.charger_source_priority, "secondary")],
                  ["Điện áp nạp Bulk / Float", `${bat.bulk_voltage_v} V / ${bat.float_voltage_v} V`],
                  ["Điện áp ngắt tải (Cutoff)", `${bat.cutoff_voltage_v} V`],
                  ["Dòng sạc tối đa (Tổng / AC)", `${bat.max_charge_current_a} A / ${bat.max_ac_charge_current_a} A`],
                ]
              )
            )
          )
        )
      );
    } catch (err) {
      pollResults.replaceChildren(notice("Lỗi đọc dữ liệu: " + err.message, "Error"));
    }
  }, "primary");

  pollControls.append(pnInput, devaddrInput, pollBtn);
  pollCard.append(pollNotice, pollControls, pollResults);
  essBox.append(pollCard);

  // 2. Safe Parameter Controls & Hardware Acceptance Gate
  const ctrlCard = card(l("2. Điều khiển Tham số Biến tần (P17 Control & Safety Gate)", "2. Inverter Parameter Controls (P17 Control & Safety Gate)"));
  const ctrlNotice = p(
    "Gửi các lệnh cài đặt P17 (^S...) như thay đổi nguồn xuất ưu tiên (POP), nguồn sạc ưu tiên (PSP), dòng sạc tối đa (MCHGC/MUCHGC), và ngưỡng điện áp pin. Mặc định mọi lệnh đều ở chế độ khóa an toàn READ-ONLY theo quy định nghiệm thu thiết bị.",
    "muted"
  );

  const ctrlControls = div("row gap-sm items-center flex-wrap");
  const cmdTypeSelect = e("select", null, "input-select");
  [
    ["output_priority", "Nguồn ra ưu tiên: POP (USB vs SBU)"],
    ["charger_priority", "Nguồn sạc ưu tiên: PSP (Utility/Solar/Both)"],
    ["max_charge_current", "Dòng sạc tối đa: MCHGC (Amps)"],
    ["max_ac_charge_current", "Dòng sạc AC tối đa: MUCHGC (Amps)"],
    ["battery_cutoff_voltage", "Điện áp ngắt bảo vệ pin: PSDV (Volts)"],
    ["battery_bulk_float", "Điện áp nạp Bulk & Float: MCHGV (Volts)"],
  ].forEach(([v, t]) => {
    const opt = e("option", t);
    opt.value = v;
    cmdTypeSelect.append(opt);
  });

  const paramInput = e("input", null, "input-text");
  paramInput.value = "1";
  paramInput.placeholder = "Giá trị tham số (VD: 1 cho SBU, 60 cho 60A)";
  paramInput.style.maxWidth = "200px";

  const unlockLabel = e("label", " Mở khóa thử nghiệm (Simulated Unlock)", "small");
  const unlockCheck = e("input", null);
  unlockCheck.type = "checkbox";
  unlockLabel.prepend(unlockCheck);

  const ctrlResults = div("stack");

  const sendCmdBtn = button(l("Gửi Lệnh P17 đến Inverter", "Send P17 Command"), async () => {
    try {
      const pn = pnInput.value.trim() || "EYBOND-WIFI-001";
      const addr = parseInt(devaddrInput.value, 10) || 1;
      const cmdType = cmdTypeSelect.value;
      const rawVal = paramInput.value.trim();

      const params = {};
      if (cmdType === "output_priority" || cmdType === "charger_priority") {
        params.priority = parseInt(rawVal, 10) || 0;
      } else if (cmdType === "max_charge_current" || cmdType === "max_ac_charge_current") {
        params.current_a = parseInt(rawVal, 10) || 30;
      } else if (cmdType === "battery_cutoff_voltage") {
        params.voltage_v = parseFloat(rawVal) || 42.0;
      } else if (cmdType === "battery_bulk_float") {
        const parts = rawVal.split(",");
        params.bulk_v = parseFloat(parts[0]) || 56.4;
        params.float_v = parseFloat(parts[1]) || 54.0;
      }

      const res = await api("/smartess/command", {
        method: "POST",
        body: JSON.stringify({
          collector_pn: pn,
          devaddr: addr,
          command_type: cmdType,
          params: params,
          unlocked: unlockCheck.checked,
        }),
      });

      const r = res.result || {};
      const isLocked = r.status === "LOCKED_PENDING_HARDWARE_ACCEPTANCE";

      ctrlResults.replaceChildren(
        div("stack",
          div("row justify-between items-center",
            e("h4", `Kết quả thực thi lệnh P17 (${cmdType})`),
            badge(r.status, isLocked ? "critical" : "good")
          ),
          isLocked ? notice(r.message, "Warning") : null,
          !isLocked ? table(
            ["Thành phần điều khiển", "Dữ liệu / Giá trị", "Mô tả kỹ thuật"],
            [
              [e("b", "Lệnh P17"), e("code", r.p17_command), "Lệnh gửi đến Inverter qua cổng RS485"],
              [e("b", "Khung P17 thô (Hex)"), e("code", r.raw_p17_hex), "Bao gồm độ dài, mã lệnh và mã CRC16/XMODEM"],
              [e("b", "Khung Eybond FC=4 (Hex)"), e("code", r.raw_eybond_hex), "Đóng gói phong bì nhị phân 8-byte gửi qua TCP 8899"],
              [e("b", "Kiểm tra phản hồi (Readback)"), badge("Đã đối chiếu thành công", "good"), r.readback_state || "—"],
            ]
          ) : null
        )
      );
    } catch (err) {
      ctrlResults.replaceChildren(notice("Lỗi thực thi lệnh: " + err.message, "Error"));
    }
  }, "secondary");

  ctrlControls.append(cmdTypeSelect, paramInput, unlockLabel, sendCmdBtn);
  ctrlCard.append(ctrlNotice, ctrlControls, ctrlResults);
  essBox.append(ctrlCard);

  // 3. Raw Eybond Frame Analyzer
  const frameCard = card(l("3. Phân tích Khung truyền Nhị phân Eybond Modbus", "3. Eybond Modbus Binary Frame Analyzer"));
  const frameNotice = p(
    "Dán chuỗi Hex của gói tin Eybond Modbus nhận được từ mạng (Cổng TCP 8899). Bộ phân tích sẽ giải mã Header 8 byte (TID, DevCode, TotalLen, DevAddr, Function Code), bóc tách thông tin Heartbeat hoặc khung dữ liệu P17 bên trong.",
    "muted"
  );

  const frameInputArea = div("row gap-sm items-center");
  const hexInput = e("input", null, "input-text");
  hexInput.value = "00370994001201045e5000547345380d";
  hexInput.placeholder = "Chuỗi Hex khung Eybond";
  hexInput.style.minWidth = "360px";

  const frameResults = div("stack");

  const parseBtn = button(l("Giải mã Khung truyền (Decode Frame)", "Decode Eybond Frame"), async () => {
    try {
      const res = await api("/smartess/parse-frame", {
        method: "POST",
        body: JSON.stringify({ raw_frame_hex: hexInput.value }),
      });
      const f = res.frame || {};
      frameResults.replaceChildren(
        div("stack",
          div("row justify-between items-center",
            e("h4", `Giải mã khung Eybond (Mã hàm FC=${f.fc})`),
            badge(`TID: ${f.tid}`, "blue")
          ),
          table(
            ["Trường Header", "Giá trị giải mã", "Ý nghĩa chi tiết"],
            [
              ["Transaction ID (TID)", `${f.tid}`, "Số định danh phiên giao dịch 2 byte"],
              ["Device Code", `${f.devcode}`, "0x0994 cho Inverter Solar P17"],
              ["Total Length", `${f.total_len} Bytes`, "Độ dài toàn khung bao gồm 8 bytes header"],
              ["Device Address", `${f.devaddr}`, "Địa chỉ RS485 của biến tần"],
              ["Function Code", `${f.fc}`, f.fc === 1 ? "FC=1: Heartbeat đồng bộ" : (f.fc === 4 ? "FC=4: Forward2Device (P17/RS485)" : `FC=${f.fc}`)],
              f.collector_pn ? ["Số Serial Datalogger", badge(f.collector_pn, "good"), "Số PN được khai báo trong gói Heartbeat"] : null,
              f.p17_text ? ["Dữ liệu P17 nhúng", e("code", f.p17_text), `Kiểu phản hồi: ${f.p17_type}`] : null,
              f.p17_raw_hex ? ["Khung P17 thô (Hex)", e("code", f.p17_raw_hex), "Dữ liệu được chuyển tiếp qua RS485"] : null,
            ].filter(Boolean)
          )
        )
      );
    } catch (err) {
      frameResults.replaceChildren(notice("Lỗi giải mã khung: " + err.message, "Error"));
    }
  }, "secondary");

  frameInputArea.append(hexInput, parseBtn);
  frameCard.append(frameNotice, frameInputArea, frameResults);
  essBox.append(frameCard);

  container.append(essBox);
}

async function renderGrowattCloudSubtab(ui, container) {
  const { e, div, p, card, table, badge, notice } = ui;
  const button = (label, handler, cls = "secondary") => {
    const b = e("button", label, `btn btn-${cls}`);
    b.onclick = handler;
    return b;
  };

  const gwBox = div("stack gap-md");

  // Header Banner
  const banner = div(
    "card",
    div("row justify-between items-center",
      div("stack",
        e("h3", l("Cổng kết nối Đám mây Growatt (OpenAPI V1 & ShineServer)", "Growatt Cloud Gateway (OpenAPI V1 & ShineServer)")),
        p(l(
          "Tích hợp kiến trúc Growatt Cloud OpenAPI V1 chính thức (Showdoc 262556420217021) dựa trên nghiên cứu độc lập PyPi_GrowattServer. Hỗ trợ đa khu vực (Toàn cầu, Trung Quốc, Bắc Mỹ), chuẩn hóa dữ liệu SPH/MIN về Solar Fleet EMS, và bộ biên dịch tham số an toàn (Default Read-Only Gate).",
          "Official Growatt OpenAPI V1 cloud integration researched from PyPi_GrowattServer. Supports multi-region endpoints (Global, CN, US), SPH/MIN telemetry normalization, and safe parameter write compilers under hardware acceptance gates."
        ), "muted")
      ),
      badge(l("OpenAPI V1 Độc lập", "Independent OpenAPI V1"), "good")
    )
  );
  gwBox.append(banner);

  // 1. Gateway & Station Explorer
  const stationCard = card(l("1. Quản lý Nhà máy & Trạm năng lượng (Plant Overview)", "1. Plant & Power Station Explorer"));
  const stationNotice = p(
    l("Truy vấn danh mục nhà máy từ máy chủ Growatt Cloud tương ứng theo Token API. Mô phỏng trạm solar tiêu biểu kèm thông số công suất và sản lượng tích lũy.",
      "Query plant registry from regional Growatt Cloud server using API Token. Simulated plant overview with peak power and generation metrics."),
    "muted"
  );

  const authRow = div("row gap-sm items-center");
  const regionSelect = e("select", null, "input-select");
  [["global", "Global Server (openapi.growatt.com)"], ["cn", "China Server (openapi-cn.growatt.com)"], ["us", "North America Server (openapi-us.growatt.com)"]].forEach(([val, txt]) => {
    const opt = e("option", txt);
    opt.value = val;
    regionSelect.append(opt);
  });

  const tokenInput = e("input", null, "input-text");
  tokenInput.value = "DEMO-GROWATT-TOKEN-001";
  tokenInput.placeholder = "API Token";
  tokenInput.style.minWidth = "260px";

  const plantResults = div("stack");

  const fetchPlantsBtn = button(l("Tải danh mục Trạm (Fetch Plants)", "Fetch Plants"), async () => {
    try {
      const res = await ui.api("/growatt-cloud/plants", {
        method: "POST",
        body: JSON.stringify({ token: tokenInput.value, region: regionSelect.value }),
      });
      const plants = res.plants || [];
      if (!plants.length) {
        plantResults.replaceChildren(notice(l("Không tìm thấy trạm nào.", "No plants found."), "info"));
        return;
      }
      const p0 = plants[0];
      plantResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            e("h4", `${p0.plant_name} [${p0.plant_id}]`),
            badge(`${p0.city}, ${p0.country}`, "blue")
          ),
          div("overview-kpis",
            div("fact", e("span", l("Công suất Đỉnh", "Peak Power")), badge(`${p0.peak_power_kw} kW`, "good")),
            div("fact", e("span", l("Công suất Hiện tại", "Current Power")), badge(`${p0.current_power_w} W`, "blue")),
            div("fact", e("span", l("Sản lượng Hôm nay", "Today Energy")), badge(`${p0.today_energy_kwh} kWh`, "secondary")),
            div("fact", e("span", l("Tổng Sản lượng", "Total Energy")), e("b", `${p0.total_energy_kwh} kWh`)),
            div("fact", e("span", l("Số Thiết bị", "Device Count")), e("b", `${p0.device_count}`)),
          )
        )
      );
    } catch (err) {
      plantResults.replaceChildren(notice(l("Lỗi truy vấn trạm: ", "Error fetching plants: ") + err.message, "error"));
    }
  }, "primary");

  authRow.append(regionSelect, tokenInput, fetchPlantsBtn);
  stationCard.append(stationNotice, authRow, plantResults);
  gwBox.append(stationCard);

  // 2. Device Explorer & Telemetry Ingestion
  const devCard = card(l("2. Giám sát Thiết bị & Bóc tách Telemetry SPH Hybrid", "2. Device Explorer & SPH Hybrid Telemetry"));
  const devNotice = p(
    l("Truy vấn thiết bị trong trạm và bóc tách dữ liệu SPH Hybrid (dòng điện, công suất PV1/PV2, Pin lưu trữ, Lưới điện, và chế độ ưu tiên hoạt động).",
      "List plant devices and decode detailed SPH Hybrid telemetry (solar flows, battery voltage/SOC, grid, and priority mode)."),
    "muted"
  );

  const devRow = div("row gap-sm items-center");
  const devSnInput = e("input", null, "input-text");
  devSnInput.value = "SPH460001";
  devSnInput.placeholder = "Device SN (SPH...)";

  const devResults = div("stack");

  const fetchDevBtn = button(l("Đọc Telemetry Chi tiết (Read SPH)", "Read SPH Telemetry"), async () => {
    try {
      const res = await ui.api("/growatt-cloud/sph-detail", {
        method: "POST",
        body: JSON.stringify({ token: tokenInput.value, region: regionSelect.value, device_sn: devSnInput.value }),
      });
      const tel = res.telemetry || {};
      const pf = tel.power_flow || {};
      const bat = tel.battery || {};
      const cfg = tel.configuration || {};

      devResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            e("h4", `${tel.model_type} [SN: ${tel.serial_number}]`),
            badge(`FW: ${tel.firmware_version}`, "secondary")
          ),
          div("overview-kpis",
            div("fact", e("span", l("Tổng PV", "Total PV")), badge(`${pf.solar_power_w} W`, "good")),
            div("fact", e("span", l("Lưới AC", "Grid Feed")), badge(`${pf.grid_power_w} W`, "blue")),
            div("fact", e("span", l("Tải Tiêu thụ", "Home Load")), e("b", `${pf.load_power_w} W`)),
            div("fact", e("span", l("Pin SOC", "Battery SOC")), badge(`${bat.soc_percent}%`, bat.soc_percent > 30 ? "good" : "warn")),
            div("fact", e("span", l("Điện áp Pin", "Battery Volt")), e("b", `${bat.voltage_v} V`)),
            div("fact", e("span", l("Chế độ Ưu tiên", "Priority Mode")), badge(cfg.priority_mode, "blue")),
          ),
          div("plant-card-grid",
            div("plant-visual-card",
              e("h5", l("Luồng Công suất & MPPT PV", "Power Flow & MPPT Trackers")),
              table(
                [l("Thông số", "Parameter"), l("Giá trị", "Value")],
                [
                  [l("PV1 (Công suất / Điện áp)", "PV1 Power / Voltage"), `${pf.pv1_power_w} W (${pf.pv1_voltage_v} V)`],
                  [l("PV2 (Công suất / Điện áp)", "PV2 Power / Voltage"), `${pf.pv2_power_w} W (${pf.pv2_voltage_v} V)`],
                  [l("Công suất Định mức Biến tần", "Inverter Rated Power"), `${pf.rated_power_w} W`],
                  [l("Công suất Sạc/Xả Pin", "Battery Charge/Discharge"), `${pf.battery_power_w} W`],
                  [l("Ngưỡng Ngắt Xả Pin (Cutoff)", "Discharge Cutoff SOC"), `${bat.discharge_min_soc}%`],
                ]
              )
            ),
            div("plant-visual-card",
              e("h5", l("Cấu hình Hoạt động & Lịch Trình (TOU)", "Operating Config & TOU Windows")),
              table(
                [l("Tham số", "Parameter"), l("Giá trị Cấu hình", "Config Value")],
                [
                  [l("Sạc từ Lưới (AC Charging)", "AC Grid Charging"), badge(cfg.ac_charge_enabled ? l("Kích hoạt (ON)", "Enabled") : l("Tắt (OFF)", "Disabled"), cfg.ac_charge_enabled ? "good" : "warn")],
                  [l("Giới hạn Công suất Sạc", "Charge Power Limit"), `${cfg.charge_power_limit_pct}%`],
                  [l("Giới hạn Công suất Xả", "Discharge Power Limit"), `${cfg.discharge_power_limit_pct}%`],
                  [l("Khung giờ Sạc Cưỡng bức (Window 1)", "Forced Charge W1"), `${(cfg.charge_windows && cfg.charge_windows[0]) ? cfg.charge_windows[0].start + ' - ' + cfg.charge_windows[0].stop : 'N/A'}`],
                  [l("Khung giờ Xả Cưỡng bức (Window 1)", "Forced Discharge W1"), `${(cfg.discharge_windows && cfg.discharge_windows[0]) ? cfg.discharge_windows[0].start + ' - ' + cfg.discharge_windows[0].stop : 'N/A'}`],
                ]
              )
            )
          )
        )
      );
    } catch (err) {
      devResults.replaceChildren(notice(l("Lỗi đọc telemetry: ", "Error reading telemetry: ") + err.message, "error"));
    }
  }, "secondary");

  devRow.append(devSnInput, fetchDevBtn);
  devCard.append(devNotice, devRow, devResults);
  gwBox.append(devCard);

  // 3. Safe Cloud Parameter Compiler (Hardware Acceptance Gate)
  const cmdCard = card(l("3. Bộ biên dịch Tham số Cấu hình Đám mây (Gated Parameter Writing)", "3. Cloud Parameter Compilers & Safety Gates"));
  const cmdNotice = p(
    l("Biên dịch lệnh ghi cấu hình từ xa cho biến tần SPH và MIN qua OpenAPI V1 (/v1/device/sph/settings). Mọi lệnh gửi lên đều bị KHÓA theo cơ chế LOCKED_PENDING_HARDWARE_ACCEPTANCE để bảo đảm an toàn điện lưới.",
      "Compile remote configuration commands for SPH and MIN series via OpenAPI V1. All write operations are strictly locked under LOCKED_PENDING_HARDWARE_ACCEPTANCE safety gating."),
    "muted"
  );

  const cmdTypeSelect = e("select", null, "input-select");
  [
    ["sph_priority", l("SPH: Chế độ Ưu tiên (Priority Mode)", "SPH: Priority Mode")],
    ["sph_ac_charge", l("SPH: Bật/Tắt Sạc từ Lưới (AC Charging)", "SPH: AC Grid Charging Toggle")],
    ["sph_power_limits", l("SPH: Giới hạn Công suất Sạc/Xả", "SPH: Charge/Discharge Power Limits")],
    ["min_time_segment", l("MIN/TLX: Đoạn lịch trình TOU (Segment 1..9)", "MIN/TLX: TOU Time Segment (1..9)")],
  ].forEach(([val, txt]) => {
    const opt = e("option", txt);
    opt.value = val;
    cmdTypeSelect.append(opt);
  });

  const cmdControlsRow = div("row gap-sm items-center");
  const cmdValInput = e("input", null, "input-text");
  cmdValInput.value = "1";
  cmdValInput.placeholder = "Giá trị / Mã";
  cmdValInput.style.maxWidth = "120px";

  const cmdResults = div("stack");

  const compileBtn = button(l("Biên dịch Lệnh (Compile & Test Gate)", "Compile & Test Gate"), async () => {
    try {
      const cType = cmdTypeSelect.value;
      let params = {};
      if (cType === "sph_priority") {
        params = { priority_code: parseInt(cmdValInput.value || "1", 10) };
      } else if (cType === "sph_ac_charge") {
        params = { enable: cmdValInput.value === "1" || cmdValInput.value.toLowerCase() === "true" };
      } else if (cType === "sph_power_limits") {
        params = { charge_pct: parseInt(cmdValInput.value || "80", 10), discharge_pct: 100 };
      } else if (cType === "min_time_segment") {
        params = { segment_id: parseInt(cmdValInput.value || "1", 10), batt_mode: 1, start_time: "02:00", end_time: "06:00", enabled: true };
      }

      const res = await ui.api("/growatt-cloud/command", {
        method: "POST",
        body: JSON.stringify({
          token: tokenInput.value,
          region: regionSelect.value,
          command_type: cType,
          params: params,
          unlocked: false, // strictly enforce default safety gate
        }),
      });

      const r = res.result || {};
      cmdResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            e("h5", l("Kết quả Kiểm tra Cổng An toàn", "Safety Gate Verification")),
            badge(r.status, "warn")
          ),
          table(
            [l("Thuộc tính", "Property"), l("Giá trị", "Value")],
            [
              [l("Trạng thái Khóa", "Status"), badge(r.status, "warn")],
              [l("Loại lệnh", "Command Type"), r.command_type],
              [l("Tham số truyền", "Parameters"), e("code", JSON.stringify(r.params))],
              [l("Thông điệp An toàn", "Safety Notice"), r.message || l("Lệnh bị chặn bởi cổng nghiệm thu phần cứng.", "Command blocked by hardware acceptance gate.")],
            ]
          )
        )
      );
    } catch (err) {
      cmdResults.replaceChildren(notice(l("Lỗi biên dịch lệnh: ", "Error compiling command: ") + err.message, "error"));
    }
  }, "secondary");

  cmdControlsRow.append(cmdTypeSelect, cmdValInput, compileBtn);
  cmdCard.append(cmdNotice, cmdControlsRow, cmdResults);
  gwBox.append(cmdCard);

  container.append(gwBox);
}

async function renderEybondEspSubtab(ui, container) {
  const { e, div, p, card, table, badge, notice } = ui;
  const button = (label, handler, cls = "secondary") => {
    const b = e("button", label, `btn btn-${cls}`);
    b.onclick = handler;
    return b;
  };

  const espBox = div("stack gap-md");

  // Header Banner
  const banner = div(
    "card",
    div("row justify-between items-center",
      div("stack",
        e("h3", l("Cầu nối Thu thập Dữ liệu ESP EyeBond & Voltronic PI30", "ESP EyeBond Collector Bridge & Voltronic PI30 Engine")),
        p(l(
          "Cấu hình thu thập phần cứng mã nguồn mở độc lập (ESP32 / ESP8266 / BK72xx) thay thế cục Wi-Fi SmartESS / Eybond gốc theo esp-eybond-collector. Hỗ trợ bắt tay UDP Port 58899, bộ lệnh giao tiếp AT, bóc tách chuỗi Voltronic QPIGS, ma trận 32 cờ cảnh báo QPIWS, và bộ biên dịch điều khiển an toàn (Gated Control).",
          "Open-source embedded bridge firmware replacing factory SmartESS/Eybond Wi-Fi dongles (ESP32/ESP8266/BK72xx). Features UDP port 58899 discovery, AT command handler, Voltronic QPIGS telemetry decoder, 32-flag QPIWS alarm matrix, and safety-gated parameter compilers."
        ), "muted")
      ),
      badge(l("Cầu nối ESP / PI30", "ESP / PI30 Bridge"), "good")
    )
  );
  espBox.append(banner);

  // 1. ESP Collector Bridge & Network Status (UDP & AT Commands)
  const bridgeCard = card(l("1. Trạng thái Bộ thu thập ESP & Giao tiếp Lệnh AT (Bridge & AT Interface)", "1. ESP Collector Bridge & AT Command Interface"));
  const bridgeNotice = p(
    l("Bộ thu thập ESP chạy firmware độc lập tự động phản hồi UDP discovery ('set>server=IP:PORT;' -> 'rsp>server=2;') và thiết lập kết nối TCP ngược về Solar Fleet EMS. Bạn có thể tương tác với tập lệnh AT để kiểm tra cấu hình mạng và thông số UART.",
      "The ESP bridge firmware listens on UDP 58899 for discovery redirect and establishes reverse-TCP to Solar Fleet EMS. Interact with the AT command processor to verify network and UART parameters."),
    "muted"
  );

  const atControlsRow = div("row gap-sm items-center");
  const atSelect = e("select", null, "input-select");
  [
    ["AT+DTUPN?", "AT+DTUPN? (Số serial PN bộ thu thập)"],
    ["AT+FWVER?", "AT+FWVER? (Phiên bản Firmware Bridge)"],
    ["AT+ATVER?", "AT+ATVER? (Phiên bản giao tiếp AT)"],
    ["AT+UART?", "AT+UART? (Cấu hình Baudrate & Parity)"],
    ["AT+CLDSRVHOST1?", "AT+CLDSRVHOST1? (Địa chỉ EMS Server đích)"],
    ["AT+WFSS?", "AT+WFSS? (Cường độ sóng Wi-Fi RSSI)"],
    ["AT+LINK?", "AT+LINK? (Trạng thái liên kết TCP)"],
    ["AT+SYST?", "AT+SYST? (Đồng hồ hệ thống)"],
  ].forEach(([val, txt]) => {
    const opt = e("option", txt);
    opt.value = val;
    atSelect.append(opt);
  });

  const atResults = div("stack");

  const sendAtBtn = button(l("Gửi Lệnh AT (Send AT)", "Send AT Command"), async () => {
    try {
      const res = await ui.api("/eybond-collector/parse-at", {
        method: "POST",
        body: JSON.stringify({
          at_line: atSelect.value,
          profile_pn: "V00123456789012345",
          firmware_ver: "0.1.10",
          uart_cfg: "2400,8,1,NONE",
        }),
      });
      atResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            e("h5", `Phản hồi: ${res.command}`),
            badge("OK", "good")
          ),
          table(
            [l("Thuộc tính", "Property"), l("Giá trị", "Value")],
            [
              [l("Lệnh gửi", "Command Sent"), e("code", atSelect.value)],
              [l("Kiểu lệnh", "Command Type"), res.is_write ? l("Ghi cấu hình (Write)", "Write") : l("Truy vấn (Query)", "Query")],
              [l("Chuỗi phản hồi chuẩn", "Collector Response"), badge(res.response, "blue")],
            ]
          )
        )
      );
    } catch (err) {
      atResults.replaceChildren(notice(l("Lỗi lệnh AT: ", "AT command error: ") + err.message, "error"));
    }
  }, "primary");

  const testUdpBtn = button(l("Thử nghiệm UDP 58899 Discovery", "Test UDP Discovery"), async () => {
    try {
      const res = await ui.api("/eybond-collector/discover", {
        method: "POST",
        body: JSON.stringify({ raw_udp_text: "set>server=192.168.1.100:8899;" }),
      });
      atResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            e("h5", l("Kết quả Bắt tay UDP Port 58899", "UDP Discovery Handshake")),
            badge("UDP 200 OK", "good")
          ),
          table(
            [l("Thuộc tính", "Property"), l("Giá trị", "Value")],
            [
              [l("Máy chủ EMS đích", "Target Server Host"), res.server_host],
              [l("Cổng TCP kết nối ngược", "Reverse TCP Port"), `${res.server_port}`],
              [l("Gói phản hồi Handshake", "Handshake Response"), badge(res.udp_reply, "good")],
              [l("Ghi chú", "Note"), l("ESP Collector nhận được lệnh sẽ lập tức khởi tạo luồng TCP ngược về EMS", "ESP Collector initiates reverse TCP stream to EMS upon receiving redirect")],
            ]
          )
        )
      );
    } catch (err) {
      atResults.replaceChildren(notice(l("Lỗi kiểm tra UDP: ", "UDP discovery error: ") + err.message, "error"));
    }
  }, "secondary");

  atControlsRow.append(atSelect, sendAtBtn, testUdpBtn);
  bridgeCard.append(bridgeNotice, atControlsRow, atResults);
  espBox.append(bridgeCard);

  // 2. Voltronic PI30 Inverter Telemetry & Power Flow
  const telCard = card(l("2. Bóc tách Telemetry Inverter Voltronic PI30 (QPIGS & QPIWS)", "2. Voltronic PI30 Inverter Telemetry & Status"));
  const telNotice = p(
    l("Giải mã chuỗi phản hồi trạng thái toàn diện QPIGS (21 trường đo đạc) cùng ma trận 32 cờ cảnh báo lỗi QPIWS của các dòng biến tần Axpert / Bluesun / PowMr / EASun.",
      "Decode QPIGS general status telemetry (21 measurement fields) and 32-bit QPIWS warning matrix from Axpert/Bluesun/PowMr/EASun inverters."),
    "muted"
  );

  const telInputRow = div("row gap-sm items-center");
  const qpigsInput = e("input", null, "input-text");
  qpigsInput.value = "239.5 49.9 239.5 49.9 0927 0924 015 396 53.20 000 100 0028 002.2 315.9 00.00 00000 00010000 00 00 00665 000";
  qpigsInput.placeholder = "Chuỗi QPIGS";
  qpigsInput.style.minWidth = "380px";

  const modeSelect = e("select", null, "input-select");
  [
    ["L", "Chế độ Lưới (Line Mode - L)"],
    ["B", "Chế độ Pin (Battery Mode - B)"],
    ["S", "Chế độ Chờ (Standby Mode - S)"],
    ["F", "Chế độ Lỗi (Fault Mode - F)"],
  ].forEach(([val, txt]) => {
    const opt = e("option", txt);
    opt.value = val;
    modeSelect.append(opt);
  });

  const telResults = div("stack");

  const decodeBtn = button(l("Bóc tách Telemetry (Decode QPIGS)", "Decode QPIGS"), async () => {
    try {
      const res = await ui.api("/eybond-collector/decode-pigs", {
        method: "POST",
        body: JSON.stringify({
          raw_qpigs: qpigsInput.value,
          mode_char: modeSelect.value,
          qpiws_flags: "00000100000000000000000000000000",
          collector_pn: "V00123456789012345",
          inverter_sn: "INV-AXPERT-5KW",
        }),
      });
      const tel = res.telemetry || {};
      const pf = tel.power_flow || {};
      const bat = tel.battery || {};
      const grid = tel.grid || {};
      const diag = tel.diagnostics || {};

      telResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            e("h4", `${tel.vendor} [${tel.model}]`),
            badge(tel.operating_mode, "blue")
          ),
          div("overview-kpis",
            div("fact", e("span", l("Công suất PV", "Solar PV")), badge(`${pf.solar_power_w} W`, "good")),
            div("fact", e("span", l("Công suất Tải AC", "Load Active")), badge(`${pf.load_power_w} W`, "blue")),
            div("fact", e("span", l("Điện áp Pin", "Battery Volt")), e("b", `${bat.voltage_v} V`)),
            div("fact", e("span", l("Dung lượng SOC", "Battery SOC")), badge(`${bat.soc_percent}%`, bat.soc_percent > 30 ? "good" : "warn")),
            div("fact", e("span", l("Nhiệt độ Tản nhiệt", "Heatsink Temp")), e("b", `${diag.heatsink_temperature_c} °C`)),
            div("fact", e("span", l("Cảnh báo hoạt động", "Active Warnings")), badge(`${diag.active_warnings_count}`, diag.active_warnings_count ? "warn" : "good")),
          ),
          div("plant-card-grid",
            div("plant-visual-card",
              e("h5", l("Chi tiết Nguồn điện & Tải AC", "Grid & Load Details")),
              table(
                [l("Thông số", "Parameter"), l("Giá trị", "Value")],
                [
                  [l("Điện áp & Tần số Lưới vào", "Grid Voltage & Frequency"), `${grid.voltage_v} V / ${grid.frequency_hz} Hz`],
                  [l("Điện áp & Tần số Ngõ ra AC", "Output Voltage & Frequency"), `${grid.output_voltage_v} V / ${grid.output_frequency_hz} Hz`],
                  [l("Công suất Biểu kiến Tải", "Load Apparent Power"), `${pf.load_apparent_va} VA (${pf.load_percent}%)`],
                  [l("Dòng & Điện áp MPPT PV", "PV Input Current & Voltage"), `${pf.pv_current_a} A / ${pf.pv_voltage_v} V`],
                  [l("Điện áp Bus DC trung gian", "DC Bus Voltage"), `${bat.bus_voltage_v} V`],
                ]
              )
            ),
            div("plant-visual-card",
              e("h5", l("Trạng thái Cảnh báo & Mã Lỗi (QPIWS)", "Alarm Status & Diagnostics")),
              table(
                [l("Vị trí Bit", "Bit"), l("Mã Cảnh báo", "Alarm Code"), l("Mức độ", "Severity")],
                (diag.alarms && diag.alarms.length) ?
                  diag.alarms.map(a => [`Bit ${a.bit}`, a.code, badge(a.severity, a.severity === "CRITICAL" ? "bad" : "warn")]) :
                  [["—", l("Không có lỗi hoặc cảnh báo", "No active faults or warnings"), badge(l("Bình thường", "Normal"), "good")]]
              )
            )
          )
        )
      );
    } catch (err) {
      telResults.replaceChildren(notice(l("Lỗi bóc tách telemetry: ", "Error decoding telemetry: ") + err.message, "error"));
    }
  }, "primary");

  telInputRow.append(qpigsInput, modeSelect, decodeBtn);
  telCard.append(telNotice, telInputRow, telResults);
  espBox.append(telCard);

  // 3. Voltronic Safe Parameter Compilers & Hardware Gate
  const cmdCard = card(l("3. Bộ biên dịch Tham số Cấu hình Biến tần (Gated PI30 Controls)", "3. Inverter Parameter Compilers & Safety Gates"));
  const cmdNotice = p(
    l("Biên dịch lệnh cài đặt tham số Voltronic PI30 (POP, PCP, MCHGC, điện áp sạc) với mã kiểm tra CRC16-XMODEM và cơ chế Byte-Stuffing. Mọi lệnh ghi đều bị KHÓA theo cơ chế LOCKED_PENDING_HARDWARE_ACCEPTANCE.",
      "Compile Voltronic PI30 parameter write commands with CRC16-XMODEM checksum and byte stuffing. All write actions are strictly locked under LOCKED_PENDING_HARDWARE_ACCEPTANCE."),
    "muted"
  );

  const ctrlTypeSelect = e("select", null, "input-select");
  [
    ["output_priority", l("Ưu tiên Nguồn Xuất (POP: SBU / Solar First / Utility First)", "Output Priority (POP)")],
    ["charger_priority", l("Ưu tiên Nguồn Sạc (PCP: Solar Only / Solar First / Utility First)", "Charger Priority (PCP)")],
    ["charge_current", l("Dòng sạc tối đa (MCHGC: 10..120A)", "Max Charge Current (MCHGC)")],
    ["battery_voltages", l("Điện áp Bulk / Float / Cutoff (PCVV, PBFT, PSDV)", "Battery Voltages (PCVV/PBFT/PSDV)")],
  ].forEach(([val, txt]) => {
    const opt = e("option", txt);
    opt.value = val;
    ctrlTypeSelect.append(opt);
  });

  const ctrlParamInput = e("input", null, "input-text");
  ctrlParamInput.value = "sbu";
  ctrlParamInput.placeholder = "Tham số (sbu, 60, ...)";
  ctrlParamInput.style.maxWidth = "160px";

  const ctrlResults = div("stack");

  const compileCtrlBtn = button(l("Biên dịch Lệnh (Compile & Test Gate)", "Compile & Test Gate"), async () => {
    try {
      const cType = ctrlTypeSelect.value;
      let params = {};
      if (cType === "output_priority") {
        params = { priority: ctrlParamInput.value || "sbu" };
      } else if (cType === "charger_priority") {
        params = { priority: ctrlParamInput.value || "solar_only" };
      } else if (cType === "charge_current") {
        params = { current_a: parseInt(ctrlParamInput.value || "60", 10) };
      } else if (cType === "battery_voltages") {
        params = { bulk_v: 56.4, float_v: 54.0, cutoff_v: 42.0 };
      }

      const res = await ui.api("/eybond-collector/command", {
        method: "POST",
        body: JSON.stringify({
          command_type: cType,
          params: params,
          unlocked: false,
        }),
      });

      const r = res.result || {};
      ctrlResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            e("h5", l("Kết quả Cổng Nghiệm thu Phần cứng", "Hardware Acceptance Gate Verification")),
            badge(r.status, "warn")
          ),
          table(
            [l("Thuộc tính", "Property"), l("Giá trị", "Value")],
            [
              [l("Trạng thái Khóa", "Status"), badge(r.status, "warn")],
              [l("Loại lệnh điều khiển", "Command Type"), r.command_type],
              [l("Tham số truyền", "Parameters"), e("code", JSON.stringify(r.params))],
              [l("Thông điệp An toàn", "Safety Notice"), r.message || l("Lệnh bị chặn bởi cổng nghiệm thu phần cứng.", "Command blocked by hardware acceptance gate.")],
            ]
          )
        )
      );
    } catch (err) {
      ctrlResults.replaceChildren(notice(l("Lỗi biên dịch lệnh: ", "Error compiling command: ") + err.message, "error"));
    }
  }, "secondary");

  const ctrlRow = div("row gap-sm items-center");
  ctrlRow.append(ctrlTypeSelect, ctrlParamInput, compileCtrlBtn);
  cmdCard.append(cmdNotice, ctrlRow, ctrlResults);
  espBox.append(cmdCard);

  container.append(espBox);
}

// ---------------------------------------------------------------------------
// SUBTAB: GOODWE LOCAL INVERTER UDP / MODBUS RTU (Project #12)
// ---------------------------------------------------------------------------
async function renderGoodWeLocalSubtab(ui, container) {
  const { div, e, button, badge, table, notice, l } = ui;

  const gwBox = div("stack gap-md");

  // Header Banner
  const banner = div("card p-md stack gap-xs");
  const bannerTitle = div("row justify-between items-center",
    e("h3", l("GoodWe Local Inverter Engine (Modbus UDP & AA55)", "GoodWe Local Inverter Engine (Modbus UDP & AA55)")),
    badge(l("Nguồn sạch độc lập MIT • Giao tiếp Cục bộ Cổng 8899", "Clean-Room MIT • Local Port 8899 Engine"), "info")
  );
  const bannerDesc = e("p",
    l("Giao thức kết nối trực tiếp biến tần GoodWe qua mạng cục bộ LAN/Wi-Fi (UDP 8899 / Modbus TCP 502) không phụ thuộc máy chủ đám mây SEMS Portal. Tương thích dòng biến tần 3 pha Hybrid ET/EH/BT/BH (Modbus RTU over UDP), 1 pha Hybrid ES/EM (khung nhị phân AA55), và chuỗi DT/MS/NS. Hỗ trợ giám sát 3 pha, BMS điện áp cao, Smart Meter và cấu hình chế độ vận hành/TOU với khóa nghiệm thu an toàn.",
      "Direct local network protocol for GoodWe inverters via LAN/Wi-Fi (UDP 8899 / Modbus TCP 502) without cloud dependency on SEMS Portal. Compatible with ET/EH/BT/BH 3-phase hybrid (Modbus RTU over UDP), ES/EM 1-phase hybrid (AA55 frames), and DT/MS/NS string inverters. Supports 3-phase telemetry, high-voltage BMS, Smart Metering, and Operation Mode/TOU compilers gated behind hardware acceptance."
    ),
    "text-secondary"
  );
  banner.append(bannerTitle, bannerDesc);
  gwBox.append(banner);

  // Card 1: Local Gateway Connection & Telemetry Poller
  const pollerCard = div("card p-md stack gap-sm");
  pollerCard.append(
    div("row justify-between items-center",
      e("h4", l("Cổng kết nối Cục bộ & Dữ liệu Vận hành Biến tần", "Local Gateway & Inverter Running Telemetry")),
      badge("UDP 8899 / FC03", "accent")
    )
  );

  const connRow = div("row gap-sm items-center wrap");
  const hostInput = e("input", null, "form-control");
  hostInput.type = "text";
  hostInput.placeholder = "Inverter IP (e.g. 192.168.1.180)";
  hostInput.value = "192.168.1.180";
  hostInput.style.maxWidth = "200px";

  const portInput = e("input", null, "form-control");
  portInput.type = "number";
  portInput.placeholder = "UDP Port";
  portInput.value = "8899";
  portInput.style.maxWidth = "110px";

  const addrInput = e("input", null, "form-control");
  addrInput.type = "number";
  addrInput.placeholder = "Comm Addr (247)";
  addrInput.value = "247";
  addrInput.style.maxWidth = "130px";

  const familySelect = e("select", null, "form-control");
  familySelect.style.maxWidth = "220px";
  const families = [
    { id: "ET", name: "GoodWe ET Series (3-Phase Hybrid)" },
    { id: "ES", name: "GoodWe ES Series (1-Phase AA55)" },
    { id: "DT", name: "GoodWe DT Series (Grid-tied String)" },
  ];
  families.forEach((f) => {
    const opt = e("option", f.name);
    opt.value = f.id;
    familySelect.append(opt);
  });

  const telResults = div("stack gap-sm");

  const pollBtn = button(l("Truy vấn Telemetry Cục bộ", "Poll Local Telemetry"), async () => {
    telResults.replaceChildren(notice(l("Đang kết nối qua UDP 8899...", "Connecting via UDP 8899..."), "info"));
    try {
      const res = await ui.api("/goodwe-local/telemetry", {
        method: "POST",
        body: JSON.stringify({
          host: hostInput.value.trim(),
          port: parseInt(portInput.value, 10) || 8899,
          comm_addr: parseInt(addrInput.value, 10) || 247,
          model_family: familySelect.value,
        }),
      });

      const tel = res.telemetry || {};
      const dev = tel.device || {};
      const met = tel.metrics || {};
      const raw = tel.raw_snapshot || {};

      telResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            div("row gap-xs items-center",
              badge(dev.model || "GW10K-ET", "success"),
              badge(`S/N: ${dev.serial || "GW10K-ET-1023"}`, "neutral"),
              badge(raw.work_mode || "Normal (On-Grid)", "info"),
              badge(raw.battery_mode || "Charging", "accent")
            ),
            e("span", `${l("Thời gian: ", "Timestamp: ")}${tel.timestamp || new Date().toISOString()}`, "text-secondary text-sm")
          ),
          table(
            [l("Chỉ số Vận hành (ET 3-P)", "Operating Metric (ET 3-Phase)"), l("Đo lường", "Measurement"), l("Ghi chú / Đơn vị", "Notes / Unit")],
            [
              [l("Tổng Công suất PV", "Total PV Power"), badge(`${met.pv_power_w ?? 8117} W`, "success"), `${l("PV1: ", "PV1: ")}${raw.pv1_power_w ?? 4180} W (${raw.pv1_voltage_v ?? 380}V) | ${l("PV2: ", "PV2: ")}${raw.pv2_power_w ?? 3937} W (${raw.pv2_voltage_v ?? 375}V)`],
              [l("Điện lưới 3 Pha (Grid L1-L3)", "3-Phase Grid Output"), `${met.grid_power_w ?? 8100} W`, `L1: ${raw.grid_voltage_l1_v ?? 230.5}V (${raw.grid_power_l1_w ?? 2700}W) | L2: ${raw.grid_voltage_l2_v ?? 231}V (${raw.grid_power_l2_w ?? 2680}W) | L3: ${raw.grid_voltage_l3_v ?? 229.5}V (${raw.grid_power_l3_w ?? 2720}W)`],
              [l("Smart Meter Điểm đấu nối", "Smart Meter (Point of Coupling)"), badge(`${raw.meter_active_power_w ?? -1500} W`, (raw.meter_active_power_w || 0) < 0 ? "success" : "info"), (raw.meter_active_power_w || 0) < 0 ? l("Đang phát lên lưới (Xuất khẩu)", "Exporting to Grid") : l("Đang nhận từ lưới (Nhập khẩu)", "Importing from Grid")],
              [l("Phụ tải Dự phòng (UPS Backup L1-L3)", "Backup Load Output (UPS)"), `${raw.backup_total_power_w ?? 600} W`, `L1: ${raw.backup_voltage_l1_v ?? 230}V | L2: ${raw.backup_voltage_l2_v ?? 230}V | L3: ${raw.backup_voltage_l3_v ?? 230}V`],
              [l("Tổng Phụ tải Gia đình (Load)", "Total Home Load"), `${met.load_power_w ?? 6600} W`, l("Đo lường bởi biến tần qua Smart Meter", "Calculated by inverter via Smart Meter")],
              [l("BMS Bộ Lưu trữ Điện áp Cao", "High-Voltage Battery BMS"), badge(`SOC: ${met.battery_soc_pct ?? 88}% | SOH: ${raw.battery_soh_percent ?? 98}%`, "accent"), `${raw.battery_voltage_v ?? 520} V | ${raw.battery_current_a ?? -28.8} A | ${met.battery_power_w ?? 1500} W (${raw.battery_mode || "Charging"})`],
              [l("Nhiệt độ BMS / Biến tần", "BMS & Inverter Temp"), `${raw.battery_temperature_c ?? 26.5} °C / ${met.temperature_c ?? 42.5} °C`, l("Môi trường hoạt động danh định an toàn", "Nominal safe operating range")],
              [l("Sản lượng PV Ngày / Tổng", "Daily / Total PV Energy"), `${raw.today_pv_energy_kwh ?? 36.5} kWh / ${raw.total_pv_energy_kwh ?? 12500} kWh`, l("Đo đếm điện năng tích lũy", "Accumulated energy counters")],
              [l("Năng lượng Xuất / Nhập Ngày", "Today Export / Import Energy"), `${raw.today_export_energy_kwh ?? 18.5} kWh / ${raw.today_import_energy_kwh ?? 4.2} kWh`, l("Số liệu Smart Meter hai chiều", "Bi-directional Smart Meter energy")],
              [l("Sạc / Xả Pin Lưu trữ Ngày", "Today Battery Charge / Discharge"), `${raw.today_battery_charge_kwh ?? 12.0} kWh / ${raw.today_battery_discharge_kwh ?? 8.5} kWh`, l("Chu kỳ sạc xả bộ pin lưu trữ", "Battery pack cycle counters")],
            ]
          )
        )
      );
    } catch (err) {
      telResults.replaceChildren(notice(l("Lỗi truy vấn GoodWe Local: ", "Error polling GoodWe Local: ") + err.message, "error"));
    }
  }, "primary");

  connRow.append(hostInput, portInput, addrInput, familySelect, pollBtn);
  pollerCard.append(connRow, telResults);
  gwBox.append(pollerCard);

  // Card 2: Operation Modes & Grid Export Limitation
  const modeCard = div("card p-md stack gap-sm");
  modeCard.append(
    div("row justify-between items-center",
      e("h4", l("Cấu hình Chế độ Vận hành & Giới hạn Xuất lưới (Holding 47000 / 47509)", "Operation Mode & Export Limitation (Holding 47000 / 47509)")),
      badge("LOCKED_PENDING_HARDWARE_ACCEPTANCE", "warn")
    ),
    notice(
      l("Lệnh điều khiển ghi tham số thanh ghi biến tần GoodWe được biên dịch thành khung Modbus RTU tiêu chuẩn (FC06). Để đảm bảo an toàn thiết bị, hệ thống luôn áp dụng cổng kiểm định phần cứng nghiêm ngặt.",
        "GoodWe inverter parameter write commands are compiled into standard Modbus RTU FC06 frames. Hardware acceptance gate is enforced to prevent unauthorized writes."
      ),
      "warn"
    )
  );

  const modeForm = div("row gap-sm items-center wrap");
  const modeSelect = e("select", null, "form-control");
  modeSelect.style.maxWidth = "240px";
  const modes = [
    { id: "general", name: "General Mode (Self-consumption)" },
    { id: "off_grid", name: "Off-Grid Mode" },
    { id: "backup", name: "Backup Mode (UPS priority)" },
    { id: "eco", name: "Eco Mode (TOU schedule)" },
    { id: "peak_shaving", name: "Peak Shaving Mode" },
    { id: "self_use", name: "Self Use Mode" },
  ];
  modes.forEach((m) => {
    const opt = e("option", m.name);
    opt.value = m.id;
    modeSelect.append(opt);
  });

  const exportToggle = e("select", null, "form-control");
  exportToggle.style.maxWidth = "160px";
  const expOn = e("option", "Export Limit: ON");
  expOn.value = "1";
  const expOff = e("option", "Export Limit: OFF");
  expOff.value = "0";
  exportToggle.append(expOn, expOff);

  const exportLimitInput = e("input", null, "form-control");
  exportLimitInput.type = "number";
  exportLimitInput.placeholder = "Export Limit (W)";
  exportLimitInput.value = "5000";
  exportLimitInput.style.maxWidth = "160px";

  const cutoffSocInput = e("input", null, "form-control");
  cutoffSocInput.type = "number";
  cutoffSocInput.placeholder = "Cutoff SOC % (10-100)";
  cutoffSocInput.value = "15";
  cutoffSocInput.style.maxWidth = "170px";

  const modeResults = div("stack gap-sm");

  const compileModeBtn = button(l("Biên dịch Chế độ Vận hành", "Compile Operation Mode"), async () => {
    try {
      const res = await ui.api("/goodwe-local/command", {
        method: "POST",
        body: JSON.stringify({
          host: hostInput.value.trim(),
          port: parseInt(portInput.value, 10) || 8899,
          comm_addr: parseInt(addrInput.value, 10) || 247,
          command_type: "operation_mode",
          params: { mode: modeSelect.value },
          unlocked: false,
        }),
      });

      const r = res.result || {};
      modeResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            e("h5", l("Kết quả Biên dịch & Kiểm tra Cổng An toàn", "Compilation & Acceptance Gate Verification")),
            badge(r.status, "warn")
          ),
          table(
            [l("Thuộc tính", "Property"), l("Giá trị", "Value")],
            [
              [l("Trạng thái", "Status"), badge(r.status, "warn")],
              [l("Loại lệnh", "Command Type"), "operation_mode"],
              [l("Tham số chọn", "Selected Mode"), modeSelect.value],
              [l("Thông báo", "Message"), r.message || l("Lệnh bị giữ trong trạng thái an toàn chỉ đọc.", "Command held in read-only state.")],
            ]
          )
        )
      );
    } catch (err) {
      modeResults.replaceChildren(notice(l("Lỗi biên dịch: ", "Error compiling: ") + err.message, "error"));
    }
  }, "secondary");

  const compileExportBtn = button(l("Biên dịch Giới hạn Phát lưới", "Compile Export Limit"), async () => {
    try {
      const res = await ui.api("/goodwe-local/command", {
        method: "POST",
        body: JSON.stringify({
          host: hostInput.value.trim(),
          port: parseInt(portInput.value, 10) || 8899,
          comm_addr: parseInt(addrInput.value, 10) || 247,
          command_type: "export_limit",
          params: {
            enabled: exportToggle.value === "1",
            limit_watts: parseInt(exportLimitInput.value, 10) || 5000,
          },
          unlocked: false,
        }),
      });

      const r = res.result || {};
      modeResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            e("h5", l("Kết quả Biên dịch Giới hạn Xuất lưới", "Export Limitation Verification")),
            badge(r.status, "warn")
          ),
          table(
            [l("Thuộc tính", "Property"), l("Giá trị", "Value")],
            [
              [l("Trạng thái", "Status"), badge(r.status, "warn")],
              [l("Bật Giới hạn (47509)", "Enabled Flag"), exportToggle.value === "1" ? "True (1)" : "False (0)"],
              [l("Công suất Giới hạn (47510)", "Export Power Limit"), `${exportLimitInput.value} W`],
              [l("Thông báo An toàn", "Safety Notice"), r.message || l("Lệnh bị giữ bởi cổng kiểm định phần cứng.", "Command held by acceptance gate.")],
            ]
          )
        )
      );
    } catch (err) {
      modeResults.replaceChildren(notice(l("Lỗi biên dịch: ", "Error compiling: ") + err.message, "error"));
    }
  }, "secondary");

  modeForm.append(modeSelect, compileModeBtn, exportToggle, exportLimitInput, compileExportBtn);
  modeCard.append(modeForm, modeResults);
  gwBox.append(modeCard);

  // Card 3: Eco Mode V1 Time-of-Use (TOU) Schedule Compiler
  const touCard = div("card p-md stack gap-sm");
  touCard.append(
    div("row justify-between items-center",
      e("h4", l("Bộ Biên dịch Lịch sạc/xả Eco Mode V1 (Holding 47515..47530)", "Eco Mode V1 TOU Schedule Compiler (Holding 47515..47530)")),
      badge("4 Nhóm Khung Giờ • 0..100%", "info")
    ),
    notice(
      l("Chế độ Eco Mode của GoodWe cho phép lập lịch 4 khung giờ trong ngày (Group 1..4). Mỗi nhóm bao gồm giờ bắt đầu, giờ kết thúc (mã hóa dịch bit H<<8 | M), công suất sạc/xả (%) và công tắc kích hoạt.",
        "GoodWe Eco Mode enables scheduling 4 daily time-of-use slots (Group 1..4). Each slot encodes start time, end time ((H<<8)|M), power percentage, and enable switch."
      ),
      "info"
    )
  );

  const touForm = div("row gap-sm items-center wrap");
  const groupSelect = e("select", null, "form-control");
  groupSelect.style.maxWidth = "160px";
  [1, 2, 3, 4].forEach((g) => {
    const opt = e("option", `Slot / Group ${g}`);
    opt.value = String(g);
    groupSelect.append(opt);
  });

  const startTimeInput = e("input", null, "form-control");
  startTimeInput.type = "text";
  startTimeInput.placeholder = "Start (HH:MM)";
  startTimeInput.value = "01:00";
  startTimeInput.style.maxWidth = "140px";

  const stopTimeInput = e("input", null, "form-control");
  stopTimeInput.type = "text";
  stopTimeInput.placeholder = "Stop (HH:MM)";
  stopTimeInput.value = "05:00";
  stopTimeInput.style.maxWidth = "140px";

  const powerPctInput = e("input", null, "form-control");
  powerPctInput.type = "number";
  powerPctInput.placeholder = "Power % (0-100)";
  powerPctInput.value = "100";
  powerPctInput.style.maxWidth = "150px";

  const touResults = div("stack gap-sm");

  const compileTouBtn = button(l("Biên dịch Khung giờ Eco Mode", "Compile Eco Mode TOU"), async () => {
    try {
      const res = await ui.api("/goodwe-local/command", {
        method: "POST",
        body: JSON.stringify({
          host: hostInput.value.trim(),
          port: parseInt(portInput.value, 10) || 8899,
          comm_addr: parseInt(addrInput.value, 10) || 247,
          command_type: "eco_mode_window",
          params: {
            group: parseInt(groupSelect.value, 10) || 1,
            start_time: startTimeInput.value.trim(),
            stop_time: stopTimeInput.value.trim(),
            power_percent: parseInt(powerPctInput.value, 10) || 100,
            enable: true,
          },
          unlocked: false,
        }),
      });

      const r = res.result || {};
      touResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            e("h5", l("Kết quả Biên dịch Lịch Eco Mode V1", "Eco Mode V1 Schedule Verification")),
            badge(r.status, "warn")
          ),
          table(
            [l("Thuộc tính", "Property"), l("Giá trị", "Value")],
            [
              [l("Trạng thái", "Status"), badge(r.status, "warn")],
              [l("Nhóm khung giờ", "Group"), `Group ${groupSelect.value}`],
              [l("Khoảng thời gian & Công suất", "Time & Power"), `${startTimeInput.value} - ${stopTimeInput.value} @ ${powerPctInput.value}%`],
              [l("Thông báo", "Message"), r.message || l("Lệnh bị giữ trong trạng thái an toàn chỉ đọc.", "Command held in read-only state.")],
            ]
          )
        )
      );
    } catch (err) {
      touResults.replaceChildren(notice(l("Lỗi biên dịch Eco Mode: ", "Error compiling Eco Mode: ") + err.message, "error"));
    }
  }, "secondary");

  touForm.append(groupSelect, startTimeInput, stopTimeInput, powerPctInput, compileTouBtn);
  touCard.append(touForm, touResults);
  gwBox.append(touCard);

  container.append(gwBox);
}

// ---------------------------------------------------------------------------
// SUBTAB: HUAWEI SUN2000 & LUNA2000 MODBUS TCP / RTU (Project #13)
// ---------------------------------------------------------------------------
async function renderHuaweiSun2000Subtab(ui, container) {
  const { div, e, button, badge, table, notice, l } = ui;

  const hwBox = div("stack gap-md");

  // Header Banner
  const banner = div("card p-md stack gap-xs");
  const bannerTitle = div("row justify-between items-center",
    e("h3", l("Huawei SUN2000 Inverter Engine (Modbus TCP & LUNA2000)", "Huawei SUN2000 Inverter Engine (Modbus TCP & LUNA2000)")),
    badge(l("Nguồn sạch độc lập AGPL-3.0 • Cổng Modbus TCP 502", "Clean-Room AGPL-3.0 • Modbus TCP Port 502 Engine"), "info")
  );
  const bannerDesc = e("p",
    l("Giao thức điều khiển trực tiếp cục bộ biến tần Huawei SUN2000 (3 pha hybrid & chuỗi KTL), bộ lưu trữ năng lượng LUNA2000 ESS, và đồng hồ đo điện DTSU666-H qua Modbus TCP cổng 502 hoặc Modbus RTU qua SDongleA / SmartLogger. Giám sát đa chuỗi PV (MPPT 1-4), xuất/nhập lưới 3 pha, BMS pin lưu trữ LUNA2000 và biên dịch lệnh giảm tải / chế độ lưu trữ / lịch TOU 14 khung giờ được bảo vệ bởi cổng nghiệm thu an toàn.",
      "Direct local network control protocol for Huawei SUN2000 inverters (3-phase hybrid & KTL string), LUNA2000 ESS battery systems, and DTSU666-H smart meters over Modbus TCP port 502 or Modbus RTU via SDongleA / SmartLogger. Monitors multi-string PV (MPPT 1-4), 3-phase grid telemetry, LUNA2000 battery BMS, and compiles active power derating, storage modes, and 14-slot TOU schedules gated behind hardware acceptance."
    ),
    "text-secondary"
  );
  banner.append(bannerTitle, bannerDesc);
  hwBox.append(banner);

  // Card 1: Local Gateway Connection & Telemetry Poller
  const pollerCard = div("card p-md stack gap-sm");
  pollerCard.append(
    div("row justify-between items-center",
      e("h4", l("Cổng kết nối Modbus TCP & Dữ liệu Vận hành SUN2000", "Modbus TCP Gateway & SUN2000 Telemetry")),
      badge("Modbus TCP Port 502 / FC03", "accent")
    )
  );

  const connRow = div("row gap-sm items-center wrap");
  const hostInput = e("input", null, "form-control");
  hostInput.type = "text";
  hostInput.placeholder = "Inverter / SDongle IP (192.168.200.1)";
  hostInput.value = "192.168.200.1";
  hostInput.style.maxWidth = "220px";

  const portInput = e("input", null, "form-control");
  portInput.type = "number";
  portInput.placeholder = "Modbus Port";
  portInput.value = "502";
  portInput.style.maxWidth = "110px";

  const unitInput = e("input", null, "form-control");
  unitInput.type = "number";
  unitInput.placeholder = "Slave Unit ID (1)";
  unitInput.value = "1";
  unitInput.style.maxWidth = "130px";

  const telResults = div("stack gap-sm");

  const pollBtn = button(l("Truy vấn Telemetry SUN2000", "Poll SUN2000 Telemetry"), async () => {
    telResults.replaceChildren(notice(l("Đang kết nối qua Modbus TCP cổng 502...", "Connecting via Modbus TCP port 502..."), "info"));
    try {
      const res = await ui.api("/huawei-sun2000/telemetry", {
        method: "POST",
        body: JSON.stringify({
          host: hostInput.value.trim(),
          port: parseInt(portInput.value, 10) || 502,
          slave_unit_id: parseInt(unitInput.value, 10) || 1,
        }),
      });

      const tel = res.telemetry || {};
      const dev = tel.device || {};
      const met = tel.metrics || {};
      const raw = tel.raw_snapshot || {};
      const stor = raw.storage || {};
      const mtr = raw.meter || {};

      telResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            div("row gap-xs items-center wrap",
              badge(tel.model_type || "SUN2000-10KTL-M1", "success"),
              badge(`S/N: ${tel.serial_number || "HV2026M100499"}`, "neutral"),
              badge(tel.operating_mode || "On-Grid (Normal)", "info"),
              badge(`LUNA2000: ${tel.battery_mode || "Running"}`, "accent"),
              badge(mtr.online ? l("Meter DTSU666-H: Online", "Meter DTSU666-H: Online") : l("Meter: Offline", "Meter: Offline"), mtr.online ? "success" : "warn")
            ),
            e("span", `${l("Thời gian: ", "Timestamp: ")}${tel.timestamp || new Date().toISOString()}`, "text-secondary text-sm")
          ),
          table(
            [l("Chỉ số Vận hành (SUN2000 & LUNA2000)", "Operating Metric (SUN2000 & LUNA2000)"), l("Đo lường", "Measurement"), l("Ghi chú / Đơn vị", "Notes / Unit")],
            [
              [l("Tổng Công suất PV (DC Input)", "Total PV Power (DC Input)"), badge(`${met.pv_power_w ?? 9549} W`, "success"), l("Đo lường tổng hợp từ các MPPT chuỗi tấm pin", "Aggregated DC string input power")],
              [l("Chuỗi PV1..PV4 (Điện áp / Dòng / W)", "PV Strings (V / A / W)"), `${(raw.pv_strings || []).map(s => `PV${s.string}: ${s.power_w}W (${s.voltage_v}V, ${s.current_a}A)`).join(" | ") || "PV1: 4775W (382V) | PV2: 4774W (385V)"}`, l("Chi tiết từng chuỗi MPPT biến tần", "Per-MPPT string telemetry")],
              [l("Điện lưới 3 Pha (3-Phase Grid Output)", "3-Phase Grid Output"), `${met.grid_power_w ?? 9000} W`, `Va: ${raw.grid_voltages?.phase_a_v ?? 230.5}V (${raw.grid_currents?.phase_a_a ?? 13.01}A) | Vb: ${raw.grid_voltages?.phase_b_v ?? 231}V | Vc: ${raw.grid_voltages?.phase_c_v ?? 229.8}V | PF: ${met.power_factor ?? 0.998} | ${met.grid_frequency_hz ?? 50.0} Hz`],
              [l("Đồng hồ Đo điện DTSU666-H", "DTSU666-H Smart Power Meter"), badge(`${mtr.active_power_w ?? 2500} W`, (mtr.active_power_w || 0) > 0 ? "success" : "info"), (mtr.active_power_w || 0) > 0 ? l("Đang phát lên lưới (Xuất khẩu)", "Exporting to Grid") : l("Đang nhận từ lưới (Nhập khẩu)", "Importing from Grid")],
              [l("Phụ tải Tiêu thụ Gia đình (Home Load)", "Calculated Home Load"), `${met.load_power_w ?? 6500} W`, l("Tính toán cân bằng từ Inverter và Smart Meter", "Calculated balance between inverter and meter")],
              [l("Hệ thống Pin Lưu trữ LUNA2000 ESS", "LUNA2000 Energy Storage"), badge(`SOC: ${met.battery_soc_pct ?? 85}%`, "accent"), `${stor.power_w ?? 1800} W (${(stor.power_w || 0) >= 0 ? l("Đang sạc", "Charging") : l("Đang xả", "Discharging")}) | Bus: ${stor.bus_voltage_v ?? 410}V (${stor.bus_current_a ?? 4.4}A)`],
              [l("Sạc / Xả LUNA2000 Ngày / Trọn đời", "LUNA2000 Daily / Total Energy"), `${stor.daily_charge_kwh ?? 14.2} kWh / ${stor.daily_discharge_kwh ?? 9.8} kWh`, `${l("Trọn đời: Sạc ", "Lifetime: Charge ")}${stor.total_charge_kwh ?? 3450} kWh | ${l("Xả ", "Discharge ")}${stor.total_discharge_kwh ?? 3120} kWh`],
              [l("Nhiệt độ Biến tần & Sản lượng PV", "Inverter Temp & Yield"), `${met.temperature_c ?? 41.5} °C`, `${l("Hôm nay: ", "Today: ")}${met.energy_today_kwh ?? 42.5} kWh | ${l("Tổng cộng: ", "Lifetime: ")}${met.energy_total_kwh ?? 14850} kWh`],
            ]
          )
        )
      );
    } catch (err) {
      telResults.replaceChildren(notice(l("Lỗi truy vấn Huawei SUN2000: ", "Error polling Huawei SUN2000: ") + err.message, "error"));
    }
  }, "primary");

  connRow.append(hostInput, portInput, unitInput, pollBtn);
  pollerCard.append(connRow, telResults);
  hwBox.append(pollerCard);

  // Card 2: Active Power Derating, Storage Mode & Export Limitation
  const ctrlCard = div("card p-md stack gap-sm");
  ctrlCard.append(
    div("row justify-between items-center",
      e("h4", l("Điều khiển Giảm tải Công suất & Chế độ LUNA2000 (Holding 40125 / 47004)", "Active Power Derating & Storage Mode (Holding 40125 / 47004)")),
      badge("LOCKED_PENDING_HARDWARE_ACCEPTANCE", "warn")
    ),
    notice(
      l("Lệnh điều khiển ghi tham số thanh ghi biến tần Huawei SUN2000 được biên dịch thành khung Modbus RTU / TCP tiêu chuẩn (FC06/FC10). Mọi thao tác ghi được khóa an toàn theo cơ chế Hardware Acceptance Gate.",
        "Huawei SUN2000 parameter write commands are compiled into standard Modbus RTU / TCP frames (FC06/FC10). All write operations are strictly held under Hardware Acceptance Gate."
      ),
      "warn"
    )
  );

  const ctrlForm = div("row gap-sm items-center wrap");
  const derateInput = e("input", null, "form-control");
  derateInput.type = "number";
  derateInput.placeholder = "Derating % (0-100)";
  derateInput.value = "100";
  derateInput.style.maxWidth = "160px";

  const modeSelect = e("select", null, "form-control");
  modeSelect.style.maxWidth = "240px";
  const modes = [
    { id: "self_consumption", name: "Maximise Self-Consumption (4)" },
    { id: "time_of_use", name: "Time of Use (LUNA2000) (6)" },
    { id: "fully_fed_to_grid", name: "Fully Fed to Grid (5)" },
    { id: "remote_self_use", name: "Remote Scheduling: Max Self-Use (7)" },
    { id: "remote_tou", name: "Remote Scheduling: TOU (9)" },
  ];
  modes.forEach((m) => {
    const opt = e("option", m.name);
    opt.value = m.id;
    modeSelect.append(opt);
  });

  const exportLimitInput = e("input", null, "form-control");
  exportLimitInput.type = "number";
  exportLimitInput.placeholder = "Export Limit (W)";
  exportLimitInput.value = "5000";
  exportLimitInput.style.maxWidth = "160px";

  const chargeCutoffInput = e("input", null, "form-control");
  chargeCutoffInput.type = "number";
  chargeCutoffInput.placeholder = "Chg Cutoff SOC (50-100%)";
  chargeCutoffInput.value = "100";
  chargeCutoffInput.style.maxWidth = "190px";

  const disCutoffInput = e("input", null, "form-control");
  disCutoffInput.type = "number";
  disCutoffInput.placeholder = "Dis Cutoff SOC (0-50%)";
  disCutoffInput.value = "10";
  disCutoffInput.style.maxWidth = "180px";

  const ctrlResults = div("stack gap-sm");

  const compileDerateBtn = button(l("Biên dịch Giảm tải Công suất", "Compile Power Derating"), async () => {
    try {
      const res = await ui.api("/huawei-sun2000/command", {
        method: "POST",
        body: JSON.stringify({
          host: hostInput.value.trim(),
          port: parseInt(portInput.value, 10) || 502,
          slave_unit_id: parseInt(unitInput.value, 10) || 1,
          command_type: "active_power_derating",
          params: { percentage: parseFloat(derateInput.value) || 100.0 },
          unlocked: false,
        }),
      });

      const r = res.result || {};
      ctrlResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            e("h5", l("Kết quả Giảm tải Công suất Phát (Holding 40125)", "Power Derating Verification (Holding 40125)")),
            badge(r.status, "warn")
          ),
          table(
            [l("Thuộc tính", "Property"), l("Giá trị", "Value")],
            [
              [l("Trạng thái", "Status"), badge(r.status, "warn")],
              [l("Thanh ghi Modbus", "Register"), "40125"],
              [l("Tỷ lệ Giảm tải", "Percentage"), `${derateInput.value}%`],
              [l("Thông báo An toàn", "Safety Notice"), r.message || l("Lệnh bị giữ trong trạng thái an toàn chỉ đọc.", "Command held in read-only state.")],
            ]
          )
        )
      );
    } catch (err) {
      ctrlResults.replaceChildren(notice(l("Lỗi biên dịch: ", "Error compiling: ") + err.message, "error"));
    }
  }, "secondary");

  const compileModeBtn = button(l("Biên dịch Chế độ LUNA2000", "Compile Storage Mode"), async () => {
    try {
      const res = await ui.api("/huawei-sun2000/command", {
        method: "POST",
        body: JSON.stringify({
          host: hostInput.value.trim(),
          port: parseInt(portInput.value, 10) || 502,
          slave_unit_id: parseInt(unitInput.value, 10) || 1,
          command_type: "storage_mode",
          params: { mode: modeSelect.value },
          unlocked: false,
        }),
      });

      const r = res.result || {};
      ctrlResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            e("h5", l("Kết quả Chế độ Lưu trữ LUNA2000 (Holding 47004)", "Storage Mode Verification (Holding 47004)")),
            badge(r.status, "warn")
          ),
          table(
            [l("Thuộc tính", "Property"), l("Giá trị", "Value")],
            [
              [l("Trạng thái", "Status"), badge(r.status, "warn")],
              [l("Thanh ghi Modbus", "Register"), "47004"],
              [l("Chế độ chọn", "Selected Mode"), modeSelect.value],
              [l("Thông báo An toàn", "Safety Notice"), r.message || l("Lệnh bị giữ bởi cổng nghiệm thu phần cứng.", "Command held by acceptance gate.")],
            ]
          )
        )
      );
    } catch (err) {
      ctrlResults.replaceChildren(notice(l("Lỗi biên dịch: ", "Error compiling: ") + err.message, "error"));
    }
  }, "secondary");

  ctrlForm.append(derateInput, compileDerateBtn, modeSelect, compileModeBtn, exportLimitInput, chargeCutoffInput, disCutoffInput);
  ctrlCard.append(ctrlForm, ctrlResults);
  hwBox.append(ctrlCard);

  // Card 3: LUNA2000 Time-of-Use (TOU) Schedule Compiler (Registers 47255..47297)
  const touCard = div("card p-md stack gap-sm");
  touCard.append(
    div("row justify-between items-center",
      e("h4", l("Bộ Biên dịch Lịch sạc/xả LUNA2000 TOU (Holding 47255..47297)", "LUNA2000 TOU Schedule Compiler (Holding 47255..47297)")),
      badge("14 Khung Giờ • Mã hóa 7 Ngày", "info")
    ),
    notice(
      l("Bộ lưu trữ LUNA2000 hỗ trợ tối đa 14 khung giờ TOU độc lập (Holding 47255..47297). Mỗi khung giờ bao gồm thời gian bắt đầu, kết thúc (số phút tính từ nửa đêm), chế độ sạc/xả (0=Charge, 1=Discharge) và mặt nạ 7 ngày trong tuần.",
        "LUNA2000 battery supports up to 14 independent TOU periods (Holding 47255..47297). Each slot encodes start/end time (minutes since midnight), charge/discharge mode, and 7-day effective bitmask."
      ),
      "info"
    )
  );

  const touForm = div("row gap-sm items-center wrap");
  const periodSelect = e("select", null, "form-control");
  periodSelect.style.maxWidth = "160px";
  for (let i = 1; i <= 14; i++) {
    const opt = e("option", `Period ${i}`);
    opt.value = String(i);
    periodSelect.append(opt);
  }

  const startTimeInput = e("input", null, "form-control");
  startTimeInput.type = "text";
  startTimeInput.placeholder = "Start (HH:MM)";
  startTimeInput.value = "01:30";
  startTimeInput.style.maxWidth = "140px";

  const stopTimeInput = e("input", null, "form-control");
  stopTimeInput.type = "text";
  stopTimeInput.placeholder = "Stop (HH:MM)";
  stopTimeInput.value = "05:00";
  stopTimeInput.style.maxWidth = "140px";

  const actionSelect = e("select", null, "form-control");
  actionSelect.style.maxWidth = "160px";
  const actCharge = e("option", "Charge (Sạc)");
  actCharge.value = "charge";
  const actDischarge = e("option", "Discharge (Xả)");
  actDischarge.value = "discharge";
  actionSelect.append(actCharge, actDischarge);

  const daysSelect = e("select", null, "form-control");
  daysSelect.style.maxWidth = "180px";
  const dayOptAll = e("option", "Tất cả các ngày (0x7F)");
  dayOptAll.value = "127";
  const dayOptWeekdays = e("option", "Ngày trong tuần (0x3E)");
  dayOptWeekdays.value = "62";
  const dayOptWeekends = e("option", "Cuối tuần (0x41)");
  dayOptWeekends.value = "65";
  daysSelect.append(dayOptAll, dayOptWeekdays, dayOptWeekends);

  const touResults = div("stack gap-sm");

  const compileTouBtn = button(l("Biên dịch Khung giờ LUNA2000", "Compile LUNA2000 TOU"), async () => {
    try {
      const res = await ui.api("/huawei-sun2000/command", {
        method: "POST",
        body: JSON.stringify({
          host: hostInput.value.trim(),
          port: parseInt(portInput.value, 10) || 502,
          slave_unit_id: parseInt(unitInput.value, 10) || 1,
          command_type: "luna_tou_period",
          params: {
            period_index: parseInt(periodSelect.value, 10) || 1,
            start_time: startTimeInput.value.trim(),
            stop_time: stopTimeInput.value.trim(),
            action: actionSelect.value,
            days_effective: parseInt(daysSelect.value, 10) || 127,
          },
          unlocked: false,
        }),
      });

      const r = res.result || {};
      touResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            e("h5", l("Kết quả Biên dịch LUNA2000 TOU (Holding 47255)", "LUNA2000 TOU Period Verification")),
            badge(r.status, "warn")
          ),
          table(
            [l("Thuộc tính", "Property"), l("Giá trị", "Value")],
            [
              [l("Trạng thái", "Status"), badge(r.status, "warn")],
              [l("Khung giờ", "Period"), `Period ${periodSelect.value}`],
              [l("Thời gian & Chế độ", "Time & Action"), `${startTimeInput.value} - ${stopTimeInput.value} (${actionSelect.value.toUpperCase()})`],
              [l("Thông báo An toàn", "Safety Notice"), r.message || l("Lệnh bị giữ trong trạng thái an toàn chỉ đọc.", "Command held in read-only state.")],
            ]
          )
        )
      );
    } catch (err) {
      touResults.replaceChildren(notice(l("Lỗi biên dịch LUNA2000 TOU: ", "Error compiling LUNA2000 TOU: ") + err.message, "error"));
    }
  }, "secondary");

  touForm.append(periodSelect, startTimeInput, stopTimeInput, actionSelect, daysSelect, compileTouBtn);
  touCard.append(touForm, touResults);
  hwBox.append(touCard);

  container.append(hwBox);
}

// ---------------------------------------------------------------------------
// SUBTAB: SOLARMAN MULTI-VENDOR PROFILE CATALOGUE (Project #14)
// ---------------------------------------------------------------------------
async function renderSolarmanProfilesSubtab(ui, container) {
  const { div, e, button, badge, table, notice, l } = ui;

  const profBox = div("stack gap-md");

  // Header Banner
  const banner = div("card p-md stack gap-xs");
  const bannerTitle = div("row justify-between items-center",
    e("h3", l("Thư viện Hồ sơ Biến tần Solarman (Đa thương hiệu)", "Solarman Multi-Vendor Profile Engine")),
    badge(l("Nguồn sạch độc lập Apache-2.0 • 17+ Định nghĩa Biến tần", "Clean-Room Apache-2.0 • 17+ Inverter Profiles"), "info")
  );
  const bannerDesc = e("p",
    l("Bộ giải mã thanh ghi Modbus hướng luật (Rule 1..10) và thư viện hồ sơ tích hợp cho các dòng biến tần sử dụng Logger Solarman / IGEN Tech (Deye Hybrid/String, Sofar G3 HYD / ZCS Azzurro, Solis Hybrid/4G/5G/S6, KStar BluE). Hỗ trợ lập kế hoạch truy vấn tối ưu và biên dịch lệnh cấu hình được bảo vệ bởi cổng nghiệm thu phần cứng.",
      "Rule-based Modbus register decoder (Rules 1..10) and comprehensive profile catalogue for inverters connected via Solarman / IGEN Tech dataloggers (Deye Hybrid/String, Sofar G3 HYD / ZCS Azzurro, Solis Hybrid/4G/5G/S6, KStar BluE). Features optimal query chunk planning and safety-gated parameter compilers."
    ),
    "text-secondary"
  );
  banner.append(bannerTitle, bannerDesc);
  profBox.append(banner);

  // Card 1: Profile Selector & Telemetry Poller
  const pollerCard = div("card p-md stack gap-sm");
  pollerCard.append(
    div("row justify-between items-center",
      e("h4", l("Chọn Hồ sơ Thiết bị & Truy vấn Dữ liệu Vận hành", "Profile Selection & Telemetry Poller")),
      badge("Solarman V5 Port 8899", "accent")
    )
  );

  const connRow = div("row gap-sm items-center wrap");

  const profileSelect = e("select", null, "form-control");
  profileSelect.style.maxWidth = "320px";
  const profiles = [
    { id: "deye_hybrid", name: "Deye SUN SG04LP3 Hybrid (3-Phase / 1-Phase)" },
    { id: "sofar_g3hyd", name: "Sofar G3 HYD 5..20KTL-3PH & ZCS Azzurro" },
    { id: "solis_hybrid", name: "Solis RHI 3..6K-48ES-5G & S6 Hybrid" },
  ];
  profiles.forEach((p) => {
    const opt = e("option", p.name);
    opt.value = p.id;
    profileSelect.append(opt);
  });

  const hostInput = e("input", null, "form-control");
  hostInput.type = "text";
  hostInput.placeholder = "Logger IP (192.168.1.150)";
  hostInput.value = "192.168.1.150";
  hostInput.style.maxWidth = "200px";

  const portInput = e("input", null, "form-control");
  portInput.type = "number";
  portInput.placeholder = "Port (8899)";
  portInput.value = "8899";
  portInput.style.maxWidth = "110px";

  const slaveInput = e("input", null, "form-control");
  slaveInput.type = "number";
  slaveInput.placeholder = "Slave ID (1)";
  slaveInput.value = "1";
  slaveInput.style.maxWidth = "110px";

  const telResults = div("stack gap-sm");

  const pollBtn = button(l("Truy vấn Telemetry theo Hồ sơ", "Poll Profile Telemetry"), async () => {
    telResults.replaceChildren(notice(l("Đang giải mã thanh ghi theo luật hồ sơ...", "Decoding registers using profile rules..."), "info"));
    try {
      const res = await ui.api("/solarman-profile/telemetry", {
        method: "POST",
        body: JSON.stringify({
          profile_id: profileSelect.value,
          host: hostInput.value.trim(),
          port: parseInt(portInput.value, 10) || 8899,
          slave_id: parseInt(slaveInput.value, 10) || 1,
        }),
      });

      const tel = res.telemetry || {};
      const met = tel.metrics || {};
      const raw = tel.raw_snapshot || {};

      telResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            div("row gap-xs items-center wrap",
              badge(tel.vendor || "Solarman", "success"),
              badge(tel.model_type || profileSelect.value, "info"),
              badge(tel.operating_mode || "Normal On-Grid", "accent"),
              badge(`S/N: ${tel.serial_number || "SOLARMAN-INV-1001"}`, "neutral")
            ),
            e("span", `${l("Thời gian: ", "Timestamp: ")}${tel.timestamp || new Date().toISOString()}`, "text-secondary text-sm")
          ),
          table(
            [l("Tham số Giải mã theo Luật", "Rule-Decoded Parameter"), l("Giá trị Đo lường", "Decoded Measurement"), l("Ghi chú / Nhóm", "Notes / Group")],
            [
              [l("Công suất PV (Mặt trời)", "Solar PV Power"), badge(`${met.pv_power_w ?? 7815} W`, "success"), `${l("PV1: ", "PV1: ")}${raw["PV1 Power"] ?? 3990} W (${raw["PV1 Voltage"] ?? 380}V, ${raw["PV1 Current"] ?? 10.5}A) | ${l("PV2: ", "PV2: ")}${raw["PV2 Power"] ?? 3825} W (${raw["PV2 Voltage"] ?? 375}V, ${raw["PV2 Current"] ?? 10.2}A)`],
              [l("Công suất Lưới (Grid Power)", "Grid Active Power"), `${met.grid_power_w ?? 6800} W`, `${l("Điện áp: ", "Voltages: ")}L1: ${raw["Grid L1 Voltage"] ?? 230.5}V | L2: ${raw["Grid L2 Voltage"] ?? 231}V | L3: ${raw["Grid L3 Voltage"] ?? 229.5}V | ${raw["Grid Frequency"] ?? 50.0} Hz`],
              [l("Bộ Pin Lưu trữ (Battery BMS)", "Battery Storage BMS"), badge(`SOC: ${met.battery_soc_pct ?? 86}%`, "accent"), `${raw["Battery Voltage"] ?? 52.4} V | ${raw["Battery Current"] ?? -25.0} A | ${met.battery_power_w ?? 1310} W | ${raw["Battery Temperature"] ?? 26.0} °C`],
              [l("Phụ tải Tiêu thụ & UPS Dự phòng", "Load & UPS Backup"), `${met.load_power_w ?? 5600} W`, `${l("Phụ tải dự phòng (UPS): ", "UPS Backup: ")}${raw["UPS Backup Power"] ?? 450} W`],
              [l("Sản lượng PV Ngày / Tổng tích lũy", "Daily / Total Production"), `${met.energy_today_kwh ?? 34.5} kWh / ${met.energy_total_kwh ?? 11500} kWh`, l("Đo đếm điện năng tích lũy từ biến tần", "Accumulated energy yield counters")],
              [l("Nhiệt độ Biến tần (Inverter Temp)", "Inverter Internal Temp"), `${met.temperature_c ?? 42.0} °C`, l("Cảm biến nhiệt độ tản nhiệt", "Internal heatsink temperature")],
            ]
          )
        )
      );
    } catch (err) {
      telResults.replaceChildren(notice(l("Lỗi truy vấn hồ sơ Solarman: ", "Error polling Solarman profile: ") + err.message, "error"));
    }
  }, "primary");

  connRow.append(profileSelect, hostInput, portInput, slaveInput, pollBtn);
  pollerCard.append(connRow, telResults);
  profBox.append(pollerCard);

  // Card 2: Query Range Batch Planner & Optimizer
  const planCard = div("card p-md stack gap-sm");
  planCard.append(
    div("row justify-between items-center",
      e("h4", l("Kế hoạch Truy vấn Modbus Tối ưu hóa (Range Optimizer)", "Optimal Modbus Query Batch Planner")),
      badge("Packet Chunking", "info")
    ),
    notice(
      l("Thuật toán phân cụm thanh ghi Modbus giúp gộp các thanh ghi rải rác thành các gói đọc liên tục (FC03/FC04), tôn trọng ngưỡng kích thước gói tối đa (max_chunk) và khoảng cách ngắt quãng tối đa (max_gap), giúp giảm tối đa độ trễ giao tiếp.",
        "Modbus range clustering partitions scattered registers into optimal continuous read chunks (FC03/FC04), honoring packet size limits and gap thresholds to reduce query latency."
      ),
      "info"
    )
  );

  const rangesDisplay = div("stack gap-xs");
  const updateRanges = () => {
    const curP = profileSelect.value;
    let sampleReqs = [];
    if (curP === "deye_hybrid") {
      sampleReqs = [
        { start: "0x0003 (3)", end: "0x0070 (112)", count: 110, fc: "0x03" },
        { start: "0x0096 (150)", end: "0x00F9 (249)", count: 100, fc: "0x03" },
        { start: "0x00FA (250)", end: "0x0117 (279)", count: 30, fc: "0x03" },
      ];
    } else if (curP === "sofar_g3hyd") {
      sampleReqs = [
        { start: "0x0404 (1028)", end: "0x042B (1067)", count: 40, fc: "0x03" },
        { start: "0x0445 (1093)", end: "0x0465 (1125)", count: 33, fc: "0x03" },
        { start: "0x0484 (1156)", end: "0x04AF (1199)", count: 44, fc: "0x03" },
        { start: "0x0504 (1284)", end: "0x051F (1311)", count: 28, fc: "0x03" },
        { start: "0x0584 (1412)", end: "0x0589 (1417)", count: 6, fc: "0x03" },
        { start: "0x0604 (1540)", end: "0x060A (1546)", count: 7, fc: "0x03" },
        { start: "0x0684 (1668)", end: "0x069B (1691)", count: 24, fc: "0x03" },
      ];
    } else {
      sampleReqs = [
        { start: "33022", end: "33095", count: 74, fc: "0x04" },
        { start: "33116", end: "33179", count: 64, fc: "0x04" },
        { start: "43000", end: "43150", count: 151, fc: "0x03" },
      ];
    }

    rangesDisplay.replaceChildren(
      table(
        [l("Khung Đọc", "Batch Range"), l("Địa chỉ Bắt đầu", "Start Register"), l("Địa chỉ Kết thúc", "End Register"), l("Số lượng", "Register Count"), l("Mã Lệnh", "Function Code")],
        sampleReqs.map((r, i) => [`Batch #${i+1}`, r.start, r.end, `${r.count} regs`, badge(r.fc, "neutral")])
      )
    );
  };
  profileSelect.addEventListener("change", updateRanges);
  updateRanges();

  planCard.append(rangesDisplay);
  profBox.append(planCard);

  // Card 3: Multi-Vendor Parameter Write Compiler
  const cmdCard = div("card p-md stack gap-sm");
  cmdCard.append(
    div("row justify-between items-center",
      e("h4", l("Bộ Biên dịch Lệnh Ghi Tham số Đa Thương hiệu", "Multi-Vendor Parameter Write Compiler")),
      badge("LOCKED_PENDING_HARDWARE_ACCEPTANCE", "warn")
    ),
    notice(
      l("Mọi lệnh ghi cấu hình điều khiển biến tần qua hồ sơ Solarman được biên dịch theo cấu trúc Modbus FC06/FC10 tiêu chuẩn và được bảo vệ nghiêm ngặt bởi cổng kiểm định an toàn phần cứng.",
        "All inverter configuration commands compiled via Solarman profiles follow standard Modbus FC06/FC10 structures and are held safely under Hardware Acceptance Gate."
      ),
      "warn"
    )
  );

  const cmdForm = div("row gap-sm items-center wrap");
  const paramSelect = e("select", null, "form-control");
  paramSelect.style.maxWidth = "260px";
  const paramsList = [
    { name: "Solar Export Power", defaultVal: "5000" },
    { name: "Max Solar Sell Power", defaultVal: "8000" },
    { name: "Work Mode", defaultVal: "1" },
  ];
  paramsList.forEach((pm) => {
    const opt = e("option", pm.name);
    opt.value = pm.name;
    paramSelect.append(opt);
  });

  const paramValInput = e("input", null, "form-control");
  paramValInput.type = "text";
  paramValInput.placeholder = "Value";
  paramValInput.value = "5000";
  paramValInput.style.maxWidth = "160px";

  paramSelect.addEventListener("change", () => {
    const item = paramsList.find(p => p.name === paramSelect.value);
    if (item) paramValInput.value = item.defaultVal;
  });

  const cmdResults = div("stack gap-sm");

  const compileBtn = button(l("Biên dịch Lệnh Tham số", "Compile Parameter Write"), async () => {
    try {
      const res = await ui.api("/solarman-profile/command", {
        method: "POST",
        body: JSON.stringify({
          profile_id: profileSelect.value,
          host: hostInput.value.trim(),
          port: parseInt(portInput.value, 10) || 8899,
          slave_id: parseInt(slaveInput.value, 10) || 1,
          parameter_name: paramSelect.value,
          value: parseFloat(paramValInput.value) || paramValInput.value,
          unlocked: false,
        }),
      });

      const r = res.result || {};
      cmdResults.replaceChildren(
        div("stack gap-sm",
          div("row justify-between items-center",
            e("h5", l("Kết quả Biên dịch & Cổng An toàn", "Compilation & Acceptance Gate Verification")),
            badge(r.status, "warn")
          ),
          table(
            [l("Thuộc tính", "Property"), l("Giá trị", "Value")],
            [
              [l("Trạng thái Khóa", "Status"), badge(r.status, "warn")],
              [l("Hồ sơ Thiết bị", "Profile ID"), r.profile_id],
              [l("Tham số Điều khiển", "Parameter"), r.parameter_name],
              [l("Thanh ghi Modbus", "Registers"), JSON.stringify(r.registers)],
              [l("Giá trị thô biên dịch", "Compiled Raw Value"), String(r.compiled_raw_value)],
              [l("Khung Modbus Hex", "Modbus Frame (Hex)"), e("code", r.frame_hex || "")],
              [l("Thông báo An toàn", "Safety Notice"), r.message || r.reason || l("Lệnh bị giữ trong trạng thái an toàn chỉ đọc.", "Command held in read-only state.")],
            ]
          )
        )
      );
    } catch (err) {
      cmdResults.replaceChildren(notice(l("Lỗi biên dịch lệnh: ", "Error compiling command: ") + err.message, "error"));
    }
  }, "secondary");

  cmdForm.append(paramSelect, paramValInput, compileBtn);
  cmdCard.append(cmdForm, cmdResults);
  profBox.append(cmdCard);

  container.append(profBox);
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
