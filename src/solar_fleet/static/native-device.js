import { l, t, language } from "./i18n.js";

export function nativeDevice(ui, info) {
  const { div, p, card, tabs, table, badge, btn, notice, controlForm, principal } = ui;
  const root = div("stack"),
    content = div("stack"),
    adapter = info.adapter;
  if (!adapter.groups.length)
    return card(
      l("Theo hãng / OEM", "Vendor / OEM native"),
      p(
        l(
          "Chưa có mô tả thông số cho adapter này. Cần hợp đồng theo model và nền tảng kết nối thực tế.",
          "This adapter has no parameter descriptor yet. The exact model and actual platform contract are required.",
        ),
      ),
    );
  const groups = adapter.groups.map((g) => ({ ...g, intents: [...g.intents] }));
  for (const profile of info.control_profiles || []) {
    const group = groups.find((g) => g.id === profile.group);
    if (group && !group.intents.includes(profile.intent)) group.intents.push(profile.intent);
  }
  const remaining = info.capabilities.filter((c) => !groups.some((g) => g.intents.includes(c.intent)));
  const advanced = groups.find((g) => g.id === "advanced");
  if (advanced) advanced.intents.push(...remaining.map((c) => c.intent));
  function draw(id) {
    const group = groups.find((g) => g.id === id),
      capabilities = info.capabilities.filter((c) =>
        group.intents.includes(c.intent),
      );
    content.replaceChildren(
      tabs(
        groups.map((g) => [g.id, g.label[language] || g.label.en]),
        id,
        draw,
      ),
      card(
        `${adapter.id} · ${group.label[language] || group.label.en}`,
        capabilities.length
          ? table(
              [
                l("Tham số / mục đích", "Parameter / intent"),
                t("status"),
                l("Cách áp dụng", "Semantics"),
                "",
              ],
              capabilities.map((c) => [
                t(c.intent),
                badge(c.state),
                badge(c.semantic_match),
                c.state === "VERIFIED" &&
                c.hardware_verified &&
                c.semantic_match === "exact" &&
                ({Operator: 1, Installer: 2, "Senior Engineer": 3}[principal?.role] || 0) >=
                  ({Operator: 1, Installer: 2, "Senior Engineer": 3}[c.required_role] || 99) &&
                (!c.required_permission || principal?.permissions?.includes(c.required_permission))
                  ? btn(l("Thiết lập", "Configure"), () =>
                      controlForm(info.device, c),
                    )
                  : p(
                      l(
                        "Chưa nghiệm thu model và readback.",
                        "Model and readback not commissioned.",
                      ),
                    ),
              ]),
            )
          : p(
              l(
                "Chưa có trường hoặc hợp đồng được xác minh cho nhóm này. Không tự tạo thanh ghi hay giá trị giới hạn.",
                "No verified fields or contract for this group yet. Registers and limits are not inferred.",
              ),
            ),
      ),
    );
  }
  root.append(
    notice(
      "Thông số hiển thị theo adapter, còn quyền thực thi được kiểm tra theo thiết bị. Dữ liệu gốc của hãng không phải lệnh có thể gửi tự do.",
      "Descriptors come from the adapter; execution is validated per device. Vendor data does not expose arbitrary command submission.",
    ),
    ...(info.control_profiles?.length ? [card(l("Hồ sơ áp dụng cho thiết bị", "Device acceptance profiles"),
      table([l("Mục đích", "Intent"), l("Mức tương thích", "Compatibility"), l("Giải thích", "Explanation"), l("Hết hạn nghiệm thu", "Acceptance expires")],
        info.control_profiles.map((profile) => [t(profile.intent), badge(profile.semantics),
          profile.explanation[language] || profile.explanation.en, profile.expires_at])))] : []),
    content,
  );
  draw(groups[0].id);
  return root;
}
