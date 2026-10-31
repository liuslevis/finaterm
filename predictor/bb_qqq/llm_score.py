"""Stage 2 — turn a daily brief into QQQ probabilities for the next 1/3/7 days.

Two input modes, both tested in the report:

* ``--input brief`` (default): the LLM sees only the structured daily brief
  produced by ``make_brief.py`` — the "每日节目总结" channel.
* ``--input full``: the LLM sees the entire transcript.

Neither prompt contains any price, return or label.  The model is told to answer
as of 10:30 ET on the show date and is forbidden from using later knowledge.

``--blind`` replaces absolute dates (and the show date) with placeholders.  That
is the leakage control: a model that has memorised 2026 loses its edge when the
date is hidden.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

from common import DATA, FILES, resolve_llm

PROMPT_VERSION = "predict-v1"

SYSTEM = (
    "You are a macro strategist who has traded Nasdaq-100 futures for twenty years. "
    "You read one morning's market briefing and convert it into calibrated probabilities "
    "for the next 1, 3 and 7 trading days. You answer with strict JSON and nothing else."
)

RULES = """\
Below is {what} for the morning of {date_phrase}. You are reading it at 10:30 New York
time that same morning. Do not read anything that happened after that moment.

Your job: estimate the probability that QQQ (Invesco Nasdaq-100 ETF) is HIGHER at the
16:00 New York close exactly 1, 3 and 7 trading days later, measured from the 16:00
close of {date_phrase}.

Hard rules:
1. Use ONLY information contained in the material below. Do not use your own knowledge of
   what markets did afterwards, and do not use news you may recall from around this date.
2. Probabilities are between 0.05 and 0.95. An uninformative morning is 0.50-0.55.
   QQQ drifts up, so neutral-but-normal is a shade above 0.50, not 0.50 exactly.
3. Weight what the guests and the data actually said, not what the anchors repeated.
4. Do not list every theme; give the drivers you actually used.

Return strict JSON with exactly these keys:
{{
  "p_up_1d": <float 0..1>,
  "p_up_3d": <float 0..1>,
  "p_up_7d": <float 0..1>,
  "sentiment": <int -2..2, -2 = strongly risk-off, +2 = strongly risk-on>,
  "confidence": <int 0..100, how much genuine signal this material carried>,
  "preopen_move": "<one of: sharply_up, up, flat, down, sharply_down>  -- the overnight /
                    pre-open tape the material describes>",
  "drivers": [{{"theme": "<short label>", "direction": "<bullish|bearish|neutral>",
               "weight": <int 0..100>}}],
  "rationale": "<one or two sentences, max 60 words, in English>"
}}

{body_header}
==========
{body}
"""

MASK_PATTERNS = [
    (re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|"
                r"November|December)\s+\d{1,2}(?:st|nd|rd|th)?\b"), "[DATE]"),
    (re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+of\s+(January|February|March|April|May|June|July|"
                r"August|September|October|November|December)\b"), "[DATE]"),
    (re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|"
                r"November|December)\b"), "[MONTH]"),
    (re.compile(r"\b(19|20)\d{2}\b"), "[YEAR]"),
    (re.compile(r"^\*\*BVID\*\*:.*$", re.MULTILINE), ""),
]

TIME_HEADER = re.compile(r"^\[\d{2}:\d{2}:\d{2}\s*-\s*\d{2}:\d{2}:\d{2}\]\s*$")


def mask_dates(text: str) -> str:
    for pattern, repl in MASK_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def clean_transcript(raw: str) -> str:
    lines = [ln for ln in raw.splitlines() if not TIME_HEADER.match(ln.strip())]
    return re.sub(r"[ \t]+", " ", "\n".join(lines)).strip()


def build_prompt(show_date: str, body: str, *, mode: str, blind: bool) -> tuple[str, str]:
    if mode == "brief":
        what = "the structured morning brief distilled from Bloomberg Surveillance"
        body_header = "BRIEF"
        body = re.sub(r"^#.*\n", "", body, count=1)  # drop the dated title line
    else:
        what = "the complete transcript of Bloomberg Surveillance, broadcast 06:00-10:00 New York time"
        body_header = "TRANSCRIPT"
        body = clean_transcript(body)

    if blind:
        body = mask_dates(body)
        date_phrase = "an unspecified trading day"
    else:
        date_phrase = show_date

    user = RULES.format(what=what, date_phrase=date_phrase, body_header=body_header, body=body)
    return SYSTEM, user


def cache_path(model: str, mode: str, blinded: bool, bvid: str, repeats: int = 1) -> Path:
    tag = "blind" if blinded else "dated"
    d = DATA / "llm_cache" / tag / mode / model.replace("/", "_")
    d.mkdir(parents=True, exist_ok=True)
    suffix = "" if repeats <= 1 else f"_r{repeats}"
    return d / f"{bvid}{suffix}.json"


def call_llm(llm, system: str, user: str, *, use_json_mode: bool, max_tokens: int = 8000) -> dict:
    payload = {
        "model": llm.model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    if use_json_mode:
        payload["response_format"] = {"type": "json_object"}
    response = requests.post(
        llm.endpoint,
        headers={"Authorization": f"Bearer {llm.api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=900,
    )
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
    data = response.json()
    choice = data["choices"][0]
    content = choice["message"].get("content") or ""
    if not content.strip():
        raise RuntimeError(f"empty content (finish_reason={choice.get('finish_reason')})")
    return {"raw": content, "usage": data.get("usage", {})}


def parse_json(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def validate(obj: dict) -> dict:
    def prob(key: str) -> float:
        return min(0.95, max(0.05, float(obj.get(key, 0.5))))

    return {
        "p_up_1d": prob("p_up_1d"),
        "p_up_3d": prob("p_up_3d"),
        "p_up_7d": prob("p_up_7d"),
        "sentiment": max(-2, min(2, int(round(float(obj.get("sentiment", 0)))))),
        "confidence": max(0, min(100, int(round(float(obj.get("confidence", 50)))))),
        "preopen_move": str(obj.get("preopen_move", "flat")).strip().lower(),
        "drivers": obj.get("drivers", []),
        "rationale": str(obj.get("rationale", ""))[:400],
    }


def average_parsed(items: list[dict]) -> dict:
    """Average independent calls; the factor is the noise-reduced consensus."""
    if len(items) == 1:
        return items[0]
    out = dict(items[0])
    for key in ("p_up_1d", "p_up_3d", "p_up_7d", "confidence"):
        out[key] = round(float(sum(x[key] for x in items) / len(items)), 4)
    out["sentiment"] = int(round(sum(x["sentiment"] for x in items) / len(items)))
    moves = [x.get("preopen_move", "flat") for x in items]
    out["preopen_move"] = max(set(moves), key=moves.count)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="deepseek")
    ap.add_argument("--input", dest="mode", choices=["brief", "full"], default="brief")
    ap.add_argument("--blind", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--repeats", type=int, default=1,
                    help="independent calls per episode, averaged to cut sampling noise")
    args = ap.parse_args()

    llm = resolve_llm(args.model)
    use_json_mode = llm.provider in {"deepseek", "glm", "qwen"}
    episodes = pd.read_csv(FILES["episodes"])
    if args.limit:
        episodes = episodes.head(args.limit)

    rows = []
    for i, row in enumerate(episodes.itertuples(index=False), 1):
        bvid = row.bvid
        if args.mode == "brief":
            brief_json = DATA / "briefs" / f"{bvid}.json"
            if not brief_json.is_file():
                print(f"[{i}/{len(episodes)}] {bvid} no brief yet, skipped")
                continue
            body = (DATA / "briefs" / f"{bvid}.md").read_text(encoding="utf-8", errors="replace")
        else:
            body = Path(row.transcript).read_text(encoding="utf-8", errors="replace")

        path = cache_path(llm.model, args.mode, args.blind, bvid, args.repeats)
        if path.is_file() and not args.force:
            payload = json.loads(path.read_text(encoding="utf-8"))
            cached = True
        else:
            system, user = build_prompt(row.show_date, body, mode=args.mode, blind=args.blind)
            last_error = None
            repeats = []
            for attempt in range(1, 7):
                try:
                    repeats = []
                    for rep in range(max(1, args.repeats)):
                        response = call_llm(llm, system, user, use_json_mode=use_json_mode,
                                            max_tokens=8000 if attempt == 1 else 12000)
                        repeats.append({
                            "parsed": validate(parse_json(response["raw"])),
                            "usage": response["usage"],
                        })
                        if args.repeats > 1 and rep + 1 < args.repeats:
                            time.sleep(1)
                    payload = {
                        "model": llm.model,
                        "prompt_version": PROMPT_VERSION,
                        "mode": args.mode,
                        "blind": args.blind,
                        "bvid": bvid,
                        "show_date": row.show_date,
                        "repeats": len(repeats),
                        "parsed": average_parsed([r["parsed"] for r in repeats]),
                        "per_repeat": [r["parsed"] for r in repeats],
                        "usage": repeats[-1]["usage"],
                        "prompt_sha": hashlib.sha256(user.encode()).hexdigest()[:16],
                    }
                    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                    cached = False
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    time.sleep(min(90, 5 * 2 ** (attempt - 1)))
            else:
                print(f"[{i}/{len(episodes)}] {bvid} FAILED: {last_error}")
                continue

        parsed = payload["parsed"]
        rows.append({
            "bvid": bvid, "show_date": row.show_date, "model": payload["model"],
            "mode": args.mode, "blind": args.blind,
            "p_up_1d": parsed["p_up_1d"], "p_up_3d": parsed["p_up_3d"], "p_up_7d": parsed["p_up_7d"],
            "sentiment": parsed["sentiment"], "confidence": parsed["confidence"],
            "preopen_move": parsed["preopen_move"], "rationale": parsed["rationale"],
            "cached": cached,
        })
        print(f"[{i}/{len(episodes)}] {bvid} {row.show_date} p1={parsed['p_up_1d']:.2f} "
              f"p3={parsed['p_up_3d']:.2f} p7={parsed['p_up_7d']:.2f} s={parsed['sentiment']:+d}"
              f"{'  (cache)' if cached else ''}")

    out = pd.DataFrame(rows)
    suffix = "_blind" if args.blind else ""
    rep_suffix = "" if args.repeats <= 1 else f"_r{args.repeats}"
    out_path = DATA / f"llm_scores_{args.model}_{args.mode}{suffix}{rep_suffix}.csv"
    out.to_csv(out_path, index=False)
    print(f"wrote {out_path} rows={len(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())




