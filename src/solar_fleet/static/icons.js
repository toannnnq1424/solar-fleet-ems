// One SVG icon vocabulary for navigation and components. No external assets.
const paths = {
  home: "M3 10l9-7 9 7M5 9v12h5v-7h4v7h5V9",
  plant: "M3 21V9l6 3V6l6 3V3h6v18H3zM6 16h1m4 0h1m5 0h1",
  grid: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
  map: "M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1116 0zM15 10a3 3 0 11-6 0 3 3 0 016 0",
  device: "M4 3h16v18H4zM8 7h8v6H8zM8 17h1m6 0h1",
  control:
    "M5 3v7m0 4v7M12 3v12m0 4v2M19 3v2m0 4v12M2 10h6v4H2zM9 15h6v4H9zM16 5h6v4h-6z",
  calendar: "M4 5h16v16H4zM4 10h16M8 2v6m8-6v6M8 14h1m5 0h1m-7 4h1m5 0h1",
  activity: "M2 12h5l3-8 4 16 3-8h5",
  chart: "M4 14h4v7H4zM10 8h4v13h-4zM16 3h4v18h-4z",
  bell: "M4 17h16l-2-3V9a6 6 0 00-12 0v5l-2 3zM9 21h6",
  report: "M5 2h9l5 5v15H5zM14 2v6h5M9 12h6m-6 4h6",
  tool: "M14 3a6 6 0 00-6 8L2 17l5 5 6-6a6 6 0 008-7l-4 4-5-5 4-4z",
  settings:
    "M12 8a4 4 0 110 8 4 4 0 010-8M9 2h6l1 4 4 1 2 5-3 3v4l-5 3-3-2-4 1-4-4 1-4-2-3 3-5 4-1z",
  search: "M16 16l6 6M18 10a8 8 0 11-16 0 8 8 0 0116 0",
  help: "M9 8a3 3 0 116 0c0 2-3 2-3 5m0 4h.01M22 12a10 10 0 11-20 0 10 10 0 0120 0",
  check: "M8 12l3 3 6-7M22 12a10 10 0 11-20 0 10 10 0 0120 0",
  circle: "M22 12a10 10 0 11-20 0 10 10 0 0120 0",
  shield: "M12 2l9 4v6c0 6-9 10-9 10S3 18 3 12V6l9-4zM8 12l3 3 5-6",
  key: "M14 10l-9 11H2v-4l9-9M21 6a5 5 0 11-10 0 5 5 0 0110 0",
  alert: "M12 2L1 21h22L12 2zM12 8v6m0 3h.01",
  info: "M12 11v6m0-10h.01M22 12a10 10 0 11-20 0 10 10 0 0120 0",
};
export function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", "ui-icon");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(svg.namespaceURI, "path");
  path.setAttribute("d", paths[name] || paths.grid);
  svg.append(path);
  return svg;
}
