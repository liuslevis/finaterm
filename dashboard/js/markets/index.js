// 全球市场: renderAll and event bindings.

function renderAll() {
  renderTickers();
  renderCompareSelectors();
  renderMarketCharts();
  renderCorrelation();
  updateRatesTerm();
}

document.querySelectorAll("[data-range]").forEach(button => {
  button.addEventListener("click", () => {
    const moduleId = button.closest("[data-module-id]")?.dataset.moduleId;
    setActiveRangeButton(moduleId, button.dataset.range);
    if (moduleId === "correlation") {
      correlationState.range = button.dataset.range;
      loadCorrelationData();
    } else {
      state.range = button.dataset.range;
      state.resetMarketRange = true;
      loadMarkets();
    }
  });
});

document.querySelectorAll("[data-kline-period]").forEach(button => {
  button.addEventListener("click", () => {
    const period = button.dataset.klinePeriod;
    if (!KLINE_PERIODS[period] || period === state.klinePeriod) return;
    document.querySelectorAll('[data-module-id="market"] [data-kline-period]').forEach(item => {
      item.classList.toggle("active", item === button);
    });
    state.klinePeriod = period;
    renderMarketCandleChart();
  });
});

document.getElementById("refreshBtn").addEventListener("click", loadCorrelationData);

document.getElementById("closeMacroDialog").addEventListener("click", () => {
  document.getElementById("macroIndicatorDialog").close();
});
document.getElementById("macroIndicatorSearch").addEventListener("input", renderMacroIndicatorOptions);
document.getElementById("macroIndicatorDialog").addEventListener("click", event => {
  if (event.target === event.currentTarget) event.currentTarget.close();
});
document.getElementById("closeTickerDialog").addEventListener("click", () => {
  document.getElementById("tickerDialog").close();
});
document.getElementById("tickerSearch").addEventListener("input", renderTickerOptions);
document.getElementById("tickerDialog").addEventListener("click", event => {
  if (event.target === event.currentTarget) event.currentTarget.close();
});
