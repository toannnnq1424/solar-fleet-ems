import { l, number } from './i18n.js';

// A single tooltip per chart, with per-period hit areas for pointer, touch and
// keyboard. Never interpolates missing values or mutates the supplied readings.
export function inspectDailyChart(svg, rows, keys, geometry, unit) {
  const {left, right, top, bottom} = geometry;
  const wrapper = document.createElement('div');
  wrapper.className = 'interactive-chart';
  const tooltip = document.createElement('div');
  tooltip.className = 'chart-inspector';
  tooltip.setAttribute('role', 'tooltip');
  tooltip.hidden = true;
  const heading = document.createElement('strong');
  const list = document.createElement('dl');
  tooltip.append(heading, list);
  const node = (tag, attrs) => {
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, String(value));
    return el;
  };
  const crosshair = node('line', {y1: top, y2: bottom, class: 'chart-crosshair'});
  svg.append(crosshair);
  const targets = [];
  let pinned = false;
  const hide = () => { tooltip.hidden = true; crosshair.classList.remove('is-visible'); };
  const show = index => {
    const row = rows[index];
    heading.textContent = String(row.date);
    list.replaceChildren();
    for (const [key, label, tone] of keys) {
      const dt = document.createElement('dt'), dd = document.createElement('dd');
      dt.textContent = label;
      dt.className = 'inspector-series ' + tone;
      const value = row[key];
      dd.textContent = Number.isFinite(value) && value >= 0 ? number(value, 2) + ' ' + unit : '—';
      list.append(dt, dd);
    }
    tooltip.hidden = false;
    const x = left + (index + .5) * (right - left) / rows.length;
    crosshair.setAttribute('x1', x); crosshair.setAttribute('x2', x);
    crosshair.classList.add('is-visible');
  };
  rows.forEach((row, index) => {
    const width = (right - left) / rows.length;
    const hit = node('rect', {x: left + index * width, y: top, width, height: bottom - top,
      class: 'chart-hit-target', tabindex: 0, role: 'button',
      'aria-label': l('Xem số liệu ngày ', 'Inspect observations for ') + row.date});
    hit.onpointerenter = () => { if (!pinned) show(index); };
    hit.onfocus = () => show(index);
    hit.onclick = () => { pinned = true; show(index); };
    hit.onkeydown = event => {
      if (event.key === 'Escape') { pinned = false; hide(); }
      else if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); pinned = true; show(index); }
      else if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
        event.preventDefault();
        targets[Math.max(0, Math.min(rows.length - 1, index + (event.key === 'ArrowRight' ? 1 : -1)))].focus();
      }
    };
    targets.push(hit); svg.append(hit);
  });
  wrapper.onpointerleave = () => { if (!pinned && !wrapper.contains(document.activeElement)) hide(); };
  wrapper.onfocusout = event => { if (!pinned && !wrapper.contains(event.relatedTarget)) hide(); };
  const close = document.createElement('button');
  close.type = 'button'; close.className = 'chart-inspector-close';
  close.textContent = '×'; close.setAttribute('aria-label', l('Đóng thông số', 'Close observations'));
  close.onclick = () => { pinned = false; hide(); };
  tooltip.append(close);
  wrapper.append(svg, tooltip);
  return wrapper;
}
