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

function svgNode(tag, attributes, ...children) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, val] of Object.entries(attributes)) {
    if (val != null) node.setAttribute(key, String(val));
  }
  for (const child of children) {
    if (typeof child === 'string') node.textContent = child;
    else if (child) node.append(child);
  }
  return node;
}

// --- Rich SVG Geometry Illustrations for Energy Flow Nodes -----------------

function solarPvIllustration() {
  const svg = svgNode('svg', { viewBox: '0 0 48 48', class: 'energy-art-svg solar-art', 'aria-hidden': 'true' });
  // Sun in top-right with radiating rays
  const sun = svgNode('circle', { cx: '36', cy: '11', r: '5.5', fill: '#f59e0b', opacity: '0.9' });
  const rays = svgNode('g', { stroke: '#f59e0b', 'stroke-width': '1.3', 'stroke-linecap': 'round', opacity: '0.85' });
  rays.append(
    svgNode('line', { x1: '36', y1: '2', x2: '36', y2: '4' }),
    svgNode('line', { x1: '43', y1: '4', x2: '41.5', y2: '5.5' }),
    svgNode('line', { x1: '45', y1: '11', x2: '43', y2: '11' }),
    svgNode('line', { x1: '29', y1: '4', x2: '30.5', y2: '5.5' }),
  );

  // Tilted PV Panel 1 (left module)
  const p1 = svgNode('polygon', {
    points: '5,37 17,19 30,19 18,37',
    fill: 'var(--surface)',
    stroke: 'currentColor',
    'stroke-width': '1.8',
    'stroke-linejoin': 'round',
  });
  const lH1 = svgNode('line', { x1: '11', y1: '28', x2: '24', y2: '28', stroke: 'currentColor', 'stroke-width': '0.9', opacity: '0.6' });
  const lV1 = svgNode('line', { x1: '12', y1: '37', x2: '23', y2: '19', stroke: 'currentColor', 'stroke-width': '0.9', opacity: '0.6' });

  // Tilted PV Panel 2 (right module)
  const p2 = svgNode('polygon', {
    points: '20,37 32,19 43,19 31,37',
    fill: 'var(--surface)',
    stroke: 'currentColor',
    'stroke-width': '1.8',
    'stroke-linejoin': 'round',
  });
  const lH2 = svgNode('line', { x1: '26', y1: '28', x2: '37', y2: '28', stroke: 'currentColor', 'stroke-width': '0.9', opacity: '0.6' });
  const lV2 = svgNode('line', { x1: '26', y1: '37', x2: '37', y2: '19', stroke: 'currentColor', 'stroke-width': '0.9', opacity: '0.6' });

  // Mounting structure
  const mount = svgNode('path', {
    d: 'M12 37 L12 43 M24 37 L24 43 M32 37 L32 43 M7 43 H38',
    stroke: 'currentColor',
    'stroke-width': '1.4',
    'stroke-linecap': 'round',
    opacity: '0.45'
  });

  svg.append(sun, rays, mount, p1, lH1, lV1, p2, lH2, lV2);
  return svg;
}

function gridIllustration() {
  const svg = svgNode('svg', { viewBox: '0 0 48 48', class: 'energy-art-svg grid-art', 'aria-hidden': 'true' });
  const tower = svgNode('g', { stroke: 'currentColor', 'stroke-width': '1.5', 'stroke-linejoin': 'round', 'stroke-linecap': 'round', fill: 'none' });

  // Pylon lattice legs tapering from bottom to top
  const legs = svgNode('path', { d: 'M13 44 L21 17 L24 6 L27 17 L35 44' });

  // Upper & lower transmission crossarms
  const crossarm1 = svgNode('line', { x1: '11', y1: '17', x2: '37', y2: '17' });
  const crossarm2 = svgNode('line', { x1: '6', y1: '25', x2: '42', y2: '25' });

  // Lattice diagonal cross-bracing
  const lattice = svgNode('path', {
    d: 'M18 44 L30 33 M30 44 L18 33 M18 33 L28 25 M30 33 L20 25 M20 25 L26 17 M28 25 L22 17 M21 17 L24 6 M27 17 L24 6',
    'stroke-width': '1.1',
    opacity: '0.6'
  });

  // Insulator strings hanging from crossarms
  const insulators = svgNode('path', {
    d: 'M11 17 V21 M37 17 V21 M6 25 V29 M42 25 V29',
    'stroke-width': '2.2',
    'stroke-linecap': 'round'
  });

  // High-tension catenary transmission lines
  const wires = svgNode('path', {
    d: 'M2 23 Q6 29 11 21 M37 21 Q42 29 46 23 M2 31 Q6 35 6 29 M42 29 Q44 35 46 31',
    'stroke-width': '1.2',
    opacity: '0.75'
  });

  const ground = svgNode('line', { x1: '10', y1: '44', x2: '38', y2: '44', opacity: '0.5' });

  tower.append(legs, crossarm1, crossarm2, lattice, insulators, wires, ground);
  svg.append(tower);
  return svg;
}

function batteryIllustration(soc = null, isCharging = false, isDischarging = false) {
  const svg = svgNode('svg', { viewBox: '0 0 48 48', class: 'energy-art-svg battery-art', 'aria-hidden': 'true' });
  
  // Outer battery cabinet chassis
  const chassis = svgNode('rect', {
    x: '13', y: '9', width: '22', height: '35', rx: '4',
    fill: 'var(--surface)', stroke: 'currentColor', 'stroke-width': '1.8'
  });

  // Battery terminal cathode cap (+ post)
  const terminal = svgNode('rect', {
    x: '20', y: '5', width: '8', height: '4', rx: '1.5',
    fill: 'currentColor', opacity: '0.85'
  });

  // 5 Segmented energy level bars
  const barY = [37, 31, 25, 19, 13];
  const barsGroup = svgNode('g', { class: 'battery-bars-group' });
  for (let i = 0; i < 5; i++) {
    const bar = svgNode('rect', {
      x: '16', y: String(barY[i]), width: '16', height: '4.5', rx: '1.2',
      fill: 'var(--line)', opacity: '0.3', class: 'battery-bar-segment'
    });
    barsGroup.append(bar);
  }

  // Active status glyph overlay (charging bolt or discharging arrow)
  const glyphGroup = svgNode('g', { class: 'battery-status-glyph' });

  svg.append(chassis, terminal, barsGroup, glyphGroup);
  updateBatteryIllustration(svg, soc, isCharging, isDischarging);
  return svg;
}

function updateBatteryIllustration(svg, soc, isCharging, isDischarging) {
  const bars = svg.querySelectorAll('.battery-bar-segment');
  const glyphGroup = svg.querySelector('.battery-status-glyph');
  if (!bars.length) return;

  const validSoc = Number.isFinite(soc) ? Math.max(0, Math.min(100, soc)) : null;
  const numLit = validSoc != null ? Math.ceil(validSoc / 20) : 0;
  const barColor = validSoc == null ? 'var(--line)' :
                   validSoc <= 20 ? '#ef4444' :
                   validSoc <= 50 ? '#f59e0b' : '#10b981';

  bars.forEach((bar, idx) => {
    const lit = idx < numLit;
    bar.setAttribute('fill', lit ? barColor : 'var(--line)');
    bar.setAttribute('opacity', lit ? '0.95' : '0.25');
  });

  if (glyphGroup) {
    glyphGroup.replaceChildren();
    if (isCharging) {
      const bolt = svgNode('path', {
        d: 'M25 18 L21 26 H26 L23 34 L29 25 H24 Z',
        fill: '#f59e0b', stroke: '#ffffff', 'stroke-width': '0.75',
        class: 'art-charging-bolt'
      });
      glyphGroup.append(bolt);
    } else if (isDischarging) {
      const arrow = svgNode('path', {
        d: 'M24 19 V31 M20 27 L24 31 L28 27',
        stroke: '#3b82f6', 'stroke-width': '2.2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round',
        fill: 'none', class: 'art-discharging-arrow'
      });
      glyphGroup.append(arrow);
    }
  }
}

function inverterHubIllustration(active = false) {
  const svg = svgNode('svg', { viewBox: '0 0 54 54', class: 'energy-art-svg inverter-art' + (active ? ' is-active' : ''), 'aria-hidden': 'true' });
  
  // Side heat-sink cooling fins
  const ribs = svgNode('path', {
    d: 'M6 14 H9 M6 20 H9 M6 26 H9 M6 32 H9 M6 38 H9 M45 14 H48 M45 20 H48 M45 26 H48 M45 32 H48 M45 38 H48',
    stroke: 'currentColor', 'stroke-width': '1.5', 'stroke-linecap': 'round', opacity: '0.6'
  });

  // Main inverter enclosure
  const chassis = svgNode('rect', {
    x: '9', y: '7', width: '36', height: '40', rx: '4',
    fill: 'var(--surface)', stroke: 'currentColor', 'stroke-width': '2'
  });

  // Tempered glass digital display screen
  const display = svgNode('rect', {
    x: '14', y: '12', width: '26', height: '16', rx: '2',
    fill: '#0f172a', stroke: 'currentColor', 'stroke-width': '0.75', opacity: '0.9'
  });

  // DC to AC conversion glyphs:
  // DC symbol (=) on left
  const dcGlyph = svgNode('path', {
    d: 'M17 18 H22 M17 21 H22',
    stroke: '#38bdf8', 'stroke-width': '1.2', 'stroke-linecap': 'round'
  });
  // Center conversion arrow
  const arrowGlyph = svgNode('path', {
    d: 'M25 20 H28 M27 18 L29 20 L27 22',
    stroke: '#94a3b8', 'stroke-width': '1.2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round'
  });
  // AC sine wave (~) on right
  const acGlyph = svgNode('path', {
    d: 'M31 20 Q32.5 17 34 20 T37 20',
    stroke: '#22c55e', 'stroke-width': '1.4', 'stroke-linecap': 'round', fill: 'none'
  });

  // Status LED cluster:
  // LED 1 (Run)
  const ledRun = svgNode('circle', {
    cx: '20', cy: '36', r: '2.2',
    fill: active ? '#22c55e' : '#64748b',
    class: 'art-led-run' + (active ? ' art-led-active' : '')
  });
  // LED 2 (Comms)
  const ledComms = svgNode('circle', {
    cx: '27', cy: '36', r: '2.2',
    fill: active ? '#38bdf8' : '#64748b',
    class: 'art-led-comms'
  });
  // LED 3 (Alarm)
  const ledAlarm = svgNode('circle', {
    cx: '34', cy: '36', r: '2.2',
    fill: '#334155',
    class: 'art-led-alarm'
  });

  const brandLine = svgNode('line', {
    x1: '18', y1: '42', x2: '36', y2: '42',
    stroke: 'currentColor', 'stroke-width': '1', opacity: '0.4'
  });

  svg.append(ribs, chassis, display, dcGlyph, arrowGlyph, acGlyph, ledRun, ledComms, ledAlarm, brandLine);
  return svg;
}

function updateInverterIllustration(svg, active) {
  svg.classList.toggle('is-active', Boolean(active));
  const ledRun = svg.querySelector('.art-led-run');
  const ledComms = svg.querySelector('.art-led-comms');
  if (ledRun) {
    ledRun.setAttribute('fill', active ? '#22c55e' : '#64748b');
    ledRun.classList.toggle('art-led-active', Boolean(active));
  }
  if (ledComms) {
    ledComms.setAttribute('fill', active ? '#38bdf8' : '#64748b');
  }
}

function loadIllustration() {
  const svg = svgNode('svg', { viewBox: '0 0 48 48', class: 'energy-art-svg load-art', 'aria-hidden': 'true' });
  const facility = svgNode('g', { stroke: 'currentColor', 'stroke-width': '1.5', 'stroke-linejoin': 'round', fill: 'none' });

  // Facility / Building profile
  const building = svgNode('path', {
    d: 'M8 42 V22 L22 10 L36 22 V42 Z',
    fill: 'var(--surface)', 'stroke-width': '1.8'
  });

  // Roof vent unit
  const roofVent = svgNode('path', { d: 'M28 15 V11 H33 V19' });

  // Warm illuminated window panes
  const win1 = svgNode('rect', { x: '13', y: '25', width: '6', height: '6', rx: '1', fill: '#f59e0b', opacity: '0.75', stroke: 'none' });
  const win2 = svgNode('rect', { x: '25', y: '25', width: '6', height: '6', rx: '1', fill: '#f59e0b', opacity: '0.75', stroke: 'none' });

  // Main doorway
  const door = svgNode('path', { d: 'M19 42 V34 H25 V42', fill: 'var(--surface)' });

  // Site energy meter widget
  const meter = svgNode('circle', { cx: '38', cy: '34', r: '5', stroke: 'currentColor', 'stroke-width': '1.2', fill: 'var(--surface)' });
  const indicator = svgNode('path', { d: 'M38 34 L40 32', stroke: 'currentColor', 'stroke-width': '1.2', 'stroke-linecap': 'round' });

  facility.append(roofVent, building, win1, win2, door, meter, indicator);
  svg.append(facility);
  return svg;
}

function backupIllustration() {
  const svg = svgNode('svg', { viewBox: '0 0 48 48', class: 'energy-art-svg backup-art', 'aria-hidden': 'true' });
  const shield = svgNode('path', {
    d: 'M24 6 L38 12 V24 C38 33 24 42 24 42 C24 42 10 33 10 24 V12 Z',
    fill: 'var(--surface)', stroke: 'currentColor', 'stroke-width': '1.8', 'stroke-linejoin': 'round'
  });
  const innerCrest = svgNode('path', {
    d: 'M24 10 L34 15 V23 C34 30 24 37 24 37 C24 37 14 30 14 23 V15 Z',
    fill: 'none', stroke: 'currentColor', 'stroke-width': '0.9', opacity: '0.5'
  });
  const bolt = svgNode('path', {
    d: 'M26 14 L19 24 H25 L22 34 L30 22 H24 Z',
    fill: '#06b6d4', stroke: 'currentColor', 'stroke-width': '0.75'
  });
  svg.append(shield, innerCrest, bolt);
  return svg;
}

function generatorIllustration() {
  const svg = svgNode('svg', { viewBox: '0 0 48 48', class: 'energy-art-svg generator-art', 'aria-hidden': 'true' });
  const genset = svgNode('g', { stroke: 'currentColor', 'stroke-width': '1.5', 'stroke-linejoin': 'round', fill: 'none' });
  const chassis = svgNode('rect', { x: '8', y: '16', width: '32', height: '24', rx: '3', fill: 'var(--surface)', 'stroke-width': '1.8' });
  const rotor = svgNode('circle', { cx: '30', cy: '28', r: '6', stroke: 'currentColor', 'stroke-width': '1.2' });
  const louvers = svgNode('path', {
    d: 'M12 21 H18 M12 25 H18 M12 29 H18 M12 33 H18',
    'stroke-width': '1.2', 'stroke-linecap': 'round', opacity: '0.7'
  });
  const exhaust = svgNode('path', { d: 'M14 16 V10 H20 V16', 'stroke-width': '1.4' });
  const skids = svgNode('line', { x1: '6', y1: '42', x2: '42', y2: '42', 'stroke-width': '2', 'stroke-linecap': 'round' });
  genset.append(exhaust, chassis, rotor, louvers, skids);
  svg.append(genset);
  return svg;
}

function createBranchArt(tone) {
  const wrap = document.createElement('div');
  wrap.className = 'power-node-art';
  let art;
  if (tone === 'solar') art = solarPvIllustration();
  else if (tone === 'grid') art = gridIllustration();
  else if (tone === 'battery') art = batteryIllustration();
  else if (tone === 'load') art = loadIllustration();
  else if (tone === 'backup') art = backupIllustration();
  else if (tone === 'generator') art = generatorIllustration();
  else art = icon('device');
  wrap.append(art);
  return { wrap, art };
}

// ---------------------------------------------------------------------------

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

  // Central Inverter Hub with rich hybrid inverter geometry
  const hub = btn('', () => navigate('devices'), 'power-node power-hub');
  const hubArtWrap = div('power-node-art');
  const hubArt = inverterHubIllustration(false);
  hubArtWrap.append(hubArt);
  const hubTitle = div('power-node-heading', e('b', l('Biến tần Hybrid', 'Hybrid Inverter')));
  const hubThroughput = e('strong', '—', 'power-value');
  const hubStatus = p(l('Xem thiết bị', 'View equipment'), 'small muted power-source');
  hub.append(hubArtWrap, hubTitle, hubThroughput, hubStatus);
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
    const { wrap: artWrap, art } = createBranchArt(tone);
    const reading = e('strong', '—', 'power-value');
    const direction = p('', 'power-direction');
    const source = p('', 'small muted power-source');
    node.append(artWrap, div('power-node-heading', e('b', l(vi, en))), reading, direction, source);
    stage.append(node);
    nodes.push({ metric, wire, node, art, reading, direction, source, label: l(vi, en), tone });
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
    let anyActiveFlow = false;
    let anyValidPower = false;
    let totalThroughputW = 0;

    for (const entry of nodes) {
      const state = flowState(entry.metric, snapshot);
      const { value: val } = state;
      count += val !== null ? 1 : 0;
      if (val !== null) anyValidPower = true;
      if (state.active) {
        anyActiveFlow = true;
        if (entry.metric === 'pv_w') totalThroughputW += Math.abs(val);
        else if (entry.metric === 'battery_w') totalThroughputW += Math.abs(val);
      }

      entry.wire.classList.toggle('is-active', state.active);
      entry.wire.classList.toggle('is-reversed', state.reverse);
      const absVal = Math.abs(val || 0);
      entry.wire.dataset.direction = !state.active ? 'stopped' : state.reverse ? 'reverse' : 'forward';
      entry.wire.dataset.power = !state.active ? 'none' : absVal >= 5000 ? 'high' : absVal >= 1000 ? 'medium' : 'low';
      entry.node.classList.toggle('is-unavailable', val === null);
      entry.reading.textContent = val === null ? '—' : absVal >= 1000 ? `${number(absVal / 1000, 2)} kW` : `${number(absVal, 0)} W`;

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

      if (entry.metric === 'battery_w') {
        const isCharging = val !== null && val > 10;
        const isDischarging = val !== null && val < -10;
        updateBatteryIllustration(entry.art, soc, isCharging, isDischarging);
        if (soc != null) {
          entry.source.textContent = `SOC ${number(soc, 0)}%`;
          entry.node.dataset.soc = String(Math.round(Math.min(100, Math.max(0, soc))));
        } else {
          entry.source.textContent = origins.join(' · ') || l('Chưa có SOC', 'No SOC');
        }
      } else {
        entry.source.textContent = origins.join(' · ');
      }
      entry.node.title = `${entry.label} · ${state.status}\n${(meta?.sources || []).map(s => `${s.device_id} · ${s.metric} · ${s.source_timestamp}`).join('\n')}`;
    }

    // Refresh central inverter hub state & throughput
    updateInverterIllustration(hubArt, anyActiveFlow);
    if (!anyValidPower) {
      hubThroughput.textContent = '—';
      hubStatus.textContent = l('Chưa có số đo', 'No telemetry');
    } else if (totalThroughputW >= 1000) {
      hubThroughput.textContent = `${number(totalThroughputW / 1000, 2)} kW`;
      hubStatus.textContent = l('Tổng công suất biến đổi', 'Conversion throughput');
    } else if (totalThroughputW > 0) {
      hubThroughput.textContent = `${number(totalThroughputW, 0)} W`;
      hubStatus.textContent = l('Tổng công suất biến đổi', 'Conversion throughput');
    } else {
      hubThroughput.textContent = l('Sẵn sàng', 'Standby');
      hubStatus.textContent = l('Không có dòng tải', 'Zero throughput');
    }

    summary.textContent = `${count}/${nodes.length} ${l('nhánh có số đo', 'measured branches')}`;
  };

  root.append(
    div('toolbar', summary, div('row', mode, motion, full)),
    stage,
    div('power-flow-legend', ...nodes.map(n => div(`row ${n.wire.getAttribute('class').split(' ')[1]}`, e('span', '●'), e('span', n.label)))),
    p(l('Mũi tên thể hiện chiều công suất; không suy ra điện từ nguồn nào cấp riêng cho từng tải. Số đo thiếu hoặc hết hạn dừng chuyển động. EPS là công suất đo, không xác nhận khả năng dự phòng.',
      'Arrows show power direction, not source-to-load allocation or electrical wiring. Missing or expired readings stop motion. EPS power does not certify backup readiness.'), 'small muted')
  );
  root.refresh();
  outer.append(root);
  return outer;
}
