// Startup. Loaded last; tests load every other script and skip this one.

updateClock();
setInterval(updateClock, 1000);
setupMovablePanels();
renderSemiAssetChips();
renderSemiSignals();
renderCloudCapex();
renderQqqDecisions();
renderQqqRiskDashboard();
document.getElementById("opinionDate").value = new Date().toISOString().slice(0, 10);
renderSemiOpinions();
renderSelectors();
renderCompareSelectors();
renderTickers();
(async function initialize() {
  await applySharedMarketsSelection();
  await loadMarkets();
  void preloadAllMarketDataPoints([...state.tickers, ...state.selected]);
  correlationState.series = Object.fromEntries(
    Object.entries(state.series).map(([key, rows]) => [key, [...rows]])
  );
  renderCorrelation();
  await Promise.all([loadMacroCalendar(), loadMacroHistory()]);
})();
setInterval(loadMarkets, 60_000);
