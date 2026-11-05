// 全球市场: correlation matrix.

function changesByPeriod(key, rows, monthly) {
  const grouped = new Map();
  rows.forEach(row => {
    const date = new Date(row.time).toISOString();
    grouped.set(monthly ? date.slice(0, 7) : date.slice(0, 10), row.close);
  });
  const entries = [...grouped.entries()].sort(([a], [b]) => a.localeCompare(b));
  const result = new Map();
  for (let i = 1; i < entries.length; i++) {
    const [period, current] = entries[i];
    const previous = entries[i - 1][1];
    if (!Number.isFinite(previous) || !Number.isFinite(current)) continue;
    const kind = ASSETS[key].kind;
    const change = kind === "macro" || kind === "rate" ? current - previous : previous ? current / previous - 1 : NaN;
    if (Number.isFinite(change)) result.set(period, change);
  }
  return result;
}

function correlation(a, b) {
  const dates = [...a.keys()].filter(key => b.has(key));
  const n = dates.length;
  if (n < 3) return { value: null, n };
  const x = dates.map(key => a.get(key));
  const y = dates.map(key => b.get(key));
  const mx = x.reduce((s, n) => s + n, 0) / x.length;
  const my = y.reduce((s, n) => s + n, 0) / y.length;
  let numerator = 0, dx = 0, dy = 0;
  x.forEach((value, i) => {
    const ax = value - mx;
    const ay = y[i] - my;
    numerator += ax * ay;
    dx += ax * ax;
    dy += ay * ay;
  });
  return { value: dx && dy ? numerator / Math.sqrt(dx * dy) : null, n };
}

function renderCorrelation() {
  const host = document.getElementById("correlationChart");
  const keys = [...correlationState.selected]
    .filter(key => (correlationState.series[key]?.length || 0) > 2);
  if (keys.length < 2) {
    host.innerHTML = '<div class="empty">请选择至少两个有数据的资产</div>';
    return;
  }
  const monthly = keys.some(key => ASSETS[key].kind === "macro");
  const maps = Object.fromEntries(keys.map(key => [
    key,
    changesByPeriod(key, correlationState.series[key], monthly)
  ]));
  const mix = (start, end, amount) => start.map((value, index) =>
    Math.round(value + (end[index] - value) * amount)
  );
  const cellColor = value => {
    if (value == null) return "#12212e";
    const rgb = value < 0
      ? mix([24, 43, 58], [181, 75, 97], Math.abs(value))
      : mix([24, 43, 58], [39, 187, 169], value);
    return `rgb(${rgb.join(",")})`;
  };
  const labels = ['<div class="correlation-label"></div>']
    .concat(keys.map(key => `<div class="correlation-label">${escapeHtml(ASSETS[key].short)}</div>`));
  const cells = keys.flatMap(y => {
    const row = [`<div class="correlation-label">${escapeHtml(ASSETS[y].short)}</div>`];
    keys.forEach(x => {
      if (x === y) {
        row.push(`<div class="correlation-cell" style="background:${cellColor(1)}" title="${escapeHtml(`${ASSETS[x].short}：1.00`)}">1.00</div>`);
        return;
      }
      const { value, n } = correlation(maps[x], maps[y]);
      const text = value == null ? "—" : value.toFixed(2);
      const pair = `${ASSETS[x].short} / ${ASSETS[y].short}`;
      const title = value == null
        ? `${pair}：同期数据不足（n=${n}）`
        : `${pair}：${text}（n=${n}${n < 12 ? "，样本偏少" : ""}）`;
      const className = n < 12 ? "correlation-cell low-sample" : "correlation-cell";
      row.push(`<div class="${className}" style="background:${cellColor(value)}" title="${escapeHtml(title)}"><span>${text}</span><small>n=${n}</small></div>`);
    });
    return row;
  });
  host.innerHTML = `
    <div class="correlation-grid" style="grid-template-columns:72px repeat(${keys.length}, minmax(52px, 1fr))">
      ${labels.join("")}${cells.join("")}
    </div>
    <div class="correlation-scale"></div>
    <div class="correlation-note">收益率/利差按变化量（bp）计算；A 股与美股按同一自然日对齐，A 股收盘早于美股，同日相关可能被低估；样本少于 12 期置灰。</div>
  `;
}
