import json
from pathlib import Path

runs = {n: json.loads(Path(f'reports/metrics_{n}.json').read_text(encoding='utf-8'))
        for n in ['brief', 'brief_blind', 'full', 'full_blind']}

print('variant         h    n    IC      p     rho    NWt    CI95')
for name, m in runs.items():
    for h in ['1d', '3d', '7d']:
        b = m['table']['llm_p(2p-1)'][h]
        if 'pearson' not in b:
            print(f'{name:15s} {h:3s} n={b["n"]:3d}  too few')
            continue
        print(f'{name:15s} {h:3s} {b["n"]:3d}  {b["pearson"]:+.3f} {b["p_pearson"]:.3f} '
              f'{b["spearman"]:+.3f} {b["t_nw"]:+.2f}  [{b["ci95"][0]:+.2f},{b["ci95"][1]:+.2f}]')
    plc = m.get('placebo', {}).get('next_score_vs_today_r1', {})
    print('   placebo r =', plc.get('pearson'), ' p =', plc.get('p_pearson'))
    print('   diag     =', m.get('diagnostics'))
    print('   persistence =', m.get('persistence'))
    print('   split    =', {k: v['n_dates'] for k, v in m.get('split', {}).items()})
    for k, v in m.get('split', {}).items():
        ic = {h: (round(b['pearson'], 3) if 'pearson' in b else None) for h, b in v['ic'].items()}
        print('      ', k, ic)
    print()
