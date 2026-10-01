import { l, t, date } from "./i18n.js";
import { renderMappingWorkspace } from "./mapping-workspace.js";

const aliases = {quality: "overview", sync: "sync_logs", agents: "agent"};
const sections = new Set(["overview", "sources", "meters", "cloud", "agent", "collection", "mapping", "diagnostics", "sync_logs"]);

export function dataWorkspaceSection(state) {
  const section = state.section === "main" ? state.tab || "overview" : state.section;
  return aliases[section] || section;
}

export function ownsDataWorkspaceRoute(state) {
  return state.page === "reports" && sections.has(dataWorkspaceSection(state));
}

export async function renderDataConnectionsWorkspace(ui, forcedSection) {
  const {state, div, e, p, btn, badge, number, card, table, tabs, select, field, notice, api, go, form, input, showDialog, closeDialog, refresh, admin} = ui;
  const root=div("stack data-connections-root");
  const selected=forcedSection||dataWorkspaceSection(state);
  const key=aliases[selected]||selected||'overview';
  root.append(tabs([['overview',l('Tổng quan','Overview')],['sources',l('Nguồn dữ liệu','Sources')],['meters',l('Công tơ 3 pha','Smart Meters')],['cloud',l('Tài khoản cloud','Cloud accounts')],['agent','Local Agent'],['collection',l('Thu thập','Collection')],['mapping',l('Ánh xạ','Mapping')],['diagnostics',l('Chẩn đoán','Diagnostics')],['sync_logs',l('Nhật ký đồng bộ','Sync log')],['telemetry',l('Dữ liệu đo','Measurements')]],key,
    tab=>go('reports',tab,'main')));
  if(key==='meters') {
    const meters = (state.fleet.devices || []).filter(d => (!state.site || d.site_id === state.site) && /meter/i.test(d.type || ""));
    root.append(card(l("Công tơ & số đo đã thu thập", "Meters & collected observations"),
      p(l("Số đo lấy từ thiết bị đã liên kết. Chưa có dữ liệu thì không suy đoán công suất, điện năng hay chất lượng điện.", "Measurements come from bound devices. Missing power, energy or quality readings are not synthesized.")),
      table([l("Thiết bị", "Device"), l("Model", "Model"), l("Thao tác", "Action")], meters.map(d => [d.name || d.id, d.model || "—",
        btn(l("Mở dữ liệu thiết bị", "Open device measurements"), () => go("devices", d.id))]))));
    return root;
  }
  if(key==='cloud') {
    root.append(card(l('Tài khoản cloud dùng chung','Shared cloud accounts'),p(l('Thêm kết nối, kiểm tra và đồng bộ thiết bị tại trang tài khoản hãng.','Add connections, check access and synchronize devices in vendor accounts.')),
      btn(l('Mở tài khoản hãng','Open vendor accounts'),()=>go('settings','connections'),'primary')));
    return root;
  }
  if(key==='agent') {
    let devices = [];
    try {
      devices = await api('/agent/devices');
    } catch {
      devices = [];
    }

    const openAddDialog = () => {
      const devId = input('text'); devId.placeholder = 'inv-local-01'; devId.required = true;
      const siteList = (state.fleet?.sites || []).map(s => [s.id, s.name]);
      const sitePicker = select(siteList.length ? siteList : [['default', 'Mặc định / Default']], state.site || 'default');
      const vendorPicker = select([
        ['growatt', 'Growatt (SPH / MIN / MID / MAX)'],
        ['sungrow', 'Sungrow (SHx / SH / SG)'],
        ['huawei', 'Huawei (SUN2000 / LUNA2000)'],
        ['deye', 'Deye (Hybrid SG01/SG04)'],
        ['sunsynk', 'Sunsynk (Hybrid 3.6k-16k)'],
        ['goodwe', 'GoodWe (UDP 8899 / TCP 502)'],
        ['eybond', 'Eybond (SMG / PI17 / PI30 / Bluesun)'],
        ['solis', 'Solis (S6 / 4G / 5G)'],
        ['sofar', 'Sofar Solar (HYD / ME series)'],
        ['solax', 'SolaX (X1 / X3 Hybrid)'],
        ['foxess', 'FoxESS (H1 / H3 / KH series)'],
      ], 'growatt');
      const transportPicker = select([
        ['modbus_tcp', 'Modbus TCP (Chuẩn cổng 502)'],
        ['sunsynk_local', 'Sunsynk / Deye Modbus TCP (Direct 502)'],
        ['goodwe_local', 'GoodWe UDP Direct (Cổng 8899)'],
        ['eybond_local', 'Eybond / Bluesun Local (Cổng 8000)'],
        ['solarman_local', 'SOLARMAN V5 Logger Stick (Cổng 8899)'],
      ], 'modbus_tcp');
      const addr = input('text'); addr.placeholder = '192.168.1.100'; addr.required = true;
      const port = input('number', 502); port.min = '1'; port.max = '65535';
      const series = input('text'); series.placeholder = 'SPH, SHx, SUN2000...';
      const unitId = input('number', 1); unitId.min = '1'; unitId.max = '255';
      const interval = input('number', 15); interval.min = '5'; interval.max = '300';

      const f = form(async () => {
        await api('/agent/devices', {
          device_id: devId.value.trim(),
          site_id: sitePicker.value,
          transport: transportPicker.value,
          address: addr.value.trim(),
          port: Number(port.value),
          vendor: vendorPicker.value,
          model_series: series.value.trim(),
          unit_id: Number(unitId.value),
          poll_interval_s: Number(interval.value),
        });
        closeDialog();
        await refresh();
      });

      f.finish(
        field(l('Mã định danh thiết bị', 'Device ID'), devId),
        field(l('Nhà máy', 'Site / Plant'), sitePicker),
        field(l('Hãng sản xuất', 'Inverter Vendor'), vendorPicker),
        field(l('Giao thức truyền dẫn', 'Transport Protocol'), transportPicker),
        field(l('Địa chỉ IP / Host', 'IP Address / Host'), addr),
        field(l('Cổng mạng (Port)', 'Network Port'), port),
        field(l('Dòng máy / Profile', 'Model Series / Profile'), series),
        field(l('Modbus Slave ID (Unit ID)', 'Slave / Unit ID'), unitId),
        field(l('Chu kỳ đọc (giây)', 'Poll Interval (seconds)'), interval),
      );
      showDialog(l('Thêm biến tần kết nối cục bộ', 'Add Local Inverter'), f);
    };

    const pollDevice = async (id) => {
      try {
        const res = await api('/agent/devices/' + encodeURIComponent(id) + '/poll', {});
        if (res.status === 'success') {
          const summary = Object.entries(res.points || {})
            .slice(0, 4)
            .map(([k, v]) => `${k}: ${v}`)
            .join(' | ');
          alert(l('Đọc thành công!\n' + summary, 'Poll succeeded!\n' + summary));
        } else {
          alert(l('Đọc thất bại hoặc thiết bị đang phản hồi lỗi.', 'Poll failed or device returned error.'));
        }
        await refresh();
      } catch (err) {
        alert(l('Lỗi khi đọc: ', 'Error polling: ') + err.message);
      }
    };

    const deleteDevice = async (id) => {
      if (!confirm(l('Xác nhận xóa thiết bị cục bộ này?', 'Delete this local device?'))) return;
      try {
        await api('/agent/devices/' + encodeURIComponent(id) + '/delete', {});
        await refresh();
      } catch (err) {
        alert(l('Lỗi khi xóa: ', 'Error deleting: ') + err.message);
      }
    };

    const rows = devices.map(d => {
      const st = d.status || {};
      const statusBadge = st.quarantined
        ? badge(l('Cách ly (Lỗi liên tiếp)', 'Quarantined'), 'red')
        : st.consecutive_failures > 0
          ? badge(`${st.consecutive_failures} ${l('lỗi', 'errors')}`, 'orange')
          : badge(l('Bình thường', 'Active'), 'green');

      return [
        d.device_id,
        d.site_id || 'default',
        `${d.vendor?.toUpperCase() || '—'} (${d.model_series || 'Default'})`,
        `${d.transport} @ ${d.address}:${d.port}`,
        statusBadge,
        st.last_poll ? date(st.last_poll) : '—',
        div('row gap-xs',
          btn(l('Đọc ngay', 'Poll now'), () => pollDevice(d.device_id), 'small-btn secondary'),
          admin() ? btn(l('Xóa', 'Delete'), () => deleteDevice(d.device_id), 'small-btn danger') : '—'
        ),
      ];
    });

    root.append(
      card(
        l('Field Gateway / Local Agent Daemon', 'Field Gateway / Local Agent Daemon'),
        p(l(
          'Dịch vụ nền tự động thu thập dữ liệu biến tần qua Modbus TCP, GoodWe UDP, Eybond LAN và SOLARMAN V5. Hỗ trợ cách ly sự cố (Quarantine Circuit-Breaker sau 5 lần lỗi) và đồng bộ trực tiếp vào cơ sở dữ liệu telemetry của trạm.',
          'Background daemon automatically polling inverters via Modbus TCP, GoodWe UDP, Eybond LAN and SOLARMAN V5. Includes quarantine circuit-breaker after 5 failures and feeds telemetry directly into plant metrics.'
        )),
        admin() ? btn(l('Thêm biến tần cục bộ', 'Add Local Inverter'), openAddDialog, 'primary') : div()
      ),
      card(
        l('Danh sách thiết bị kết nối nội bộ', 'Local Connected Inverters'),
        devices.length === 0
          ? p(l('Chưa có thiết bị cục bộ nào được đăng ký.', 'No local devices enrolled yet.'))
          : table(
              [
                l('Mã thiết bị', 'Device ID'),
                l('Nhà máy', 'Site'),
                l('Hãng / Dòng máy', 'Vendor / Series'),
                l('Giao thức & Địa chỉ', 'Transport & Address'),
                l('Trạng thái', 'Status'),
                l('Lần đọc cuối', 'Last Poll'),
                l('Thao tác', 'Actions'),
              ],
              rows
            )
      ),
      notice(
        'Đọc trực tiếp qua mạng LAN/RS485 là kênh dữ liệu thời gian thực độc lập với Cloud hãng. Dữ liệu đọc được sẽ gắn nhãn MEASURED và ưu tiên cao hơn cloud khi đồng bộ.',
        'Direct LAN/RS485 polling provides real-time telemetry independent of vendor cloud. Measurements are tagged MEASURED and prioritized over cloud data in EMS dispatch.'
      )
    );
    return root;
  }
  if(key==='collection') {
    if(!admin()){root.append(p(l('Cần quyền quản trị để thay đổi chu kỳ thu thập.','Administrator access is required for collection policies.')));return root;}
    const data=await api('/collection');
    const editPolicy=(c)=>{
      const interval=input('number',c.policy.interval_seconds), limit=input('number',c.policy.max_devices_per_poll);
      interval.min=String(c.minimum_interval_seconds||120);interval.max='3600';limit.min='1';limit.max='50';
      const f=form(async()=>{await api('/collection/'+encodeURIComponent(c.integration_id),{revision:c.policy.revision,interval_seconds:Number(interval.value),max_devices_per_poll:Number(limit.value)});closeDialog();await refresh();});
      f.finish(field(l('Chu kỳ (giây)','Interval (seconds)'),interval),field(l('Thiết bị mỗi lượt','Devices per poll'),limit));showDialog(c.name,f);
    };
    root.append(card(l('Chính sách thu thập','Collection policies'),table([t('name'),l('Chu kỳ (giây)','Interval (seconds)'),l('Thiết bị mỗi lượt','Devices per poll'),t('status'),l('Lần thử gần nhất','Last attempt'),l('Thao tác','Action')],data.connections.map(c=>[
      c.name,c.policy.interval_seconds,c.policy.max_devices_per_poll,c.state?.state||'UNKNOWN',date(c.state?.last_attempt),admin()?btn(l('Chỉnh sửa','Edit'),()=>editPolicy(c)):'—']))));
    return root;
  }
  const plantId=state.site||(state.fleet.sites||[])[0]?.id;
  if(!plantId){root.append(p(l('Thêm nhà máy và kết nối trước.','Add a plant and connection first.')));return root;}
  const picker=select((state.fleet.sites||[]).map(s=>[s.id,s.name]),plantId);
  picker.onchange=()=>{state.site=picker.value;ui.render();};root.append(field(t('plants'),picker));
  if(key==='mapping') {
    root.append(await renderMappingWorkspace(ui,plantId));
    return root;
  }
  const data=await api('/data-sources?site_id='+encodeURIComponent(plantId));
  if(key==='sync_logs') {
    root.append(card(l('Sự kiện đồng bộ','Synchronization events'),table([l('Thời điểm','Time'),l('Sự kiện','Event'),l('Chi tiết','Details')],
      data.recent_sync_errors.map(r=>[date(r.time),r.title,r.desc||'—']))));
  } else if(key==='diagnostics') {
    root.append(card(l('Chất lượng dữ liệu','Data quality'),p(data.diagnostics.status),p(data.diagnostics.data_freshness)),
      btn(l('Nghiệm thu / bàn giao','Commissioning / handover'),()=>{state.site=plantId;return go('operations','','handover');}));
  } else {
    root.append(card(l('Nguồn dữ liệu đã kết nối','Configured data sources'),table([t('name'),l('Loại','Type'),t('status'),l('Quyền','Access'),l('Đồng bộ cuối','Last sync')],
      data.sources.map(s=>[s.name,s.type,s.status,s.permissions,date(s.last_sync)]))),
      card(l('Ưu tiên nguồn','Source priority'),p(data.priority.map(s=>s.title).join(' → ')),
        btn(l('Sửa chính sách nguồn','Edit source policy'),()=>go('settings','','source_policy'))),
      notice('Trạng thái đã đăng ký agent không đồng nghĩa thiết bị đang trực tuyến. Dữ liệu thiếu nguồn xác minh chưa được dùng làm chỉ số vận hành.',
        'Agent enrollment does not establish online status. Unverified measurements are not used as operational KPIs.'));
  }
  return root;
}

export function createDataWorkspace(ui) {
  return {view:section=>renderDataConnectionsWorkspace(ui,section)};
}
