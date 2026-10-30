// 全球市场: asset selectors, ticker cards and the add-ticker dialog.

function renderSelectors() {
  const host = document.getElementById("assetSelector");
  host.innerHTML = Object.entries(ASSETS).map(([key, item]) => `
    <label class="asset-chip">
      <input type="checkbox" value="${key}" ${correlationState.selected.has(key) ? "checked" : ""}>
      <span>${item.short}</span>
    </label>
  `).join("");
  host.querySelectorAll("input").forEach(input => {
    input.addEventListener("change", () => {
      if (input.checked) correlationState.selected.add(input.value);
      else correlationState.selected.delete(input.value);
      if (!correlationState.selected.size) {
        input.checked = true;
        correlationState.selected.add(input.value);
      }
      loadCorrelationData();
    });
  });
}

function renderCompareSelectors() {
  const host = document.getElementById("compareAssetSelector");
  host.innerHTML = Object.entries(ASSETS).map(([key, item]) => `
    <label class="asset-chip">
      <input type="checkbox" value="${key}" ${state.selected.has(key) ? "checked" : ""}>
      <span>${item.short}</span>
    </label>
  `).join("");
  host.querySelectorAll("input").forEach(input => {
    input.addEventListener("change", async () => {
      if (input.checked) {
        state.selected.add(input.value);
      } else if (state.selected.size > 1) {
        state.selected.delete(input.value);
      } else {
        input.checked = true;
        return;
      }
      if (input.checked && !state.series[input.value]?.length) {
        try {
          await loadAssetSeries(input.value);
          void preloadMarketHistory(input.value);
          showError("");
        } catch (error) {
          console.error(input.value, error);
          state.series[input.value] = [];
          showError(`${ASSETS[input.value].name}：${error.message}`);
        }
      }
      renderAll();
    });
  });
}

function formatValue(key, value) {
  if (!Number.isFinite(value)) return "—";
  const asset = ASSETS[key];
  const number = value.toLocaleString("en-US", {
    minimumFractionDigits: asset.digits ?? 1,
    maximumFractionDigits: asset.digits ?? 1
  });
  return `${asset.prefix || ""}${number}${asset.unit || ""}`;
}

function formatTickerValue(key, value) {
  if (!Number.isFinite(value)) return "—";
  const asset = ASSETS[key];
  const number = value.toLocaleString("en-US", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1
  });
  return `${asset.prefix || ""}${number}${asset.unit || ""}`;
}

function latestStats(key, rows) {
  const valid = rows.filter(x => Number.isFinite(x.close));
  if (!valid.length) return {};
  const last = valid.at(-1);
  const prev = valid.at(-2) || last;
  const change = last.close - prev.close;
  const pct = prev.close ? change / prev.close * 100 : 0;
  return { value: last.close, change, pct, directionValue: ASSETS[key].kind === "macro" ? change : pct, time: last.time };
}

function renderTickers() {
  const host = document.getElementById("tickerGrid");
  const cards = state.tickers.map(key => {
    const asset = ASSETS[key];
    const stats = latestStats(key, state.series[key] || []);
    const direction = !Number.isFinite(stats.directionValue) || stats.directionValue === 0 ? "flat" : stats.directionValue > 0 ? "up" : "down";
    const sign = stats.directionValue > 0 ? "+" : "";
    const changeText = asset.kind === "macro"
      ? `${sign}${Number.isFinite(stats.change) ? stats.change.toFixed(1) : "—"}${asset.unit || ""}`
      : `${sign}${Number.isFinite(stats.pct) ? stats.pct.toFixed(1) : "—"}%`;
    return `
      <article class="ticker ${state.active === key ? "active" : ""}" data-key="${key}" aria-label="${escapeHtml(asset.name)}" draggable="true">
        <div class="ticker-head">
          <span>${escapeHtml(asset.short)}</span>
          <span class="ticker-name" role="tooltip">${escapeHtml(asset.name)}</span>
        </div>
        <div class="ticker-metrics">
          <div class="ticker-value">${formatTickerValue(key, stats.value)}</div>
          <div class="change ${direction}">${Number.isFinite(stats.directionValue) ? changeText : "等待数据"}</div>
        </div>
      </article>
    `;
  }).join("");
  host.innerHTML = `${cards}<button type="button" class="ticker-add" id="addTicker">＋ 添加</button>`;
  let draggedCard = null;
  let droppedInTrash = false;
  host.querySelectorAll(".ticker").forEach(card => {
    card.addEventListener("dragstart", event => {
      draggedCard = card;
      droppedInTrash = false;
      card.dataset.dragged = "true";
      card.classList.add("ticker-dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", card.dataset.key);
      if (state.tickers.length > 1) {
        showDragTrash(() => {
          if (!draggedCard || state.tickers.length <= 1) return;
          droppedInTrash = true;
          const key = draggedCard.dataset.key;
          state.tickers = state.tickers.filter(item => item !== key);
          state.selected.delete(key);
          if (state.active === key) state.active = state.tickers[0];
          state.selected.add(state.active);
          saveTickerSelection();
          draggedCard.remove();
        });
      }
    });
    card.addEventListener("dragend", () => {
      card.classList.remove("ticker-dragging");
      hideDragTrash();
      draggedCard = null;
      if (droppedInTrash) {
        renderSelectors();
        renderAll();
      } else {
        state.tickers = [...host.querySelectorAll(".ticker[data-key]")]
          .map(item => item.dataset.key);
        saveTickerSelection();
      }
      setTimeout(() => delete card.dataset.dragged, 0);
    });
    card.addEventListener("click", () => {
      if (card.dataset.dragged === "true") return;
      const key = card.dataset.key;
      state.active = key;
      void preloadMarketHistory(key);
      renderAll();
    });
  });
  host.addEventListener("dragover", event => {
    if (!draggedCard) return;
    const target = event.target.closest(".ticker");
    if (!target || target === draggedCard) return;
    event.preventDefault();
    const rect = target.getBoundingClientRect();
    const insertAfter = event.clientX > rect.left + rect.width / 2;
    host.insertBefore(draggedCard, insertAfter ? target.nextSibling : target);
  });
  document.getElementById("addTicker").addEventListener("click", openTickerDialog);
}

function renderTickerOptions() {
  const query = document.getElementById("tickerSearch").value.trim().toLowerCase();
  const selected = new Set(state.tickers);
  const categoryHost = document.getElementById("tickerCategoryFilters");
  categoryHost.innerHTML = TICKER_CATEGORIES.map(([key, label]) => {
    const count = key === "all"
      ? Object.keys(ASSETS).length
      : Object.values(ASSETS).filter(asset => asset.category === key).length;
    return `<button type="button" class="ticker-filter ${tickerCategory === key ? "active" : ""}" data-ticker-category="${key}">${label} · ${count}</button>`;
  }).join("");
  categoryHost.querySelectorAll("[data-ticker-category]").forEach(button => {
    button.addEventListener("click", () => {
      tickerCategory = button.dataset.tickerCategory;
      renderTickerOptions();
    });
  });

  const categories = tickerCategory === "all"
    ? TICKER_CATEGORIES.slice(1)
    : TICKER_CATEGORIES.filter(([key]) => key === tickerCategory);
  const groups = categories.map(([category, label]) => {
    const options = Object.entries(ASSETS)
      .filter(([, asset]) => asset.category === category)
      .filter(([, asset]) => !query || `${asset.name} ${asset.short} ${asset.symbol || ""}`.toLowerCase().includes(query));
    if (!options.length) return "";
    return `
      <div class="macro-country">${label}</div>
      ${options.map(([key, asset]) => `
        <label class="macro-option ticker-option">
          <input type="checkbox" data-ticker-key="${key}" ${selected.has(key) ? "checked" : ""}>
          <span class="ticker-option-name">${asset.name}</span>
          <span class="ticker-option-code">${asset.short}</span>
          <span class="ticker-option-source">${tickerDataSource(asset)}</span>
        </label>
      `).join("")}
    `;
  }).join("");
  const host = document.getElementById("tickerOptions");
  host.innerHTML = groups || '<div class="macro-options-empty">没有匹配的资产</div>';
  host.querySelectorAll("input[data-ticker-key]").forEach(input => {
    input.addEventListener("change", async () => {
      const key = input.dataset.tickerKey;
      if (input.checked) {
        if (!state.tickers.includes(key)) state.tickers.push(key);
      } else if (state.tickers.length > 1) {
        state.tickers = state.tickers.filter(item => item !== key);
        if (state.active === key) {
          state.active = state.tickers[0];
          state.selected.add(state.active);
        }
      } else {
        input.checked = true;
        return;
      }
      saveTickerSelection();
      if (input.checked && !state.series[key]?.length) {
        try {
          await loadAssetSeries(key);
          void preloadMarketHistory(key);
          showError("");
        } catch (error) {
          console.error(key, error);
          state.series[key] = [];
          showError(`${ASSETS[key].name}：${error.message}`);
        }
      }
      renderAll();
    });
  });
}

function tickerDataSource(asset) {
  if (asset.source === "usdata" || asset.usdataId) return "USData";
  if (asset.source === "calendar-history") return "TradingView";
  if (asset.akshareSymbol) return "AKShare";
  if (asset.futu) return "Futu / Yahoo";
  return "Yahoo Finance";
}

function connectedDataSources(results) {
  const servedLocally = ["localhost", "127.0.0.1"].includes(location.hostname);
  const sources = new Set();
  results.filter(result => result.ok).forEach(result => {
    if (result.key === "macro") {
      sources.add("USData");
      sources.add("TradingView");
      return;
    }
    const asset = ASSETS[result.key];
    if (asset?.source === "usdata" || asset?.usdataId) {
      sources.add("USData");
    } else if (asset?.source === "calendar-history") {
      sources.add("TradingView");
    } else if (asset?.akshareSymbol) {
      sources.add("AKShare");
    } else if (servedLocally && asset?.futu && !state.futuErrors.has(result.key)) {
      sources.add("Futu OpenD");
    } else if (asset) {
      sources.add("Yahoo Finance");
    }
  });
  return [...sources].join(" | ");
}

function openTickerDialog() {
  const dialog = document.getElementById("tickerDialog");
  document.getElementById("tickerSearch").value = "";
  tickerCategory = "all";
  renderTickerOptions();
  dialog.showModal();
  requestAnimationFrame(() => document.getElementById("tickerSearch").focus());
}
