import { registerReadingsEditor, collectionEditor } from "./collection-editor.js";
import { l } from "./i18n.js";

function downloadJson(value, name) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function renderModelLibrary(ui, devices) {
  const { e, div, p, btn, badge, card, table, notice, api, go } = ui;
  const root = div("stack model-library");
  const response = await api("/model-library");
  const catalog = response.profiles;
  const search = e("input", "", "input-search");
  search.placeholder = l("Tìm hãng, model hoặc profile…", "Find a brand, model or profile…");
  search.setAttribute("aria-label", l("Tìm profile", "Find profile"));
  const list = div("stack model-profile-list");
  const detail = div("stack model-profile-detail", card(l("Chi tiết model", "Model details"), p(l("Chọn một model để xem thông số, kế hoạch đọc và công cụ giải mã.", "Choose a model to inspect parameters, read plans and decoding tools."), "empty-state")));
  let selectedProfile = null;
  let selectedFields = new Set();
  let generation = 0;
  root.append(notice(
    "Thư viện model cộng đồng: chọn đúng inverter và logger trước khi lập cấu hình. Các profile chưa được nghiệm thu tại công trình. Xem trước và giải mã bên dưới không kết nối thiết bị.",
    "Community model library: identify the inverter and logger before configuring collection. Profiles are not accepted at your installation. Preview and decoding below do not connect to devices."
  ), div("row", badge(`${catalog.length} profiles`, "blue"),
    badge(l("Chỉ đọc · chưa nghiệm thu", "Read only · not commissioned"), "warn"),
    btn(l("Quản lý Local Agent", "Manage Local Agents"), () => go("settings", "agents", "main")),
    btn(l("Ánh xạ dữ liệu", "Data mapping"), () => go("reports", "mapping", "main"))), search, div("model-library-layout",list,detail));

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
      const readings = registerReadingsEditor(ui,()=>result.replaceChildren());
      async function run(kind) {
        const body = { profile_digest: profile.profile_digest, field_ids: [...selectedFields] };
        try {
          if (kind === "decode") body.readings = readings.read();
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
        readings.root,
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
    const profile=kind==='model'?selectedProfile:null;
    const ids=[...selectedFields];
    setup.replaceChildren(collectionEditor(ui,kind,devices,profile,ids,config=>downloadJson(config,kind+'-collection.json')));
    setup.scrollIntoView({ block: "nearest", behavior: "instant" });
  }
  return root;
}
