import { energyFlowCard } from './energy-flow.js';
import { nativeDevice } from "./native-device.js";
import { createLiveFeed } from "./live.js";
import {
  l,
  t,
  language,
  setLanguage,
  number,
  date,
  errorText,
} from "./i18n.js";
import { createWorkbench, maintenanceSections } from "./workbench.js";
import { accountsView } from "./accounts.js";
import { icon } from "./icons.js";
import { schemaControl } from "./schema-form.js";
import { renderPlantsMainWorkspace, openPlantWizard } from "./plant-workspace.js";
import { renderDevicesMainWorkspace, createDeviceWorkspace } from "./device-workspace.js";
import { createCommissioningWorkspace } from "./commissioning-workspace.js";
import { renderGisMapWorkspace, createGisMapView } from "./gis-map.js";
import { renderTopologyWorkspace, createTopologyView } from "./topology-view.js";
import { createFirmwareWorkspace } from "./firmware-workspace.js";
import { renderSiteOverviewWorkspace } from "./site-overview-workspace.js";
import { renderControlMainWorkspace } from "./control-workspace.js";
import { renderScheduleMainWorkspace } from "./schedule-workspace.js";
import { renderEmsWorkspace } from "./ems-workspace.js";
import { renderDataConnectionsWorkspace, ownsDataWorkspaceRoute } from "./data-workspace.js";
import { renderIncidentWorkspace } from "./incident-workspace.js";
import { renderReportWorkspace } from "./report-workspace.js";
import { renderJournalMainWorkspace } from "./journal-workspace.js";
import { renderSettingsWorkspace } from "./settings-workspace.js";

const $ = (s, p = document) => p.querySelector(s);
const state = {
  me: null,
  csrf: "",
  page: "overview",
  site: "",
  tab: "",
  fleet: { sites: [], devices: [] },
  ops: {},
  providers: [],
  epoch: 0,
  section: "main",
  work: {},
};
const pages = [
  "overview",
  "plants",
  "topology",
  "devices",
  "operations",
  "incidents",
  "reports",
  "settings",
];
function navigation() {
  return [
    ["overview", "main", "", l("Tổng quan", "Overview"), "home"],
    ["plants", "main", "", l("Nhà máy", "Plants"), "plant"],
    ["topology", "main", "", l("Hệ thống / SLD", "Topology / SLD"), "activity"],
    ["plants", "map", "", l("Bản đồ", "Map"), "map"],
    ["devices", "main", "", l("Thiết bị", "Devices"), "device"],
    ["operations", "main", "control", l("Điều khiển", "Control"), "control"],
    [
      "operations",
      "main",
      "schedules",
      l("Lịch / TOU", "Schedules / TOU"),
      "calendar",
    ],
    [
      "operations",
      "main",
      "rules",
      l("Điều phối EMS", "EMS coordination"),
      "activity",
    ],
    [
      "reports",
      "main",
      "",
      l("Dữ liệu & kết nối", "Data & connections"),
      "chart",
    ],
    ["incidents", "main", "", l("Cảnh báo", "Alerts"), "bell"],
    ["reports", "analytics", "", l("Báo cáo", "Reports"), "report"],
    ["incidents", "health", "", l("Bảo trì", "Maintenance"), "tool"],
    ["operations", "main", "journal", l("Nhật ký", "Journal"), "report"],
    ["settings", "main", "users", l("Người dùng", "Users"), "device"],
    [
      "settings",
      "main",
      "connections",
      l("Cài đặt & Hãng", "Settings & Vendors"),
      "settings",
    ],
  ];
}
function routeHash() {
  return [state.page, state.section, state.tab].filter(Boolean).join("/");
}
function settingsMenu() {
  showDialog(
    l("Cài đặt & trợ giúp", "Settings & help"),
    div(
      "stack",
      ...[
        ["main", "users", l("Người dùng & phân quyền", "Users & access")],
        ["main", "vendors", l("Tài khoản hãng & kết nối", "Vendor accounts")],
        ["main", "site_config", l("Cấu hình nhà máy", "Site configuration")],
        ["main", "device_onboarding", l("Liên kết thiết bị mới", "Device onboarding")],
        ["agents", "", l("Local Agent", "Local Agents")],
        ["source_policy", "", l("Nguồn dữ liệu", "Data sources")],
        ["notification_policy", "", l("Thông báo", "Notifications")],
        ["main", "security", l("Nhật ký bảo mật", "Security journal")],
        [
          "main",
          "evidence",
          l("Tài liệu & tương thích", "Evidence & compatibility"),
        ],
      ]
        .filter(([, tab]) => admin() || !["users", "security", "site_config", "device_onboarding"].includes(tab))
        .map(([section, tab, label]) =>
          btn(label, () => {
            closeDialog();
            return go("settings", tab, section);
          }),
        ),
      p(
        l(
          "Tài khoản hãng: thêm kết nối → chọn tài khoản → kiểm tra → đồng bộ. Điều khiển luôn cần kiểm tra tương thích và đọc lại thiết bị.",
          "Vendor accounts: add a connection → select the account → check → synchronize. Control always requires compatibility checks and device readback.",
        ),
      ),
    ),
  );
}
function globalSearch(query = "") {
  const search = input("search", query);
  search.placeholder = l(
    "Tìm nhà máy, thiết bị, cảnh báo…",
    "Search plants, devices, alerts…",
  );
  search.setAttribute("aria-label", search.placeholder);
  const results = div("stack");
  const draw = () => {
    const q = search.value.toLocaleLowerCase().trim();
    const sites = state.fleet.sites.filter((s) =>
      `${s.name} ${s.customer || ""}`.toLocaleLowerCase().includes(q),
    );
    const devices = state.fleet.devices.filter((d) =>
      `${d.name || ""} ${d.vendor_id} ${d.identity.vendor}`
        .toLocaleLowerCase()
        .includes(q),
    );
    const alerts = (state.ops.incident || []).filter((a) =>
      a.title.toLocaleLowerCase().includes(q),
    );
    results.replaceChildren(
      ...sites.slice(0, 6).map((site) =>
        btn("⌂ " + site.name, () => {
          closeDialog();
          state.site = site.id;
          return go("plants", "", "plant");
        }),
      ),
      ...devices
        .slice(0, 6)
        .map((device) =>
          btn("▤ " + device.vendor_id, () => deviceDetail(device.id)),
        ),
      ...alerts.slice(0, 5).map((a) =>
        btn("△ " + a.title, () => {
          closeDialog();
          state.site = a.site_id;
          return go("incidents");
        }),
      ),
    );
    if (!results.childElementCount) results.append(p(t("noData")));
  };
  search.oninput = draw;
  draw();
  showDialog(l("Tìm trong hệ thống", "Search the workspace"), search, results);
  search.focus();
}
const e = (tag, text = "", cls = "") => {
  const n = document.createElement(tag);
  n.textContent = text;
  n.className = cls;
  return n;
};
const add = (parent, ...children) => {
  parent.append(...children.filter(Boolean));
  return parent;
};
const div = (cls, ...children) => add(e("div", "", cls), ...children);
const p = (text) => e("p", text, "muted");
const btn = (text, action, cls = "") => {
  const n = e("button", text, cls);
  n.type = "button";
  n.onclick = () =>
    run(async () => {
      n.disabled = true;
      try {
        await action();
      } finally {
        n.disabled = false;
      }
    });
  return n;
};
const badge = (text, kind = "") => e("span", text, "badge " + kind);
const status = (value) =>
  badge(
    t(value),
    [
      "CONNECTED",
      "VERIFIED",
      "resolved",
      "closed",
      "pass",
      "online",
      "GOOD",
    ].includes(value)
      ? "good"
      : ["critical", "fail", "FAILED", "ERROR", "offline"].includes(value)
        ? "bad"
        : "warn",
  );
const card = (title, ...children) =>
  div("card", title ? e("h2", title) : null, ...children);
const raw = (title, value) =>
  add(
    e("details"),
    e("summary", title),
    e("pre", JSON.stringify(value, null, 2)),
  );
function link(text, url) {
  const a = e("a", text);
  if (/^https:\/\//.test(url)) {
    a.href = url;
    a.target = "_blank";
    a.rel = "noreferrer noopener";
  }
  return a;
}
function input(type = "text", value = "") {
  const n = e("input");
  n.type = type;
  n.value = value ?? "";
  return n;
}
function select(options, value = "") {
  const n = e("select");
  for (const [id, label] of options) {
    const o = e("option", label);
    o.value = id;
    n.append(o);
  }
  n.value = value;
  if (n.selectedIndex < 0 && options.length) n.selectedIndex = 0;
  return n;
}
let fieldSequence = 0;
const field = (label, control) => {
  const caption = e("span", label);
  caption.id = `field-label-${++fieldSequence}`;
  // Explicit labelling excludes a select's options from its accessible name.
  control.setAttribute("aria-labelledby", caption.id);
  return add(e("label", "", "field"), caption, control);
};
const fact = (label, value) =>
  div("fact", e("span", label), e("b", value ?? "—"));
function notice(vi, en, warn = false) {
  return e("div", l(vi, en), "notice" + (warn ? " warning" : ""));
}
function empty(title, description, action) {
  return div(
    "empty",
    e("div", "◈", "empty-icon"),
    e("h2", title),
    p(description),
    action,
  );
}
function toast(text) {
  const el = $("#toast");
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (el.hidden = true), 9000);
}
async function run(action) {
  try {
    await action();
  } catch (err) {
    toast(
      err.message ||
        l("Không hoàn tất thao tác.", "Could not complete the action."),
    );
  }
}
async function api(path, body) {
  const options = { credentials: "same-origin", headers: {} };
  if (body !== undefined) {
    options.method = "POST";
    options.headers = {
      "Content-Type": "application/json",
      "X-CSRF-Token": state.csrf,
    };
    options.body = JSON.stringify(body);
  }
  const response = await fetch("/api" + path, options);
  let result;
  try {
    result = await response.json();
  } catch {
    throw new Error(l("Không đọc được phản hồi.", "Invalid server response."));
  }
  if (!response.ok) {
    if (response.status === 401 && path != "/login") {
      state.me = null;
      state.csrf = "";
      showLogin();
    }
    const error = new Error(
      errorText(result.error || result.detail || "request_failed"),
    );
    error.status = response.status;
    throw error;
  }
  return result;
}
async function download(path, name) {
  const r = await fetch("/api" + path, { credentials: "same-origin" });
  if (!r.ok) throw new Error(l("Không xuất được dữ liệu.", "Export failed."));
  const url = URL.createObjectURL(await r.blob());
  const a = e("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
  if (r.headers.get("X-Data-Truncated") === "true")
    toast(
      l(
        "Dữ liệu vượt giới hạn xuất. Thu hẹp khoảng thời gian.",
        "Export limit reached. Narrow the date range.",
      ),
    );
}
const admin = () =>
  state.me?.user.role === "Administrator" &&
  state.me.user.site_ids.includes("*");
const operator = () => state.me?.user.role !== "Viewer";
const siteName = (id) => state.fleet.sites.find((s) => s.id === id)?.name || id;
const sites = () =>
  state.fleet.sites.filter((s) => !state.site || s.id === state.site);
const devices = () =>
  state.fleet.devices.filter((d) => !state.site || d.site_id === state.site);
const records = (kind) =>
  (state.ops[kind] || []).filter(
    (r) => !state.site || r.site_id === state.site,
  );
const siteSelect = (value) =>
  select(
    state.fleet.sites.map((s) => [s.id, s.name]),
    value || state.site,
  );
function showDialog(title, ...children) {
  $("#dialog-close").setAttribute("aria-label", l("Đóng", "Close"));
  $("#dialog-title").textContent = title;
  $("#dialog-content").replaceChildren(...children);
  if (!$("#dialog").open) $("#dialog").showModal();
}
function closeDialog() {
  $("#dialog").close();
  $("#dialog-content").replaceChildren();
}
$("#dialog-close").onclick = closeDialog;
$("#dialog").addEventListener("close", () =>
  $("#dialog-content").replaceChildren(),
);
function form(onSubmit, label = t("save")) {
  const f = e("form", "", "form"),
    error = e("div", "", "error");
  error.setAttribute("role", "alert");
  const submit = e("button", label, "primary");
  submit.type = "submit";
  f.finish = (...children) =>
    add(
      f,
      ...children,
      error,
      div("form-actions", btn(t("cancel"), closeDialog), submit),
    );
  f.onsubmit = async (event) => {
    event.preventDefault();
    if (!f.reportValidity()) return;
    submit.disabled = true;
    const workspace = $("#content");
    const controls = [...(workspace?.querySelectorAll('input,select,textarea,button') || [])]
      .map(node => [node, node.disabled]);
    controls.forEach(([node]) => { node.disabled = true; });
    if (workspace) { workspace.inert = true; workspace.setAttribute('aria-busy', 'true'); }
    error.textContent = "";
    try {
      await onSubmit();
    } catch (err) {
      error.textContent = err.message;
    } finally {
      submit.disabled = false;
      controls.forEach(([node, disabled]) => { if (node.isConnected) node.disabled = disabled; });
      if (workspace) { workspace.inert = false; workspace.removeAttribute('aria-busy'); }
    }
  };
  return f;
}
function languagePicker() {
  const el = select(
    [
      ["vi", "Tiếng Việt"],
      ["en", "English"],
    ],
    language,
  );
  el.className = "language";
  el.setAttribute("aria-label", "Language / Ngôn ngữ");
  el.onchange = () => {
    setLanguage(el.value);
    closeDialog();
    if (state.me) run(render);
    else showLogin();
  };
  return el;
}
function brand() {
  return div(
    "brand",
    e("span", "", "brand-icon"),
    div(
      "brand-copy",
      e("span", "SolarOne"),
      e("small", "Smart O&M for a brighter tomorrow"),
    ),
  );
}
function table(headers, rows) {
  const table = e("table");
  const tr = e("tr");
  headers.forEach((h) => tr.append(e("th", h)));
  add(table, add(e("thead"), tr));
  const body = e("tbody");
  for (const row of rows) {
    const tr = e("tr");
    for (const cell of row) {
      const td = e("td");
      td.append(
        cell instanceof Node ? cell : document.createTextNode(cell ?? "—"),
      );
      tr.append(td);
    }
    body.append(tr);
  }
  table.append(body);
  return div("table-scroll", table);
}
function tabs(options, current, change) {
  const root = e("div", "", "tabs");
  root.setAttribute("role", "tablist");
  for (const [key, label] of options) {
    const b = btn(label, () => change(key), key === current ? "active" : "");
    b.setAttribute("role", "tab");
    b.setAttribute("aria-selected", String(key === current));
    root.append(b);
  }
  return root;
}
function kpis(items) {
  return div(
    "kpis",
    ...items.map(([icon, label, value]) =>
      div(
        "card kpi",
        e("div", icon, "icon"),
        div("", e("span", label), e("strong", value)),
      ),
    ),
  );
}
function searchable(headers, items, build, filters = []) {
  const q = input("search"),
    v = select([
      ["", l("Tất cả hãng", "All vendors")],
      ...[
        ...new Set(
          items.map((x) => x.identity?.vendor || x.vendor).filter(Boolean),
        ),
      ].map((x) => [x, x]),
    ]);
  q.placeholder = t("search");
  q.setAttribute("aria-label", t("search"));
  v.setAttribute("aria-label", t("vendor"));
  const out = div(""),
    info = e("p", "", "small muted"),
    pager = div("row between");
  let page = 0;
  function draw() {
    let found = items.filter(
      (x) =>
        (!v.value || (x.identity?.vendor || x.vendor) === v.value) &&
        JSON.stringify([
          x.name,
          x.vendor_id,
          x.identity?.vendor,
          x.customer,
          x.address,
          x.vendor,
        ])
          .toLocaleLowerCase()
          .includes(q.value.toLocaleLowerCase()),
    );
    const size = 15;
    page = Math.min(page, Math.max(0, Math.ceil(found.length / size) - 1));
    out.replaceChildren(
      found.length
        ? table(headers, found.slice(page * size, (page + 1) * size).map(build))
        : empty(
            t("noData"),
            l(
              "Thử thay đổi bộ lọc hoặc thêm kết nối.",
              "Try changing filters or adding a connection.",
            ),
          ),
    );
    info.textContent = l("Số kết quả: ", "Results: ") + found.length;
    const prev = btn("←", () => {
        page--;
        draw();
      }),
      next = btn("→", () => {
        page++;
        draw();
      });
    prev.disabled = page === 0;
    next.disabled = (page + 1) * size >= found.length;
    prev.setAttribute("aria-label", l("Trang trước", "Previous page"));
    next.setAttribute("aria-label", l("Trang sau", "Next page"));
    pager.replaceChildren(
      info,
      div(
        "row",
        prev,
        e(
          "span",
          `${page + 1} / ${Math.max(1, Math.ceil(found.length / size))}`,
        ),
        next,
      ),
    );
  }
  q.oninput = () => {
    page = 0;
    draw();
  };
  v.onchange = () => {
    page = 0;
    draw();
  };
  draw();
  return div("stack", div("toolbar", q, v, ...filters), out, pager);
}
function showLogin() {
  // An initial /me rejection and its caller can both request this view.
  // Preserve any credentials the user has already begun entering.
  if ($("#root .login")) return;
  $(".skip-link").textContent = l("Tới nội dung chính", "Skip to content");
  closeDialog();
  const user = input(),
    password = input("password");
  user.required = password.required = true;
  user.autocomplete = "username";
  password.autocomplete = "current-password";
  user.maxLength = 100;
  password.maxLength = 256;
  const f = form(
    async () => {
      await api("/login", { username: user.value, password: password.value });
      password.value = "";
      await load();
      await render();
    },
    l("Vào không gian làm việc →", "Open workspace →"),
  );
  f.finish(
    field(l("Tài khoản cục bộ", "Local account"), user),
    field(t("password"), password),
  );
  f.querySelector(".form-actions button").remove();
  $("#root").replaceChildren(
    div(
      "login",
      div(
        "login-story",
        brand(),
        div(
          "",
          e(
            "div",
            l("MỘT NỀN TẢNG. NHIỀU HỆ THỐNG.", "ONE PLATFORM. MANY SYSTEMS."),
            "eyebrow",
          ),
          e(
            "h1",
            l(
              "Nắm rõ năng lượng.\nChủ động vận hành.",
              "Understand your energy.\nStay in control.",
            ),
          ),
          p(
            l(
              "Quản lý nhà máy, thiết bị và công việc vận hành từ một nơi.",
              "Manage plants, equipment and operational work in one place.",
            ),
          ),
        ),
        p(l("Controller tại máy của bạn · 0.2", "Your local controller · 0.2")),
      ),
      div(
        "login-side",
        languagePicker(),
        div(
          "login-box",
          e("div", l("CHÀO MỪNG TRỞ LẠI", "WELCOME BACK"), "eyebrow"),
          e("h2", l("Đăng nhập Solar Fleet", "Sign in to Solar Fleet")),
          p(
            l(
              "Dùng tài khoản được quản trị viên cấp.",
              "Use the account provided by your administrator.",
            ),
          ),
          f,
        ),
      ),
    ),
  );
}
let livePending = false,
  liveBusy = false,
  liveTimer;
const live = createLiveFeed({
  authenticated: () => Boolean(state.me),
  status: (value) => {
    state.streamStatus = value;
    const label = document.querySelector(".stream-status");
    if (label)
      label.textContent =
        value === "CONNECTED"
          ? l("Cập nhật trực tiếp", "Live updates")
          : l("Kết nối UI: ", "UI connection: ") + value;
  },
  changed: () => {
    livePending = true;
    clearTimeout(liveTimer);
    liveTimer = setTimeout(updateLive, 1000);
  },
});
async function updateLive() {
  if (!livePending || !state.me || liveBusy) return;
  if (
    document.hidden ||
    document.fullscreenElement ||
    document.querySelector("dialog[open]") ||
    document.activeElement?.matches("input,select,textarea") ||
    !["overview", "devices"].includes(state.page) ||
    state.section !== "main"
  ) {
    return; // Manual workspaces keep their inputs; refresh is explicit there.
  }
  livePending = false;
  liveBusy = true;
  try {
    await load();
    // A fullscreen diagram is a reading snapshot. Keep its DOM and freshness
    // timer intact if a stream refresh started just before entering fullscreen.
    if (document.fullscreenElement) {
      livePending = true;
      return;
    }
    await render();
  } catch {
    /* Existing API handler owns session errors. */
  } finally {
    liveBusy = false;
  }
}
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) updateLive();
});
document.addEventListener("fullscreenchange", () => {
  if (!document.fullscreenElement) updateLive();
});
window.addEventListener("beforeunload", () => live.stop());
async function load() {
  state.me = await api("/me");
  state.csrf = state.me.csrf;
  live.start();
  [state.fleet, state.ops, state.providers, state.work] = await Promise.all([
    api("/fleet"),
    api("/operations"),
    api("/providers"),
    api("/workbench"),
  ]);
  if (state.site && !state.fleet.sites.some((s) => s.id === state.site))
    state.site = "";
}
async function go(page, tab = "", section = "main") {
  state.section = section;
  state.page = page;
  state.tab = tab;
  location.hash = routeHash();
  await render();
}
async function refresh() {
  await load();
  await render();
}
async function render() {
  $(".skip-link").textContent = l("Tới nội dung chính", "Skip to content");
  const epoch = ++state.epoch;
  document.documentElement.lang = language;
  document.title = `${t(state.page)} · SolarOne`;
  const nav = e("nav");
  nav.setAttribute("aria-label", l("Điều hướng chính", "Main navigation"));
  const entries = navigation();
  const maintenancePage = state.page === "incidents" && maintenanceSections.has(state.section);
  const active = entries.find(
    ([page, section, tab]) =>
      page === state.page &&
      (section === state.section || (maintenancePage && section === "health")) &&
      (!tab ||
        tab ===
          (state.tab || (page === "settings" ? "connections" : "control"))),
  );
  entries.forEach((entry) => {
    const [page, section, tab, label, symbol] = entry;
    const selected =
      entry === active ||
      (!active &&
        page === state.page &&
        section === "main" &&
        (!tab || tab === "connections"));
    const b = btn("", () => go(page, tab, section), selected ? "active" : "");
    add(b, icon(symbol), e("span", label));
    if (selected) b.setAttribute("aria-current", "page");
    nav.append(b);
  });
  const scope = select(
    [["", t("all")], ...state.fleet.sites.map((s) => [s.id, s.name])],
    state.site,
  );
  scope.setAttribute("aria-label", l("Phạm vi nhà máy", "Plant scope"));
  scope.onchange = () =>
    run(async () => {
      state.site = scope.value;
      await render();
    });
  const content = e("section");
  content.id = "content";
  content.tabIndex = -1;
  const headings = {
    overview: l(
      "Nhìn toàn cảnh. Biết việc cần làm.",
      "See the whole picture. Know what needs attention.",
    ),
    plants: l(
      "Quản lý nhà máy và khách hàng tập trung.",
      "Manage your plants and customers in one place.",
    ),
    topology: l(
      "Sơ đồ đơn tuyến điện, phân bổ chuỗi PV và kiểm định đấu nối.",
      "Single-line electrical diagram, string mapping and grid checks.",
    ),
    devices: l(
      "Thiết bị, dữ liệu và đường kết nối rõ ràng.",
      "Equipment, readings and connections at a glance.",
    ),
    operations: l(
      "Thiết lập có kiểm tra. Kết quả có truy vết.",
      "Review settings and track their outcomes.",
    ),
    incidents: l(
      "Từ ghi nhận tới xử lý, trong một luồng công việc.",
      "From first report to resolution in one workflow.",
    ),
    reports: l(
      "Dữ liệu có nguồn, đúng đơn vị và thời gian.",
      "Traceable data with explicit units and timestamps.",
    ),
    settings: l(
      "Kết nối hệ thống và quản lý quyền truy cập.",
      "Connect systems and manage access.",
    ),
  };
  const accountPage =
    state.page === "settings" &&
    state.section === "main" &&
    ["", "connections"].includes(state.tab);
  const heading = accountPage
    ? l("Tài khoản hãng & thông tin truy cập", "Vendor accounts & access")
    : ownsDataWorkspaceRoute(state)
      ? l("Dữ liệu & kết nối", "Data & connections")
      : active?.[3] || t(state.page);
  document.title = `${heading} · SolarOne`;
  const reportsAnalyticsPage =
    state.page === "reports" && state.section === "analytics";
  const description = accountPage
    ? l(
        "Quản lý các tài khoản đám mây của hãng, thông tin xác thực và quyền truy cập để đồng bộ dữ liệu về SolarOne.",
        "Manage vendor cloud accounts, credentials and access to synchronize data with SolarOne.",
      )
    : maintenancePage
      ? l(
          "Theo dõi thiết bị, lập kế hoạch và kiểm tra kết quả bảo trì.",
          "Observe equipment, plan work and review maintenance results.",
        )
      : reportsAnalyticsPage
        ? l(
            "Trung tâm báo cáo & phân tích hiệu suất năng lượng, tài chính EVN và chỉ số ESG.",
            "Reports & analytics center for solar energy, EVN tariffs and ESG metrics.",
          )
        : headings[state.page];
  const wrapper = div(
    "content-wrap",
    div(
      "breadcrumb",
      e("span", t(state.page)),
      e("span", "›"),
      e(
        "strong",
        accountPage
          ? heading
          : state.site
            ? siteName(state.site)
            : l("Không gian vận hành", "Operations workspace"),
      ),
    ),
    div(
      "page-heading",
      div("", e("h1", heading), p(description)),
      accountPage
        ? btn(l("▣ Hướng dẫn cấu hình", "▣ Setup guide"), settingsMenu)
        : btn(l("↻ Cập nhật", "↻ Refresh"), refresh),
    ),
  );
  if (state.site)
    wrapper.append(
      div(
        "scope-banner",
        e("b", siteName(state.site)),
        btn(l("Xem tất cả nhà máy", "Show all plants"), async () => {
          state.site = "";
          await render();
        }),
      ),
    );
  add(
    wrapper,
    content,
    div(
      "footer",
      e("span", "SolarOne · 0.2.0"),
      e(
        "span",
        l(
          "“—” là chưa biết · Không có dữ liệu mô phỏng trong vận hành",
          "“—” means unknown · No simulated operational data",
        ),
      ),
    ),
  );
  $("#root").replaceChildren(
    div(
      "shell",
      add(
        e("aside", "", "sidebar"),
        brand(),

        nav,
        div(
          "sidebar-bottom",
          e("b", state.me.user.id),
          p(t(state.me.user.role)),
          btn(l("Đăng xuất", "Sign out"), logout),
        ),
      ),
      div(
        "main",
        add(
          e("header", "", "topbar"),
          div("scope", scope),
          (() => {
            const b = btn("", () => globalSearch(), "search-trigger");
            add(
              b,
              icon("search"),
              e(
                "span",
                l(
                  "Tìm nhà máy, thiết bị, cảnh báo…",
                  "Search plants, devices, alerts…",
                ),
              ),
            );
            b.setAttribute(
              "aria-label",
              l("Tìm kiếm toàn hệ thống", "Search workspace"),
            );
            return b;
          })(),
          (() => {
            const b = btn("", () => go("overview", "", "inbox"), "icon-button");
            b.append(icon("bell"));
            b.setAttribute("aria-label", l("Thông báo", "Notifications"));
            return b;
          })(),
          (() => {
            const b = btn("", settingsMenu, "icon-button");
            b.append(icon("help"));
            b.setAttribute(
              "aria-label",
              l("Trợ giúp và cài đặt", "Help and settings"),
            );
            return b;
          })(),
          e(
            "span",
            state.streamStatus === "CONNECTED"
              ? l("Cập nhật trực tiếp", "Live updates")
              : l("Kết nối cập nhật", "Update connection"),
            "stream-status muted small",
          ),
          languagePicker(),
          div("avatar", e("span", state.me.user.id.slice(0, 2).toUpperCase())),
          div(
            "account",
            e("b", state.me.user.id),
            e("span", t(state.me.user.role), "muted"),
          ),
          btn(
            "⌄",
            () =>
              showDialog(
                l("Tài khoản", "Account"),
                p(state.me.user.id),
                btn(l("Đăng xuất", "Sign out"), logout),
              ),
            "icon-button",
          ),
        ),
        wrapper,
      ),
    ),
  );
  $(".topbar>button:last-child").setAttribute(
    "aria-label",
    l("Menu tài khoản", "Account menu"),
  );
  content.append(e("div", l("Đang tải…", "Loading…"), "progress-loading"));
  const views = {
    overview,
    plants: plantsView,
    topology: topologyView,
    devices: devicesView,
    operations: operationsView,
    incidents: incidentsView,
    reports: reportsView,
    settings: settingsView,
  };
  try {
    const suite = createWorkbench({
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
    });
    const view = await suite.wrap(state.page, views[state.page]);
    if (epoch === state.epoch) content.replaceChildren(view);
  } catch (err) {
    if (epoch === state.epoch)
      content.replaceChildren(
        empty(
          l("Chưa tải được trang", "Could not load this page"),
          err.message,
          btn(l("Thử lại", "Try again"), render),
        ),
      );
  }
}
async function logout() {
  live.stop();
  await api("/logout", {});
  state.me = null;
  state.csrf = "";
  state.site = "";
  showLogin();
}

async function overview() {
  if (state.site) {
    return await renderSiteOverview(state.site);
  }
  const ds = devices(),
    open = records("incident").filter(
      (r) => !["resolved", "closed"].includes(r.status),
    );
  const root = div(
    "stack",
    kpis([
      ["⌂", t("plants"), number(sites().length, 0)],
      ["▤", t("devices"), number(ds.length, 0)],
      ["△", l("Sự cố đang mở", "Open incidents"), number(open.length, 0)],
      [
        "◷",
        l("Cần kiểm tra dữ liệu", "Readings need attention"),
        number(ds.filter((d) => d.stale || !d.online).length, 0),
      ],
    ]),
  );
  const next = card(l("Bắt đầu vận hành", "Get started"));
  [
    [
      l("Kết nối tài khoản hãng", "Connect vendor accounts"),
      l(
        "Tự khám phá nhà máy và thiết bị từ các tài khoản được cấp quyền.",
        "Discover plants and devices from authorized accounts.",
      ),
      "settings",
    ],
    [
      l("Sắp xếp nhà máy", "Organize plants"),
      l(
        "Thêm khách hàng, địa chỉ và múi giờ của từng công trình.",
        "Add customers, addresses and timezones for each plant.",
      ),
      "plants",
    ],
    [
      l("Kiểm tra thiết bị & dữ liệu", "Inspect devices and data"),
      l(
        "Đối chiếu model, nguồn và thời gian đo trước khi vận hành.",
        "Check model identity, sources and measurement times.",
      ),
      "devices",
    ],
  ].forEach(([title, desc, page], i) =>
    next.append(
      div(
        "step",
        e("span", String(i + 1), "index"),
        div(
          "",
          btn(title, () => go(page), "link"),
          p(desc),
        ),
      ),
    ),
  );
  const alerts = card(l("Việc cần chú ý", "Needs attention"));
  if (open.length)
    alerts.append(
      ...open.slice(0, 5).map((r) =>
        div(
          "step",
          status(r.severity),
          div(
            "",
            btn(r.title, () => recordDetail("incident", r), "link"),
            p(siteName(r.site_id)),
          ),
        ),
      ),
    );
  else
    alerts.append(
      p(
        l(
          "Chưa có sự cố được ghi nhận. Đây không phải kết luận tất cả thiết bị đều bình thường.",
          "No incidents recorded. This does not establish that all devices are healthy.",
        ),
      ),
      btn(
        l("Mở trung tâm sự cố →", "Open incident center →"),
        () => go("incidents"),
        "link",
      ),
    );
  root.append(div("grid", next, alerts));
  root.append(
    card(l("Danh mục nhà máy", "Plant portfolio"), plantTable(sites())),
  );
  return root;
}

async function renderSiteOverview(siteId) {
  const ctx = {
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
    empty,
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
    siteForm,
    records,
    recordDetail,
    controlForm,
    l,
    t,
    number,
    date,
  };
  return await renderSiteOverviewWorkspace(ctx, siteId);
}

function plantTable(rows) {
  return searchable(
    [
      t("name"),
      t("customer"),
      t("vendor"),
      t("capacity"),
      t("devices"),
      t("details"),
    ],
    rows,
    (s) => [
      btn(
        s.name,
        async () => {
          state.site = s.id;
          state.tab = "overview";
          await go("overview");
        },
        "link",
      ),
      s.customer || "—",
      s.vendor || t("MANUAL"),
      number(s.capacity_kwp),
      number(state.fleet.devices.filter((d) => d.site_id === s.id).length, 0),
      admin()
        ? btn(l("Thông tin", "Profile"), () => siteForm(s))
        : btn(t("details"), async () => {
            state.site = s.id;
            state.tab = "overview";
            await go("overview");
          }),
    ],
  );
}
async function plantsView() {
  if (state.section === "map") {
    return await renderGisMapWorkspace({
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
      go,
      siteName,
      sites,
      siteForm,
    });
  }
  return await renderPlantsMainWorkspace({
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
    go,
    siteName,
    sites,
    siteForm,
  });
}
async function topologyView() {
  return await renderTopologyWorkspace({
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
    go,
    siteName,
    sites,
    siteForm,
  });
}
function siteForm(site) {
  const fields = {
    name: input("text", site?.name),
    customer: input("text", site?.customer),
    address: input("text", site?.address),
    timezone: input("text", site?.timezone || "Asia/Ho_Chi_Minh"),
    capacity_kwp: input("number", site?.capacity_kwp),
    latitude: input("number", site?.latitude),
    longitude: input("number", site?.longitude),
  };
  fields.name.required = true;
  fields.timezone.required = true;
  fields.name.maxLength = 160;
  fields.customer.maxLength = 160;
  fields.address.maxLength = 300;
  for (const key of ["capacity_kwp", "latitude", "longitude"])
    fields[key].step = "any";
  fields.capacity_kwp.min = "0";
  const f = form(async () => {
    const body = Object.fromEntries(
      Object.entries(fields).map(([k, v]) => [
        k,
        ["capacity_kwp", "latitude", "longitude"].includes(k)
          ? v.value === ""
            ? null
            : Number(v.value)
          : v.value,
      ]),
    );
    await api(site ? `/sites/${site.id}/profile` : "/sites", body);
    closeDialog();
    await refresh();
    toast(l("Đã lưu nhà máy.", "Plant saved."));
  });
  f.finish(
    div(
      "form-grid",
      ...Object.entries(fields).map(([key, control]) =>
        field(t(key === "capacity_kwp" ? "capacity" : key), control),
      ),
    ),
  );
  showDialog(
    site
      ? l("Thông tin nhà máy", "Plant profile")
      : l("Thêm nhà máy", "Add plant"),
    f,
  );
}
async function devicesView() {
  return await renderDevicesMainWorkspace({
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
    go,
    siteName,
    sites,
    siteForm,
    deviceDetail,
  });
}
async function deviceDetail(id, tab = "data") {
  const info = await api("/devices/" + id),
    d = info.device;
  const root = div(
    "stack",
    div(
      "row",
      e("b", d.name || d.vendor_id, "device-title"),
      badge(d.identity.vendor, "blue"),
      status(d.last_seen ? (d.online ? "online" : "offline") : "UNKNOWN"),
    ),
  );
  root.append(
    tabs(
      [
        ["data", l("Giám sát", "Monitoring")],
        ["control", l("Điều khiển từ xa", "Remote Control")],
        ["native", l("Cấu hình nâng cao", "Advanced Config")],
        ["alarms", l("Nhật ký & Cảnh báo", "Journal & Alarms")],
        ["documents", l("Tài liệu", "Documents")],
        ["sources", l("Bảo trì & Nguồn", "Maintenance & Sources")],
      ],
      tab,
      (key) => deviceDetail(id, key),
    ),
  );
  if (tab === "data") {
    const monitoring = await api('/journal/realtime/' + encodeURIComponent(id));
    root.append(energyFlowCard({ e, div, p, btn, card, badge }, monitoring.energy_flow, target => {
      if (target === 'control') deviceDetail(id, 'control');
      else { closeDialog(); state.site = d.site_id; go('overview', target, 'main'); }
    }));
    root.append(
      div(
        "grid",
        card(
          l("Thông tin kết nối", "Connection info"),
          fact(t("plants"), siteName(d.site_id)),
          fact(t("lastSeen"), date(d.last_seen)),
          fact(t("source"), t(info.latest.source || "VENDOR_CLOUD")),
        ),
        card(
          l("Chất lượng dữ liệu", "Data quality"),
          p(
            l(
              "Dữ liệu gốc được giữ đúng tên và đơn vị của hãng. Chưa tự quy đổi thành sơ đồ năng lượng khi thiếu mapping.",
              "Native readings retain vendor names and units. Energy flow needs a verified mapping.",
            ),
          ),
          badge(
            l(
              "Đối chiếu thiết bị trước khi điều khiển",
              "Commission equipment before control",
            ),
            "warn",
          ),
        ),
      ),
    );
    root.append(
      card(
        l("Thông số mới nhất", "Latest readings"),
        info.latest.samples.length
          ? table(
              [
                l("Thông số", "Metric"),
                l("Giá trị", "Value"),
                l("Đơn vị", "Unit"),
                t("lastSeen"),
                l("Chất lượng", "Quality"),
              ],
              info.latest.samples.map((s) => [
                s.metric,
                number(s.value),
                s.unit || "—",
                date(s.source_timestamp),
                status(s.quality),
              ]),
            )
          : p(t("noData")),
      ),
    );
    const nativePoints = info.latest.native?.dataList;
    if (Array.isArray(nativePoints) && nativePoints.length) {
      root.append(card(
        l("Thông số gốc từ hãng", "Vendor native readings"),
        notice(
          "Giữ nguyên tên, trạng thái và đơn vị do nền tảng cung cấp. Thời điểm nhận dữ liệu không thay thế thời điểm thiết bị đo.",
          "Names, states and units are preserved from the platform. Receipt time does not replace the device measurement time."
        ),
        table(
          [l("Thông số", "Metric"), l("Giá trị gốc", "Native value"), l("Đơn vị", "Unit")],
          nativePoints.map((point) => [
            point.title || point.name || point.key || "—",
            point.value == null ? "—" : String(point.value),
            point.unit || "—",
          ]),
        ),
      ));
    }
    root.append(
      raw(
        l("Chi tiết dữ liệu gốc", "Native data details"),
        info.latest.native || {},
      ),
    );
  } else if (tab === "history") {
    const result = await api("/devices/" + id + "/history");
    root.append(
      p(
        l(
          "Dữ liệu lưu cục bộ trong 7 ngày.",
          "Locally retained data for 7 days.",
        ),
      ),
      btn(
        l("Mở báo cáo & xuất CSV", "Open report & CSV export"),
        async () => {
          state.reportDevice = id;
          closeDialog();
          await go("reports");
        },
        "primary",
      ),
      table(
        [
          l("Thông số", "Metric"),
          l("Giá trị", "Value"),
          l("Đơn vị", "Unit"),
          t("lastSeen"),
        ],
        result.samples
          .slice(0, 100)
          .map((s) => [
            s.metric,
            number(s.value),
            s.unit || "—",
            date(s.source_timestamp),
          ]),
      ),
    );
  } else if (tab === "native") {
    root.append(
      nativeDevice(
        { div, p, card, tabs, table, badge, btn, notice, controlForm, principal: state.me.user },
        info,
      ),
    );
  } else if (tab === "documents") {
    root.append(
      card(
        l("Tài liệu adapter", "Adapter documentation"),
        ...info.adapter.documentation
          .filter((doc) => doc.url.startsWith("https://"))
          .map((doc) => {
            const link = e("a", doc.title);
            link.href = doc.url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            return link;
          }),
        p(
          l(
            "Tài liệu tham khảo không thay thế nghiệm thu cấu hình của thiết bị này.",
            "Reference documentation does not replace this device's acceptance record.",
          ),
        ),
      ),
    );
  } else if (tab === "alarms") {
    const output = div("stack");
    root.append(
      notice(
        "Cảnh báo do hãng trả về được giữ riêng với phiếu xử lý nội bộ. Chỉ đọc dữ liệu, không xóa lỗi thiết bị.",
        "Vendor alarms are separate from internal incidents. Reading them does not clear device faults.",
      ),
    );
    if (info.adapter.features.includes("alarms"))
      root.append(
        btn(
          l("Đọc cảnh báo 24 giờ", "Read last 24 hours of alarms"),
          async () => {
            const result = await api("/devices/" + id + "/alerts", {});
            output.replaceChildren(
              fact(
                l("Thời gian nhận", "Received at"),
                date(result.received_at),
              ),
              raw(
                l("Cảnh báo gốc từ hãng", "Native vendor alarms"),
                result.native,
              ),
            );
          },
          "primary",
        ),
      );
    else
      root.append(
        p(
          l(
            "Adapter này chưa có hợp đồng đọc cảnh báo được triển khai. Có thể ghi nhận sự cố thủ công trong Sự cố & bảo trì.",
            "This adapter does not yet implement an alarm contract. Record an internal incident in Incidents & maintenance.",
          ),
        ),
      );
    root.append(output);
  } else if (tab === "control") {
    root.append(
      notice(
        "Mỗi mục được kiểm tra theo model, firmware, logger, quyền truy cập và khả năng đọc lại. Tài khoản cloud kết nối thành công chưa mở khóa điều khiển.",
        "Each action is checked against the model, firmware, logger, permissions and readback. A connected cloud account does not unlock control.",
      ),
    );
    root.append(
      table(
        [
          l("Mục đích vận hành", "Operating intent"),
          t("status"),
          l("Điều kiện", "Prerequisite"),
          l("Thiết lập", "Configure"),
        ],
        info.capabilities.map((c) => [
          t(c.intent),
          status(c.state),
          l(
            "Cần profile và nghiệm thu thiết bị thực.",
            "Device profile and hardware acceptance required.",
          ),
          c.state === "VERIFIED" &&
          c.hardware_verified &&
          c.semantic_match === "exact" &&
          operator()
            ? btn(l("Xem trước thay đổi", "Preview change"), () =>
                controlForm(d, c),
              )
            : badge(l("Chưa mở điều khiển", "Control locked")),
        ]),
      ),
    );
    if (info.adapter.features.includes("configuration"))
      root.append(
        btn(l("Đọc cấu hình qua API", "Read API configuration"), async () => {
          const result = await api("/devices/" + id + "/configuration", {});
          showDialog(
            l("Cấu hình đọc từ hãng", "Vendor configuration"),
            notice(
              "Cấu hình trả về có thể được cache. Thời gian nhận không phải thời gian thiết bị xác nhận.",
              "Returned configuration may be cached. Receipt time is not device confirmation time.",
            ),
            raw(l("Xem nội dung", "View content"), result),
          );
        }),
      );
  } else {
    root.append(
      card(
        l("Nhận diện thiết bị", "Device identity"),
        ...Object.entries(d.identity).map(([key, value]) =>
          fact(key, value || t("UNKNOWN")),
        ),
      ),
      raw(l("Các đường kết nối", "Connection bindings"), info.bindings),
      raw(l("Metadata của hãng", "Vendor metadata"), d.metadata),
    );
  }
  showDialog(l("Không gian thiết bị", "Device workspace"), root);
}

function controlForm(device, capability) {
  const definitions = Object.entries(capability.constraints);
  let controls;
  try {
    controls = definitions.map(([key, c]) => ({
      key,
      c,
      ...schemaControl(
        c.json_schema ||
          (c.enum
            ? { enum: c.enum }
            : {
                type: "number",
                minimum: c.min,
                maximum: c.max,
                multipleOf: c.step,
              }),
        { e, div, input, select, field, btn },
      ),
    }));
  } catch (err) {
    showDialog(t(capability.intent), p(err.message));
    return;
  }
  const f = form(
    async () => {
      const parameters = Object.fromEntries(
        controls.map(({ key, read }) => [key, read()]),
      );
      const plan = await api("/plans", {
        device_id: device.id,
        intent: capability.intent,
        parameters,
      });
      const key = crypto.randomUUID(),
        acknowledgement = input("checkbox"),
        outcome = div("stack");
      const confirm = btn(
        l("Xác nhận gửi lệnh", "Confirm and send"),
        async () => {
          if (
            !acknowledgement.checked ||
            Date.now() >= Date.parse(plan.expires_at)
          )
            throw new Error(
              l(
                "Xác nhận tác động và tạo lại bản xem trước nếu đã hết hạn.",
                "Acknowledge the impact and recreate the preview if it expired.",
              ),
            );
          try {
            const result = await api("/commands", {
              plan_id: plan.id,
              digest: plan.digest,
              idempotency_key: key,
            });
            outcome.replaceChildren(
              status(result.status),
              p(
                l(
                  "Lệnh đã được ghi nhận. Theo dõi readback trong nhật ký; hãng nhận lệnh chưa đồng nghĩa thiết bị áp dụng thành công.",
                  "Command recorded. Follow readback in the journal; vendor acceptance does not establish successful device application.",
                ),
              ),
              btn(l("Mở nhật ký lệnh", "Open command journal"), async () => {
                closeDialog();
                await go("operations", "journal");
              }),
            );
          } catch (err) {
            outcome.replaceChildren(
              p(err.message),
              notice(
                "Không tự gửi lại. Kiểm tra nhật ký lệnh trước khi tạo thao tác mới.",
                "Do not automatically resend. Check the command journal before creating a new action.",
                true,
              ),
              btn(l("Mở nhật ký lệnh", "Open command journal"), async () => {
                closeDialog();
                await go("operations", "journal");
              }),
            );
          } finally {
            confirm.remove();
            acknowledgement.disabled = true;
          }
        },
        "primary",
      );
      confirm.disabled = true;
      acknowledgement.onchange = () => {
        confirm.disabled =
          !acknowledgement.checked || Date.now() >= Date.parse(plan.expires_at);
      };
      showDialog(
        l("Xem trước thay đổi", "Preview change"),
        div(
          "stack",
          fact(t("devices"), device.name || device.vendor_id),
          fact(t("plants"), siteName(device.site_id)),
          fact(l("Mục đích", "Intent"), t(plan.intent)),
          table(
            [
              l("Thông số", "Parameter"),
              l("Trước", "Before"),
              l("Sau", "After"),
            ],
            Object.entries(plan.expected).map(([field, value]) => [
              field,
              JSON.stringify(plan.previous[field] ?? null),
              JSON.stringify(value),
            ]),
          ),
          fact(l("Hết hạn lúc", "Expires at"), date(plan.expires_at)),
          ...plan.risks.map((r) => p(r)),
          add(
            e("label", "", "check"),
            acknowledgement,
            e(
              "span",
              l(
                "Tôi đã kiểm tra thiết bị, giá trị và tác động vận hành.",
                "I reviewed the target device, values and operating impact.",
              ),
            ),
          ),
          div("row", btn(t("cancel"), closeDialog), confirm),
          outcome,
        ),
      );
    },
    l("Kiểm tra & xem trước", "Validate & preview"),
  );
  f.finish(
    notice(
      "Bản xem trước đọc cấu hình hiện tại và kiểm tra lại quyền, giới hạn, profile. Bước này chưa gửi lệnh điều khiển.",
      "Preview reads current configuration and rechecks permissions, limits and the profile. This step does not send control commands.",
    ),
    ...controls.map(({ key, c, node }) =>
      field(`${key}${c.unit ? " (" + c.unit + ")" : ""}`, node),
    ),
  );
  showDialog(t(capability.intent), f);
}

async function settingsView() {
  const ui = {
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
    icon,
  };
  return ["", "connections", "vendors"].includes(state.tab) ? accountsView(ui) : renderSettingsWorkspace(ui);
}
function accessForm(user) {
  const role = select(
      [
        "Viewer",
        "Operator",
        "Installer",
        "Senior Engineer",
        "Administrator",
      ].map((r) => [r, t(r)]),
      user.role,
    ),
    all = input("checkbox");
  all.checked = user.site_ids.includes("*");
  const choices = state.fleet.sites.map((site) => {
    const box = input("checkbox");
    box.checked = user.site_ids.includes(site.id);
    return { site, box };
  });
  const rights = [
    "grid_settings",
    "raw_commands",
    "firmware_upgrade",
    "battery_settings",
  ].map((key) => {
    const box = input("checkbox");
    box.checked = (user.permissions || []).includes(key);
    return { key, box };
  });
  const f = form(async () => {
    await api(`/users/${encodeURIComponent(user.id)}/access`, {
      role: role.value,
      site_ids: all.checked
        ? ["*"]
        : choices.filter((c) => c.box.checked).map((c) => c.site.id),
      permissions: rights.filter((r) => r.box.checked).map((r) => r.key),
    });
    closeDialog();
    await refresh();
  });
  f.finish(
    notice(
      "Thay đổi quyền sẽ thu hồi các phiên đăng nhập hiện tại của tài khoản này. Quyền kỹ thuật vẫn cần profile thiết bị đã nghiệm thu.",
      "Access changes revoke this account’s active sessions. Technical permissions still require commissioned device profiles.",
    ),
    field(t("role"), role),
    add(
      e("label", "", "check"),
      all,
      e("span", l("Tất cả nhà máy", "All plants")),
    ),
    div(
      "checklist",
      ...choices.map(({ site, box }) =>
        add(e("label", "", "check"), box, e("span", site.name)),
      ),
    ),
    e("h3", l("Quyền kỹ thuật riêng", "Additional technical permissions")),
    div(
      "checklist",
      ...rights.map(({ key, box }) =>
        add(e("label", "", "check"), box, e("span", t(key))),
      ),
    ),
  );
  showDialog(l("Phân quyền · ", "Access · ") + user.id, f);
}
function resetPasswordForm(user) {
  const password = input("password");
  password.required = true;
  password.minLength = 12;
  password.maxLength = 1024;
  password.autocomplete = "new-password";
  const f = form(async () => {
    await api(`/users/${encodeURIComponent(user.id)}/password`, {
      password: password.value,
    });
    password.value = "";
    closeDialog();
    await refresh();
  });
  f.finish(
    field(
      l(
        "Mật khẩu mới, tối thiểu 12 ký tự",
        "New password, at least 12 characters",
      ),
      password,
    ),
    notice(
      "Tất cả phiên của tài khoản này sẽ bị thu hồi.",
      "All sessions for this account will be revoked.",
    ),
  );
  showDialog(l("Đặt lại mật khẩu · ", "Reset password · ") + user.id, f);
}
async function commandDetail(id) {
  const result = await api(`/commands/${id}/timeline`),
    root = div(
      "stack",
      fact(l("Thiết bị", "Device"), result.command.device_id),
      status(result.command.status),
    );
  if (result.plan)
    root.append(
      table(
        [l("Thông số", "Field"), l("Trước", "Before"), l("Sau", "After")],
        Object.entries(result.plan.expected).map(([k, v]) => [
          k,
          JSON.stringify(result.plan.previous[k]),
          JSON.stringify(v),
        ]),
      ),
    );
  root.append(
    table(
      [l("Thời gian", "Time"), l("Sự kiện", "Event"), t("status")],
      result.events.map((r) => [
        date(r.timestamp),
        t(r.event),
        t(r.status || "—"),
      ]),
    ),
    raw(l("Phản hồi và đối chiếu", "Order and readback"), result.command),
  );
  root.append(
    btn(l("Cập nhật trạng thái", "Refresh status"), () => commandDetail(id)),
  );
  if (
    result.command.status === "TIMEOUT" &&
    ["Installer", "Senior Engineer"].includes(state.me.user.role)
  )
    root.append(
      notice(
        "Đối chiếu chỉ đọc trạng thái order và cấu hình mới. Nếu không có order ID hoặc hãng chưa kết thúc, thiết bị tiếp tục được giữ khóa.",
        "Reconciliation only reads order status and fresh configuration. Missing or pending orders keep the device quarantined.",
      ),
      btn(
        l("Đọc lại & đối chiếu", "Read and reconcile"),
        async () => {
          await api(`/commands/${id}/reconcile`, {});
          await commandDetail(id);
        },
        "primary",
      ),
    );
  showDialog(l("Vòng đời lệnh", "Command lifecycle"), root);
}
function integrationForm(spec) {
  const name = input(
    "text",
    (spec.equipment_brand ? spec.equipment_brand + " · " : "") +
      spec.id +
      " Cloud",
  );
  name.required = true;
  name.maxLength = 120;
  const region = select(
    spec.regions.map((r) => [
      r,
      spec.region_names?.[r] || {
        global: l("Quốc tế", "International"),
        cn: l("Trung Quốc", "China"),
        eu: l("Châu Âu", "Europe"),
        am: l("Châu Mỹ", "Americas"),
        india: l("Ấn Độ", "India"),
        au: l("Úc", "Australia"),
        server: l("Máy chủ Growatt (server)", "Growatt server (server)"),
      }[r] || r,
    ]),
  );
  const identity = select(
    [
      ["email", "Email"],
      ["username", l("Tên tài khoản", "Username")],
    ],
    "email",
  );
  const org = input("number");
  org.min = "1";
  const fields = Object.fromEntries(
    spec.fields.map((key) => {
      const control = input(
        [...(spec.secret_fields || []), "key_secret", "app_secret", "password", "token", "system_code", "user_password"].includes(key)
          ? "password"
          : "text",
      );
      control.required = true;
      control.value = spec.field_defaults?.[key] || "";
      control.maxLength = 4096;
      control.autocomplete = "off";
      return [key, control];
    }),
  );
  const f = form(
    async () => {
      const body = {
        name: name.value,
        vendor: spec.id,
        equipment_brand: spec.equipment_brand || null,
        region: region.value,
        identity_field: identity.value,
        credentials: Object.fromEntries(
          Object.entries(fields).map(([k, v]) => [k, v.value]),
        ),
        org_id:
          spec.organization === true && org.value ? Number(org.value) : null,
      };
      await api("/integrations", body);
      Object.values(fields).forEach((f) => (f.value = ""));
      closeDialog();
      await refresh();
      toast(
        l(
          "Đã lưu. Chọn tài khoản để kiểm tra kết nối; dùng Đồng bộ trong menu tài khoản để lấy danh mục.",
          "Saved. Select the account to check access; use Synchronize in its menu to import the inventory.",
        ),
      );
    },
    l("Lưu kết nối", "Save connection"),
  );
  f.finish(
    notice(
      spec.setup_help?.vi || "Chọn đúng vùng dữ liệu và nhập thông tin xác thực của nền tảng hãng theo các trường bên dưới. Không nhập mật khẩu cục bộ của Solar Fleet. Lưu chỉ tạo cấu hình; kiểm tra kết nối và đồng bộ danh mục là bước riêng, không cấp quyền điều khiển thiết bị.",
      spec.setup_help?.en || "Select the correct data center and enter the vendor platform credentials requested below. Do not enter your local Solar Fleet password. Saving only creates configuration; checking access and synchronizing inventory are separate steps and do not authorize device control.",
    ),
    div(
      "form-grid",
      field(t("name"), name),
      field(spec.region_label ? l(spec.region_label.vi, spec.region_label.en) : l("Vùng dữ liệu", "Data center"), region),
      spec.identity
        ? field(l("Cách đăng nhập hãng", "Vendor login method"), identity)
        : null,
      ...Object.entries(fields).map(([key, control]) => field(spec.field_labels?.[key] ? l(spec.field_labels[key].vi, spec.field_labels[key].en) : t(key), control)),
      spec.organization === true
        ? field(
            l(
              "Org ID (tùy chọn, Solarman Pro)",
              "Org ID (optional, Solarman Pro)",
            ),
            org,
          )
        : null,
    ),
  );
  showDialog(l("Kết nối ", "Connect ") + spec.id, f);
}
function userForm() {
  const username = input(),
    password = input("password");
  username.required = password.required = true;
  username.maxLength = 100;
  username.autocomplete = "off";
  password.autocomplete = "new-password";
  password.minLength = 12;
  password.maxLength = 256;
  const role = select(
    ["Viewer", "Operator", "Installer", "Senior Engineer", "Administrator"].map(
      (r) => [r, t(r)],
    ),
    "Viewer",
  );
  const all = input("checkbox");
  const choices = state.fleet.sites.map((s) => ({
    id: s.id,
    name: s.name,
    box: input("checkbox"),
  }));
  const f = form(async () => {
    await api("/users", {
      username: username.value,
      password: password.value,
      role: role.value,
      site_ids: all.checked
        ? ["*"]
        : choices.filter((c) => c.box.checked).map((c) => c.id),
    });
    password.value = "";
    closeDialog();
    await refresh();
  });
  f.finish(
    div(
      "form-grid",
      field(l("Tên tài khoản", "Username"), username),
      field(
        l("Mật khẩu (ít nhất 12 ký tự)", "Password (at least 12 characters)"),
        password,
      ),
      field(l("Vai trò", "Role"), role),
    ),
    add(
      e("label", "", "check"),
      all,
      e(
        "span",
        l(
          "Tất cả nhà máy, kể cả nhà máy thêm sau này",
          "All plants, including future additions",
        ),
      ),
    ),
    div(
      "checklist",
      ...choices.map((c) =>
        add(e("label", "", "check"), c.box, e("span", c.name)),
      ),
    ),
  );
  showDialog(l("Thêm người dùng", "Add user"), f);
}

async function incidentsView() {
  if (state.tab !== "work_order") {
    return await renderIncidentWorkspace({
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
      operator,
      siteName,
      siteSelect,
      deviceDetail,
      go,
      records,
    });
  }
  const kind = state.tab === "work_order" ? "work_order" : "incident";
  const rows = records(kind);
  const root = div(
    "stack",
    tabs(
      [
        ["incident", l("Trung tâm sự cố", "Incident center")],
        ["work_order", l("Công việc bảo trì", "Maintenance work")],
      ],
      kind,
      (key) => go("incidents", key),
    ),
    kpis([
      [
        "△",
        l("Đang mở", "Open"),
        rows.filter((r) => !["resolved", "closed"].includes(r.status)).length,
      ],
      [
        "!",
        t("critical"),
        rows.filter(
          (r) =>
            r.severity === "critical" &&
            !["resolved", "closed"].includes(r.status),
        ).length,
      ],
      [
        "↻",
        t("in_progress"),
        rows.filter((r) => r.status === "in_progress").length,
      ],
      [
        "✓",
        t("resolved"),
        rows.filter((r) => ["resolved", "closed"].includes(r.status)).length,
      ],
    ]),
  );
  const actions = div("row");
  if (operator())
    actions.append(
      btn(
        l("+ Tạo ", "+ Create ") + t(kind),
        () => recordForm(kind),
        "primary",
      ),
    );
  actions.append(
    btn(l("Xuất CSV", "Export CSV"), () =>
      download("/reports/records/" + kind, kind + ".csv"),
    ),
  );
  root.append(actions);
  if (!rows.length)
    root.append(
      empty(
        l("Chưa có bản ghi", "No records yet"),
        l(
          "Ghi nhận vấn đề, phân công người phụ trách và theo dõi xử lý. Các bản ghi ở đây không xóa cảnh báo trên inverter.",
          "Record issues, assign an owner and track resolution. These records do not clear inverter alarms.",
        ),
      ),
    );
  else {
    const q = input("search"),
      filter = select([
        ["", l("Tất cả trạng thái", "All statuses")],
        ...["open", "acknowledged", "in_progress", "resolved", "closed"].map(
          (x) => [x, t(x)],
        ),
      ]);
    q.placeholder = l(
      "Tìm sự cố, người phụ trách…",
      "Search issues, assignees…",
    );
    q.setAttribute("aria-label", q.placeholder);
    filter.setAttribute("aria-label", t("status"));
    const out = div("");
    const draw = () =>
      out.replaceChildren(
        table(
          [
            t("severity"),
            t("title"),
            t("plants"),
            t("status"),
            t("assignee"),
            l("Cập nhật", "Updated"),
          ],
          rows
            .filter(
              (r) =>
                (!filter.value || r.status === filter.value) &&
                (r.title + " " + r.assigned_to)
                  .toLowerCase()
                  .includes(q.value.toLowerCase()),
            )
            .map((r) => [
              status(r.severity),
              btn(r.title, () => recordDetail(kind, r), "link"),
              siteName(r.site_id),
              status(r.status),
              r.assigned_to || t("unassigned"),
              date(r.updated_at),
            ]),
        ),
      );
    q.oninput = filter.onchange = draw;
    draw();
    root.append(card("", div("toolbar", q, filter), out));
  }
  return root;
}
function recordForm(kind, incident = null) {
  if (!state.fleet.sites.length) {
    showDialog(
      t(kind),
      empty(
        l("Cần có nhà máy trước", "Create a plant first"),
        l(
          "Thêm nhà máy hoặc đồng bộ từ tài khoản hãng.",
          "Add a plant or sync a vendor account.",
        ),
      ),
    );
    return;
  }
  const site = siteSelect(incident?.site_id),
    title = input("text", incident?.title || ""),
    description = e("textarea"),
    severity = select(
      ["critical", "high", "medium", "low"].map((s) => [s, t(s)]),
      incident?.severity || "medium",
    ),
    due = input("date");
  title.required = true;
  title.maxLength = 200;
  description.maxLength = 4000;
  const assigned = select([
    ["", t("unassigned")],
    ...(state.ops.assignees || []).map((a) => [a.id, a.id]),
  ]);
  if (incident) site.disabled = true;
  const f = form(async () => {
    await api("/records/" + kind, {
      site_id: site.value,
      title: title.value,
      description: description.value,
      severity: severity.value,
      assigned_to: assigned.value,
      due_date: due.value || null,
      incident_id: incident?.id || null,
      device_id: null,
    });
    closeDialog();
    await refresh();
  });
  f.finish(
    div(
      "form-grid",
      field(t("plants"), site),
      field(t("severity"), severity),
      field(t("title"), title),
      field(t("assignee"), assigned),
      field(t("dueDate"), due),
    ),
    field(t("description"), description),
  );
  showDialog(l("Tạo ", "Create ") + t(kind), f);
}
function recordDetail(kind, row) {
  const root = div(
    "stack",
    div(
      "row",
      status(row.severity),
      status(row.status),
      e("b", siteName(row.site_id)),
    ),
    p(row.description),
  );
  if (kind === "incident" && operator())
    root.append(
      btn(
        l(
          "Tạo phiếu bảo trì từ sự cố",
          "Create maintenance work from incident",
        ),
        () => recordForm("work_order", row),
      ),
    );
  if (row.incident_id)
    root.append(
      fact(
        l("Sự cố liên quan", "Linked incident"),
        (state.ops.incident || []).find((i) => i.id === row.incident_id)
          ?.title || row.incident_id,
      ),
    );
  const timeline = e("div", "", "timeline");
  row.timeline.forEach((item) =>
    timeline.append(
      add(
        e("article"),
        e("b", t(item.status)),
        p(item.note),
        e("small", `${date(item.at)} · ${item.actor}`, "muted"),
      ),
    ),
  );
  root.append(timeline);
  if (operator()) {
    const statusInput = select(
        ["open", "acknowledged", "in_progress", "resolved", "closed"].map(
          (s) => [s, t(s)],
        ),
        row.status,
      ),
      assigned = select(
        [
          ["", t("unassigned")],
          ...(state.ops.assignees || []).map((a) => [a.id, a.id]),
        ],
        row.assigned_to,
      ),
      note = e("textarea");
    note.required = true;
    note.maxLength = 2000;
    const f = form(async () => {
      await api(`/records/${kind}/${row.id}`, {
        revision: row.revision,
        status: statusInput.value,
        assigned_to: assigned.value,
        note: note.value,
      });
      closeDialog();
      await refresh();
    });
    f.finish(
      div(
        "form-grid",
        field(t("status"), statusInput),
        field(t("assignee"), assigned),
      ),
      field(t("note"), note),
    );
    root.append(f);
  }
  showDialog(row.title, root);
}

async function operationsView() {
  const tab = state.tab || "control";
  if (
    [
      "rules",
      "fleet_batch",
      "ems_batch",
      "automation",
      "optimization",
      "compatibility",
      "ems_simulation",
    ].includes(tab)
  ) {
    return await renderEmsWorkspace({
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
      go,
      siteName,
      sites,
      devices,
      controlForm,
      deviceDetail,
      ruleForm,
    });
  }
  if (["control", "remote", "advanced", "batch", "pq_dispatch", "safety_gates"].includes(tab)) {
    return await renderControlMainWorkspace({
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
      go,
      siteName,
      sites,
      devices,
      controlForm,
      deviceDetail,
      ruleForm,
    });
  }
  if (["schedules", "weekly", "tariffs", "simulation", "compiler", "deploy"].includes(tab)) {
    return await renderScheduleMainWorkspace({
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
      go,
      siteName,
      sites,
      devices,
      scheduleForm,
    });
  }
  if (["journal", "control_journal", "realtime", "audit_trail", "sync_journal"].includes(tab)) {
    return await renderJournalMainWorkspace({
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
      go,
      siteName,
      sites,
      devices,
    });
  }
  const root = div(
    "stack",
    tabs(
      [
        ["control", l("Điều khiển", "Control")],
        ["schedules", l("Lịch / TOU", "Schedules / TOU")],
        ["rules", l("Quy tắc EMS", "EMS rules")],
        ["bulk", l("Nhiều thiết bị", "Multiple devices")],
        ["journal", l("Nhật ký lệnh", "Command journal")],
        ["commission", l("Nghiệm thu", "Commissioning")],
      ],
      tab,
      (key) => go("operations", key),
    ),
  );
  if (tab === "schedules") {
    root.append(
      notice(
        "Lịch được lưu dưới dạng nháp. Chưa gửi xuống inverter hoặc chạy trên controller. Giới hạn số khung giờ sẽ được kiểm tra theo từng model.",
        "Schedules are saved as drafts. They are not sent to inverters or executed by the controller. Slot limits must be checked per model.",
      ),
    );
    if (operator())
      root.append(
        div(
          "row",
          btn(l("+ Tạo lịch nháp", "+ Create draft"), scheduleForm, "primary"),
        ),
      );
    const rows = records("schedule");
    root.append(
      card(
        l("Lịch đã lưu", "Saved schedules"),
        rows.length
          ? table(
              [
                t("name"),
                t("plants"),
                t("timezone"),
                t("status"),
                l("Chi tiết", "Details"),
              ],
              rows.map((r) => [
                r.name,
                siteName(r.site_id),
                r.timezone,
                status(r.state),
                btn(t("details"), () =>
                  showDialog(
                    r.name,
                    scheduleTable(r.slots),
                    p(r.timezone),
                    status("DRAFT"),
                  ),
                ),
              ]),
            )
          : p(t("noData")),
      ),
    );
  } else if (tab === "rules") {
    root.append(
      notice(
        "Tạo quy tắc và chạy thử bằng dữ liệu hiện có. Chỉ đánh giá điều kiện khi mẫu đo đã xác minh, còn mới và đúng đơn vị. Chạy thử không gửi lệnh.",
        "Create rules and evaluate current readings. Conditions require verified, fresh measurements in the expected unit. Dry runs send no commands.",
      ),
    );
    if (operator())
      root.append(
        div(
          "row",
          btn(
            l("+ Tạo quy tắc nháp", "+ Create draft rule"),
            ruleForm,
            "primary",
          ),
        ),
      );
    const rows = records("rule");
    root.append(
      card(
        l("Quy tắc vận hành", "Operating rules"),
        rows.length
          ? table(
              [t("name"), t("plants"), t("status"), l("Thao tác", "Action")],
              rows.map((r) => [
                r.name,
                siteName(r.site_id),
                status(r.state),
                operator()
                  ? btn(l("Chạy thử", "Dry run"), async () => {
                      const result = await api(
                        "/rules/" + r.id + "/evaluate",
                        {},
                      );
                      await load();
                      showDialog(
                        r.name,
                        notice(
                          "Kết quả đánh giá tại thời điểm hiện tại; chưa có lệnh được gửi.",
                          "Evaluation at the current time; no commands were sent.",
                        ),
                        fact(
                          l("Điều kiện", "Conditions"),
                          l(
                            {
                              TRUE: "Thỏa điều kiện",
                              FALSE: "Chưa thỏa điều kiện",
                              UNKNOWN: "Chưa đủ dữ liệu",
                            }[result.condition_state],
                            {
                              TRUE: "Matched",
                              FALSE: "Not matched",
                              UNKNOWN: "Insufficient data",
                            }[result.condition_state],
                          ),
                        ),
                        table(
                          [
                            l("Thông số", "Metric"),
                            l("Giá trị", "Value"),
                            t("status"),
                          ],
                          result.conditions.map((c) => [
                            c.metric,
                            number(c.value),
                            l(
                              c.state === "UNKNOWN"
                                ? "Cần dữ liệu đã xác minh"
                                : c.state === "TRUE"
                                  ? "Thỏa"
                                  : "Không thỏa",
                              c.state === "UNKNOWN"
                                ? "Verified data needed"
                                : c.state === "TRUE"
                                  ? "Matched"
                                  : "Not matched",
                            ),
                          ]),
                        ),
                        raw(
                          l("Chi tiết đánh giá", "Evaluation details"),
                          result,
                        ),
                      );
                    })
                  : badge(t("readOnly")),
              ]),
            )
          : p(t("noData")),
      ),
    );
    const runs = records("rule_run");
    root.append(
      card(
        l("Lịch sử chạy thử", "Dry run history"),
        runs.length
          ? table(
              [
                t("name"),
                l("Thời gian", "Time"),
                l("Điều kiện", "Conditions"),
                l("Thực thi", "Execution"),
              ],
              runs
                .slice(-30)
                .reverse()
                .map((r) => [
                  rows.find((x) => x.id === r.rule_id)?.name || r.rule_id,
                  date(r.evaluated_at),
                  r.condition_state,
                  l("Không gửi lệnh", "No dispatch"),
                ]),
            )
          : p(t("noData")),
      ),
    );
  } else if (tab === "bulk") {
    const intent = select(
      [
        "SET_ZERO_EXPORT",
        "SET_RESERVE_SOC",
        "SET_TOU",
        "SET_EXPORT_LIMIT",
        "ENABLE_GRID_CHARGE",
        "SET_WORK_MODE",
      ].map((i) => [i, t(i)]),
    );
    const choices = devices().map((d) => ({ d, box: input("checkbox") })),
      result = div("");
    root.append(
      card(
        l("Kiểm tra tương thích nhiều thiết bị", "Assess multiple devices"),
        notice(
          "Đây là bước đánh giá khả năng, không gửi lệnh. Mỗi thiết bị được kiểm tra riêng; không suy ra tương thích từ thương hiệu.",
          "This assessment sends no commands. Each device is checked independently; vendor branding does not establish compatibility.",
        ),
        field(l("Mục đích vận hành", "Operating intent"), intent),
        div(
          "checklist",
          ...choices.map(({ d, box }) =>
            add(
              e("label", "", "check"),
              box,
              e(
                "span",
                `${d.name || d.vendor_id} · ${d.identity.vendor} · ${siteName(d.site_id)}`,
              ),
            ),
          ),
        ),
        btn(
          l("Kiểm tra khả năng", "Check capabilities"),
          async () => {
            const ids = choices.filter((c) => c.box.checked).map((c) => c.d.id);
            if (!ids.length) {
              toast(
                l("Chọn ít nhất một thiết bị.", "Select at least one device."),
              );
              return;
            }
            const data = await api("/compatibility", {
              device_ids: ids,
              intent: intent.value,
            });
            result.replaceChildren(
              table(
                [
                  t("name"),
                  t("vendor"),
                  t("status"),
                  l("Bước tiếp theo", "Next step"),
                ],
                data.targets.map((r) => [
                  devices().find((d) => d.id === r.device_id)?.vendor_id,
                  r.vendor,
                  status(r.state),
                  l(
                    "Bổ sung profile, quyền và readback",
                    "Add profile, permissions and readback",
                  ),
                ]),
              ),
            );
          },
          "primary",
        ),
        result,
      ),
    );
  } else if (tab === "journal") {
    const rows = (await api("/commands")).filter(
      (r) => !state.site || r.site_id === state.site,
    );
    root.append(
      notice(
        "Hãng nhận lệnh và thiết bị xác minh kết quả là hai trạng thái khác nhau. Lệnh chưa rõ kết quả không được tự gửi lại.",
        "Vendor acceptance and device verification are different states. Commands with unknown outcomes are not automatically resent.",
      ),
    );
    root.append(
      card(
        l("Nhật ký điều khiển", "Command journal"),
        rows.length
          ? table(
              [
                l("Thời gian", "Time"),
                t("plants"),
                l("Người thực hiện", "Operator"),
                t("status"),
                t("details"),
              ],
              rows.map((r) => [
                date(r.updated_at),
                siteName(r.site_id),
                r.operator_id,
                status(r.status),
                btn(t("details"), () => commandDetail(r.id)),
              ]),
            )
          : p(l("Chưa có lệnh được gửi.", "No commands have been sent.")),
      ),
    );
  } else if (tab === "commission") {
    root.append(
      notice(
        "Lưu kết quả kiểm tra do kỹ thuật viên thực hiện tại công trình. Bản ghi thủ công không tự mở quyền điều khiển hay tạo chứng nhận phần cứng.",
        "Record inspections performed by a technician at the plant. Manual records do not unlock control or certify hardware.",
      ),
    );
    if (["Installer", "Senior Engineer"].includes(state.me.user.role))
      root.append(
        btn(
          l("+ Ghi kết quả kiểm tra", "+ Record inspection"),
          commissionForm,
          "primary",
        ),
      );
    root.append(
      card(
        l("Kết quả kiểm tra", "Inspection results"),
        records("commissioning").length
          ? table(
              [
                t("plants"),
                l("Hạng mục", "Check"),
                l("Kết quả", "Result"),
                l("Bằng chứng", "Evidence"),
                l("Người kiểm tra", "Inspector"),
              ],
              records("commissioning").map((r) => [
                siteName(r.site_id),
                t(r.check),
                status(r.result),
                r.evidence,
                r.created_by,
              ]),
            )
          : p(t("noData")),
      ),
    );
  }
  return root;
}
const days = () => [
  l("Thứ 2", "Monday"),
  l("Thứ 3", "Tuesday"),
  l("Thứ 4", "Wednesday"),
  l("Thứ 5", "Thursday"),
  l("Thứ 6", "Friday"),
  l("Thứ 7", "Saturday"),
  l("Chủ nhật", "Sunday"),
];
function scheduleTable(slots) {
  return table(
    [
      l("Ngày", "Day"),
      l("Bắt đầu", "Start"),
      l("Kết thúc", "End"),
      l("Chế độ", "Mode"),
      "SOC (%)",
      "kW",
    ],
    slots.map((s) => [
      days()[s.day],
      s.start,
      s.end,
      t(s.mode),
      number(s.target_soc),
      number(s.power_kw),
    ]),
  );
}
function scheduleForm(existing = null) {
  if (!state.fleet.sites.length) {
    toast(
      l(
        "Thêm nhà máy trước khi tạo lịch.",
        "Add a plant before creating a schedule.",
      ),
    );
    return;
  }
  const name = input("text", existing?.name || ""),
    site = siteSelect(existing?.site_id);
  site.disabled = !!existing;
  name.required = true;
  name.maxLength = 120;
  const slots = [],
    list = div("stack");
  const addSlot = (values = {}) => {
    const day = select(
        days().map((d, i) => [String(i), d]),
        String(values.day ?? 0),
      ),
      start = input("time", values.start || "00:00"),
      end = input("text", values.end || "06:00"),
      mode = select(
        ["self_use", "charge", "discharge", "hold"].map((m) => [m, t(m)]),
        values.mode || "hold",
      ),
      soc = input("number", values.target_soc ?? ""),
      power = input("number", values.power_kw ?? "");
    soc.min = "0";
    soc.max = "100";
    power.min = "0";
    power.step = "any";
    start.required = end.required = true;
    end.pattern = "(?:(?:[01][0-9]|2[0-3]):[0-5][0-9]|24:00)";
    const row = div(
      "slot-row",
      field(l("Ngày", "Day"), day),
      field(l("Từ", "From"), start),
      field(l("Đến", "To"), end),
      field(l("Chế độ", "Mode"), mode),
      field("SOC %", soc),
      field("kW", power),
    );
    const entry = {
      row,
      read: () => ({
        day: Number(day.value),
        start: start.value,
        end: end.value,
        mode: mode.value,
        target_soc: soc.value === "" ? null : Number(soc.value),
        power_kw: power.value === "" ? null : Number(power.value),
      }),
    };
    slots.push(entry);
    const remove = btn("×", () => {
      slots.splice(slots.indexOf(entry), 1);
      row.remove();
    });
    remove.setAttribute("aria-label", l("Xóa khung giờ", "Remove time slot"));
    row.append(remove);
    list.append(row);
  };
  for (const slot of existing?.slots || [{}]) addSlot(slot);
  const f = form(
    async () => {
      const data = {
        name: name.value,
        site_id: site.value,
        slots: slots.map((s) => s.read()),
      };
      await api(
        existing ? `/schedules/${existing.id}/edit` : "/schedules",
        existing
          ? { id: existing.id, revision: existing.revision || 1, data }
          : data,
      );
      closeDialog();
      await refresh();
    },
    l("Lưu bản nháp", "Save draft"),
  );
  f.finish(
    div("form-grid", field(t("name"), name), field(t("plants"), site)),
    notice(
      "Không xếp chồng khung giờ. Tách lịch qua đêm tại 24:00; có thể sao chép khung giờ đầu tiên sang cả tuần.",
      "Do not overlap slots. Split overnight periods at 24:00; you can copy the first slot across the week.",
    ),
    list,
    div(
      "row",
      btn(l("+ Thêm khung giờ", "+ Add slot"), () => addSlot()),
      btn(l("Sao chép khung đầu sang tuần", "Copy first slot to week"), () => {
        if (!slots.length) return;
        const first = slots[0].read();
        for (let d = 0; d < 7; d++)
          if (d !== first.day) addSlot({ ...first, day: d });
      }),
    ),
  );
  showDialog(l("Tạo lịch sạc / xả", "Create charge / discharge schedule"), f);
}
function commissionForm() {
  const site = siteSelect(),
    check = select(
      [
        "topology",
        "meter_ct",
        "power_direction",
        "battery",
        "control_readback",
        "alarms",
      ].map((s) => [s, t(s)]),
    ),
    result = select(
      ["pending", "pass", "warning", "fail"].map((s) => [s, t(s)]),
    ),
    evidence = e("textarea");
  evidence.required = true;
  evidence.maxLength = 3000;
  const f = form(async () => {
    await api("/commissioning", {
      site_id: site.value,
      check: check.value,
      result: result.value,
      evidence: evidence.value,
    });
    closeDialog();
    await refresh();
  });
  f.finish(
    div(
      "form-grid",
      field(t("plants"), site),
      field(l("Hạng mục", "Check"), check),
      field(l("Kết quả", "Result"), result),
    ),
    field(
      l("Bằng chứng / ghi chú đối chiếu", "Evidence / verification notes"),
      evidence,
    ),
  );
  showDialog(l("Ghi kết quả kiểm tra", "Record inspection"), f);
}

async function ruleForm() {
  const ds = devices();
  if (!ds.length) {
    toast(
      l(
        "Cần thiết bị và dữ liệu để tạo quy tắc.",
        "Devices and readings are needed to create a rule.",
      ),
    );
    return;
  }
  const name = input(),
    device = select(
      ds.map((d) => [
        d.id,
        `${d.name || d.vendor_id} · ${siteName(d.site_id)}`,
      ]),
    ),
    metric = select([]),
    comparison = select([
      ["lt", l("Nhỏ hơn", "Less than")],
      ["gt", l("Lớn hơn", "Greater than")],
    ]),
    threshold = input("number"),
    reserve = input("number", "30");
  name.required = true;
  name.maxLength = 120;
  threshold.required = true;
  threshold.step = "any";
  reserve.required = true;
  reserve.min = "0";
  reserve.max = "100";
  let samples = [];
  async function measurements() {
    samples = (await api("/devices/" + device.value)).latest.samples || [];
    const choices = select(
      samples.map((s, i) => [
        String(i),
        `${s.metric} (${s.unit || "?"}) · ${t(s.quality)}`,
      ]),
    );
    metric.replaceChildren(...choices.children);
  }
  await measurements();
  device.onchange = () => run(measurements);
  const f = form(
    async () => {
      const sample = samples[Number(metric.value)];
      if (!sample?.unit)
        throw new Error(
          l(
            "Cần thông số có đơn vị xác định.",
            "A metric with an explicit unit is required.",
          ),
        );
      await api("/rules", {
        site_id: ds.find((d) => d.id === device.value).site_id,
        name: name.value,
        conditions: [
          {
            device_id: device.value,
            metric: sample.metric,
            unit: sample.unit,
            comparison: comparison.value,
            threshold: Number(threshold.value),
          },
        ],
        actions: [
          {
            device_id: device.value,
            intent: "SET_RESERVE_SOC",
            parameters: { value: Number(reserve.value) },
          },
        ],
      });
      closeDialog();
      await refresh();
    },
    l("Lưu bản nháp", "Save draft"),
  );
  f.finish(
    field(t("name"), name),
    div(
      "form-grid",
      field(t("devices"), device),
      field(l("Khi thông số", "When metric"), metric),
      field(l("So sánh", "Comparison"), comparison),
      field(
        l("Ngưỡng (cùng đơn vị thông số)", "Threshold (same metric unit)"),
        threshold,
      ),
    ),
    field(
      l("Đề xuất mức dự phòng pin (%)", "Proposed battery reserve (%)"),
      reserve,
    ),
    notice(
      "Mẫu chưa xác minh có thể dùng để soạn quy tắc nhưng sẽ chặn đánh giá. Đây là bản nháp; chưa bật tự động điều khiển.",
      "Unverified metrics can be used to draft a rule but block evaluation. This is a draft; automatic control remains inactive.",
    ),
  );
  showDialog(l("Quy tắc dự phòng pin", "Battery reserve rule"), f);
}

function plot(rows, metric) {
  const samples = rows
    .filter(
      (s) =>
        s.metric === metric && s.source_timestamp && Number.isFinite(s.value),
    )
    .sort(
      (a, b) => new Date(a.source_timestamp) - new Date(b.source_timestamp),
    );
  if (!samples.length || new Set(samples.map((s) => s.unit)).size !== 1)
    return empty(
      t("noData"),
      l(
        "Biểu đồ cần thời gian đo xác định và cùng đơn vị.",
        "Charting requires known measurement times and matching units.",
      ),
    );
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 780 300");
  svg.classList.add("plot");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", l("Biểu đồ ", "Chart: ") + metric);
  const node = (tag, attrs, text = "") => {
    const el = document.createElementNS(svg.namespaceURI, tag);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
    el.textContent = text;
    svg.append(el);
    return el;
  };
  const values = samples.map((s) => s.value),
    minimum = Math.min(...values),
    maximum = Math.max(...values),
    lo = minimum === maximum ? minimum - 1 : minimum,
    hi = minimum === maximum ? maximum + 1 : maximum;
  const from = +new Date(samples[0].source_timestamp),
    to = +new Date(samples.at(-1).source_timestamp),
    x = (s) =>
      65 +
      ((+new Date(s.source_timestamp) - from) / Math.max(1, to - from)) * 680,
    y = (s) => 250 - ((s.value - lo) / (hi - lo)) * 215;
  for (let i = 0; i <= 4; i++) {
    const yy = 35 + (i * 215) / 4;
    node("line", { x1: 65, x2: 745, y1: yy, y2: yy, class: "gridline" });
    node(
      "text",
      { x: 57, y: yy + 4, "text-anchor": "end" },
      number(hi - (i * (hi - lo)) / 4),
    );
  }
  // Points make gaps explicit; no interpolation across missing data or differing sources.
  samples.slice(-1500).forEach((s) => {
    const dot = node("circle", { cx: x(s), cy: y(s), r: 2.5 });
    const title = document.createElementNS(svg.namespaceURI, "title");
    title.textContent = `${date(s.source_timestamp)} · ${number(s.value)} ${s.unit || ""} · ${s.binding_id}`;
    dot.append(title);
  });
  node("text", { x: 65, y: 282 }, date(samples[0].source_timestamp));
  node(
    "text",
    { x: 745, y: 282, "text-anchor": "end" },
    date(samples.at(-1).source_timestamp),
  );
  node("text", { x: 65, y: 18 }, samples[0].unit || "");
  return svg;
}
async function reportsView() {
  const ctx = {
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
    go,
    siteName,
    sites,
    devices,
  };
  if (ownsDataWorkspaceRoute(state)) {
    return await renderDataConnectionsWorkspace(ctx);
  }
  if (state.tab !== "telemetry") {
    return await renderReportWorkspace(ctx);
  }
  const ds = devices();
  if (!ds.length)
    return empty(
      l("Chưa có dữ liệu để lập báo cáo", "No readings to report yet"),
      l(
        "Kết nối thiết bị trước. Các chỉ số chi phí, CO₂ và sản lượng không được tạo từ dữ liệu mẫu.",
        "Connect equipment first. Cost, CO₂ and generation figures are not filled with sample data.",
      ),
    );
  const device = select(
    ds.map((d) => [d.id, `${d.name || d.vendor_id} · ${siteName(d.site_id)}`]),
    state.reportDevice || ds[0].id,
  );
  const metric = select([["", l("Tất cả thông số", "All metrics")]]),
    start = input("datetime-local"),
    end = input("datetime-local"),
    out = div("stack");
  const root = div(
    "stack",
    card(
      "",
      div(
        "form-grid",
        field(t("devices"), device),
        field(l("Thông số", "Metric"), metric),
        field(l("Từ (giờ máy tính)", "From (computer time)"), start),
        field(l("Đến (không bao gồm)", "Until (exclusive)"), end),
      ),
    ),
    div(
      "row",
      btn(l("Xem dữ liệu", "View readings"), draw, "primary"),
      btn(l("Xuất CSV", "Export CSV"), () =>
        download(
          "/reports/telemetry?" + params(true),
          "solar-fleet-telemetry.csv",
        ),
      ),
      btn(l("In báo cáo", "Print report"), () => window.print()),
      btn(l("Xuất Excel", "Export Excel"), () =>
        download("/reports/telemetry.xlsx?" + params(), "solar-fleet.xlsx"),
      ),
    ),
    out,
  );
  function params(download = false) {
    const q = new URLSearchParams({ device_id: device.value });
    if (metric.value) q.set("metric", metric.value);
    if (start.value) q.set("start", new Date(start.value).toISOString());
    if (end.value) q.set("end", new Date(end.value).toISOString());
    if (download) q.set("download", "true");
    return q.toString();
  }
  async function draw() {
    state.reportDevice = device.value;
    const data = await api("/reports/telemetry?" + params());
    const metrics = [...new Set(data.rows.map((r) => r.metric))];
    if (!metric.value) {
      const opts = select([
        ["", l("Tất cả thông số", "All metrics")],
        ...metrics.map((m) => [m, m]),
      ]);
      metric.replaceChildren(...opts.children);
    }
    out.replaceChildren(
      notice(
        "Lưu tối đa 7 ngày. Chỉ số min/max áp dụng cho một thông số cùng đơn vị; chưa tính tổng kWh từ công suất rời rạc.",
        "Retention is up to 7 days. Min/max apply to one metric with matching units; sparse power readings are not summed into kWh.",
      ),
      kpis([
        ["▥", l("Số mẫu", "Samples"), number(data.sample_count, 0)],
        ["↓", l("Thấp nhất", "Minimum"), number(data.min)],
        ["↑", l("Cao nhất", "Maximum"), number(data.max)],
        ["◷", l("Lưu trữ (ngày)", "Retention (days)"), 7],
      ]),
    );
    if (data.truncated)
      out.append(
        notice(
          "Kết quả đạt giới hạn 10.000 mẫu. Thu hẹp khoảng thời gian.",
          "The result reached the 10,000-sample limit. Narrow the time range.",
          true,
        ),
      );
    if (metric.value)
      out.append(
        card(
          metric.value,
          plot(data.rows, metric.value),
          p(
            l(
              "Điểm đo gốc; chưa đối chiếu thiết bị. Di chuột để xem thời gian và nguồn.",
              "Native measurement points, not commissioned. Hover for time and source.",
            ),
          ),
        ),
      );
    out.append(
      card(
        l(
          "Mẫu dữ liệu (tối đa 200 dòng hiển thị)",
          "Readings (up to 200 displayed)",
        ),
        table(
          [
            t("lastSeen"),
            l("Thông số", "Metric"),
            l("Giá trị", "Value"),
            l("Đơn vị", "Unit"),
            l("Chất lượng", "Quality"),
          ],
          data.rows
            .slice(0, 200)
            .map((s) => [
              date(s.source_timestamp),
              s.metric,
              number(s.value),
              s.unit || "—",
              status(s.quality),
            ]),
        ),
      ),
    );
  }
  device.onchange = () =>
    run(async () => {
      metric.value = "";
      await draw();
    });
  metric.onchange = () => run(draw);
  await draw();
  return root;
}

function readRoute() {
  const [page, section = "main", tab = ""] = location.hash.slice(1).split("/");
  if (pages.includes(page)) {
    state.page = page;
    state.section = section;
    state.tab = tab;
  }
}
async function start() {
  readRoute();
  try {
    await load();
    await render();
  } catch (err) {
    if (!state.me) showLogin();
    else $("#root").replaceChildren(card(
      l("Không tải được không gian làm việc", "Could not load the workspace"),
      p(err.message), btn(l("Thử lại", "Retry"), start),
    ));
  }
}
window.addEventListener("hashchange", () => {
  if (state.me && location.hash.slice(1) !== routeHash()) {
    readRoute();
    run(render);
  }
});
window.addEventListener("keydown", (event) => {
  if (
    state.me &&
    (event.ctrlKey || event.metaKey) &&
    event.key.toLowerCase() === "k"
  ) {
    event.preventDefault();
    globalSearch();
  }
});
start();
