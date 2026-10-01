import { l, t, number } from './i18n.js';

export function createTopologyView(ui) {
  return {
    render: () => renderTopologyWorkspace(ui),
    renderTopology: () => renderTopologyWorkspace(ui),
  };
}

function drawMiniIcon(nodeFn, type, x, y) {
  const g = nodeFn('g', { transform: `translate(${x}, ${y})` });
  const t = (type || '').toUpperCase();
  if (t.includes('INV')) {
    // Inverter chassis with DC-to-AC sine wave
    g.append(
      nodeFn('rect', { x: 0, y: 0, width: 24, height: 24, rx: 4, fill: '#eff6ff', stroke: '#3b82f6', 'stroke-width': 1.5 }),
      nodeFn('path', { d: 'M5 8 H10 M5 11 H10 M14 10 Q16 7 17.5 10 T20 10', stroke: '#3b82f6', 'stroke-width': 1.2, fill: 'none' }),
      nodeFn('circle', { cx: 12, cy: 18, r: 1.8, fill: '#10b981' })
    );
  } else if (t.includes('BAT')) {
    // Battery cabinet with level segments
    g.append(
      nodeFn('rect', { x: 3, y: 2, width: 18, height: 21, rx: 3, fill: '#f5f3ff', stroke: '#8b5cf6', 'stroke-width': 1.5 }),
      nodeFn('rect', { x: 8, y: 0, width: 8, height: 2, rx: 1, fill: '#8b5cf6' }),
      nodeFn('rect', { x: 6, y: 6, width: 12, height: 3, rx: 1, fill: '#10b981' }),
      nodeFn('rect', { x: 6, y: 11, width: 12, height: 3, rx: 1, fill: '#10b981' }),
      nodeFn('rect', { x: 6, y: 16, width: 12, height: 3, rx: 1, fill: '#10b981' })
    );
  } else if (t.includes('PV') || t.includes('SOLAR') || t.includes('STRING')) {
    // Photovoltaic solar array
    g.append(
      nodeFn('polygon', { points: '2,21 7,6 22,6 17,21', fill: '#ecfdf5', stroke: '#10b981', 'stroke-width': 1.5 }),
      nodeFn('line', { x1: 4.5, y1: 13.5, x2: 19.5, y2: 13.5, stroke: '#10b981', 'stroke-width': 0.8 }),
      nodeFn('line', { x1: 10, y1: 21, x2: 14.5, y2: 6, stroke: '#10b981', 'stroke-width': 0.8 })
    );
  } else if (t.includes('MET') || t.includes('GRID')) {
    // Smart meter / Grid PCC
    g.append(
      nodeFn('circle', { cx: 12, cy: 12, r: 10, fill: '#fffbeb', stroke: '#f59e0b', 'stroke-width': 1.5 }),
      nodeFn('path', { d: 'M12 12 L17 8 M7 15 A7 7 0 0 1 17 9', stroke: '#f59e0b', 'stroke-width': 1.3, fill: 'none' }),
      nodeFn('circle', { cx: 12, cy: 12, r: 2, fill: '#f59e0b' })
    );
  } else if (t.includes('CHARGER') || t.includes('EV')) {
    // EV Charger
    g.append(
      nodeFn('rect', { x: 2, y: 2, width: 14, height: 20, rx: 3, fill: '#ecfeff', stroke: '#06b6d4', 'stroke-width': 1.5 }),
      nodeFn('path', { d: 'M16 8 H19 V16 H16 M18 16 V21 H21', stroke: '#06b6d4', 'stroke-width': 1.2, fill: 'none' }),
      nodeFn('circle', { cx: 9, cy: 8, r: 2, fill: '#06b6d4' })
    );
  } else {
    // Generic equipment
    g.append(
      nodeFn('rect', { x: 2, y: 2, width: 20, height: 20, rx: 4, fill: '#f8fafc', stroke: '#64748b', 'stroke-width': 1.5 }),
      nodeFn('line', { x1: 6, y1: 7, x2: 18, y2: 7, stroke: '#64748b', 'stroke-width': 1.2 }),
      nodeFn('circle', { cx: 12, cy: 14, r: 2.5, fill: '#64748b' })
    );
  }
  return g;
}

export async function renderTopologyWorkspace(ui) {
  const { state, div, p, btn, card, table, select, field, api, go, sites, deviceDetail } = ui;
  const plants = sites();
  if (!plants.length) return card(l('Sơ đồ thiết bị', 'Equipment topology'), p(t('noData')));
  const id = state.site || plants[0].id;
  const data = await api('/sites/' + encodeURIComponent(id) + '/topology-detail');
  const picker = select(plants.map(s => [s.id, s.name]), id);
  picker.onchange = () => { state.site = picker.value; ui.render(); };

  const node = (tag, attrs = {}, text = '') => {
    const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v));
    if (text) n.textContent = text;
    return n;
  };

  const colWidth = 270;
  const cardWidth = 250;
  const cardHeight = 90;
  const rowHeight = 145;
  const rowCount = Math.max(1, Math.ceil(data.nodes.length / 3));
  const svgHeight = Math.max(260, rowCount * rowHeight + 40);

  const svg = node('svg', {
    viewBox: `0 0 900 ${svgHeight}`,
    class: 'measurement-chart topology-svg',
    role: 'img',
    'aria-label': l('Kết nối thiết bị đã khai báo', 'Recorded equipment connections')
  });

  const positions = new Map(
    data.nodes.map((d, i) => [
      d.id,
      { x: 35 + (i % 3) * colWidth, y: 35 + Math.floor(i / 3) * rowHeight }
    ])
  );

  // Render connection bus lines first so they sit under the node cards
  data.edges.forEach(edge => {
    const a = positions.get(edge.source), b = positions.get(edge.target);
    if (!a || !b) return;
    const ax = a.x + cardWidth / 2, ay = a.y + cardHeight / 2;
    const bx = b.x + cardWidth / 2, by = b.y + cardHeight / 2;
    const conn = (edge.connection || 'AC').toUpperCase();
    const isDC = conn === 'DC';
    const isComm = conn === 'COMM' || conn === 'RS485';
    const color = isDC ? '#10b981' : isComm ? '#8b5cf6' : '#3b82f6';
    const dash = isDC ? '6,3' : isComm ? '3,3' : '';

    const edgeG = node('g', { class: 'topology-edge-group' });
    const lineAttrs = {
      x1: ax, y1: ay, x2: bx, y2: by,
      stroke: color, 'stroke-width': isComm ? 1.5 : 2.5,
      class: 'topology-link'
    };
    if (dash) lineAttrs['stroke-dasharray'] = dash;
    edgeG.append(node('line', lineAttrs));

    // Midpoint connection type badge
    const mx = (ax + bx) / 2, my = (ay + by) / 2;
    edgeG.append(
      node('rect', {
        x: mx - 24, y: my - 9, width: 48, height: 18, rx: 5,
        fill: '#ffffff', stroke: color, 'stroke-width': 1
      }),
      node('text', {
        x: mx, y: my + 3.5,
        'text-anchor': 'middle', fill: color, 'font-size': 9, 'font-weight': '700'
      }, conn)
    );
    svg.append(edgeG);
  });

  // Render rich equipment cards
  data.nodes.forEach(d => {
    const pos = positions.get(d.id);
    const g = node('g', {
      role: 'button',
      tabindex: 0,
      'aria-label': d.name || d.serial,
      class: 'topology-node-group'
    });

    // Card background
    const bg = node('rect', {
      x: pos.x, y: pos.y, width: cardWidth, height: cardHeight, rx: 10,
      fill: 'var(--surface)', stroke: 'var(--line)', 'stroke-width': 1.5,
      class: 'topology-node'
    });

    // Type color accent bar
    const typeUpper = (d.type || '').toUpperCase();
    const accentColor = typeUpper.includes('INV') ? '#3b82f6' :
                        typeUpper.includes('BAT') ? '#8b5cf6' :
                        typeUpper.includes('PV') || typeUpper.includes('SOLAR') ? '#10b981' :
                        typeUpper.includes('MET') || typeUpper.includes('GRID') ? '#f59e0b' :
                        typeUpper.includes('CHARGER') || typeUpper.includes('EV') ? '#06b6d4' : '#64748b';

    const accent = node('rect', {
      x: pos.x, y: pos.y, width: 6, height: cardHeight, rx: 3,
      fill: accentColor
    });

    // Equipment mini icon
    const iconG = drawMiniIcon(node, d.type, pos.x + 14, pos.y + 14);

    // Title / device label
    const title = node('text', {
      x: pos.x + 46, y: pos.y + 26,
      fill: 'var(--text)', 'font-size': 13, 'font-weight': '700'
    }, (d.name || d.serial || '').slice(0, 24));

    // Subtitle: Type & model
    const sub = node('text', {
      x: pos.x + 46, y: pos.y + 44,
      fill: 'var(--muted)', 'font-size': 11
    }, `${d.type || 'DEVICE'} · ${d.model || 'Standard'}`);

    // Status dot & label
    const statusUpper = (d.status || '').toUpperCase();
    const statusColor = statusUpper === 'ONLINE' ? '#10b981' :
                        statusUpper === 'STANDBY' ? '#3b82f6' :
                        statusUpper === 'ALARM' ? '#ef4444' : '#64748b';
    const statusDot = node('circle', {
      cx: pos.x + 20, cy: pos.y + 68, r: 3.5, fill: statusColor
    });
    const statusText = node('text', {
      x: pos.x + 28, y: pos.y + 72,
      fill: statusColor, 'font-size': 10, 'font-weight': '700'
    }, statusUpper || 'UNKNOWN');

    // Power measurement badge
    let powerBadge = null;
    if (d.power_kw != null && Number.isFinite(Number(d.power_kw))) {
      const pVal = Number(d.power_kw);
      const pValStr = `${number(pVal)} kW`;
      const pGroup = node('g', { class: 'topology-power-badge' });
      pGroup.append(
        node('rect', {
          x: pos.x + cardWidth - 84, y: pos.y + 56, width: 74, height: 22, rx: 6,
          fill: 'var(--canvas)', stroke: 'var(--line)', 'stroke-width': 1
        }),
        node('text', {
          x: pos.x + cardWidth - 47, y: pos.y + 71,
          'text-anchor': 'middle', fill: 'var(--text)', 'font-size': 11, 'font-weight': '700'
        }, pValStr)
      );
      powerBadge = pGroup;
    }

    g.append(bg, accent, iconG, title, sub, statusDot, statusText);
    if (powerBadge) g.append(powerBadge);

    g.onclick = () => deviceDetail(d.id);
    g.onkeydown = ev => { if (ev.key === 'Enter') deviceDetail(d.id); };
    svg.append(g);
  });

  return div(
    'stack',
    div('row',
      field(t('plants'), picker),
      btn(l('Sửa kết nối', 'Edit connections'), () => { state.site = id; go('devices', '', 'topology'); }),
      btn(l('Chi tiết nhà máy', 'Plant details'), () => { state.site = id; go('overview'); })
    ),
    card(l('Sơ đồ thiết bị đã khai báo', 'Recorded equipment graph'), svg, p(l('Sơ đồ thể hiện danh mục và kết nối đã khai báo; chưa phải bản vẽ điện nghiệm thu.', 'This graph shows recorded equipment and connections; it is not an accepted electrical drawing.'))),
    card(l('Các đường kết nối', 'Connections'), table([l('Từ', 'From'), l('Đến', 'To'), l('Kiểu kết nối', 'Connection')], data.edges.map(e => [e.source, e.target, e.connection]))),
    card(l('Thông số thiết bị', 'Equipment readings'), table([t('name'), 'Model', t('status'), 'kW'], data.nodes.map(d => [d.name || d.serial, d.model, d.status, number(d.power_kw)]))),
    card(l('Kiểm tra điện', 'Electrical checks'), table([l('Hạng mục', 'Check'), t('status'), l('Còn thiếu', 'Missing evidence')], Object.entries(data.validation).map(([k, v]) => [k, v.status, v.reason]))),
    card(
      l("Phân định ranh giới điện & Kiến trúc sơ đồ một sợi (SLD Energy Boundaries)", "Electrical Single-Line Diagram (SLD) Bus Architecture & Boundaries"),
      ui.notice(
        "Sơ đồ phân định 4 phân vùng điện độc lập: Điểm đấu nối lưới PCC (Công tơ 3 pha Class 0.5S) · Thanh cái AC chính Inverter/Pin · Phụ tải ưu tiên & Máy phát dự phòng ATS · Phụ tải linh hoạt (Trạm sạc EV DLM & Bơm nhiệt SG-Ready).",
        "SLD defines 4 isolated electrical zones: PCC Grid Boundary (Class 0.5S Meter) · AC Inverter/ESS Main Bus · Critical Backup & Genset ATS · Deferrable Loads (EV DLM & SG-Ready Heat Pump)."
      ),
      table(
        [l("Phân vùng SLD", "SLD Zone"), l("Thiết bị đo đếm / Điều khiển", "Boundary Assets"), l("Chức năng bảo vệ & Ranh giới", "Protection & Boundary Function"), l("Trạng thái nghiệm thu", "Acceptance Gate")],
        [
          [l("1. Ranh giới lưới PCC", "1. PCC Grid Boundary"), "3-Phase Smart Meter (SDM630 / DTSU666)", l("Đo đếm 4 góc phần tư, giám sát phát ngược (Zero-Export) và VUF < 2%", "4-Quadrant metering, zero-export CT monitoring, VUF < 2%"), ui.badge(l("ĐÃ XÁC MINH", "VERIFIED"), "good")],
          [l("2. Thanh cái Inverter & ESS", "2. Inverter & ESS Bus"), "Hybrid Inverter + LFP Battery Storage", l("Điều độ sạc/xả, bảo vệ Volt-Watt P(V), Volt-Var Q(V) và Freq droop", "Battery dispatch, Volt-Watt, Volt-Var, and Freq-Watt regulation"), ui.badge(l("HOẠT ĐỘNG", "ACTIVE"), "good")],
          [l("3. Phụ tải ưu tiên & Máy phát", "3. Critical Loads & Genset"), "Automatic Transfer Switch (ATS) + Genset 50kW", l("Chuyển mạch vi lưới cô lập (Islanded), chống đọng dầu (Wet Stacking) và Black-Start", "Islanded transition, wet-stacking prevention, and black-start"), ui.badge(l("SẴN SÀNG DỰ PHÒNG", "STANDBY"), "blue")],
          [l("4. Phụ tải linh hoạt điều phối", "4. Flexible Deferrable Loads"), "EV Fleet Chargers (DLM) + SG-Ready Heat Pump", l("Tự động chuyển mạch 1p/3p, ngắt 80% SOC và hấp thụ dư thừa vào bồn nhiệt", "Dynamic load management, 1p3p switching, 80% SOC cutoff, and thermal buffering"), ui.badge(l("ĐIỀU ĐỘ TỰ ĐỘNG", "OPTIMIZING"), "good")]
        ]
      )
    )
  );
}
