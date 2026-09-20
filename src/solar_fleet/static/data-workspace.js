import { l, t, date, number } from "./i18n.js";

export function createDataWorkspace(ui) {
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
    form,
    api,
    showDialog,
    closeDialog,
    refresh,
    admin,
    siteName,
    devices,
    deviceDetail,
    go,
  } = ui;
  const editor = () =>
    ["Installer", "Senior Engineer", "Administrator"].includes(
      state.me.user.role,
    );
  const name = (id) => state.fleet.devices.find((d) => d.id === id)?.name || id;
  async function view(section) {
    if (section === "collection" || section === "sync")
      return collection(section);
    const data = await api("/data-workspace");
    const rows = data.devices.filter(
      (d) => !state.site || d.site_id === state.site,
    );
    if (section === "mapping") return mappings(data);
    return div(
      "stack",
      div(
        "grid",
        ...[
          [
            l("Kênh dữ liệu", "Channels"),
            rows.reduce((n, d) => n + d.channels, 0),
          ],
          [
            l("Mẫu còn mới", "Fresh channels"),
            rows.reduce((n, d) => n + d.fresh, 0),
          ],
          [
            l("Đã xác minh và còn mới", "Verified and fresh"),
            rows.reduce((n, d) => n + d.verified, 0),
          ],
          [
            l("Dữ liệu không hợp lệ", "Invalid channels"),
            rows.reduce((n, d) => n + d.invalid, 0),
          ],
        ].map(([label, value]) =>
          card(label, e("strong", number(value, 0), "metric-value")),
        ),
      ),
      notice(
        "Độ mới và tính đúng của mapping là hai điều kiện riêng. Kênh còn mới chưa chắc đã dùng được cho EMS.",
        "Freshness and mapping validity are separate. A fresh channel is not necessarily usable by EMS.",
      ),
      card(
        l("Chất lượng theo thiết bị", "Quality by device"),
        table(
          [
            t("devices"),
            t("plants"),
            l("Kênh", "Channels"),
            l("Còn mới", "Fresh"),
            l("Đã xác minh", "Verified"),
            l("Không hợp lệ", "Invalid"),
            "",
          ],
          rows.map((d) => [
            name(d.device_id),
            siteName(d.site_id),
            d.channels,
            d.fresh,
            d.verified,
            d.invalid,
            btn(l("Xem dữ liệu", "View readings"), () =>
              deviceDetail(d.device_id),
            ),
          ]),
        ),
      ),
      div(
        "row",
        btn(l("Thiết lập mapping", "Configure mapping"), () =>
          go("reports", "", "mapping"),
        ),
        btn(l("Cấu hình thu thập", "Collection settings"), () =>
          go("reports", "", "collection"),
        ),
      ),
      card(
        l("Lưu trữ tại controller", "Controller retention"),
        fact(l("Ngày lưu tối đa", "Maximum days"), data.retention.days),
        fact(
          l("Giới hạn số điểm", "Point limit"),
          number(data.retention.max_points, 0),
        ),
      ),
    );
  }
  function mappings(data) {
    const rows = data.mappings.filter(
      (r) => !state.site || r.site_id === state.site,
    );
    return div(
      "stack",
      notice(
        "Lưu và duyệt mapping để đối chiếu. Kích hoạt dữ liệu chuẩn cần profile đúng model, firmware và biên bản nghiệm thu trong adapter.",
        "Save and review mappings for comparison. Canonical activation needs an exact model/firmware profile and acceptance record in the adapter.",
      ),
      editor()
        ? btn(
            l("+ Tạo mapping", "+ Create mapping"),
            () => edit(data),
            "primary",
          )
        : null,
      card(
        l("Bản đồ dữ liệu", "Data mapping"),
        table(
          [
            t("name"),
            t("devices"),
            l("Phiên bản", "Revision"),
            t("status"),
            l("Số kênh", "Channels"),
            "",
          ],
          rows.map((r) => [
            r.name,
            name(r.device_id),
            r.revision,
            badge(r.state),
            r.mappings.length,
            div(
              "row",
              btn(l("Xem / thử", "Inspect / simulate"), () => inspect(r)),
              editor() ? btn(l("Sửa", "Edit"), () => edit(data, r)) : null,
            ),
          ]),
        ),
      ),
    );
  }
  async function edit(data, existing) {
    const ds = devices();
    if (!ds.length) {
      showDialog(
        l("Mapping", "Mapping"),
        p(l("Cần có thiết bị trước.", "Register equipment first.")),
      );
      return;
    }
    const device = select(
      ds.map((d) => [d.id, d.name || d.vendor_id]),
      existing?.device_id,
    );
    if (existing) device.disabled = true;
    const binding = select([]),
      title = input("text", existing?.name || ""),
      evidence = input("text", existing?.evidence_ids.join(", ") || ""),
      notes = input("text", existing?.notes || ""),
      list = div("stack");
    let channels = [],
      available = [];
    async function loadSources() {
      const info = await api("/devices/" + device.value);
      available = info.latest.samples;
      const bindings = [
        ...data.bindings
          .filter((b) => b.device_id === device.value)
          .map((b) => b.id),
        ...(state.work.agents || [])
          .filter((a) => a.enabled && a.device_ids.includes(device.value))
          .map((a) => a.id),
      ];
      const choices = select(
        [...new Set(bindings)].map((id) => [id, id]),
        existing?.binding_id,
      );
      binding.replaceChildren(...choices.children);
      channels = [];
      list.replaceChildren();
      for (const row of existing?.mappings || [{}]) addChannel(row);
    }
    function addChannel(row = {}) {
      const key = input("text", row.source_key || "");
      const candidates = available.filter(
        (s) => s.binding_id === binding.value,
      );
      const source = select([
        ["", l("Chọn kênh đang có", "Choose observed channel")],
        ...candidates.map((s) => [s.metric, `${s.metric} (${s.unit || "?"})`]),
      ]);
      const unit = select(
          data.units.map((u) => [u, u]),
          row.source_unit || "W",
        ),
        metric = select(
          Object.entries(data.metrics).map(([m, u]) => [m, `${m} (${u})`]),
          row.metric,
        ),
        direction = select(
          [
            ["nonnegative", l("Giá trị không âm", "Nonnegative")],
            ["positive", l("Lấy chiều dương", "Positive direction")],
            ["negative", l("Lấy chiều âm", "Negative direction")],
            ["signed", l("Nhiệt độ có dấu", "Signed temperature")],
          ],
          row.direction,
        );
      source.onchange = () => {
        key.value = source.value;
        const s = candidates.find((s) => s.metric === source.value);
        if (s?.unit) unit.value = s.unit;
      };
      const entry = {
        read: () => ({
          source_key: key.value,
          source_unit: unit.value,
          metric: metric.value,
          direction: direction.value,
        }),
      };
      const item = card(
        l("Quy đổi kênh", "Channel mapping"),
        div(
          "form-grid",
          field(l("Kênh có sẵn", "Observed channel"), source),
          field(l("Tên kênh gốc đầy đủ", "Full native channel key"), key),
          field(l("Đơn vị gốc", "Source unit"), unit),
          field(l("Thông số chuẩn", "Canonical metric"), metric),
          field(l("Quy ước chiều", "Direction convention"), direction),
        ),
        btn(l("Bỏ kênh", "Remove channel"), () => {
          channels = channels.filter((c) => c !== entry);
          item.remove();
        }),
      );
      channels.push(entry);
      list.append(item);
    }
    device.onchange = () => loadSources();
    binding.onchange = () => {
      channels = [];
      list.replaceChildren();
      addChannel();
    };
    const f = form(async () => {
      await api(existing ? "/mappings/" + existing.id : "/mappings", {
        device_id: device.value,
        name: title.value,
        binding_id: binding.value,
        evidence_ids: evidence.value
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        notes: notes.value,
        mappings: channels.map((c) => c.read()),
        revision: existing?.revision || 0,
      });
      closeDialog();
      await refresh();
    });
    f.prepend(
      div(
        "form-grid",
        field(t("name"), title),
        field(t("devices"), device),
        field(l("Nguồn kết nối", "Binding"), binding),
        field(
          l(
            "ID tài liệu bằng chứng, cách nhau dấu phẩy",
            "Evidence IDs, comma separated",
          ),
          evidence,
        ),
        field(l("Ghi chú về đơn vị / chiều", "Unit / direction notes"), notes),
      ),
      list,
      btn(l("+ Thêm kênh", "+ Add channel"), () => addChannel()),
    );
    await loadSources();
    showDialog(l("Thiết lập mapping", "Mapping editor"), f);
  }
  async function inspect(row) {
    const output = div("stack"),
      root = div(
        "stack",
        fact(t("devices"), name(row.device_id)),
        fact(l("Bản sửa đổi", "Revision"), row.revision),
        badge(row.state),
        raw(l("Cấu hình", "Configuration"), row.mappings),
        btn(
          l("Thử với mẫu hiện có", "Simulate observed samples"),
          async () => {
            const result = await api("/mappings/" + row.id + "/simulate", {});
            output.replaceChildren(
              table(
                [
                  l("Kênh gốc", "Source"),
                  l("Kênh chuẩn", "Target"),
                  t("value"),
                  t("status"),
                ],
                result.results.map((r) => [
                  r.mapping.source_key,
                  r.mapping.metric,
                  `${number(r.value)} ${r.unit}`,
                  badge(r.result),
                ]),
              ),
              p(
                l(
                  "Chỉ xem trước. Không lưu mẫu chuẩn, không gửi lệnh.",
                  "Preview only. No canonical samples stored and no commands sent.",
                ),
              ),
            );
          },
          "primary",
        ),
        output,
        btn(l("Xem lịch sử phiên bản", "Version history"), async () => {
          const versions = await api("/mappings/" + row.id + "/versions");
          output.replaceChildren(
            raw(l("Phiên bản và review", "Versions and reviews"), versions),
          );
        }),
      );
    if (
      state.me.user.role === "Senior Engineer" &&
      row.author !== state.me.user.id &&
      row.state === "DRAFT"
    ) {
      const decision = select([
          ["REVIEWED", l("Đã đối chiếu", "Reviewed")],
          ["CHANGES_REQUESTED", l("Cần sửa", "Changes requested")],
        ]),
        notes = input("text");
      const f = form(async () => {
        await api("/mappings/" + row.id + "/review", {
          revision: row.revision,
          outcome: decision.value,
          notes: notes.value,
        });
        closeDialog();
        await refresh();
      });
      f.prepend(
        field(l("Kết luận review", "Review outcome"), decision),
        field(l("Ghi chú kiểm tra", "Review notes"), notes),
      );
      root.append(f);
    }
    showDialog(row.name, root);
  }
  async function collection(section) {
    if (!admin())
      return card(
        l("Cấu hình tài khoản dùng chung", "Shared account configuration"),
        p(
          l(
            "Quản trị viên tổ chức quản lý chu kỳ thu thập và nhật ký đồng bộ của tài khoản cloud.",
            "The organization administrator manages cloud polling and sync logs.",
          ),
        ),
      );
    const data = await api("/collection");
    return div(
      "stack",
      notice(
        "Chu kỳ là mục tiêu của controller, phụ thuộc tick 120 giây và quota adapter. Không thay đổi tần suất đo của inverter.",
        "The interval is a controller target, subject to its 120-second tick and adapter quotas. It does not change the inverter sample rate.",
      ),
      card(
        section === "sync"
          ? l("Nhật ký đồng bộ gần nhất", "Latest sync status")
          : l("Cấu hình thu thập", "Collection settings"),
        table(
          [
            t("name"),
            l("Chu kỳ (giây)", "Interval (s)"),
            l("Thiết bị / lượt", "Devices / poll"),
            t("status"),
            l("Lần thử gần nhất", "Last attempt"),
            "",
          ],
          data.connections.map((c) => [
            c.name,
            c.policy.interval_seconds,
            c.policy.max_devices_per_poll,
            badge(c.state?.state || "NO_DATA"),
            date(c.state?.last_attempt),
            div(
              "row",
              btn(l("Chi tiết", "Details"), () =>
                showDialog(
                  c.name,
                  raw(l("Kết quả đồng bộ", "Sync outcome"), c),
                ),
              ),
              btn(l("Chỉnh sửa", "Edit"), () => {
                const interval = input("number", c.policy.interval_seconds),
                  size = input("number", c.policy.max_devices_per_poll);
                interval.min = "120";
                interval.max = "3600";
                size.min = "1";
                size.max = "50";
                const f = form(async () => {
                  await api("/collection/" + c.integration_id, {
                    interval_seconds: Number(interval.value),
                    max_devices_per_poll: Number(size.value),
                    revision: c.policy.revision,
                  });
                  closeDialog();
                  await refresh();
                });
                f.prepend(
                  field(
                    l("Chu kỳ mục tiêu (giây)", "Target interval (s)"),
                    interval,
                  ),
                  field(
                    l("Giới hạn thiết bị / lượt", "Maximum devices / poll"),
                    size,
                  ),
                );
                showDialog(c.name, f);
              }),
            ),
          ]),
        ),
      ),
      p(
        l(
          "Lưu tối đa 7 ngày / 200.000 điểm. Backfill lịch sử từ cloud chưa triển khai.",
          "Retention: up to 7 days / 200,000 points. Cloud history backfill is not implemented.",
        ),
      ),
    );
  }
  return { view };
}
