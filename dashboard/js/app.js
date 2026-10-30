// App shell: zoom, workspace switching, cache clearing, global bindings, movable panels, clock.

const DASHBOARD_ZOOM_MIN = 0.8;
const DASHBOARD_ZOOM_MAX = 1.4;
let dashboardZoom = 1;

function updateDashboardZoom() {
  document.documentElement.style.zoom = String(dashboardZoom);
}

function adjustDashboardZoom(amount) {
  dashboardZoom = Math.max(DASHBOARD_ZOOM_MIN, Math.min(
    DASHBOARD_ZOOM_MAX,
    Math.round((dashboardZoom + amount) * 10) / 10
  ));
  updateDashboardZoom();
}

function activateWorkspace(name) {
  document.querySelectorAll("[data-workspace]").forEach(workspace => {
    workspace.classList.toggle("active", workspace.dataset.workspace === name);
  });
  document.querySelectorAll("[data-workspace-tab]").forEach(button => {
    button.classList.toggle("active", button.dataset.workspaceTab === name);
  });
  if (name === "semiconductor") {
    requestAnimationFrame(() => {
      if (semiChart) semiChart.api.resize(
        document.getElementById("semiMarketChart").clientWidth,
        document.getElementById("semiMarketChart").clientHeight
      );
      if (!semiState.loaded) loadSemiDashboard();
    });
  }
  if (name === "ipo") requestAnimationFrame(loadIpoCalendar);
  if (name === "a-supply-demand") requestAnimationFrame(loadAsd);
  if (name === "us-supply-demand") requestAnimationFrame(loadUssd);
  if (name === "a-etf-share") requestAnimationFrame(loadAes);
}

async function clearDataCache() {
  const button = document.getElementById("clearCacheBtn");
  button.disabled = true;
  button.textContent = "清理中";
  setStatus("loading", "正在清除数据缓存...");
  try {
    const response = await fetch("/api/cache", { method: "DELETE", cache: "no-store" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);

    state.usdataPromise = null;
    state.series = {};
    state.macroAll = {};
    state.marketAll = {};
    state.futuErrors.clear();
    correlationState.series = {};
    semiState.series = {};
    Object.values(marketRenderCache).forEach(cache => {
      cache.key = "";
      cache.series.clear();
    });
    dataPointCache.clear();
    marketHistoryPromises.clear();

    await loadMarkets();
    void preloadAllMarketDataPoints([...state.tickers, ...state.selected]);
    const reloads = [loadCorrelationData(), loadMacroCalendar(), loadMacroHistory()];
    if (semiState.loaded) reloads.push(loadSemiDashboard());
    const ipoLoaded = Object.keys(ipoState.data).length > 0;
    ipoState.data = {};
    if (ipoLoaded) reloads.push(loadIpoCalendar());
    const asdLoaded = Boolean(asdState.data);
    asdState.data = null;
    if (asdLoaded) reloads.push(loadAsd());
    const ussdLoaded = Boolean(ussdState.data);
    ussdState.data = null;
    if (ussdLoaded) reloads.push(loadUssd());
    const aesLoaded = Boolean(aesState.data);
    aesState.data = null;
    if (aesLoaded) reloads.push(loadAes());
    await Promise.all(reloads);
  } catch (error) {
    console.error("clear cache", error);
    setStatus("error", "清除缓存失败");
    showError(`无法清除数据缓存：${error.message}`);
  } finally {
    button.disabled = false;
    button.textContent = "清除缓存";
  }
}

document.getElementById("clearCacheBtn").addEventListener("click", clearDataCache);
document.getElementById("refreshPageBtn").addEventListener("click", () => window.location.reload());
document.addEventListener("keydown", event => {
  if (!event.ctrlKey || event.altKey || event.metaKey) return;
  const zoomIn = event.code === "NumpadAdd" || event.code === "Equal" || event.key === "=";
  const zoomOut = event.code === "NumpadSubtract" || (event.key === "-" && !event.shiftKey);
  if (zoomIn) {
    event.preventDefault();
    adjustDashboardZoom(0.1);
  } else if (zoomOut) {
    event.preventDefault();
    adjustDashboardZoom(-0.1);
  }
});
updateDashboardZoom();

document.querySelectorAll("[data-workspace-tab]").forEach(button => {
  button.addEventListener("click", () => activateWorkspace(button.dataset.workspaceTab));
});

function setupMovablePanels() {
  const columns = [...document.querySelectorAll(".main-column, .side-column")];
  let draggedPanel = null;

  document.querySelectorAll(".movable-panel").forEach(panel => {
    const handle = panel.querySelector(".panel-title");
    handle.draggable = true;
    handle.title = "拖动模块";
    handle.addEventListener("dragstart", event => {
      draggedPanel = panel;
      panel.classList.add("dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", panel.dataset.moduleId);
    });
    handle.addEventListener("dragend", () => {
      panel.classList.remove("dragging");
      draggedPanel = null;
    });
  });

  columns.forEach(column => {
    column.addEventListener("dragover", event => {
      if (!draggedPanel) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      const nextPanel = [...column.querySelectorAll(".movable-panel:not(.dragging)")]
        .find(panel => event.clientY < panel.getBoundingClientRect().top + panel.offsetHeight / 2);
      column.insertBefore(draggedPanel, nextPanel || null);
    });
  });
}

function updateClock() {
  const now = new Date();
  const time = now.toLocaleTimeString("zh-CN", {
    hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit"
  });
  document.getElementById("clock").textContent = `${formatDisplayDate(now)} ${time}`;
}
