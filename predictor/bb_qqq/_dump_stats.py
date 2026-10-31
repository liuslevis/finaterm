import json
from pathlib import Path

import pandas as pd

m = json.loads(Path('reports/metrics_brief.json').read_text(encoding='utf-8'))
p = pd.read_csv('data/panel_brief.csv')
q = pd.read_csv('data/qqq_daily.csv')

print('=== sample ===')
print('dates', m['n_dates'], 'episodes', m['n_episodes'], m['date_range'])
sub = q[(q.date >= '2026-09-01') & (q.date <= '2026-10-29')]
print('QQQ close first/last:', sub.close.iloc[0], sub.close.iloc[-1],
      'window return %', round((sub.close.iloc[-1] / sub.close.iloc[0] - 1) * 100, 2))

print('\n=== label availability ===')
for h in (1, 3, 7):
    s = p.dropna(subset=[f'r{h}'])
    print(f'r{h}: n={len(s)}  mean={s[f"r{h}"].mean()*100:+.2f}%  up-rate={(s[f"r{h}"]>0).mean():.2f}')

print('\n=== score distribution (brief) ===')
for col in ['p_up_1d', 'p_up_3d', 'p_up_7d', 'sentiment', 'confidence']:
    print(f'{col:11s} mean={p[col].mean():.3f} sd={p[col].std():.3f} min={p[col].min():.3f} max={p[col].max():.3f}')

print('\n=== power ===', m['power'])
print('\n=== decay (brief, score_1d) ===')
print([(d['lag'], d['ic']) for d in m['decay']['llm_p(2p-1)']])
print('\n=== trading ===', m['trading'])
print('\n=== per-horizon detail (brief) ===')
for h in ['1d', '3d', '7d']:
    b = m['table']['llm_p(2p-1)'][h]
    print(h, {k: b.get(k) for k in ('n', 'pearson', 'p_pearson', 'p_perm_block', 't_nw', 'hit_rate',
                                     'base_up_rate', 'partial_pearson', 'ls_spread_pct')})
