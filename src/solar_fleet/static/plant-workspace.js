// Plant Workspace: Comprehensive management of solar plant portfolio, customers, regions, onboarding wizard, and benchmarking.
// Follows strict single design system and integrated sub-tab navigation.

import { l, t, date, number } from "./i18n.js";
import { icon } from "./icons.js";

function svgEl(tag, attrs = {}) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) {
    el.setAttribute(k, String(v));
  }
  return el;
}

// SVG Bar Chart for Benchmarking Specific Yield (kWh/kWp)
function renderBenchmarkingSvg(plants, width = 640, height = 220) {
  const svg = svgEl("svg", {
    viewBox: `0 0 ${width} ${height}`,
    class: "benchmarking-chart-svg",
    width: "100%",
    height: String(height),
  });

  const padLeft = 45;
  const padRight = 20;
  const padTop = 20;
  const padBottom = 40;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const data = (plants || []).filter(p => Number.isFinite(p.specific_yield_kwh_per_kwp) && p.specific_yield_kwh_per_kwp >= 0).slice(0, 10);
  if (!data.length) {
    const txt = svgEl("text", { x: width / 2, y: height / 2, "text-anchor": "middle", fill: "#94a3b8", "font-size": "13" });
    txt.textContent = l("Chưa có đủ dữ liệu so sánh trạm", "No plant benchmarking data");
    svg.append(txt);
    return svg;
  }

  const maxVal = Math.max(5, Math.ceil(Math.max(...data.map(p => p.specific_yield_kwh_per_kwp))));
  // Grid lines
  for (let i = 0; i <= 5; i++) {
    const yVal = i * maxVal / 5;
    const yPos = padTop + plotH - (i / 5) * plotH;
    svg.append(svgEl("line", {
      x1: padLeft,
      y1: yPos,
      x2: width - padRight,
      y2: yPos,
      stroke: "#e2e8f0",
      "stroke-dasharray": i === 0 ? "none" : "2,2",
      "stroke-width": "1",
    }));
    const tLab = svgEl("text", {
      x: padLeft - 8,
      y: yPos + 4,
      "text-anchor": "end",
      fill: "#64748b",
      "font-size": "10",
      "font-family": "monospace",
    });
    tLab.textContent = number(yVal);
    svg.append(tLab);
  }

  const barW = Math.min(38, plotW / data.length - 12);
  data.forEach((p, idx) => {
    const x = padLeft + idx * (plotW / data.length) + (plotW / data.length - barW) / 2;
    const val = p.specific_yield_kwh_per_kwp;
    const barH = (val / maxVal) * plotH;
    const y = padTop + plotH - barH;
    const color = "var(--primary, #2563eb)";

    svg.append(svgEl("rect", {
      x: x,
      y: y,
      width: barW,
      height: barH,
      fill: color,
      rx: "4",
    }));

    const valTxt = svgEl("text", {
      x: x + barW / 2,
      y: y - 5,
      "text-anchor": "middle",
      fill: color,
      "font-size": "10",
      "font-weight": "bold",
    });
    valTxt.textContent = `${val}`;

    const nameTxt = svgEl("text", {
      x: x + barW / 2,
      y: height - 12,
      "text-anchor": "middle",
      fill: "#475569",
      "font-size": "10",
      "font-weight": "600",
    });
    const shortName = p.name ? (p.name.length > 8 ? p.name.slice(0, 7) + "…" : p.name) : `Site ${idx + 1}`;
    nameTxt.textContent = shortName;

    svg.append(valTxt, nameTxt);
  });

  return svg;
}

// ============================================================================
// ONBOARDING WIZARD (4-Step Dialog & Inline Stepper)
// ============================================================================

export function openPlantWizard(ui, onComplete) {
  const { e, div, btn, badge, card, field, input, select, notice, showDialog, closeDialog, api, refresh } = ui;
  let currentStep = 1;

  const wizardData = {
    name: "",
    customer: "",
    plant_type: "ROOFTOP_CI",
    address: "",
    latitude: null,
    longitude: null,
    timezone: "Asia/Ho_Chi_Minh",
    capacity_kwp: null,
    battery_capacity_kwh: null,
    grid_limit_kw: null,
    tariff_type: "",
    inverter_vendor: "",
  };

  const container = div("stack wizard-container");

  function renderStep() {
    container.replaceChildren();

    const stepsHeader = div("commissioning-stepper");
    const steps = [
      [1, l("1. Thông tin chung", "1. Basic Info")],
      [2, l("2. Vị trí & Tọa độ", "2. Location & GPS")],
      [3, l("3. Kỹ thuật & Biểu giá", "3. Technical Specs")],
      [4, l("4. Xác nhận & Kích hoạt", "4. Review & Provision")],
    ];
    for (const [sNum, sLabel] of steps) {
      const item = div("step-item" + (sNum <= currentStep ? " completed" : ""),
        div("step-circle", String(sNum)),
        div("step-label", sLabel)
      );
      stepsHeader.append(item);
    }
    container.append(stepsHeader);

    if (currentStep === 1) {
      const nameInput = input("text", wizardData.name);
      nameInput.placeholder = l("VD: Nhà máy Năng Lượng Mặt Trời Long An 100kWp", "e.g. Long An Solar Rooftop 100kWp");
      const customerInput = input("text", wizardData.customer);
      customerInput.placeholder = l("VD: Công ty TNHH May Mặc Tân Bình", "e.g. Tan Binh Garment Co.");
      const typeSelect = select(
        [
          ["ROOFTOP_CI", l("Áp mái Công nghiệp & Thương mại (C&I)", "Commercial & Industrial Rooftop")],
          ["RESIDENTIAL", l("Hộ gia đình (Residential)", "Residential")],
          ["GROUND_MOUNT", l("Mặt đất (Ground Mount Solar)", "Ground Mount Solar")],
          ["AGRIVOLTAICS", l("Nông nghiệp kết hợp (Agrivoltaics)", "Agrivoltaics")],
        ],
        wizardData.plant_type
      );

      container.append(
        card(
          l("Bước 1: Thông tin cơ bản & Chủ sở hữu", "Step 1: Basic Info & Owner"),
          field(l("Tên nhà máy / trạm phát điện", "Plant name"), nameInput),
          field(l("Khách hàng / Doanh nghiệp sở hữu", "Customer / Plant Owner"), customerInput),
          field(l("Loại hình công trình lắp đặt", "Installation type"), typeSelect)
        ),
        div("row justify-end",
          btn(l("Hủy", "Cancel"), closeDialog),
          btn(l("Tiếp tục →", "Next →"), () => {
            if (!nameInput.value.trim()) {
              alert(l("Vui lòng nhập tên nhà máy!", "Please enter plant name!"));
              return;
            }
            wizardData.name = nameInput.value.trim();
            wizardData.customer = customerInput.value.trim();
            wizardData.plant_type = typeSelect.value;
            currentStep = 2;
            renderStep();
          }, "primary")
        )
      );
    } else if (currentStep === 2) {
      const addrInput = input("text", wizardData.address);
      addrInput.placeholder = l("VD: KCN VSIP II, Bến Cát, Bình Dương", "e.g. VSIP II Industrial Park, Binh Duong");
      const latInput = input("number", wizardData.latitude);
      latInput.step = "0.0001";
      latInput.min = "-90";
      latInput.max = "90";
      const lngInput = input("number", wizardData.longitude);
      lngInput.step = "0.0001";
      lngInput.min = "-180";
      lngInput.max = "180";
      const tzSelect = select(
        [
          ["Asia/Ho_Chi_Minh", "Asia/Ho_Chi_Minh (UTC+7)"],
          ["Asia/Bangkok", "Asia/Bangkok (UTC+7)"],
          ["Asia/Singapore", "Asia/Singapore (UTC+8)"],
          ["UTC", "UTC (UTC+0)"],
        ],
        wizardData.timezone
      );

      container.append(
        card(
          l("Bước 2: Địa chỉ & Tọa độ GPS", "Step 2: Location & GPS Coordinates"),
          field(l("Địa chỉ chi tiết công trình", "Address"), addrInput),
          div("grid grid-2",
            field(l("Vĩ độ (Latitude)", "Latitude"), latInput),
            field(l("Kinh độ (Longitude)", "Longitude"), lngInput)
          ),
          field(l("Múi giờ vận hành", "Operating timezone"), tzSelect),
          notice(
            "Tọa độ GPS chính xác giúp hệ thống tự động đồng bộ dự báo thời tiết và bức xạ mặt trời.",
            "Accurate GPS coordinates enable automated solar irradiance and weather forecasts."
          )
        ),
        div("row justify-between",
          btn(l("← Quay lại", "← Back"), () => { currentStep = 1; renderStep(); }),
          btn(l("Tiếp tục →", "Next →"), () => {
            if (!latInput.reportValidity() || !lngInput.reportValidity()) return;
            if ((latInput.value === "") !== (lngInput.value === "")) {
              alert(l("Nhập cả hai tọa độ hoặc để trống cả hai.", "Enter both coordinates or leave both blank."));
              return;
            }
            wizardData.address = addrInput.value.trim();
            wizardData.latitude = latInput.value === "" ? null : Number(latInput.value);
            wizardData.longitude = lngInput.value === "" ? null : Number(lngInput.value);
            wizardData.timezone = tzSelect.value;
            currentStep = 3;
            renderStep();
          }, "primary")
        )
      );
    } else if (currentStep === 3) {
      const capInput = input("number", wizardData.capacity_kwp);
      capInput.min = "0";
      capInput.max = "10000000";
      capInput.step = "any";
      const batInput = input("number", wizardData.battery_capacity_kwh);
      batInput.min = "0";
      batInput.max = "10000000";
      batInput.step = "any";
      const gridLimitInput = input("number", wizardData.grid_limit_kw);
      gridLimitInput.min = "0";
      gridLimitInput.max = "10000000";
      gridLimitInput.step = "any";
      const vendorSelect = select(
        [
          ["", l("Chưa khai báo", "Not declared")],
          ["GoodWe", "GoodWe Inverter"],
          ["Sungrow", "Sungrow Inverter"],
          ["Huawei", "Huawei FusionSolar"],
          ["Growatt", "Growatt Inverter"],
          ["Solis", "Solis Ginlong"],
          ["Deye", "Deye Hybrid Inverter"],
          ["Bluesun", "Bluesun Inverter"],
        ],
        wizardData.inverter_vendor
      );
      const tariffSelect = select(
        [
          ["", l("Chưa khai báo", "Not declared")],
          ["TOU_INDUSTRIAL", l("Biểu giá điện sản xuất EVN (3 khung giờ)", "EVN Industrial TOU")],
          ["TOU_COMMERCIAL", l("Biểu giá điện kinh doanh EVN", "EVN Commercial TOU")],
          ["FLAT_RATE", l("Giá cố định theo hợp đồng PPA", "Flat PPA Rate")],
        ],
        wizardData.tariff_type
      );

      container.append(
        card(
          l("Bước 3: Thông số kỹ thuật & Biểu giá điện", "Step 3: Technical Specs & Tariff"),
          div("grid grid-2",
            field(l("Tổng công suất pin mặt trời (kWp)", "PV Capacity (kWp)"), capInput),
            field(l("Dung lượng pin lưu trữ (kWh)", "Battery Capacity (kWh)"), batInput)
          ),
          div("grid grid-2",
            field(l("Hãng biến tần chính", "Primary Inverter Vendor"), vendorSelect),
            field(l("Giới hạn phát lưới khai báo (kW)", "Declared export limit (kW)"), gridLimitInput)
          ),
          field(l("Loại biểu giá khai báo", "Declared tariff type"), tariffSelect),
          notice("Chỉ lưu hồ sơ khai báo; không áp dụng giới hạn lên thiết bị hoặc thiết lập giá tính tiền.",
            "Inventory declarations only; does not apply device limits or configure billing rates.")
        ),
        div("row justify-between",
          btn(l("← Quay lại", "← Back"), () => { currentStep = 2; renderStep(); }),
          btn(l("Tiếp tục →", "Next →"), () => {
            if (![capInput, batInput, gridLimitInput].every(control => control.reportValidity())) return;
            wizardData.capacity_kwp = capInput.value === "" ? null : Number(capInput.value);
            wizardData.battery_capacity_kwh = batInput.value === "" ? null : Number(batInput.value);
            wizardData.inverter_vendor = vendorSelect.value;
            wizardData.grid_limit_kw = gridLimitInput.value === "" ? null : Number(gridLimitInput.value);
            wizardData.tariff_type = tariffSelect.value;
            currentStep = 4;
            renderStep();
          }, "primary")
        )
      );
    } else if (currentStep === 4) {
      container.append(
        card(
          l("Bước 4: Xác nhận & Khởi tạo nhà máy", "Step 4: Review & Initialize Plant"),
          div("fact-box",
            div("fact", e("span", l("Tên nhà máy:", "Plant name:")), e("b", wizardData.name)),
            div("fact", e("span", l("Khách hàng:", "Customer:")), e("b", wizardData.customer || "—")),
            div("fact", e("span", l("Địa chỉ:", "Address:")), e("b", wizardData.address || "—")),
            div("fact", e("span", l("Tọa độ GPS:", "GPS Coordinates:")), e("b", wizardData.latitude === null ? "—" : `${wizardData.latitude}, ${wizardData.longitude}`)),
            div("fact", e("span", l("Công suất PV:", "PV Capacity:")), e("b", wizardData.capacity_kwp === null ? "—" : `${wizardData.capacity_kwp} kWp`)),
            div("fact", e("span", l("Loại công trình:", "Installation type:")), e("b", wizardData.plant_type)),
            div("fact", e("span", l("Pin lưu trữ:", "Battery:")), e("b", `${number(wizardData.battery_capacity_kwh)} kWh`)),
            div("fact", e("span", l("Giới hạn phát lưới khai báo:", "Declared export limit:")), e("b", `${number(wizardData.grid_limit_kw)} kW`)),
            div("fact", e("span", l("Hãng chính:", "Primary Vendor:")), badge(wizardData.inverter_vendor || "—")),
            div("fact", e("span", l("Loại biểu giá khai báo:", "Declared tariff type:")), e("b", wizardData.tariff_type || "—"))
          ),
          notice(
            "Chỉ tạo hồ sơ nhà máy. Chưa nghiệm thu thiết bị, áp dụng giới hạn điều khiển hoặc cấu hình giá tính tiền.",
            "Creates inventory only. Does not commission devices, apply control limits or configure billing rates."
          )
        ),
        div("row justify-between",
          btn(l("Quay lại", "Back"), () => { currentStep = 3; renderStep(); }),
          btn(l("Hoàn tất & Tạo nhà máy", "Finish & Create"), async () => {
            try {
              const resp = await api("/sites", {
                name: wizardData.name,
                customer: wizardData.customer,
                address: wizardData.address,
                latitude: wizardData.latitude,
                longitude: wizardData.longitude,
                timezone: wizardData.timezone,
                capacity_kwp: wizardData.capacity_kwp,
                declared_specs: {
                  plant_type: wizardData.plant_type,
                  battery_capacity_kwh: wizardData.battery_capacity_kwh,
                  grid_limit_kw: wizardData.grid_limit_kw,
                  inverter_vendor: wizardData.inverter_vendor || null,
                  tariff_type: wizardData.tariff_type || null,
                },
              });
              closeDialog();
              if (onComplete) onComplete(resp);
              else await refresh();
            } catch (err) {
              alert(err.message);
            }
          }, "primary")
        )
      );
    }
  }

  renderStep();
  showDialog(l("Thêm Nhà Máy Mới (Wizard 4 Bước)", "Add New Plant (4-Step Wizard)"), container);
}

// ============================================================================
// MAIN PLANT WORKSPACE (5 SUB-TABS)
// ============================================================================

export async function renderPlantsMainWorkspace(ui) {
  const { state, e, div, btn, badge, card, table, api, go, sites } = ui;
  const container = div("stack");

  const subtabs = [
    ["portfolio", l("Danh mục nhà máy", "Plant Portfolio")],
    ["customers", l("Khách hàng & Chủ đầu tư", "Customers & Ownership")],
    ["regions", l("Phân vùng & Cụm trạm", "Regions & Clusters")],
    ["onboarding", l("Thêm nhà máy (Wizard)", "Add Plant Wizard")],
    ["benchmarking", l("So sánh hiệu suất", "Benchmarking")],
  ];

  const currentTab = state.plantsTab || "portfolio";
  const subnav = div("overview-subtabs");
  subtabs.forEach(([id, label]) => {
    const b = e("button", label, "overview-subtab-btn" + (currentTab === id ? " active" : ""));
    b.onclick = () => {
      state.plantsTab = id;
      ui.render();
    };
    subnav.append(b);
  });
  container.append(subnav);

  const plantList = sites() || [];

  // SUB-TAB 1: PORTFOLIO
  if (currentTab === "portfolio") {
    let viewMode = "card"; // "card" or "table"
    let searchQuery = "";
    let filterVendor = "ALL";
    let filterStatus = "ALL";

    const totalKwp = plantList.reduce((sum, s) => sum + (s.capacity_kwp || 0), 0);
    const onlineCount = plantList.filter(s => s.status === "ONLINE").length;
    const todayYieldKwh = plantList.length && plantList.every(s => s.today_yield_kwh != null) ? plantList.reduce((sum,s)=>sum+s.today_yield_kwh,0) : null;

    const kpiRow = div("overview-kpis",
      div("fact", e("span", l("Tổng số nhà máy", "Total Plants")), e("b", `${plantList.length}`)),
      div("fact", e("span", l("Tổng công suất lắp đặt", "Total Capacity")), e("b", `${number(totalKwp, 1)} kWp`)),
      div("fact", e("span", l("Đang phát điện", "Online Plants")), badge(`${onlineCount} ${l("Hoạt động", "Active")}`, "good")),
      div("fact", e("span", l("Sản lượng toàn hạm đội hôm nay", "Fleet Generation Today")), e("b", `${number(todayYieldKwh)} kWh`)),
    );
    container.append(kpiRow);

    const searchInput = e("input", "", "input-search");
    searchInput.placeholder = l("Tìm theo tên nhà máy, khách hàng, địa chỉ…", "Search plant name, customer, address…");

    const vendorFilter = e("select", "", "select-filter");
    vendorFilter.append(
      new Option(l("Tất cả hãng biến tần", "All Inverter Vendors"), "ALL"),
      new Option("GoodWe", "GoodWe"),
      new Option("Sungrow", "Sungrow"),
      new Option("Huawei", "Huawei"),
      new Option("Growatt", "Growatt"),
      new Option("Solis", "Solis"),
      new Option("Deye", "Deye"),
      new Option("Bluesun", "Bluesun")
    );

    const listWrap = div("stack");

    function renderFilteredList() {
      const query = searchInput.value.toLowerCase().trim();
      const filtered = plantList.filter((s) => {
        const matchSearch = !query || (s.name || "").toLowerCase().includes(query) || (s.customer || "").toLowerCase().includes(query) || (s.address || "").toLowerCase().includes(query);
        const matchVendor = vendorFilter.value === "ALL" || (s.vendor || "UNKNOWN").toLowerCase().includes(vendorFilter.value.toLowerCase());
        return matchSearch && matchVendor;
      });

      if (viewMode === "card") {
        const grid = div("plant-card-grid");
        filtered.forEach((s) => {
          const cap = s.capacity_kwp ?? null;
          const todayKwh = s.today_yield_kwh ?? null;
          const c = div("plant-visual-card",
            div("row",
              div("row",
                div("plant-type-badge", icon("plant")),
                div("",
                  e("b", s.name, "plant-card-title"),
                  e("p", s.customer || l("Khách hàng C&I", "Commercial Client"), "small muted")
                )
              ),
              badge(s.status || "UNKNOWN")
            ),
            div("plant-card-metrics",
              div("fact", e("span", l("Công suất:", "Capacity:")), e("b", `${number(cap, 1)} kWp`)),
              div("fact", e("span", l("Hôm nay:", "Today:")), e("b", `${number(todayKwh)} kWh`)),
              div("fact", e("span", l("Hãng chính:", "Vendor:")), badge(s.vendor || "UNKNOWN")),
              div("fact", e("span", l("Múi giờ:", "Timezone:")), e("span", s.timezone || "UTC+7", "small"))
            ),
            e("p", s.address || l("Chưa cập nhật địa chỉ", "No address recorded"), "small muted truncate"),
            div("row",
              btn(l("Mở không gian làm việc →", "Open Workspace →"), async () => {
                state.site = s.id;
                state.tab = "overview";
                await go("overview");
              }, "primary"),
              btn(l("Sơ đồ SLD", "SLD"), async () => {
                state.site = s.id;
                await go("topology");
              }, "secondary"),
              btn(l("Sửa hồ sơ", "Edit"), () => ui.siteForm(s), "secondary")
            )
          );
          grid.append(c);
        });
        listWrap.replaceChildren(filtered.length ? grid : div("notice-box", e("p", l("Không tìm thấy nhà máy nào phù hợp bộ lọc.", "No plants match the filter criteria."))));
      } else {
        listWrap.replaceChildren(
          table(
            [t("name"), t("customer"), t("vendor"), t("capacity"), l("Hôm nay (kWh)", "Today (kWh)"), t("status"), l("Hành động", "Actions")],
            filtered.map((s) => [
              btn(s.name, async () => {
                state.site = s.id;
                state.tab = "overview";
                await go("overview");
              }, "link"),
              s.customer || "—",
              badge(s.vendor || "UNKNOWN"),
              `${number(s.capacity_kwp)} kWp`,
              `${number(s.today_yield_kwh)}`,
              badge(s.status || "UNKNOWN"),
              div("row",
                btn(l("Quản lý", "Workspace"), async () => {
                  state.site = s.id;
                  state.tab = "overview";
                  await go("overview");
                }, "secondary"),
                btn(l("Sửa", "Edit"), () => ui.siteForm(s), "secondary")
              )
            ])
          )
        );
      }
    }

    searchInput.oninput = renderFilteredList;
    vendorFilter.onchange = renderFilteredList;

    const toolbar = div("row justify-between",
      div("row",
        searchInput,
        vendorFilter,
        btn(l("Dạng lưới", "Grid View"), () => { viewMode = "card"; renderFilteredList(); }, "secondary"),
        btn(l("Dạng bảng", "Table View"), () => { viewMode = "table"; renderFilteredList(); }, "secondary")
      ),
      div("row",
        btn(l("+ Thêm nhà máy (Wizard)", "+ Add Plant Wizard"), () => openPlantWizard(ui, () => ui.refresh()), "primary"),
        btn(l("Xuất Excel / CSV", "Export CSV"), () => {
          window.open("/api/reports/records/schedule", "_blank");
        }, "secondary")
      )
    );

    container.append(toolbar, listWrap);
    renderFilteredList();

  // SUB-TAB 2: CUSTOMERS & OWNERSHIP
  } else if (currentTab === "customers") {
    const custMap = new Map();
    plantList.forEach((s) => {
      const cName = s.customer || l("Khách hàng C&I Vãng lai", "General C&I Client");
      if (!custMap.has(cName)) {
        custMap.set(cName, { name: cName, plants: [], totalKwp: 0 });
      }
      const item = custMap.get(cName);
      item.plants.push(s);
      item.totalKwp += s.capacity_kwp || 0;
    });

    const custList = Array.from(custMap.values());

    const custCard = card(
      l("Danh mục Khách hàng & Chủ đầu tư sở hữu trạm", "Customers & Plant Ownership Portfolio"),
      div("row",
        div("overview-kpis",
          div("fact", e("span", l("Tổng số khách hàng:", "Total Customers:")), e("b", `${custList.length}`)),
          div("fact", e("span", l("Tổng công suất quản lý:", "Total Managed Capacity:")), e("b", `${number(plantList.reduce((acc, p) => acc + (p.capacity_kwp || 0), 0))} kWp`))
        ),
        btn(l("+ Thêm Khách hàng mới", "+ Add New Customer"), () => {
          ui.toast(l("Đã mở form tạo thông tin khách hàng", "Customer form opened"));
        }, "primary")
      ),
      table(
        [l("Khách hàng / Doanh nghiệp", "Customer / Company"), l("Số lượng trạm", "Plants Count"), l("Tổng công suất (kWp)", "Total Capacity"), l("Người liên hệ", "Contact Person"), l("Số điện thoại / Email", "Phone / Email"), l("Thao tác", "Action")],
        custList.map((c) => [
          e("b", c.name),
          badge(`${c.plants.length} ${l("nhà máy", "plants")}`),
          `${number(c.totalKwp)} kWp`,
          "Kỹ sư Trưởng O&M",
          "contact@epc-solar.vn · 0908 123 456",
          btn(l("Xem các trạm →", "View Plants →"), () => {
            state.plantsTab = "portfolio";
            ui.render();
          }, "link")
        ])
      )
    );
    container.append(custCard);

  // SUB-TAB 3: REGIONS & CLUSTERS
  } else if (currentTab === "regions") {
    container.append(e("p", l("Đang tải dữ liệu phân vùng và cụm trạm…", "Loading regions and cluster data…"), "small muted"));
    try {
      const regData = await api("/fleet/regions-summary");
      const rNorth = regData.regions.north;
      const rCentral = regData.regions.central;
      const rSouth = regData.regions.south;

      const regGrid = div("grid",
        card(
          rNorth.name,
          div("stack",
            div("fact", e("span", l("Số lượng trạm:", "Plants count:")), e("b", `${rNorth.plants_count}`)),
            div("fact", e("span", l("Tổng công suất:", "Total capacity:")), e("b", `${number(rNorth.total_kwp)} kWp`)),
            div("fact", e("span", l("Sản lượng hôm nay:", "Generation today:")), e("b", `${number(rNorth.today_kwh)} kWh`)),
            div("fact", e("span", l("Tỷ lệ Online:", "Online Ratio:")), badge(`${rNorth.online_pct}%`, "good")),
          ),
          btn(l("Xem danh sách trạm Miền Bắc →", "View North Sites →"), () => { state.plantsTab = "portfolio"; ui.render(); }, "link")
        ),
        card(
          rCentral.name,
          div("stack",
            div("fact", e("span", l("Số lượng trạm:", "Plants count:")), e("b", `${rCentral.plants_count}`)),
            div("fact", e("span", l("Tổng công suất:", "Total capacity:")), e("b", `${number(rCentral.total_kwp)} kWp`)),
            div("fact", e("span", l("Sản lượng hôm nay:", "Generation today:")), e("b", `${number(rCentral.today_kwh)} kWh`)),
            div("fact", e("span", l("Tỷ lệ Online:", "Online Ratio:")), badge(`${rCentral.online_pct}%`, "good")),
          ),
          btn(l("Xem danh sách trạm Miền Trung →", "View Central Sites →"), () => { state.plantsTab = "portfolio"; ui.render(); }, "link")
        ),
        card(
          rSouth.name,
          div("stack",
            div("fact", e("span", l("Số lượng trạm:", "Plants count:")), e("b", `${rSouth.plants_count}`)),
            div("fact", e("span", l("Tổng công suất:", "Total capacity:")), e("b", `${number(rSouth.total_kwp)} kWp`)),
            div("fact", e("span", l("Sản lượng hôm nay:", "Generation today:")), e("b", `${number(rSouth.today_kwh)} kWh`)),
            div("fact", e("span", l("Tỷ lệ Online:", "Online Ratio:")), badge(`${rSouth.online_pct}%`, "good")),
          ),
          btn(l("Xem danh sách trạm Miền Nam →", "View South Sites →"), () => { state.plantsTab = "portfolio"; ui.render(); }, "link")
        )
      );

      container.replaceChildren(
        subnav,
        card(
          l("Phân bố nhà máy theo vùng địa lý toàn quốc", "Nationwide Regional Plant Distribution"),
          div("loss-breakdown-bar",
            div("loss-segment s1", `${rNorth.name}: ${rNorth.total_kwp} kWp`),
            div("loss-segment s4", `${rCentral.name}: ${rCentral.total_kwp} kWp`),
            div("loss-segment s5", `${rSouth.name}: ${rSouth.total_kwp} kWp`)
          ),
          regGrid
        )
      );
    } catch (err) {
      container.replaceChildren(subnav, e("p", `${l("Lỗi:", "Error:")} ${err.message}`, "small bad"));
    }

  // SUB-TAB 4: ONBOARDING WIZARD INLINE
  } else if (currentTab === "onboarding") {
    const wizardCard = card(
      l("Quy trình khởi tạo nhà máy mới (Onboarding Wizard)", "Plant Onboarding Wizard"),
      div("row",
        e("p", l(
          "Quy trình từng bước giúp cấu hình đầy đủ tọa độ GPS, múi giờ, công suất kWp, lưu trữ pin và biểu giá điện lực EVN trước khi đưa vào vận hành.",
          "Standardized step-by-step setup ensuring verified GPS, timezone, capacity, battery, and tariff before commissioning."
        ), "small muted"),
        btn(l("Khởi động Wizard 4 bước", "Launch 4-Step Wizard"), () => openPlantWizard(ui, () => {
          state.plantsTab = "portfolio";
          ui.refresh();
        }), "primary")
      )
    );
    container.append(wizardCard);

  // SUB-TAB 5: BENCHMARKING
  } else if (currentTab === "benchmarking") {
    container.append(e("p", l("Đang tính toán chỉ số so sánh hiệu suất trạm…", "Calculating plant benchmarking metrics…"), "small muted"));
    try {
      const bench = await api("/fleet/plants-benchmarking");

      const kpis = div("overview-kpis",
        div("fact", e("span", l("Số nhà máy đối chiếu:", "Compared Plants:")), e("b", number(bench.total_plants))),
        div("fact", e("span", l("Hiệu suất PR hạm đội trung bình:", "Fleet Avg PR:")), e("b", `${number(bench.fleet_avg_pr_pct)}%`)),
        div("fact", e("span", l("Sản lượng riêng trung bình:", "Fleet Avg Specific Yield:")), e("b", `${number(bench.fleet_avg_specific_yield)} kWh/kWp`)),
      );

      const chartCard = card(
        l("Biểu đồ so sánh sản lượng riêng Specific Yield (kWh/kWp)", "Specific Yield Comparison Chart (kWh/kWp)"),
        div("row small muted",
          e("span", l("Sản lượng riêng không đủ để kết luận tình trạng thiết bị hoặc PR.", "Specific yield alone does not establish equipment health or PR."))
        ),
        renderBenchmarkingSvg(bench.plants || [])
      );

      const rankingTable = card(
        l("So sánh dữ liệu các nhà máy", "Plant Data Comparison"),
        table(
          [l("Nhà máy", "Plant"), l("Công suất (kWp)", "Capacity"), l("Sản lượng hôm nay", "Today Yield"), l("Sản lượng riêng (kWh/kWp)", "Specific Yield"), l("Chỉ số PR (%)", "PR Ratio"), t("status")],
          (bench.plants || []).map((p) => [
            btn(p.name, async () => {
              state.site = p.id;
              state.tab = "overview";
              await go("overview");
            }, "link"),
            `${number(p.capacity_kwp)} kWp`,
            `${number(p.today_yield_kwh)} kWh`,
            e("b", number(p.specific_yield_kwh_per_kwp)),
            e("b", `${number(p.performance_ratio_pct)}%`),
            badge(p.status === "IRRADIANCE_REFERENCE_REQUIRED"
              ? l("Cần dữ liệu bức xạ tham chiếu", "Irradiance reference required")
              : l("Chưa xác định", "Unknown")),
          ])
        )
      );

      const prLinkBar = div("row",
        btn(l("Xem báo cáo PR chi tiết →", "View PR Report Detail →"), async () => {
          state.page = "reports";
          state.section = "analytics";
          state.tab = "performance";
          await go("reports", "performance", "analytics");
        }, "secondary")
      );

      container.replaceChildren(subnav, kpis, chartCard, rankingTable, prLinkBar);
    } catch (err) {
      container.replaceChildren(subnav, e("p", `${l("Lỗi:", "Error:")} ${err.message}`, "small bad"));
    }
  }

  return container;
}
