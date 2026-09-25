import { l, t, date, number } from "./i18n.js";

// Route content only. Every element uses the global components and layout tokens.
export async function accountsView(ui) {
  const {
    state,
    e,
    add,
    div,
    p,
    btn,
    badge,
    card,
    raw,
    field,
    input,
    select,
    table,
    api,
    form,
    showDialog,
    closeDialog,
    refresh,
    admin,
    go,
    integrationForm,
    icon,
  } = ui;
  const allowed = admin();
  const data = allowed ? await api("/accounts/overview") : null;
  const brand = (name) => {
    const el = e("span", name, "vendor-wordmark");
    el.dataset.vendor = name;
    return el;
  };
  const providers = [...state.providers].sort((a, b) => {
    const order = [
      "Deye",
      "Solis",
      "GoodWe",
      "Sungrow",
      "Huawei",
      "Growatt",
      "SOLARMAN",
      "Bluesun",
      "Eybond / SmartESS",
    ];
    return order.indexOf(a.id) - order.indexOf(b.id);
  });
  function connect(spec) {
    if (spec.id === "Bluesun") {
      const root = div(
        "stack",
        p(
          l(
            "Chọn nền tảng thực tế đang quản lý nhà máy Bluesun của bạn.",
            "Choose the platform that actually manages your Bluesun plant.",
          ),
        ),
        card(
          "SOLARMAN Cloud",
          p(
            l(
              "Dùng khi nhà máy xuất hiện trong tài khoản SOLARMAN được cấp quyền.",
              "Use when the plant appears in your authorized SOLARMAN account.",
            ),
          ),
          btn(
            l("Kết nối tài khoản SOLARMAN", "Connect SOLARMAN account"),
            () =>
              integrationForm({
                ...state.providers.find((p) => p.id === "SOLARMAN"),
                equipment_brand: "Bluesun",
              }),
            "primary",
          ),
        ),
        card(
          l("Logger SOLARMAN tại công trình", "SOLARMAN logger on site"),
          p(
            l(
              "BSE15KH3 và BSE12KH3 có profile cộng đồng khác nhau. Xác nhận model, firmware và logger trước khi cấu hình Local Agent.",
              "BSE15KH3 and BSE12KH3 have different community profiles. Confirm model, firmware and logger before configuring the Local Agent.",
            ),
          ),
          btn(l("Quản lý Local Agent", "Manage Local Agents"), () => {
            closeDialog();
            return go("settings", "", "agents");
          }),
        ),
        card(
          "SmartESS / Eybond",
          p(
            l(
              "Dùng khi thiết bị Bluesun của bạn đã xuất hiện trên SmartESS / DessMonitor. Chọn đúng nền tảng khi đăng nhập; dữ liệu theo model vẫn cần đối chiếu.",
              "Use when your Bluesun device appears in SmartESS / DessMonitor. Select its actual account platform; model-specific data still needs verification.",
            ),
          ),
          btn(l("Kết nối SmartESS / Eybond", "Connect SmartESS / Eybond"), () => integrationForm({
            ...state.providers.find((p) => p.id === "Eybond / SmartESS"), equipment_brand: "Bluesun",
          }), "primary"),
        ),
      );
      showDialog(l("Thêm Bluesun Solar", "Add Bluesun Solar"), root);
    } else if (spec.implemented) integrationForm(spec);
    else
      showDialog(
        spec.id,
        p(
          l(
            "Hãng đã có trong danh mục nghiên cứu. Cần hoàn thiện adapter và đối chiếu tài khoản trước khi kết nối.",
            "This vendor is in the research catalogue. Its adapter and account contract need to be completed before connecting.",
          ),
        ),
        btn(
          l("Xem tài liệu và mức hỗ trợ", "View evidence and support"),
          () => {
            closeDialog();
            return go("settings", "evidence");
          },
        ),
      );
  }
  function addAccount() {
    showDialog(
      l("Thêm tài khoản hãng", "Add vendor account"),
      p(
        l(
          "Chọn hãng inverter hoặc nền tảng logger.",
          "Choose an inverter manufacturer or logger platform.",
        ),
      ),
      div(
        "grid three",
        ...providers.map((spec) => {
          const button = btn("", () => connect(spec), "choice-card");
          add(
            button,
            brand(spec.id),
            e(
              "span",
              spec.id === "Bluesun"
                ? l("Qua SmartESS / SOLARMAN / Local Agent", "Via SmartESS / SOLARMAN / Local Agent")
                : spec.implemented
                  ? l("Có kết nối đọc dữ liệu", "Read connector available")
                  : l("Đang nghiên cứu", "Research in progress"),
              "small muted",
            ),
          );
          return button;
        }),
      ),
    );
  }
  function accountActions(row) {
    showDialog(
      row.name,
      div(
        "stack",
        p(row.account),
        p(`${row.vendor} · ${row.region}`),
        row.equipment_brand
          ? p(l("Hãng khai báo: ", "Declared brand: ") + row.equipment_brand)
          : null,
        btn(
          l("Kiểm tra kết nối", "Check connection"),
          () => {
            closeDialog();
            vendor.value = row.equipment_brand || row.vendor;
            populate(row.id);
            return runCheck();
          },
          "primary",
        ),
        btn(
          l("Khám phá & đồng bộ danh mục", "Discover & synchronize inventory"),
          async () => {
            await api("/sync", {});
            closeDialog();
            await refresh();
          },
        ),
        btn(
          row.enabled
            ? l("Tạm dừng đồng bộ", "Pause synchronization")
            : l("Bật lại đồng bộ", "Resume synchronization"),
          async () => {
            await api(`/integrations/${row.id}/enabled`, {
              enabled: !row.enabled,
            });
            closeDialog();
            await refresh();
          },
        ),
        raw(
          l("Thông tin chẩn đoán gần nhất", "Latest diagnostic"),
          row.diagnostic || { state: "NOT_CHECKED" },
        ),
      ),
    );
  }
  const rows = [];
  for (const spec of providers) {
    const accounts = (data?.accounts || []).filter(
      (a) => (a.equipment_brand || a.vendor) === spec.id,
    );
    if (accounts.length)
      for (const account of accounts) {
        const check = account.diagnostic;
        const ok = check?.state === "PASS";
        const access = div(
          "stack-tight",
          e("span", l("Đọc dữ liệu", "Read data")),
          e(
            "span",
            l("Điều khiển chưa nghiệm thu", "Control not commissioned"),
            "small muted",
          ),
        );
        const auth = div(
          "stack-tight",
          badge(
            !account.enabled
              ? l("Tạm dừng", "Paused")
              : ok
                ? l("Đã xác thực", "Authenticated")
                : check?.state === "FAILED"
                  ? l("Cần kiểm tra", "Needs attention")
                  : l("Chưa kiểm tra", "Not checked"),
            ok && account.enabled
              ? "good"
              : check?.state === "FAILED"
                ? "warn"
                : "",
          ),
          e(
            "span",
            account.authentication === "API_KEY"
              ? "API key"
              : l("Hạn token: chưa có dữ liệu", "Token expiry: unavailable"),
            "small muted",
          ),
        );
        const last = account.status?.last_success;
        const action = btn("⋯", () => accountActions(account), "icon-button");
        action.setAttribute(
          "aria-label",
          l("Thao tác tài khoản ", "Account actions: ") + account.name,
        );
        rows.push([
          brand(spec.id),
          div(
            "stack-tight",
            e("span", account.account),
            e("span", account.name, "small muted"),
          ),
          access,
          auth,
          `${account.plant_count} ${l("nhà máy", "plants")}`,
          div(
            "stack-tight",
            e("span", last ? date(last) : "—"),
            e(
              "span",
              last
                ? l("Đã đồng bộ", "Synchronized")
                : l("Chưa đồng bộ", "Not synced"),
              "small muted",
            ),
          ),
          action,
        ]);
      }
    else {
      const action = allowed
        ? btn("+", () => connect(spec), "icon-button")
        : e("span", "—");
      if (allowed)
        action.setAttribute("aria-label", l("Kết nối ", "Connect ") + spec.id);
      rows.push([
        brand(spec.id),
        e("span", l("Chưa liên kết", "Not linked"), "muted"),
        e("span", "—"),
        badge(
          spec.id === "Bluesun"
            ? l("Có đường tích hợp", "Integration paths")
            : spec.implemented
              ? l("Sẵn sàng kết nối", "Connector available")
              : l("Đang nghiên cứu", "Researching"),
        ),
        "—",
        "—",
        action,
      ]);
    }
  }
  const accountCard = card(
    "",
    div(
      "card-head",
      div(
        "",
        e("h2", l("Tài khoản hãng đã liên kết", "Linked vendor accounts")),
        p(
          l(
            "Quản lý tài khoản cloud của hãng để thu thập dữ liệu, giám sát và điều khiển (nếu hỗ trợ).",
            "Manage vendor cloud accounts for data collection, monitoring and control where supported.",
          ),
        ),
      ),
      allowed
        ? btn(
            l("+ Thêm tài khoản hãng", "+ Add vendor account"),
            addAccount,
            "primary",
          )
        : null,
    ),
    table(
      [
        l("Hãng", "Vendor"),
        l("Email / tài khoản", "Email / account"),
        l("Phạm vi truy cập", "Access scope"),
        l("Trạng thái xác thực", "Authentication"),
        l("Nhà máy được phép", "Allowed plants"),
        l("Lần đồng bộ cuối", "Last synchronized"),
        l("Thao tác", "Actions"),
      ],
      rows,
    ),
  );

  const vendor = select(
    providers.map((s) => [s.id, s.id]),
    data?.accounts[0]?.equipment_brand || data?.accounts[0]?.vendor || "Deye",
  );
  const account = select([]),
    resultPanel = div("stack");
  const checks = {
    api: l("Kết nối API", "API connection"),
    authentication: l("Xác thực tài khoản", "Account authentication"),
    plants: l("Lấy danh sách nhà máy", "List plants"),
    devices: l("Lấy thiết bị (một nhà máy)", "Read devices (one plant)"),
    sample: l("Lấy dữ liệu thiết bị (mẫu)", "Read sample measurements"),
    control: l("Quyền điều khiển (nếu có)", "Control readiness"),
  };
  const states = {
    PASS: l("Thành công", "Passed"),
    FAILED: l("Thất bại", "Failed"),
    NO_DATA: l("Chưa có dữ liệu", "No data"),
    NOT_CHECKED: l("Chưa kiểm tra", "Not checked"),
    NOT_COMMISSIONED: l("Chưa nghiệm thu", "Not commissioned"),
  };
  function showResult(result) {
    resultPanel.replaceChildren();
    const pass = result?.state === "PASS",
      failed = result?.state === "FAILED";
    const summary = div(
      `notice ${pass ? "success" : failed ? "warning" : ""}`,
      div(
        "row",
        icon(pass ? "check" : failed ? "alert" : "info"),
        div(
          "",
          e(
            "strong",
            pass
              ? l("Kết nối thành công", "Connection successful")
              : failed
                ? l("Cần kiểm tra kết nối", "Connection needs attention")
                : l("Chưa kiểm tra kết nối", "Connection not checked"),
          ),
          p(
            pass
              ? l(
                  "Đã kiểm tra các bước đọc bên dưới.",
                  "Read checks are listed below.",
                )
              : l(
                  "Chọn tài khoản và kiểm tra để có kết quả thực tế.",
                  "Select an account and run a check for current results.",
                ),
          ),
        ),
      ),
      result ? e("span", date(result.checked_at), "small") : null,
    );
    resultPanel.append(
      summary,
      e("h3", l("Kiểm tra chi tiết", "Detailed checks")),
    );
    for (const [key, label] of Object.entries(checks)) {
      const row = result?.checks?.find((x) => x.key === key),
        value = row?.state || "NOT_CHECKED";
      resultPanel.append(
        div(
          "check-result",
          icon(
            value === "PASS"
              ? "check"
              : value === "FAILED"
                ? "alert"
                : "circle",
          ),
          e("span", label),
          e(
            "strong",
            states[value] || value,
            value === "PASS"
              ? "text-success"
              : value === "FAILED"
                ? "text-danger"
                : "muted",
          ),
        ),
      );
    }
    if (result)
      resultPanel.append(
        btn(
          l("▤ Xem chi tiết phản hồi", "▤ View response details"),
          () =>
            showDialog(
              l("Kết quả kiểm tra", "Check result"),
              raw(
                l("Chi tiết đã loại dữ liệu nhạy cảm", "Sanitized details"),
                result,
              ),
            ),
          "full-width",
        ),
      );
  }
  function populate(id) {
    account.replaceChildren();
    const matching = (data?.accounts || []).filter(
      (a) => (a.equipment_brand || a.vendor) === vendor.value,
    );
    for (const row of matching) {
      const opt = e("option", row.account);
      opt.value = row.id;
      account.append(opt);
    }
    if (!matching.length) {
      const opt = e(
        "option",
        l("Chưa liên kết tài khoản", "No linked account"),
      );
      opt.value = "";
      account.append(opt);
    }
    if (id) account.value = id;
    account.disabled = !matching.length;
    checkButton.disabled =
      !allowed || !matching.some((a) => a.id === account.value && a.enabled);
    showResult(matching.find((a) => a.id === account.value)?.diagnostic);
  }
  async function runCheck() {
    const id = account.value;
    if (!id) return;
    resultPanel.replaceChildren(
      p(
        l(
          "Đang kiểm tra quyền đọc và dữ liệu…",
          "Checking read access and data…",
        ),
      ),
    );
    try {
      const result = await api(`/integrations/${id}/check`, {});
      const saved = data.accounts.find((a) => a.id === id);
      if (saved) saved.diagnostic = result;
      showResult(result);
    } catch (error) {
      resultPanel.replaceChildren(
        div(
          "notice warning",
          e("strong", l("Chưa hoàn tất kiểm tra", "Check did not finish")),
          p(error.message),
        ),
      );
    }
  }
  const checkButton = btn(
    l("▷ Kiểm tra kết nối", "▷ Check connection"),
    runCheck,
    "primary full-width",
  );
  vendor.onchange = () => populate();
  account.onchange = () => populate(account.value);
  populate();
  const diagnostic = card(
    l("Kiểm tra kết nối & quyền truy cập", "Connection & access checks"),
    p(
      l(
        "Kiểm tra nhanh kết nối, xác thực và khả năng đọc của tài khoản hãng.",
        "Check connectivity, authentication and read access for a vendor account.",
      ),
    ),
    field(l("Chọn hãng", "Vendor"), vendor),
    field(l("Chọn tài khoản", "Account"), account),
    checkButton,
    resultPanel,
  );
  diagnostic.classList.add("detail-panel");
  function keysDialog() {
    showDialog(
      l("API Keys · SolarOne API", "API Keys · SolarOne API"),
      p(
        l(
          "Chỉ đọc danh mục nhà máy và thiết bị được chọn; không có quyền ghi thiết bị.",
          "Read only the selected plant and device inventory; no equipment writes.",
        ),
      ),
      table(
        [
          l("Tên", "Name"),
          l("Hết hạn", "Expires"),
          l("Trạng thái", "State"),
          l("Thao tác", "Actions"),
        ],
        (data?.keys || []).map((k) => [
          k.name,
          date(k.expires_at),
          k.active ? l("Đang cấp", "Issued") : l("Đã thu hồi", "Revoked"),
          k.active
            ? btn(l("Thu hồi", "Revoke"), () =>
                showDialog(
                  l("Thu hồi API key", "Revoke API key"),
                  p(k.name),
                  btn(
                    l("Xác nhận thu hồi", "Confirm revocation"),
                    async () => {
                      await api(`/access-keys/${k.id}/revoke`, {});
                      closeDialog();
                      await refresh();
                    },
                    "primary",
                  ),
                ),
              )
            : "—",
        ]),
      ),
      btn(l("+ Tạo API key", "+ Create API key"), createKey, "primary"),
    );
  }
  function createKey() {
    const name = input(),
      days = input("number", 90);
    name.required = true;
    name.maxLength = 120;
    days.min = 1;
    days.max = 365;
    days.required = true;
    const choices = state.fleet.sites.map((s) => {
      const box = input("checkbox");
      return { s, box };
    });
    const f = form(
      async () => {
        const result = await api("/access-keys", {
          name: name.value,
          site_ids: choices.filter((x) => x.box.checked).map((x) => x.s.id),
          expires_days: Number(days.value),
        });
        closeDialog();
        await refresh();
        const token = e("textarea");
        token.value = result.token;
        token.readOnly = true;
        token.rows = 3;
        token.setAttribute("aria-label", "API key");
        showDialog(
          l("Lưu API key này", "Save this API key"),
          p(
            l(
              "Khóa chỉ được hiển thị một lần. Sao chép vào kho bí mật của ứng dụng sử dụng.",
              "Shown once. Copy it into the consuming application’s secret store.",
            ),
          ),
          token,
          raw(l("Cách sử dụng", "Usage"), {
            method: "GET",
            path: "/api/public/v1/fleet",
            header: "Authorization: Bearer <API key>",
            scope: "fleet:read",
            expires_at: result.key.expires_at,
          }),
        );
      },
      l("Tạo API key", "Create API key"),
    );
    f.finish(
      field(l("Tên khóa", "Key name"), name),
      field(l("Hạn dùng (ngày)", "Validity (days)"), days),
      e("h3", l("Nhà máy được truy cập", "Allowed plants")),
      div(
        "checklist",
        ...choices.map(({ s, box }) =>
          add(e("label", "", "check"), box, e("span", s.name)),
        ),
      ),
      choices.length
        ? null
        : p(
            l(
              "Thêm nhà máy trước khi cấp khóa.",
              "Add a plant before issuing a key.",
            ),
          ),
    );
    showDialog(l("Tạo API key", "Create API key"), f);
  }
  const certificates = card(
    "",
    div(
      "card-head",
      e("h2", l("Chứng chỉ Local Agent", "Local Agent certificates")),
      btn(l("Xem trạng thái", "View status"), () =>
        showDialog(
          l("Chứng chỉ Local Agent", "Local Agent certificates"),
          p(
            l(
              "Chưa triển khai cấp chứng chỉ hoặc xác thực mTLS. Agent hiện dùng token riêng theo nhà máy qua HTTPS hoặc tunnel.",
              "Certificate issuance and mTLS authentication are not implemented. Agents currently use plant-scoped tokens over HTTPS or a tunnel.",
            ),
          ),
          btn(l("Quản lý Local Agent", "Manage Local Agents"), () => {
            closeDialog();
            return go("settings", "", "agents");
          }),
        ),
      ),
    ),
    p(
      l(
        "Quản lý chứng chỉ cho các Local Agent tại công trình.",
        "Manage certificates for on-site agents.",
      ),
    ),
    div(
      "metric-summary",
      div("icon-soft", icon("shield")),
      div(
        "",
        e("strong", "0"),
        e("span", l("Chứng chỉ đã cấp", "Certificates issued"), "muted"),
      ),
    ),
    e("span", l("Chưa cấu hình mTLS", "mTLS not configured"), "small muted"),
  );
  const apiCard = card(
    "",
    div(
      "card-head",
      e("h2", "API Keys (SolarOne API)"),
      allowed
        ? btn(l("+ Tạo API key", "+ Create API key"), createKey, "primary")
        : null,
    ),
    p(
      l(
        "Cấp quyền đọc cho ứng dụng và đối tác theo từng nhà máy.",
        "Issue plant-scoped read access to applications and partners.",
      ),
    ),
    div(
      "metric-summary",
      div("icon-soft", icon("key")),
      div(
        "",
        e("strong", number(data?.active_keys ?? 0, 0)),
        e("span", l("API key đang hoạt động", "Active API keys"), "muted"),
      ),
    ),
    allowed ? btn(l("Xem tất cả", "View all"), keysDialog, "link") : null,
  );
  const vault = data?.vault,
    healthy = vault?.state === "AVAILABLE";
  const vaultCard = card(
    l("Tình trạng kho bí mật", "Secret storage status"),
    p(
      l(
        "Theo dõi khả năng đọc thông tin kết nối đã mã hóa.",
        "Check availability of encrypted connection credentials.",
      ),
    ),
    div(
      `notice ${healthy ? "success" : ""}`,
      div(
        "row",
        icon(healthy ? "shield" : "info"),
        e(
          "strong",
          healthy
            ? l("Hoạt động bình thường", "Available")
            : l("Cần quyền quản trị", "Administrator access required"),
        ),
      ),
      p(
        healthy
          ? l(
              "Thông tin kết nối được mã hóa trên controller.",
              "Connection credentials are encrypted on the controller.",
            )
          : l(
              "Chỉ quản trị viên được xem thông tin kho.",
              "Only administrators may inspect the vault.",
            ),
      ),
    ),
    div(
      "row between",
      e(
        "span",
        vault ? l("Cập nhật: ", "Updated: ") + date(vault.checked_at) : "—",
        "small muted",
      ),
      allowed
        ? btn(l("Chi tiết", "Details"), () =>
            showDialog(
              l("Kho bí mật", "Secret storage"),
              raw(l("Trạng thái", "Status"), vault),
            ),
          )
        : null,
    ),
  );
  const root = div(
    "split-layout",
    div(
      "stack",
      accountCard,
      div("grid three", certificates, apiCard, vaultCard),
    ),
    diagnostic,
  );
  root.dataset.view = "vendor-accounts";
  return root;
}
