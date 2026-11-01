"""Explanation study, stage 1 — extract what the show *says happened*.

The factor study asked "does the show predict QQQ?".  This asks the opposite,
contemporaneous question: "does the show correctly describe and explain the
market moves around it?"  Three windows, all New York time, relative to the
**air date** A (= title date − 1 calendar day, see EXPLANATION.md §1):

    prev session   close(P-1) -> close(P)    P = last trading session before A
    overnight      close(P)   -> open(A)     futures during the show ≈ this gap
    after the show open(A)    -> close(A)    mostly after 10:00, so the show cannot know it

The model sees only the transcript (with its [HH:MM:SS] offsets kept so it can
say *when* in the show something was said).  No prices are passed in.  Cached
under data/explain/<BVID>.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from common import DATA, FILES, resolve_llm
from make_brief import call_llm, parse_json

PROMPT_VERSION = "explain-v1"
OUT = DATA / "explain"

SYSTEM = (
    "You are a meticulous market-desk analyst. You read a raw ASR transcript of one "
    "morning's Bloomberg Surveillance and record ONLY what the hosts and guests "
    "explicitly say about market moves and their causes. Answer with strict JSON. "
    "Never infer numbers that are not spoken; use null / 'not_stated' instead. "
    "ASR errors are common (e.g. 'double tier' = WTI, 'forty seventy' = 4.70%)."
)

USER_TEMPLATE = """\
Transcript of one Bloomberg Surveillance episode (US morning show, live 06:00-10:00 New York).
Offsets like [01:05:00 - 01:10:00] are elapsed time since the recording started.

Record what the show SAYS about three windows:
 (1) PREVIOUS SESSION = the last completed US cash session before this broadcast
     ("yesterday", "on Friday", "the close", "stocks finished ...").
 (2) THIS MORNING = futures / overnight moves while the show is live, before the cash open.
 (3) CASH OPEN = 09:30 New York, only if the recording is still running then
     ("stocks opening", "first few minutes of trading").

Return strict JSON with exactly this schema:
{{
  "air_weekday": "monday|tuesday|wednesday|thursday|friday|unclear",
  "prev_session": {{
    "described": true|false,
    "spx":    {{"direction": "up|down|flat|not_stated", "pct": <number or null, e.g. -1.2>}},
    "nasdaq": {{"direction": "up|down|flat|not_stated", "pct": <number or null>}},
    "ust10y": {{"direction": "up|down|flat|not_stated", "bp": <number or null>}},
    "oil":    {{"direction": "up|down|flat|not_stated", "pct": <number or null>}},
    "reasons": [{{"driver": "<=8 words", "category": "rates|oil_energy|fed|earnings_ai|geopolitics|macro_data|trade_policy|fiscal_politics|positioning_flows|other", "effect": "lifted|weighed"}}],
    "quote": "<=30 words, verbatim-ish, the clearest sentence about the previous session or ''"
  }},
  "this_morning": {{
    "spx_fut":    {{"direction": "up|down|flat|not_stated", "pct": <number or null>, "offset": "<HH:MM:SS of the LAST explicit mention or ''>"}},
    "nasdaq_fut": {{"direction": "up|down|flat|not_stated", "pct": <number or null>}},
    "ust10y":     {{"direction": "up|down|flat|not_stated", "bp": <number or null>}},
    "oil":        {{"direction": "up|down|flat|not_stated", "pct": <number or null>}},
    "trajectory": "improving|deteriorating|stable|unclear",
    "reasons": [{{"driver": "<=8 words", "category": "<same list>", "effect": "lifted|weighed"}}],
    "quote": "<=30 words or ''"
  }},
  "cash_open": {{"observed": true|false, "direction": "up|down|flat|not_stated", "pct": <number or null>}},
  "scheduled_today": ["<=4 items, each <=8 words: data releases / Fed speakers / earnings due later TODAY"],
  "self_check": "<=25 words: anything ambiguous about which day a move refers to"
}}

Rules: 'pct' is the percent the show states for that window (sign = direction).
If the show gives a number for the S&P but not the Nasdaq, leave the Nasdaq pct null.
Only fill prev_session from statements clearly about the completed session, not about futures.

TRANSCRIPT
==========
{transcript}
"""


def out_path(bvid: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT / f"{bvid}.json"


def extract_one(llm, row) -> str:
    path = out_path(row.bvid)
    transcript = Path(row.transcript).read_text(encoding="utf-8", errors="replace")
    user = USER_TEMPLATE.format(transcript=transcript)
    last = None
    for attempt in range(1, 4):
        try:
            response = call_llm(llm, SYSTEM, user, use_json_mode=True, max_tokens=16000)
            payload = {
                "bvid": row.bvid,
                "title_date": row.show_date,
                "model": llm.model,
                "prompt_version": PROMPT_VERSION,
                "extract": parse_json(response["raw"]),
                "usage": response["usage"],
            }
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            ex = payload["extract"]
            return (f"{row.bvid} {row.show_date} wd={ex.get('air_weekday')} "
                    f"prev={ex.get('prev_session', {}).get('nasdaq', {})} "
                    f"fut={ex.get('this_morning', {}).get('nasdaq_fut', {})}")
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(3 * attempt)
    return f"{row.bvid} FAILED: {last}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="deepseek")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    llm = resolve_llm(args.model)
    episodes = pd.read_csv(FILES["episodes"])
    todo = [r for r in episodes.itertuples(index=False)
            if args.force or not out_path(r.bvid).is_file()]
    print(f"episodes={len(episodes)} todo={len(todo)}")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(extract_one, llm, r) for r in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            print(f"[{i}/{len(todo)}] {fut.result()}", flush=True)
    print(f"cached: {len(list(OUT.glob('*.json')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
