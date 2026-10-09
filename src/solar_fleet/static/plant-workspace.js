// Plant Workspace: Comprehensive management of solar plant portfolio, customers, regions, onboarding wizard, and benchmarking.
// Follows strict single design system and integrated sub-tab navigation.

import { l, t, date, number } from "./i18n.js";
import { icon } from "./icons.js";
import { plantMedia, plantIllustrations } from "./plant-media.js";
import { metricTiles } from './ui-visuals.js';

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


function renderStatusDonutSvg(segments, centerLabel, centerSub) {
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const total = segments.reduce((sum, s) => sum + s.value, 0) || 1;

  const svg = svgEl("svg", {
    viewBox: "0 0 110 110",
    width: "110",
    height: "110",
  });

  svg.append(svgEl("circle", {
    cx: "55",
    cy: "55",
    r: String(radius),
    fill: "none",
    stroke: "#f1f5f9",
    "stroke-width": "12",
  }));

  let accumulated = 0;
  segments.forEach((seg) => {
    if (!seg.value) return;
    const strokeDash = (seg.value / total) * circumference;
    const strokeOffset = -((accumulated / total) * circumference);
    const circle = svgEl("circle", {
      cx: "55",
      cy: "55",
      r: String(radius),
      fill: "none",
      stroke: seg.color,
      "stroke-width": "12",
      "stroke-dasharray": `${strokeDash} ${circumference - strokeDash}`,
      "stroke-dashoffset": String(strokeOffset),
      transform: "rotate(-90 55 55)",
      "stroke-linecap": "round",
    });
    accumulated += seg.value;
    svg.append(circle);
  });

  const txt1 = svgEl("text", {
    x: "55",
    y: "53",
    "text-anchor": "middle",
    fill: "#0f172a",
    "font-size": "15",
    "font-weight": "bold",
  });
  txt1.textContent = centerLabel;

  const txt2 = svgEl("text", {
    x: "55",
    y: "67",
    "text-anchor": "middle",
    fill: "#64748b",
    "font-size": "9",
  });
  txt2.textContent = centerSub;

  svg.append(txt1, txt2);
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
    plant_type: "",
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
      [4, l("4. Kiểm tra & Lưu", "4. Review & Save")],
    ];
    for (const [sNum, sLabel] of steps) {
      const item = div("step-item" + (sNum < currentStep ? " completed" : sNum === currentStep ? " current" : ""),
        div("step-circle", String(sNum)),
        div("step-label", sLabel)
      );
      if (sNum === currentStep) item.setAttribute("aria-current", "step");
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
          ["", l("Chưa xác định", "Not specified")],
          ["ROOFTOP_CI", l("Áp mái Công nghiệp & Thương mại (C&I)", "Commercial & Industrial Rooftop")],
          ["RESIDENTIAL", l("Hộ gia đình (Residential)", "Residential")],
          ["GROUND_MOUNT", l("Mặt đất (Ground Mount Solar)", "Ground Mount Solar")],
          ["AGRIVOLTAICS", l("Nông nghiệp kết hợp (Agrivoltaics)", "Agrivoltaics")],
        ],
        wizardData.plant_type
      );
      const choices = div("plant-type-choices");
      function updateChoices() {
        for (const button of choices.children) button.setAttribute("aria-pressed", String(button.dataset.kind === typeSelect.value));
      }
      for (const [kind, asset] of Object.entries(plantIllustrations)) {
        const choice = btn("", () => { typeSelect.value = kind; updateChoices(); }, "plant-type-choice");
        choice.dataset.kind = kind;
        choice.append(plantMedia(ui, {plant_type:kind}),e("b",asset.label()));
        choice.setAttribute("aria-label",asset.label());
        choices.append(choice);
      }
      typeSelect.onchange = updateChoices; updateChoices();

      container.append(
        card(
          l("Bước 1: Thông tin cơ bản & Chủ sở hữu", "Step 1: Basic Info & Owner"),
          field(l("Tên nhà máy / trạm phát điện", "Plant name"), nameInput),
          field(l("Khách hàng / Doanh nghiệp sở hữu", "Customer / Plant Owner"), customerInput),
          field(l("Loại hình công trình lắp đặt", "Installation type"), typeSelect),
          choices
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
            div("fact", e("span", l("Loại công trình:", "Installation type:")), e("b", plantIllustrations[wizardData.plant_type]?.label() || (wizardData.plant_type === 'AGRIVOLTAICS' ? l('Nông nghiệp kết hợp','Agrivoltaics') : '—'))),
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
                  plant_type: wizardData.plant_type || null,
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
  showDialog(l("Thêm nhà máy · 4 bước", "Add plant · 4 steps"), container);
}

// ============================================================================
// 1-CLICK CLOUD ONBOARDING WIZARD (Non-technical user friendly)
// ============================================================================

export function openCloudOnboardingModal(ui) {
  // A single real account workflow; never pretend that a form authenticates.
  ui.go("settings", "connections");
}

// ============================================================================
// MAIN PLANT WORKSPACE (5 SUB-TABS)
// ============================================================================

export async function renderPlantsMainWorkspace(ui) {
  const { state, e, div, btn, badge, card, table, api, go, sites, select } = ui;
  const container = div("stack");

  const subtabs = [
    ["portfolio", l("Danh mục nhà máy", "Plant Portfolio")],
    ["customers", l("Khách hàng & Chủ đầu tư", "Customers & Ownership")],
    ["regions", l("Phân vùng & Cụm trạm", "Regions & Clusters")],
    ["onboarding", l("Thêm nhà máy", "Add plant")],
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

  // Detailed SolarOne portfolio reference; the simple collage is not a style target.
  if (currentTab === "portfolio") {
    const actions = div("form-actions",
      btn(l("Kết nối tài khoản hãng", "Connect vendor account"), () => openCloudOnboardingModal(ui)),
      ui.admin() ? btn(l("+ Thêm nhà máy", "+ Add plant"), () => openPlantWizard(ui, () => ui.refresh()), "primary") : null);
    const capacities = plantList.map(s => s.capacity_kwp).filter(v => v != null);
    container.append(metricTiles(ui,[['plant',l('Nhà máy đã lưu','Saved plants'),plantList.length],
      ['bolt',l('Công suất đã khai báo','Declared capacity'),capacities.length?capacities.reduce((a,b)=>a+b,0):null,'kWp','purple',capacities.length+' / '+plantList.length+' '+l('nhà máy có khai báo','plants with capacity')],
      ['device',l('Thiết bị đã liên kết','Linked equipment'),(state.fleet.devices||[]).filter(d=>!state.site||d.site_id===state.site).length,'','green']]));
    const query = ui.input("search");
    query.placeholder = l("Tìm tên, chủ sở hữu hoặc địa chỉ…","Search name, owner or address…");
    query.setAttribute("aria-label",query.placeholder);
    const vendors = [...new Set(plantList.map(s=>s.vendor).filter(Boolean))].sort();
    const vendor = select([["",l("Tất cả hãng","All vendors")],...vendors.map(v=>[v,v])]);
    vendor.setAttribute("aria-label",l("Hãng","Vendor"));
    const results = div("stack");
    function update() {
      const term = query.value.trim().toLocaleLowerCase();
      const visible = plantList.filter(s=>(!vendor.value||s.vendor===vendor.value)&&[s.name,s.customer,s.address].join(" ").toLocaleLowerCase().includes(term));
      results.replaceChildren(table(
        [l("Nhà máy","Plant"),l("Chủ sở hữu","Owner"),l("Hãng","Vendor"),l("Công suất","Capacity"),l("Địa chỉ","Address"),l("Thiết bị","Equipment")],
        visible.map(s=>[
          div("row",plantMedia(ui,s,true),btn(s.name||s.id,()=>{state.site=s.id;return go("overview","overview","main");},"link")),
          s.customer||"—",s.vendor||"—",s.capacity_kwp==null?"—":number(s.capacity_kwp,1)+" kWp",
          s.address||"—",(state.fleet.devices||[]).filter(d=>d.site_id===s.id).length
        ])), e("span",visible.length+" / "+plantList.length+" "+l("nhà máy","plants"),"small muted"));
    }
    query.oninput=update;vendor.onchange=update;update();
    container.append(card(l("Danh sách nhà máy","Plant portfolio"),actions,div("row wrap",query,vendor),results));
    container.append(div("grid",
      card(l("Vị trí nhà máy","Plant locations"),div("row",icon("map"),ui.p(l("Bản đồ sử dụng tọa độ đã khai báo. Không tự đặt vị trí cho nhà máy thiếu tọa độ.","The map uses recorded coordinates. Plants without coordinates are not placed on the map."))),
        btn(l("Mở bản đồ","Open map"),()=>go("plants","","map"))),
      card(l("Bắt đầu quản lý","Getting started"),ui.p(l("Kết nối tài khoản hãng, kiểm tra truy cập rồi đồng bộ nhà máy và thiết bị. Điều khiển là bước riêng cần quyền và xác minh kỹ thuật.","Connect a vendor account, check access, then synchronize plants and equipment. Control requires separate permissions and technical verification.")),
        btn(l("Quản lý tài khoản hãng","Manage vendor accounts"),()=>go("settings","connections")))
    ));

  // SUB-TAB 2: CUSTOMERS & OWNERSHIP
  } else if (currentTab === "customers") {
    const custMap = new Map();
    plantList.forEach((s) => {
      const cName = s.customer || l("Chưa khai báo chủ sở hữu", "Owner not recorded");
      if (!custMap.has(cName)) {
        custMap.set(cName, { name: cName, plants: [], totalKwp: 0 });
      }
      const item = custMap.get(cName);
      item.plants.push(s);
      item.totalKwp = item.totalKwp == null || s.capacity_kwp == null ? null : item.totalKwp + s.capacity_kwp;
    });

    const custList = Array.from(custMap.values());

    const custCard = card(
      l("Danh mục Khách hàng & Chủ đầu tư sở hữu trạm", "Customers & Plant Ownership Portfolio"),
      div("row",
        div("overview-kpis",
          div("fact", e("span", l("Khách hàng đã khai báo:", "Recorded customers:")), e("b", `${new Set(plantList.map(s=>s.customer).filter(Boolean)).size}`)),
          div("fact", e("span", l("Tổng công suất quản lý:", "Total Managed Capacity:")), e("b", plantList.some(p=>p.capacity_kwp==null) ? '—' : `${number(plantList.reduce((acc, p) => acc + p.capacity_kwp, 0))} kWp`))
        ),
        btn(l("+ Thêm Khách hàng mới", "+ Add New Customer"), () => {
          openPlantWizard(ui, () => ui.refresh());
        }, "primary")
      ),
      table(
        [l("Khách hàng / Doanh nghiệp", "Customer / Company"), l("Số lượng trạm", "Plants Count"), l("Tổng công suất (kWp)", "Total Capacity"), l("Người liên hệ", "Contact Person"), l("Số điện thoại / Email", "Phone / Email"), l("Thao tác", "Action")],
        custList.map((c) => [
          e("b", c.name),
          badge(`${c.plants.length} ${l("nhà máy", "plants")}`),
          c.totalKwp==null?'—':`${number(c.totalKwp)} kWp`,
          "—",
          "—",
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
      const quantity=(value,unit)=>value==null?'—':number(value)+' '+unit;
      const regGrid = div('grid three region-summary',...[
        ['north',l('Miền Bắc','North')],['central',l('Miền Trung','Central')],['south',l('Miền Nam','South')]
      ].map(([key,label])=>{
        const region=regData.regions[key]||{};
        return card(label,
          div('row',icon('map'),e('strong',String(region.plants_count??'—')),e('span',l('nhà máy','plants'))),
          div('fact',e('span',l('Công suất đã khai báo','Declared capacity')),e('b',quantity(region.total_kwp,'kWp'))),
          div('fact',e('span',l('Sản lượng hôm nay','Generation today')),e('b',quantity(region.today_kwh,'kWh'))),
          div('fact',e('span',l('Tỷ lệ có kết nối','Online ratio')),e('b',quantity(region.online_pct,'%'))));
      }));

      container.replaceChildren(
        subnav,
        card(
          l("Phân bố nhà máy theo vùng địa lý toàn quốc", "Nationwide Regional Plant Distribution"),
          e('p',l('Các trạm chưa khai báo khu vực không được tự gán vào miền. Dấu — là chưa đủ dữ liệu.','Plants without a recorded region are not assigned automatically. A dash means insufficient data.')),
          regGrid,
          btn(l('Xem danh mục nhà máy','View plant directory'),()=>{state.plantsTab='portfolio';ui.render();},'link')
        )
      );
    } catch (err) {
      container.replaceChildren(subnav, e("p", `${l("Lỗi:", "Error:")} ${err.message}`, "small bad"));
    }

  // SUB-TAB 4: ONBOARDING WIZARD INLINE
  } else if (currentTab === "onboarding") {
    const wizardCard = card(
      l("Thêm nhà máy từng bước", "Add a plant step by step"),
      div("row",
        e("p", l(
          "Tạo hồ sơ với tên, vị trí và thông số bạn biết. Có thể để trống thông tin chưa rõ và bổ sung sau. Bước này chưa kết nối hay điều khiển thiết bị.",
          "Create a record with the name, location and specifications you know. Leave unknown information blank and add it later. This does not connect or control equipment."
        ), "small muted"),
        btn(l("Bắt đầu thêm nhà máy", "Start adding a plant"), () => openPlantWizard(ui, () => {
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
