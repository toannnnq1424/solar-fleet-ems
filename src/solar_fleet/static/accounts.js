import { l, t, date, number } from "./i18n.js";
import { deyeApplicationDialog } from './deye-connection.js';

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
        row.credential_source==='MANAGED_DEYE_APPLICATION'?btn(l('Liên kết lại bằng email / mật khẩu','Reconnect with email / password'),
          ()=>integrationForm({...providers.find(p=>p.id==='Deye'),reconnect:row})):null,
        row.vendor==='GoodWe'&&row.platform==='sems_plus'?btn(l('Liên kết lại SEMS+','Reconnect SEMS+'),
          ()=>integrationForm({...providers.find(p=>p.id==='GoodWe'),reconnect:row})):null,
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
          l("Đồng bộ danh mục · xem phạm vi", "Synchronize inventory · review scope"),
          synchronizeDialog,
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
  function synchronizeDialog() {
    const enabled=(data?.accounts||[]).filter(a=>a.enabled);
    const confirm=form(async()=>{await api('/sync',{});closeDialog();await refresh();},
      l('Đồng bộ các tài khoản đang bật','Synchronize enabled accounts'));
    confirm.finish(p(l('Hiện tại thao tác này đọc và cập nhật danh mục của tất cả tài khoản đang bật, không chỉ tài khoản vừa chọn. Không gửi lệnh điều khiển.','This currently reads and updates inventory for all enabled accounts, not only the selected account. It sends no equipment commands.'),'notice'),
      table([l('Tài khoản','Account'),l('Hãng','Vendor')],enabled.map(a=>[a.name,a.equipment_brand||a.vendor])),
      p(l('Khi hoàn tất, kiểm tra trạng thái từng tài khoản và nhà máy. Yêu cầu đồng bộ hoàn tất không đảm bảo mọi nguồn đều có dữ liệu.','Afterward, review each account and plant status. Completion of the sync request does not mean every source supplied data.'),'field-help'));
    showDialog(l('Xác nhận phạm vi đồng bộ','Confirm synchronization scope'),confirm);
  }
  async function preparationDialog(){
    const options=await api('/connections/deye/options');
    const configured=options.applications.filter(a=>a.enabled);
    showDialog(l('Chuẩn bị kiểm thử tài khoản thật','Prepare a real-account test'),div('stack account-preflight',
      p(l('Bạn tự nhập thông tin trên form. Giai đoạn đầu chỉ kiểm tra đăng nhập, quyền xem, nhà máy, thiết bị và số đo; không điều khiển hoặc triển khai lịch.','Enter credentials yourself in the form. The first stage checks sign-in, read access, plants, devices and readings only; no control or schedule deployment.'),'notice'),
      card('Deye',badge(configured.length?l('Có cấu hình ứng dụng','Application configured'):l('Thiếu cấu hình ứng dụng','Application setup missing'),configured.length?'':'warn'),
        p(configured.length?l('Đã lưu cấu hình cho khu vực: ','Configuration saved for regions: ')+configured.map(a=>a.region).join(', ')+l('. Chưa chứng minh tài khoản của bạn được cấp quyền.','. This does not prove access for your account.'):
          l('Chưa nhập mật khẩu. Quản trị viên cần khóa ứng dụng được Deye cấp trước khi mở luồng email/mật khẩu.','Do not enter a password yet. An administrator needs Deye-issued application keys before the email/password flow is available.')),
        btn(l('Mở luồng Deye','Open Deye connection'),()=>integrationForm(providers.find(s=>s.id==='Deye')))),
      card('GoodWe',badge(l('SEMS+ · kiểm thử chỉ đọc','SEMS+ · read-only trial'),'warn'),p(l('Có luồng SEMS+ riêng bằng email/mật khẩu và máy chủ tài khoản, không cần App ID/App Secret hoặc nhập ID nhà máy. Chưa nghiệm thu tài khoản thật; xác thực, kiểm tra dữ liệu và đồng bộ là các bước riêng.','A separate SEMS+ email/password flow uses your account server, without App ID/App Secret or manual plant IDs. Live-account acceptance is pending; authentication, data checks and synchronization are separate steps.')),
        btn(l('Xem yêu cầu GoodWe','View GoodWe requirements'),()=>integrationForm(providers.find(s=>s.id==='GoodWe')))),
      card(l('Sau khi liên kết','After linking'),
        e('ol','', 'connection-next-steps'))));
    const list=document.querySelector('.account-preflight .connection-next-steps');
    [l('Kiểm tra kết nối: xem riêng từng bước xác thực, nhà máy, thiết bị và số đo.','Check connection: review authentication, plants, devices and readings separately.'),
      l('Xác nhận phạm vi đồng bộ rồi mới nhập danh mục về SolarOne.','Review synchronization scope before importing inventory into SolarOne.'),
      l('Đối chiếu tên, số sê-ri, thời gian và đơn vị với ứng dụng hãng; dữ liệu chưa xác minh vẫn để trống.','Compare names, serial numbers, timestamps and units with the vendor app; unverified readings stay empty.')].forEach(s=>list.append(e('li',s)));
  }
  const rows = [];
  for (const spec of providers) {
    const accounts = (data?.accounts || []).filter(
      (a) => (a.equipment_brand || a.vendor) === spec.id,
    );
    if (accounts.length)
      for (const account of accounts) {
        const check = account.diagnostic;
        const ok = check?.checks?.some(c => c.key === 'authentication' && c.state === 'PASS') || check?.state === "PASS";
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
        const action = btn(icon("moreVertical"), () => accountActions(account), "icon-button");
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
              account.status?.state === 'ERROR'
                ? l('Lần đọc mới nhất bị lỗi', 'Latest read failed')
                : account.status?.state === 'PILOT_CAPACITY_EXCEEDED'
                  ? l('Đang đọc luân phiên thiết bị', 'Reading devices in rotation')
                  : last
                    ? l("Đã hoàn tất lượt đọc", "Read cycle completed")
                    : l("Chưa đồng bộ", "Not synced"),
              "small muted",
            ),
          ),
          action,
        ]);
      }
    else {
      const action = allowed
        ? btn(icon("plus"), () => connect(spec), "icon-button")
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
              ? l("Chưa xác thực", "Not authenticated")
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
    allowed ? div('account-secondary-actions',
      btn(l('Hướng dẫn kết nối & kiểm thử','Connection & testing guide'),preparationDialog),
      btn(l('Cấu hình ứng dụng Deye','Deye application setup'),()=>deyeApplicationDialog(ui))) : null,
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
              ? l("Kiểm tra đọc mẫu thành công", "Sample read check passed")
              : failed
                ? l("Cần kiểm tra kết nối", "Connection needs attention")
                : l("Chưa kiểm tra kết nối", "Connection not checked"),
          ),
          p(
            pass
              ? l(
                  "Kết quả bên dưới chỉ kiểm tra một nhà máy và một thiết bị mẫu; chưa chứng minh mọi thiết bị có số đo hoặc có quyền điều khiển.",
                  "The checks below cover one plant and one sample device; they do not establish readings or control access for every device.",
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
          div('stack-tight',e("span", label),row?.count!=null?e('small',String(row.count)+' '+l('mục nhận được','items received'),'muted'):null),
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
    if (result) {
      resultPanel.append(p(l('Kiểm tra này chỉ đọc một nhà máy và tối đa một thiết bị mẫu; chưa đồng bộ danh mục và không xác nhận độ chính xác của mọi số đo.','This checks one plant and at most one sample device; it does not import inventory or verify every reading.'),'field-help'));
      if(pass)resultPanel.append(btn(l('Tiếp tục: xem phạm vi đồng bộ','Next: review synchronization scope'),synchronizeDialog,'full-width'));
      resultPanel.append(
        btn(
          l("Xem chi tiết phản hồi", "View response details"),
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
    if (!id||checking) return;
    checking=true;checkButton.disabled=vendor.disabled=account.disabled=true;
    resultPanel.setAttribute('aria-busy','true');
    resultPanel.replaceChildren(
      p(
        l(
          "Đang kiểm tra quyền đọc và dữ liệu…",
          "Checking read access and data…",
        ),
      ),
    );
    resultPanel.firstElementChild.setAttribute('role','status');
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
    } finally {
      checking=false;vendor.disabled=false;account.disabled=!(data?.accounts||[]).some(a=>(a.equipment_brand||a.vendor)===vendor.value);
      checkButton.disabled=!allowed||!(data?.accounts||[]).some(a=>a.id===account.value&&a.enabled);
      resultPanel.removeAttribute('aria-busy');
    }
  }
  let checking=false;
  const checkButton = btn(
    l("Kiểm tra kết nối", "Check connection"),
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
    l("Bảo mật tài khoản", "Credential security"),
    p(
      l(
        "Theo dõi khả năng lưu trữ và mã hóa an toàn thông tin kết nối hãng.",
        "Check availability of encrypted connection credentials.",
      ),
    ),
    div(
      `notice ${healthy ? "success" : ""}`,
      div(
        "row gap-sm align-center",
        icon(healthy ? "shield" : "info"),
        e(
          "strong",
          healthy
            ? l("Kho khóa an toàn • Sẵn sàng", "Vault Available & Ready")
            : allowed ? l("Chưa sẵn sàng", "Not ready") : l("Cần quyền quản trị", "Administrator access required"),
        ),
      ),
      p(
        healthy
          ? l(
              `Mã hóa đối xứng ${vault?.encryption || "Fernet AES-128"}. Bảo vệ ${vault?.encrypted_accounts || 0} tài khoản hãng trên máy chủ.`,
              `Server-side encryption ${vault?.encryption || "Fernet AES-128"}. Protecting ${vault?.encrypted_accounts || 0} accounts on controller.`,
            )
          : l(
              allowed ? "Chưa xác nhận được khả năng lưu thông tin kết nối. Kiểm tra cấu hình mã hóa trên máy chủ." : "Chỉ quản trị viên được xem thông tin kho.",
              allowed ? "Credential storage is not confirmed. Check the server encryption configuration." : "Only administrators may inspect the vault.",
            ),
      ),
    ),
    div(
      "row between align-center margin-top-xs",
      e(
        "span",
        vault ? l("Cập nhật: ", "Updated: ") + date(vault.checked_at) : "—",
        "small muted",
      ),
      allowed
        ? btn(l("Xem chi tiết kho khóa", "Inspect vault details"), () => {
            const vaultDetails = div("stack gap-sm",
              div("overview-kpis",
                div("fact", e("span", l("Trạng thái:", "Status:")), badge(vault?.state || "UNKNOWN", healthy ? "good" : "bad")),
                div("fact", e("span", l("Thuật toán mã hóa:", "Encryption Algorithm:")), badge(vault?.encryption || "Fernet (AES-128 + HMAC)", "blue")),
                div("fact", e("span", l("Số tài khoản mã hóa:", "Protected Accounts:")), e("b", `${vault?.encrypted_accounts || 0} ${l("tài khoản", "accounts")}`)),
                div("fact", e("span", l("Bảo mật trình duyệt:", "Browser Exposure:")), badge(vault?.browser_secret_access ? l("Có lộ bí mật", "Exposed") : l("An toàn (Zero Secret Exposure)", "Safe (Zero Exposure)"), "good"))
              ),
              p(l(
                "Thông tin kết nối được lưu mã hóa trên máy chủ. Giao diện quản lý không hiển thị lại mật khẩu và khóa bí mật đã lưu.",
                "Connection credentials are stored encrypted on the server. The management interface does not display stored passwords or secret keys."
              ), "small muted"),
              raw(l("Chi tiết dành cho kỹ thuật viên", "Technical details"), vault)
            );
            showDialog(l("Kho bí mật & Bảo mật thông tin xác thực", "Secret Storage & Credential Security"), vaultDetails);
          })
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
