import { l, t, date } from './i18n.js';

// One read-only inspector for every adapter. No mapping, interpolation or writes.
export function nativeReadingsPanel(ui, latest = {}) {
  const {e, div, p, card, field, input, select, table, badge} = ui;
  const points = (Array.isArray(latest.native?.dataList) ? latest.native.dataList : [])
    .filter(point => point && typeof point === 'object');
  const text = value => ['string', 'number'].includes(typeof value) ? String(value) : '';
  const groupKey = point => text(point.group_id || point.group);
  const groups = new Map(points.map(point => [groupKey(point), t(text(point.group) || groupKey(point))]).filter(([key]) => key));
  const search = input('search'), group = select([['', l('Tất cả nhóm', 'All groups')], ...groups], '');
  const technical = input('checkbox');
  const count = p('', 'field-help'), content = div('native-readings-content');
  search.placeholder = l('Tìm tên hoặc mã thông số…', 'Find a name or parameter code…');
  const heading = div('native-readings-heading',
    p(l('Số đo do hãng cung cấp, chưa quy đổi thành chỉ số tổng hợp.', 'Vendor readings, not yet mapped to aggregate metrics.'), 'field-help'),
    badge(l('Chưa xác minh quy đổi', 'Mapping unverified'), 'warn'));
  const received = div('native-readings-provenance',
    p(l('SolarOne nhận lúc: ', 'Received by SolarOne: ') + date(latest.received_at)),
    p(l('Thời điểm đo: ', 'Measurement time: ') + date(latest.native?.collectionTime)));
  const render = () => {
    const query = search.value.trim().toLocaleLowerCase();
    const selected = points.filter(point => (!group.value || groupKey(point) === group.value)
      && [point.title, point.name, point.key, point.group, t(text(point.title || point.name)), groups.get(groupKey(point))]
        .some(value => text(value).toLocaleLowerCase().includes(query)));
    count.textContent = `${selected.length} / ${points.length} ` + l('thông số', 'parameters');
    content.replaceChildren(selected.length ? table(
      [l('Thông số', 'Parameter'), l('Giá trị gốc', 'Native value'), l('Đơn vị', 'Unit'), l('Nhóm', 'Group')],
      selected.map(point => {
        let label = t(text(point.title || point.name || point.key)) || '—';
        // Use only the channel identifier explicitly carried by the native key.
        // This is a display suffix, not an electrical topology or metric mapping.
        const channel = text(point.key).match(/(?:^|:)(PHASE-[ABC]|MPPT-\d+|PV-\d+)(?=:|$)/)?.[1];
        if (channel && (point.title || point.name)) label += ' · ' + channel.replace('PHASE-', l('Pha ', 'Phase '));
        const name = div('native-reading-name', e('b', label));
        if (technical.checked && text(point.key) && label !== text(point.key)) name.append(e('small', text(point.key), 'field-help'));
        return [name, e('span', text(point.value) || '—', 'native-reading-value'), text(point.unit) || '—', groups.get(groupKey(point)) || '—'];
      }),
    ) : p(points.length ? l('Không có thông số khớp bộ lọc.', 'No parameters match these filters.')
      : l('Chưa có số đo cho thiết bị này. Thiết bị có trong tài khoản không có nghĩa hãng đã trả số đo; không coi đây là mất kết nối.',
        'No readings for this device yet. Being listed in the account does not mean readings are available; this does not establish an offline state.'), 'empty'));
  };
  search.oninput = render; group.onchange = render; technical.onchange = render;
  search.disabled = group.disabled = !points.length;
  const root = card(l('Thông số gốc từ hãng', 'Vendor native readings'), heading, received,
    div('native-readings-toolbar', field(l('Tìm thông số', 'Find parameters'), search), field(l('Nhóm thông số', 'Parameter group'), group), count),
    div('native-readings-options', field(l('Hiện mã kỹ thuật', 'Show technical codes'), technical)), content,
    p(l('Thời điểm nhận không phải thời điểm đo. Các số đo này chưa dùng cho biểu đồ theo thời gian, tính tiền hay điều khiển nếu thiếu bằng chứng thời gian, đơn vị hoặc ý nghĩa.',
      'Receipt time is not measurement time. These readings are not used for time-series charts, billing or control without verified time, units and semantics.'), 'field-help'));
  root.classList.add('native-readings'); render();
  return root;
}
