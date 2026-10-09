import { l, t, date, number } from './i18n.js';
import { icon } from './icons.js';
import { metricTiles } from './ui-visuals.js';

// Declared configuration is deliberately separate from measured connectivity.
export function networkWorkspace(ui, siteId, data) {
  const {div,e,p,card,table,btn,field,select,badge}=ui;
  const agents=data.agents||[],profiles=data.profiles||[],local=data.local_agent||{},bus=data.rs485_bus||{},logger=data.solarman_logger||{};
  const devices=(ui.state.fleet.devices||[]).filter(d=>d.site_id===siteId);
  const deviceName=id=>devices.find(d=>d.id===id)?.name||id||'—';
  const facts=rows=>div('stack',...rows.map(([label,value])=>div('fact',e('span',label),e('b',value??'—'))));
  const unknown=()=>badge(l('Chưa có bằng chứng','No evidence'),'gray');
  const equipment=card(l('Danh sách logger & bộ thu thập','Loggers & collectors'),
    div('form-actions',btn(l('Quản lý nguồn dữ liệu','Manage data sources'),()=>ui.go('reports','sources')),btn(l('Cấu hình Local Agent','Configure Local Agent'),()=>ui.go('reports','agent','main'))),
    table([l('Tên','Name'),l('Đăng ký','Enrollment'),l('Heartbeat gần nhất','Last heartbeat'),l('Lần thấy cuối','Last seen'),l('Kết nối','Connectivity')],
      agents.map(a=>[a.name||a.id,badge(a.enabled?l('Đã đăng ký','Enrolled'):l('Đã vô hiệu hóa','Disabled'),'gray'),a.last_heartbeat?date(a.last_heartbeat):'—',a.last_seen?date(a.last_seen):'—',unknown()])),
    !agents.length?p(l('Chưa có bộ thu thập được đăng ký tại công trình này.','No collectors enrolled at this site.'),'field-help'):null);
  const selection=select([['',l('Chọn hồ sơ kết nối','Choose a connection profile')],...profiles.map(r=>[r.id,r.name||r.id])],profiles[0]?.id||'');
  const configuration=div('stack'),topology=div('network-topology');
  const draw=()=>{
    const profile=profiles.find(r=>r.id===selection.value);
    const label=l('Chưa khai báo','Not declared');
    const address=profile?.address||'—';
    configuration.replaceChildren(facts([[l('Thiết bị','Equipment'),profile?deviceName(profile.device_id):null],
      [l('Kết nối khai báo','Declared connection'),profile?.connection],[l('Địa chỉ / cổng tại máy','Address / local port'),address],
      [l('Cổng TCP','TCP port'),profile?.port],[l('Địa chỉ Modbus','Modbus unit ID'),profile?.slave_id],
      [l('Tốc độ truyền khai báo','Declared baud rate'),profile?.baud],[l('Chẵn lẻ khai báo','Declared parity'),profile?.parity],
      [l('Cấp IP tự động (khai báo)','Automatic IP (declared)'),typeof profile?.dhcp==='boolean'?(profile.dhcp?l('Bật','On'):l('Tắt','Off')):null],
      [l('Ghi chú','Notes'),profile?.notes||null]]));
    const node=(glyph,title,detail)=>div('network-node',icon(glyph),e('b',title),p(detail,'field-help'));
    topology.replaceChildren(div('network-declared-link',node('device',l('Thiết bị','Equipment'),profile?deviceName(profile.device_id):label),
      div('network-link-label',e('span',profile?.connection||label),icon('arrowRight')),
      node('network',l('Hồ sơ đường truyền','Connection profile'),profile?.name||label)),
      p(l('Đường nét đứt chỉ thể hiện cấu hình đã khai báo, không xác nhận đường truyền hoạt động. Chưa có bằng chứng nối logger → agent → cloud nên không tự vẽ thêm.','Dashed links represent declared configuration, not a working connection. Logger → agent → cloud links are not inferred without evidence.'),'field-help'));
  };
  selection.onchange=draw;draw();
  const saved=card(l('Cấu hình mạng đã khai báo','Declared network configuration'),field(l('Hồ sơ kết nối','Connection profile'),selection),configuration,
    p(l('Đây là hồ sơ lưu trong SolarOne, không phải cấu hình vừa đọc từ thiết bị.','This is a SolarOne record, not configuration freshly read from equipment.'),'notice'),
    btn(l('Mở hồ sơ logger & mạng','Open logger & network profiles'),()=>ui.go('devices','','network_profile')));
  const security=card(l('Bảo mật & kết nối cloud','Security & cloud connection'),
    facts([[l('Chứng chỉ thiết bị','Device certificate'),null],[l('Hạn chứng chỉ','Certificate expiry'),null],[l('Đường hầm bảo mật','Secure tunnel'),null]]),
    p(l('Chưa có dữ liệu kiểm chứng chứng chỉ hoặc đường hầm tại thiết bị. Việc đăng nhập SolarOne không xác nhận các kết nối này.','No device certificate or tunnel verification is available. Signing into SolarOne does not verify these connections.'),'field-help'),
    btn(l('Quản lý tài khoản hãng','Manage vendor accounts'),()=>ui.go('settings','main','connections')));
  const serial=card(l('Đường truyền RS485','RS485 bus'),facts([[l('Tốc độ truyền đã quan sát','Observed baud rate'),bus.baudrate],
    [l('Kiểm tra chẵn lẻ','Parity'),bus.parity],[l('Điện trở cuối tuyến','Termination resistance'),bus.termination_resistor_ohm==null?null:number(bus.termination_resistor_ohm)+' Ω']]),
    p(l('Chưa hỗ trợ quét RS485 trực tiếp tại đây. Hồ sơ mạng không tự kích hoạt quét bus hoặc đổi đấu nối.','Direct RS485 scanning is unavailable here. A network profile does not trigger bus scans or wiring changes.'),'field-help'));
  const diagnostics=card(l('Chẩn đoán mạng','Network diagnostics'),
    facts([[l('Kết nối hiện tại','Current connectivity'),local.connected===true?l('Đã xác nhận','Confirmed'):local.connected===false?l('Mất kết nối','Disconnected'):l('Chưa xác định','Unknown')],
      [l('Heartbeat gần nhất','Last heartbeat'),local.last_heartbeat?date(local.last_heartbeat):null],
      [l('Độ trễ quan sát','Observed latency'),local.latency_ms==null?null:number(local.latency_ms)+' ms'],
      [l('Giao thức logger','Logger protocol'),logger.protocol],[l('Sê-ri logger','Logger serial'),logger.serial]]),
    table([l('Phép kiểm tra','Check'),l('Kết quả','Result')],['Ping','DNS',l('Internet','Internet'),l('Mất gói','Packet loss')].map(label=>[label,unknown()])),
    p(l('Chưa có bộ thực thi kiểm tra mạng tại hiện trường; không hiển thị thành công hoặc độ trễ giả.','No field network diagnostic executor is connected; success and latency are not fabricated.'),'field-help'));
  const firmware=card(l('Firmware & sự kiện','Firmware & events'),
    p(l('Phiên bản, lịch sử cập nhật và sự kiện nằm trong hồ sơ thiết bị và nhật ký. Chưa có kết quả thì không đánh dấu phiên bản mới nhất.','Versions, update history and events belong to equipment records and the journal. Missing results do not establish that firmware is up to date.'),'field-help'),
    div('form-actions',btn(l('Bảo trì firmware','Firmware maintenance'),()=>ui.go('incidents','','firmware')),btn(l('Mở nhật ký','Open journal'),()=>ui.go('operations','main','journal'))));
  return div('stack network-reference',ui.notice('Bộ thu thập đã đăng ký chưa chắc đang trực tuyến. Hồ sơ mạng chỉ là khai báo; trạng thái cần bằng chứng quan sát.',
    'Enrolled collectors are not necessarily online. Network profiles are declarations; connectivity requires observed evidence.'),
    metricTiles(ui,[['server',l('Bộ thu thập đã đăng ký','Enrolled collectors'),agents.length],['network',l('Hồ sơ kết nối','Connection profiles'),profiles.length],['device',l('Thiết bị trong công trình','Equipment at this site'),devices.length]]),
    div('network-reference-grid',div('stack',equipment,div('network-config-grid',saved,security),serial),div('stack',card(l('Sơ đồ kết nối khai báo','Declared connection diagram'),topology),diagnostics,firmware)));
}
