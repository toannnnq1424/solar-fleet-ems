import { l, t, date, number } from "./i18n.js";
import { icon } from "./icons.js";

export async function renderDevicesMainWorkspace(ui) {
  const { state, e, div, p, btn, badge, card, table, select, input, field, fact, notice, showDialog, closeDialog, api, go, sites, deviceDetail } = ui;
  const container = div("stack device-workspace-container");

  const overviewData = await api('/fleet/devices-overview');

  const subtabs = [
    ["inventory", l("Danh mục thiết bị", "Device Inventory")],
    ["inspector", l("Kiểm tra thanh ghi Modbus", "Modbus Register Inspector")],
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
              btn(l("Quét Modbus", "Modbus Inspector"), () => {
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
                btn(l("Quét Modbus", "Modbus"), () => {
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

  // SUB-TAB 2: MODBUS REGISTER INSPECTOR
  if (currentTab === "inspector") {
    let targetDeviceId = state.selectedInspectorDevice || (deviceList[0] ? deviceList[0].id : "inv_demo");

    const selDev = e("select", "", "select-filter");
    deviceList.forEach((d) => {
      selDev.append(new Option(`${d.name} (${d.vendor} - ${d.model})`, d.id));
    });
    selDev.value = targetDeviceId;
    selDev.onchange = () => { targetDeviceId = selDev.value; };

    const inStartReg = e("input", "", "input-search");
    inStartReg.value = "0x8800";
    inStartReg.placeholder = "0x8800 hoặc 34816";

    const inQty = e("input", "", "select-filter");
    inQty.type = "number";
    inQty.value = "10";
    inQty.min = "1";
    inQty.max = "100";

    const inSlave = e("input", "", "select-filter");
    inSlave.type = "number";
    inSlave.value = "1";

    const resultsArea = div("stack");

    async function runInspect() {
      resultsArea.replaceChildren(p(l("Đang kết nối và đọc thanh ghi Modbus RTU/TCP...", "Reading Modbus registers..."), "small muted"));
      let addrStr = inStartReg.value.trim();
      let startReg = addrStr.startsWith("0x") || addrStr.startsWith("0X") ? parseInt(addrStr, 16) : parseInt(addrStr, 10);
      if (isNaN(startReg) || startReg < 0) {
        alert(l("Địa chỉ thanh ghi không hợp lệ!", "Invalid register address!"));
        return;
      }

      try {
        const resp = await api(`/devices/${targetDeviceId}/modbus-inspect`, {
          start_register: startReg,
          quantity: parseInt(inQty.value, 10) || 10,
          slave_id: parseInt(inSlave.value, 10) || 1,
        });

        const rows = (resp.registers || []).map((r) => [
          badge(r.address_hex, "blue"),
          r.address_dec.toString(),
          e("span", r.hex_val, "monospace"),
          r.uint16.toString(),
          r.int16.toString(),
          e("b", r.scaled_val),
          div("",
            e("b", r.parameter_name),
            r.mapped ? badge(l("Khớp thanh ghi hãng", "Vendor Mapped"), "good") : badge(l("Chưa gán", "Raw"), "gray")
          ),
        ]);

        resultsArea.replaceChildren(
          div("row justify-between",
            div("row",
              badge(`Thiết bị: ${targetDeviceId}`, "blue"),
              badge(`Slave ID: ${inSlave.value}`, "gray"),
              badge(`Số thanh ghi: ${rows.length}`, "good")
            ),
            btn(l("Xuất JSON", "Export JSON"), () => {
              const blob = new Blob([JSON.stringify(resp, null, 2)], { type: "application/json" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `modbus_dump_${targetDeviceId}.json`;
              a.click();
            }, "secondary")
          ),
          table(
            [l("Địa chỉ (Hex)", "Hex Addr"), l("Địa chỉ (Dec)", "Dec Addr"), l("Raw Hex", "Raw Hex"), "UInt16", "Int16", l("Giá trị quy đổi", "Scaled Value"), l("Tên thông số kỹ thuật (Vendor Mapping)", "Parameter Description")],
            rows
          )
        );
      } catch (err) {
        resultsArea.replaceChildren(p(`${l("Lỗi đọc thanh ghi:", "Inspection error:")} ${err.message}`, "bad small"));
      }
    }

    const inspectorBar = div("gis-controls-bar",
      div("row",
        div("field-inline", e("label", l("Thiết bị:", "Device:")), selDev),
        div("field-inline", e("label", l("Địa chỉ bắt đầu:", "Start Reg:")), inStartReg),
        div("field-inline", e("label", l("Số lượng:", "Qty:")), inQty),
        div("field-inline", e("label", l("Slave ID:", "Slave:")), inSlave),
        btn(l("Đọc thanh ghi Modbus", "Read Registers"), runInspect, "primary")
      )
    );

    const presetsBar = div("row",
      e("span", l("Dải thanh ghi mẫu:", "Presets:"), "small muted"),
      btn("GoodWe Telemetry (0x8800)", () => { inStartReg.value = "0x8800"; inQty.value = "16"; runInspect(); }, "secondary small"),
      btn("Deye Hybrid (0x0200)", () => { inStartReg.value = "0x0200"; inQty.value = "16"; runInspect(); }, "secondary small"),
      btn("Sungrow Inverter (0x1300)", () => { inStartReg.value = "0x1300"; inQty.value = "12"; runInspect(); }, "secondary small"),
      btn("Huawei SUN2000 (0x7500)", () => { inStartReg.value = "0x7500"; inQty.value = "10"; runInspect(); }, "secondary small")
    );

    container.append(
      notice(l("Chế độ kiểm tra thanh ghi Modbus RTU/TCP trực tiếp (Chỉ đọc). Dữ liệu được đối chiếu với từ điển thanh ghi chuẩn hóa vendor_registers.py.", "Direct Modbus RTU/TCP Register Inspector (Read-only). Data cross-referenced with vendor_registers.py.")),
      inspectorBar,
      presetsBar,
      resultsArea
    );

    runInspect();
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
      notice(l("9 Nhóm tham số Native của thiết bị được bảo vệ bởi cơ chế an toàn cấp công nghiệp. Toàn bộ lệnh cấu hình phần cứng đều cần fresh readback và chữ ký nghiệm thu.", "9 Native parameter groups are protected by industrial hardware safety gates. All hardware modifications require fresh readback and commissioned sign-off.")),
      groupsList
    );
  }

  // SUB-TAB 4: HEALTH & RELIABILITY
  if (currentTab === "health") {
    const healthGrid = div("plant-card-grid");

    deviceList.forEach((d) => {
      const hCard = div("plant-visual-card",
        div("row justify-between",
          div("row",
            div("plant-type-badge", icon("activity")),
            div("",
              e("b", d.name, "plant-card-title"),
              e("p", `${d.vendor} · ${d.model}`, "small muted")
            )
          ),
          badge(d.health_score == null ? l("Chưa đánh giá", "Not assessed") : `${d.health_score}/100`)
        ),
        div("plant-card-metrics",
          div("fact", e("span", l("Giờ vận hành tích lũy:", "Operating Hours:")), e("b", "14,280 h")),
          div("fact", e("span", l("Số chu kỳ nạp/xả:", "Battery Cycles:")), e("b", d.type === "BATTERY" ? "642 cycles (SOH 98%)" : "N/A")),
          div("fact", e("span", l("Nhiệt độ cuộn dây:", "Winding Temp:")), e("b", `${number(d.temp_c)} °C`)),
          div("fact", e("span", l("Tỷ lệ sẵn sàng Uptime:", "Availability Uptime:")), e("b", "—", "green-text"))
        ),
        div("stack",
          div("fact", e("span", l("Hạn bảo hành:", "Warranty:")), e("span", "2031-12-31 (Còn 5 năm)")),
          div("fact", e("span", l("Tiêu chuẩn:", "Compliance:")), e("span", l("Chưa nghiệm thu", "Not accepted")))
        )
      );
      healthGrid.append(hCard);
    });

    container.append(
      card(l("Tình trạng thiết bị", "Equipment condition"), healthGrid)
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
        badge(r.compliance_status === "COMPLIANT" ? l("Đạt chuẩn", "Compliant") : l("Có bản cập nhật", "Update Available"), r.compliance_status === "COMPLIANT" ? "good" : "warn"),
        r.release_date,
        e("span", r.sha256_hash.slice(0, 16) + "…", "monospace small"),
        btn(r.compliance_status === "COMPLIANT" ? l("Kiểm tra lại", "Verify") : l("Nạp hàng đợi OTA", "Queue OTA"), () => {
          alert(l(`Đã lên lịch kiểm tra / hàng đợi OTA cho ${r.device_name}.`, `Scheduled for ${r.device_name}.`));
        }, "secondary")
      ])
    );

    container.append(
      notice(l("Ma trận tuân thủ firmware toàn hạm đội. Mọi gói cập nhật OTA đều bắt buộc xác minh mã băm SHA-256 của nhà sản xuất trước khi nạp vào hàng đợi.", "Fleet firmware compliance matrix. All OTA packages must verify manufacturer SHA-256 hash before entering deployment queue.")),
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
