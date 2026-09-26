import { l, number } from './i18n.js';
import { icon } from './icons.js';

// Design references: SEM flow card (MIT), evcc Energyflow. Independent rendering
// on the global design system; no HA services, zero-filled sensors or inline CSS.
const branches = [
  ['pv_w', 'solar', 'sun', 'Điện mặt trời', 'Solar PV', 'data', 'M100 66 H300', false],
  ['grid_w', 'grid', 'bolt', 'Lưới điện', 'Grid', 'data', 'M500 66 H300', false],
  ['battery_w', 'battery', 'battery', 'Pin / BMS', 'Battery / BMS', 'control', 'M300 66 V154 Q300 166 288 166 H112 Q100 166 100 178 V246', true],
  ['load_w', 'load', 'home', 'Tải tiêu thụ', 'Site load', 'data', 'M300 66 V246', true],
  ['eps_w', 'backup', 'shield', 'EPS / Dự phòng', 'EPS / Backup', 'devices', 'M300 66 V154 Q300 166 312 166 H488 Q500 166 500 178 V246', true],
  ['generator_w', 'generator', 'power', 'Máy phát điện', 'Generator', 'devices', 'M100 426 H22 Q10 426 10 414 V16 Q10 6 22 6 H288 Q300 6 300 18 V66', false],
];

function svgNode(tag, attributes) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, val] of Object.entries(attributes)) node.setAttribute(key, val);
  return node;
}

export function flowState(metric, snapshot, now = Date.now()) {
  const val = snapshot[metric], meta = snapshot.channels?.[metric];
  const fresh = meta?.quality === 'GOOD' && Number.isFinite(Date.parse(meta.valid_until)) && Date.parse(meta.valid_until) > now;
  if (!fresh || !Number.isFinite(val)) return { value: null, active: false, reverse: false, status: meta?.quality === 'GOOD' ? 'STALE' : meta?.quality || 'MISSING' };
  return { value: val, active: Math.abs(val) > 10, reverse: val < 0, status: 'GOOD' };
}

class EnergyFlowElement extends HTMLElement {
  connectedCallback() {
    this.refresh?.();
    this.timer = setInterval(() => this.refresh?.(), 1000);
  }
  disconnectedCallback() { clearInterval(this.timer); }
}
if (!customElements.get('solar-energy-flow')) customElements.define('solar-energy-flow', EnergyFlowElement);

export function energyFlowCard(ui, snapshot = {}, navigate) {
  const { e, div, btn, card, badge } = ui;
  const p = (text, cls = '') => e('p', text, cls);
  const root = document.createElement('solar-energy-flow');
  root.className = 'power-flow';
  const outer = card(l('Dòng năng lượng', 'Energy flow'));
  outer.classList.add('energy-flow-card');
  const hasGenerator = snapshot.generator_w != null || snapshot.channels?.generator_w?.sources?.length > 0;
  const stage = div('power-flow-stage' + (hasGenerator ? ' has-generator' : ''));
  const svg = svgNode('svg', { viewBox: `0 0 600 ${hasGenerator ? 492 : 312}`, preserveAspectRatio: 'none', class: 'power-flow-wires', 'aria-hidden': 'true' });
  stage.append(svg);
  const hub = btn('', () => navigate('devices'), 'power-node power-hub');
  hub.append(icon('device'), e('b', l('Biến tần / Hệ thống', 'Inverter / System')), p(l('Xem thiết bị', 'View equipment'), 'small muted'));
  stage.append(hub);
  const nodes = [];
  for (const [metric, tone, glyph, vi, en, route, path] of branches) {
    if (metric === 'generator_w' && !hasGenerator) continue;
    const wire = svgNode('g', { class: `power-branch tone-${tone}`, 'data-metric': metric });
    wire.append(svgNode('path', { d: path, class: 'power-wire-track' }));
    const moving = svgNode('path', { d: path, class: 'power-wire-motion' });
    wire.append(moving);
    svg.append(wire);
    const node = btn('', () => navigate(route), `power-node tone-${tone} node-${tone}`);
    node.setAttribute('aria-label', l(vi, en));
    const reading = e('strong', '—', 'power-value'), direction = p('', 'power-direction');
    const source = p('', 'small muted power-source');
    node.append(div('power-node-heading', icon(glyph), e('b', l(vi, en))), reading, direction, source);
    stage.append(node);
    nodes.push({ metric, wire, node, reading, direction, source, label: l(vi, en) });
  }
  let paused = false, tableMode = false;
  const mode = btn(l('Dạng bảng', 'Table view'), () => {
    tableMode = !tableMode; root.classList.toggle('is-table', tableMode);
    mode.textContent = tableMode ? l('Sơ đồ', 'Diagram view') : l('Dạng bảng', 'Table view');
    mode.setAttribute('aria-pressed', String(tableMode));
  });
  const motion = btn(l('Dừng chuyển động', 'Pause motion'), () => {
    paused = !paused; root.classList.toggle('is-paused', paused);
    motion.textContent = paused ? l('Tiếp tục chuyển động', 'Resume motion') : l('Dừng chuyển động', 'Pause motion');
    motion.setAttribute('aria-pressed', String(paused));
  });
  const full = btn(l('Toàn màn hình', 'Fullscreen'), async () => {
    if (document.fullscreenElement === outer) {
      try { await document.exitFullscreen(); } catch { /* Page may have exited concurrently. */ }
    }
    else if (outer.requestFullscreen) {
      try { await outer.requestFullscreen(); } catch { outer.classList.toggle('is-expanded'); }
    } else outer.classList.toggle('is-expanded');
  });
  const summary = badge('', 'gray');
  root.refresh = () => {
    root.classList.toggle('is-hidden', document.hidden);
    let count = 0;
    for (const entry of nodes) {
      const state = flowState(entry.metric, snapshot);
      const { value: val } = state;
      count += val !== null ? 1 : 0;
      entry.wire.classList.toggle('is-active', state.active);
      entry.wire.classList.toggle('is-reversed', state.reverse);
      entry.wire.dataset.direction = !state.active ? 'stopped' : state.reverse ? 'reverse' : 'forward';
      entry.node.classList.toggle('is-unavailable', val === null);
      entry.reading.textContent = val === null ? '—' : Math.abs(val) >= 1000 ? `${number(Math.abs(val) / 1000, 2)} kW` : `${number(Math.abs(val), 0)} W`;
      let direction = state.status === 'STALE' ? l('Số đo đã cũ', 'Reading expired') : l('Chưa có số đo hợp lệ', 'No accepted measurement');
      if (val !== null) {
        if (entry.metric === 'battery_w') direction = val > 0 ? l('Đang sạc ↓', 'Charging ↓') : val < 0 ? l('Đang xả ↑', 'Discharging ↑') : l('Chờ', 'Idle');
        else if (entry.metric === 'grid_w') direction = val > 0 ? l('Nhập lưới ←', 'Import ←') : val < 0 ? l('Xuất lưới →', 'Export →') : l('Cân bằng', 'Balanced');
        else direction = Math.abs(val) <= 10 ? l('Công suất thấp / chờ', 'Low power / idle') : l('Đang truyền điện', 'Power flowing');
      }
      entry.direction.textContent = direction;
      const meta = snapshot.channels?.[entry.metric];
      const origins = [...new Set((meta?.sources || []).map(s => s.source))];
      const soc = flowState('battery_soc', snapshot).value;
      entry.source.textContent = entry.metric === 'battery_w' && soc != null ? `SOC ${number(soc, 0)}%` : origins.join(' · ');
      entry.node.title = `${entry.label} · ${state.status}\n${(meta?.sources || []).map(s => `${s.device_id} · ${s.metric} · ${s.source_timestamp}`).join('\n')}`;
    }
    summary.textContent = `${count}/${nodes.length} ${l('nhánh có số đo', 'measured branches')}`;
  };
  root.append(div('toolbar', summary, div('row', mode, motion, full)), stage,
    div('power-flow-legend', ...nodes.map(n => div(`row ${n.wire.getAttribute('class').split(' ')[1]}`, e('span', '●'), e('span', n.label)))),
    p(l('Mũi tên thể hiện chiều công suất; không suy ra điện từ nguồn nào cấp riêng cho từng tải. Số đo thiếu hoặc hết hạn dừng chuyển động. EPS là công suất đo, không xác nhận khả năng dự phòng.',
      'Arrows show power direction, not source-to-load allocation or electrical wiring. Missing or expired readings stop motion. EPS power does not certify backup readiness.'), 'small muted'));
  root.refresh();
  outer.append(root);
  return outer;
}
