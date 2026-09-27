import { l, t, date, number } from "./i18n.js";
import { icon } from "./icons.js";
import { renderModelLibrary } from "./model-workspace.js";

export async function renderDevicesMainWorkspace(ui) {
  const { state, e, div, p, btn, badge, card, table, select, input, field, fact, notice, showDialog, closeDialog, api, go, sites, deviceDetail } = ui;
  const container = div("stack device-workspace-container");

  const scopeQuery = state.site ? '?site_id=' + encodeURIComponent(state.site) : '';
  const overviewData = await api('/fleet/devices-overview' + scopeQuery);

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

  // SUB-TAB 3: 9 NATIVE PARAMETER GROUPS
  if (currentTab === "native_config") {
    const targetDeviceId = deviceList.find(d => d.id === state.selectedInspectorDevice)?.id || deviceList[0]?.id;
    if (!targetDeviceId) {
      container.append(p(l("Chưa có thiết bị trong phạm vi đã chọn.", "No devices in the selected scope.")));
      return container;
    }
    const configData = await api(`/devices/${encodeURIComponent(targetDeviceId)}/native-config-groups`);

    const groupsList = div("plant-card-grid");
    (configData.groups || []).forEach((g) => {
      const gCard = div("plant-visual-card",
        div("row justify-between",
          e("b", g.title, "plant-card-title"),
          badge(l("Khóa an toàn nghiệm thu", "Locked"), "warn")
        ),
        p(l("Lý do khóa: Chưa hoàn tất biên bản nghiệm thu phần cứng hiện trường (LOCKED_PENDING_HARDWARE_ACCEPTANCE).", "Locked: Hardware acceptance required before native write."), "small bad"),
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
  const rawRegisterInput = ui.e("textarea", null, "monospace");
  rawRegisterInput.placeholder = l("Nhập JSON thanh ghi từ thiết bị đã xác minh", "Enter observed register JSON from the verified device");
  container.append(ui.field(l("Thanh ghi đầu vào (không tự lấy số mẫu)", "Observed register input (no sample data)"), rawRegisterInput));

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

        return inp;
      })(),
      e("label", "Prefix:"),
      (() => {
        const inp = e("input", "", "input-search");
        inp.id = "solis_disc_prefix";
        inp.value = "homeassistant";

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
      const simulatedRegisters = JSON.parse(rawRegisterInput.value);

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

        return inp;
      })(),
      e("label", "Mã trạm (Station ID):"),
      (() => {
        const inp = e("input", "", "input-search");
        inp.id = "goodwe_stid";
        inp.value = "gw_rooftop_vn01";

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
  const rawRegisterInput = ui.e("textarea", null, "monospace");
  rawRegisterInput.placeholder = l("Nhập JSON thanh ghi từ thiết bị đã xác minh", "Enter observed register JSON from the verified device");
  container.append(ui.field(l("Thanh ghi đầu vào (không tự lấy số mẫu)", "Observed register input (no sample data)"), rawRegisterInput));

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
      const simulatedHolding = JSON.parse(rawRegisterInput.value);

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
      const simulatedInputRegs = JSON.parse(rawRegisterInput.value);

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

  container.append(sphBox);
}

async function renderSolisHybridSubtab(ui, container) {
  const rawRegisterInput = ui.e("textarea", null, "monospace");
  rawRegisterInput.placeholder = l("Nhập JSON thanh ghi từ thiết bị đã xác minh", "Enter observed register JSON from the verified device");
  container.append(ui.field(l("Thanh ghi đầu vào (không tự lấy số mẫu)", "Observed register input (no sample data)"), rawRegisterInput));

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

  const voltInput = e("input", null, "input-text");
  voltInput.type = "number";
  voltInput.value = "51.2";
  voltInput.placeholder = "Điện áp Pin V (VD: 51.2)";

  const ttlInput = e("input", null, "input-text");
  ttlInput.type = "number";
  ttlInput.value = "1200";
  ttlInput.placeholder = "Watchdog TTL s (VD: 1200)";

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
      const mockRegs = JSON.parse(rawRegisterInput.value);

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
  const rawRegisterInput = ui.e("textarea", null, "monospace");
  rawRegisterInput.placeholder = l("Nhập JSON thanh ghi từ thiết bị đã xác minh", "Enter observed register JSON from the verified device");
  container.append(ui.field(l("Thanh ghi đầu vào (không tự lấy số mẫu)", "Observed register input (no sample data)"), rawRegisterInput));

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
      const mockRegs = JSON.parse(rawRegisterInput.value);

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

  const slotPwrInput = e("input", null, "input-text");
  slotPwrInput.type = "number";
  slotPwrInput.value = "6000";
  slotPwrInput.placeholder = "Công suất W";

  const slotSocInput = e("input", null, "input-text");
  slotSocInput.type = "number";
  slotSocInput.value = "95";
  slotSocInput.placeholder = "SOC %";

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
      const mockTelemetryRegs = JSON.parse(rawRegisterInput.value);

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

  const slaveInput = e("input", null, "input-text");
  slaveInput.type = "number";
  slaveInput.value = "1";
  slaveInput.placeholder = "Slave ID";

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

  const qtyInput = e("input", null, "input-text");
  qtyInput.type = "number";
  qtyInput.value = "10";
  qtyInput.placeholder = "Số lượng / Giá trị";

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


  // Prepopulate with a verified synthetic response frame:
  // Start=A5, Len=15 (0x0F,0x00), Code=10 15, Seq=01 00, Serial=DE C0 AD 89 (2309865694), Type=02, Status=01, Times..., Modbus RTU (01 03 02 01 F4 78 8B), Checksum=XX, End=15
  decInputArea.value = "";

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
  discInput.value = "";
  discInput.placeholder = "Chuỗi phản hồi UDP (VD: 192.168.1.150,ACCF23654128,2312345678)";

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

  const devaddrInput = e("input", null, "input-text");
  devaddrInput.type = "number";
  devaddrInput.value = "1";
  devaddrInput.min = "1";
  devaddrInput.max = "247";
  devaddrInput.placeholder = "Địa chỉ RS485";

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
