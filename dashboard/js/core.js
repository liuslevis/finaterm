// Shared helpers: formatting, HTML escaping, chart factory/legend, status banner, drag-to-delete bin.

function formatDisplayDate(value) {
  if (value && typeof value === "object" && "year" in value) {
    return `${value.year}/${String(value.month).padStart(2, "0")}/${String(value.day).padStart(2, "0")}`;
  }
  const timestamp = typeof value === "number" && value < 1e12 ? value * 1000 : value;
  const date = value instanceof Date ? value : new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, "0")}/${String(date.getDate()).padStart(2, "0")}`;
}

function createFinancialChart(host) {
  const api = LightweightCharts.createChart(host, {
    autoSize: true,
    layout: {
      background: { type: LightweightCharts.ColorType.Solid, color: "transparent" },
      textColor: "#718796",
      fontSize: 10,
      fontFamily: 'Inter, "Segoe UI", sans-serif',
      attributionLogo: true
    },
    localization: {
      locale: "zh-CN",
      timeFormatter: formatDisplayDate
    },
    grid: {
      vertLines: { color: "rgba(151,180,202,.05)" },
      horzLines: { color: "rgba(151,180,202,.08)" }
    },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: { color: "rgba(151,180,202,.35)", labelBackgroundColor: "#203645" },
      horzLine: { color: "rgba(151,180,202,.35)", labelBackgroundColor: "#203645" }
    },
    rightPriceScale: {
      borderColor: "rgba(151,180,202,.15)",
      scaleMargins: { top: .14, bottom: .12 }
    },
    leftPriceScale: {
      visible: false,
      borderColor: "rgba(151,180,202,.15)",
      scaleMargins: { top: .14, bottom: .12 }
    },
    timeScale: {
      borderColor: "rgba(151,180,202,.15)",
      timeVisible: true,
      secondsVisible: false,
      tickMarkFormatter: formatDisplayDate,
      rightOffset: 2,
      minBarSpacing: .05
    },
    handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true },
    handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true }
  });
  const legend = document.createElement("div");
  legend.className = "chart-legend";
  const empty = document.createElement("div");
  empty.className = "chart-empty";
  host.append(legend, empty);
  const chart = { api, host, series: [], legend, empty, legendItems: [], carryMarkers: new Map() };
  api.subscribeCrosshairMove(param => {
    renderChartLegend(chart, param.seriesData, param.time);
  });
  return chart;
}

const fmt = new Intl.NumberFormat("zh-CN");
const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, ch => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
})[ch]);
const dragTrash = document.getElementById("dragTrash");
let dragTrashDropHandler = null;

function showDragTrash(onDrop) {
  dragTrashDropHandler = onDrop;
  dragTrash.classList.add("visible");
  dragTrash.setAttribute("aria-hidden", "false");
}

function hideDragTrash() {
  dragTrashDropHandler = null;
  dragTrash.classList.remove("visible", "active");
  dragTrash.setAttribute("aria-hidden", "true");
}

dragTrash.addEventListener("dragover", event => {
  if (!dragTrashDropHandler) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
  dragTrash.classList.add("active");
});
dragTrash.addEventListener("dragleave", () => dragTrash.classList.remove("active"));
dragTrash.addEventListener("drop", event => {
  if (!dragTrashDropHandler) return;
  event.preventDefault();
  dragTrash.classList.remove("active");
  dragTrashDropHandler();
});

function setStatus(type, text) {
  document.getElementById("liveDot").className = `live-dot ${type === "live" ? "" : type}`;
  document.getElementById("statusText").textContent = text;
}

function showError(message) {
  const banner = document.getElementById("errorBanner");
  banner.textContent = message;
  banner.classList.toggle("show", Boolean(message));
}

function clearChart(chart) {
  chart.series.forEach(series => chart.api.removeSeries(series));
  chart.series = [];
  chart.legendItems = [];
  chart.legend.innerHTML = "";
  chart.carryMarkers.forEach(marker => marker.remove());
  chart.carryMarkers.clear();
  chart.empty.classList.remove("show");
}

function showChartEmpty(chart, message) {
  clearChart(chart);
  chart.empty.textContent = message;
  chart.empty.classList.add("show");
}

function findLatestDataPoint(data, time) {
  if (!data?.length || typeof time !== "number") return null;
  let low = 0;
  let high = data.length - 1;
  let latest = null;
  while (low <= high) {
    const middle = Math.floor((low + high) / 2);
    if (data[middle].time <= time) {
      latest = data[middle];
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return latest;
}

function renderCarryForwardMarkers(chart, seriesData, time) {
  chart.carryMarkers.forEach(marker => marker.style.display = "none");
  if (typeof time !== "number") return;
  chart.legendItems.filter(item => item.carryForward).forEach(item => {
    if (seriesData?.get(item.series)) return;
    const data = findLatestDataPoint(item.data, time);
    if (!data) return;
    const x = chart.api.timeScale().timeToCoordinate(data.time);
    const y = item.series.priceToCoordinate(data.value);
    if (x === null || y === null) return;
    let marker = chart.carryMarkers.get(item.series);
    if (!marker) {
      marker = document.createElement("i");
      marker.className = "chart-carry-marker";
      marker.style.borderColor = item.color;
      chart.host.append(marker);
      chart.carryMarkers.set(item.series, marker);
    }
    marker.style.left = `${x}px`;
    marker.style.top = `${y}px`;
    marker.style.display = "block";
  });
}

function renderChartLegend(chart, seriesData, time) {
  chart.legend.innerHTML = chart.legendItems.map(item => {
    const exactData = seriesData?.get(item.series);
    const data = exactData ||
      (item.carryForward ? findLatestDataPoint(item.data, time) : null);
    const value = data ? item.formatter(data) : "";
    const ageDays = data && !exactData && typeof time === "number"
      ? Math.max(0, Math.floor((time - data.time) / 86400))
      : null;
    const previous = ageDays === null
      ? ""
      : ` · 上次 ${formatDisplayDate(data.time)} (${ageDays}天前)`;
    return `
    <span><i class="legend-dot" style="background:${item.color}"></i>${escapeHtml(item.label)}${value ? ` · ${escapeHtml(value)}${escapeHtml(previous)}` : ""}</span>
  `;
  }).join("");
  renderCarryForwardMarkers(chart, seriesData, time);
}

function setChartLegend(chart, items) {
  chart.legendItems = items;
  renderChartLegend(chart);
}

function chartTime(timestamp) {
  return Math.floor(timestamp / 1000);
}

function priceFormat(key, suffix = "") {
  const asset = ASSETS[key];
  const digits = asset?.digits ?? 1;
  return {
    type: "custom",
    minMove: 10 ** -digits,
    formatter: value => suffix
      ? `${value.toFixed(digits)}${suffix}`
      : formatValue(key, value)
  };
}
