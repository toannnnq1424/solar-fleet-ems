import { l } from "./i18n.js";

function downloadJson(value, name) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function renderModelLibrary(ui, devices) {
  const { e, div, p, btn, badge, card, table, field, notice, api, go, state } = ui;
  const root = div("stack");
  const response = await api("/model-library");
  const catalog = response.profiles;
  const search = e("input", "", "input-search");
  search.placeholder = l("Tìm hãng, model hoặc profile…", "Find a brand, model or profile…");
  search.setAttribute("aria-label", l("Tìm profile", "Find profile"));
  const list = div("stack");
  const detail = div("stack");
  let selectedProfile = null;
  let selectedFields = new Set();
  let generation = 0;
  root.append(notice(
    "Thư viện model cộng đồng: chọn đúng inverter và logger trước khi lập cấu hình. Các profile chưa được nghiệm thu tại công trình. Xem trước và giải mã bên dưới không kết nối thiết bị.",
    "Community model library: identify the inverter and logger before configuring collection. Profiles are not accepted at your installation. Preview and decoding below do not connect to devices."
  ), div("row", badge(`${catalog.length} profiles`, "blue"),
    badge(l("Chỉ đọc · chưa nghiệm thu", "Read only · not commissioned"), "warn"),
    btn(l("Quản lý Local Agent", "Manage Local Agents"), () => go("settings", "agents", "main")),
    btn(l("Ánh xạ dữ liệu", "Data mapping"), () => go("reports", "mapping", "main"))), search, list, detail);

  function renderList() {
    const q = search.value.trim().toLowerCase();
    const matches = catalog.filter(x => `${x.name} ${x.manufacturer} ${x.models.join(" ")}`.toLowerCase().includes(q));
    list.replaceChildren(table([
      l("Hãng / model", "Brand / model"), l("Nguồn", "Source"),
      l("Trường đọc / tổng", "Readable / total"), l("Thao tác", "Actions")
    ], matches.map(x => [div("", e("b", x.name), p(x.manufacturer, "small muted")),
      `${x.source_id} · ${x.license}`, `${x.readable_count} / ${x.field_count}`,
      btn(l("Mở profile", "Open profile"), () => openProfile(x.id))])));
  }
  search.oninput = renderList;
  renderList();

  async function openProfile(id) {
    const request = ++generation;
    detail.replaceChildren(p(l("Đang tải profile…", "Loading profile…")));
    try {
      const profile = await api(`/model-library/${encodeURIComponent(id)}`);
      if (request !== generation) return;
      selectedProfile = profile;
      selectedFields = new Set();
      const result = div("stack");
      const filter = e("input", "", "input-search");
      filter.placeholder = l("Lọc thông số…", "Filter parameters…");
      filter.setAttribute("aria-label", l("Lọc thông số", "Filter parameters"));
      const count = p(l("Chưa chọn thông số", "No parameters selected"), "small muted");
      const rows = div("stack");
      function renderFields() {
        const visible = profile.fields.filter(f => `${f.name} ${f.group}`.toLowerCase().includes(filter.value.toLowerCase()));
        rows.replaceChildren(table([
          l("Chọn", "Select"), l("Thông số", "Parameter"), l("Địa chỉ / hàm đọc", "Address / function"),
          l("Đơn vị", "Unit"), l("Khả năng giải mã", "Decoding")
        ], visible.map(f => {
          const check = e("input"); check.type = "checkbox";
          check.checked = selectedFields.has(f.id); check.disabled = !f.decode;
          check.setAttribute("aria-label", `${l("Chọn", "Select")} ${f.name}`);
          check.onchange = () => {
            if (check.checked && selectedFields.size >= 100) { check.checked = false; return; }
            if (check.checked) selectedFields.add(f.id); else selectedFields.delete(f.id);
            count.textContent = `${selectedFields.size} / 100 ${l("thông số đã chọn", "parameters selected")}`;
            result.replaceChildren();
          };
          return [check, div("", e("b", f.name), p(f.id, "small muted")),
            f.decode ? `FC${f.decode.function} · ${f.decode.registers.join(", ")}` : "—", f.unit || "—",
            f.decode ? badge(l("Có bộ giải mã", "Decoder available"), "blue") : p(f.blocked_reason, "small muted")];
        })));
      }
      filter.oninput = renderFields;
      const raw = e("textarea", "", "input-search");
      raw.rows = 6; raw.value = "[]";
      raw.setAttribute("aria-label", l("Dữ liệu thanh ghi JSON", "Register readings JSON"));
      raw.placeholder = '[{"function":3,"address":0,"value":0}]';
      async function run(kind) {
        const body = { profile_digest: profile.profile_digest, field_ids: [...selectedFields] };
        try {
          if (kind === "decode") body.readings = JSON.parse(raw.value);
          const value = await api(`/model-library/${encodeURIComponent(id)}/${kind}`, body);
          if (request !== generation) return;
          if (kind === "plan") {
            result.replaceChildren(card(l("Kế hoạch đọc", "Read plan"),
              p(l("Chưa gửi yêu cầu đến thiết bị.", "No request has been sent to a device.")),
              table(["FC", l("Bắt đầu", "Start"), l("Số thanh ghi", "Register count")],
                value.blocks.map(b => [String(b.function), String(b.address), String(b.count)])),
              btn(l("Tải kế hoạch JSON", "Download plan JSON"), () => downloadJson(value, "read-plan.json"))));
          } else {
            result.replaceChildren(table([l("Thông số", "Parameter"), l("Giá trị", "Value"),
              l("Chất lượng", "Quality"), l("Lý do", "Reason")], value.results.map(r => [r.name,
                r.value === null ? "—" : `${r.value} ${r.unit || ""}`, badge(r.quality, r.quality === "UNVERIFIED" ? "warn" : "gray"), r.reason || "—"])));
          }
        } catch (err) { result.replaceChildren(p(err.message, "bad")); }
      }
      const origin = e("a", l("Xem nguồn và license", "View source and license"));
      origin.href = profile.source_url; origin.target = "_blank"; origin.rel = "noopener noreferrer";
      detail.replaceChildren(card(profile.name,
        div("row", origin, badge(profile.transport_hint, "gray")),
        p(`${l("Phiên bản profile", "Profile revision")}: ${profile.profile_digest}`, "small monospace"),
        p(profile.limitations.join(" "), "small muted"), filter, count, rows,
        div("row", btn(l("Xem kế hoạch đọc", "Preview read plan"), () => run("plan"), "primary"),
          btn(l("Soạn cấu hình Agent", "Prepare Agent configuration"), () => editCollection("model"))),
        field(l("Dữ liệu đã đọc (JSON: function, address, value)", "Collected readings (JSON: function, address, value)"), raw),
        btn(l("Giải mã dữ liệu", "Decode readings"), () => run("decode"))), result);
      renderFields();
    } catch (err) { if (request === generation) detail.replaceChildren(p(err.message, "bad")); }
  }

  const setup = div("stack");
  root.append(card(l("Kết nối hệ thống nhà ở", "Connect your home energy system"),
    p(l("Đọc sensor từ Home Assistant, kể cả sensor do SEM hoặc EMHASS cung cấp. Chọn rõ entity, thiết bị đích và đơn vị; dữ liệu đi qua Local Agent và màn ánh xạ chung.",
      "Read Home Assistant sensors, including sensors exposed by SEM or EMHASS. Bind explicit entities, target devices and units; readings use the Local Agent and shared mapping workflow.")),
    btn(l("Soạn cấu hình Home Assistant", "Prepare Home Assistant configuration"), () => editCollection("home-assistant"))), setup);

  function editCollection(kind) {
    const target = state.selectedInspectorDevice || devices[0]?.id || "";
    let draft;
    if (kind === "model") {
      draft = { agent_id: "", device_id: target, profile_id: selectedProfile.id,
        profile_digest: selectedProfile.profile_digest, field_ids: [...selectedFields], transport: "modbus_tcp",
        address: "", port: 502, unit_id: selectedProfile.unit_id_hint || 1,
        inverter_model: "", inverter_firmware: "", logger_model: "", logger_firmware: "",
        reviewed_by: "", evidence_reference: "" };
    } else {
      draft = { agent_id: "", base_url: "", bindings: [{ entity_id: "sensor.", device_id: target, expected_unit: "W" }],
        reviewed_by: "", evidence_reference: "", max_age_seconds: 300 };
    }
    const editor = e("textarea", "", "input-search monospace"); editor.rows = 18;
    editor.value = JSON.stringify(draft, null, 2);
    editor.setAttribute("aria-label", l("Cấu hình thu thập JSON", "Collection configuration JSON"));
    const feedback = div("stack");
    setup.replaceChildren(card(l("Cấu hình thu thập tại chỗ", "Local collection configuration"),
      p(l("Điền thông tin công trình và Agent đã đăng ký. Token đặt bằng biến môi trường trên Agent. Kiểm tra dưới đây chỉ xác nhận cấu trúc và phạm vi truy cập.",
        "Enter the installation details and a registered Agent. Set tokens through Agent environment variables. Validation below checks structure and access scope only.")),
      editor, btn(l("Kiểm tra và tải cấu hình", "Validate and download configuration"), async () => {
        try {
          const value = await api(`/local-collection/${kind}/validate`, JSON.parse(editor.value));
          feedback.replaceChildren(notice("Cấu hình hợp lệ. Chưa thử kết nối thiết bị.", "Configuration valid. Device connectivity has not been tested."));
          downloadJson(value.config, `${kind}-collection.json`);
        } catch (err) { feedback.replaceChildren(p(err.message, "bad")); }
      }, "primary"), feedback));
    setup.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
  return root;
}
