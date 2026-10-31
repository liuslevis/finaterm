"""Stage 1 — compress one show transcript into a structured daily brief.

This is the "每日节目总结" the factor is actually built on: a fixed-schema
reading of what the show said about (a) market indicators and their trend,
(b) expectations/pricing, (c) sentiment and narrative, (d) catalysts.

Doing this in a fixed schema instead of free prose matters for a factor: every
day gets the same fields, so the extraction is comparable across episodes and a
second, much smaller LLM call can turn the brief into probabilities without ever
seeing the raw transcript.

The brief is cached under ``data/briefs/<BVID>.json`` (+ a markdown rendering)
so the expensive call happens exactly once per episode.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

from common import DATA, FILES, resolve_llm

PROMPT_VERSION = "brief-v1"
BRIEFS = DATA / "briefs"

SYSTEM = (
    "You are a buy-side macro analyst. You read a full transcript of one morning's "
    "Bloomberg Surveillance and turn it into a fixed-schema structured brief. "
    "You answer with strict JSON and nothing else. Never invent numbers that are "
    "not in the transcript; if the show did not discuss a field, say 'not_discussed'."
)

USER_TEMPLATE = """\
Below is the complete transcript of Bloomberg Surveillance broadcast on {date_phrase}.
Extract a structured brief of what the show said. Use ONLY the transcript.

For every indicator, report the DIRECTION the show describes, not your own view of
where it should go.

Return strict JSON with exactly this schema:
{{
  "macro_regime": "risk_on | risk_off | neutral",
  "indicators": {{
    "front_end_yields":  {{"trend": "up | flat | down | not_discussed", "magnitude": "sharp | moderate | slight | na", "note": "<=15 words"}},
    "long_end_yields":   {{"trend": "...", "magnitude": "...", "note": "..."}},
    "yield_curve":       {{"trend": "steeper | flatter | unchanged | not_discussed", "magnitude": "...", "note": "..."}},
    "dollar":            {{"trend": "up | flat | down | not_discussed", "magnitude": "...", "note": "..."}},
    "oil":               {{"trend": "up | flat | down | not_discussed", "magnitude": "...", "note": "..."}},
    "gold":              {{"trend": "...", "magnitude": "...", "note": "..."}},
    "credit_spreads":    {{"trend": "widening | flat | tightening | not_discussed", "magnitude": "...", "note": "..."}},
    "equity_futures":    {{"trend": "up | flat | down | not_discussed", "magnitude": "...", "note": "..."}}
  }},
  "fed": {{
    "stance": "hawkish | neutral | dovish | not_discussed",
    "expected_path": "hike | hold | cut | unclear",
    "market_pricing": "<=20 words on what is priced in, e.g. '60% odds of a September hike'",
    "notable_speakers": ["..."]
  }},
  "earnings_ai": {{"tone": "positive | mixed | negative | not_discussed", "note": "<=20 words"}},
  "geopolitics": {{"escalation": "rising | stable | easing | not_discussed", "note": "<=20 words"}},
  "consumer": {{"tone": "strong | mixed | weak | not_discussed", "note": "<=20 words"}},
  "sentiment_score": <int -2..2, the NET tone of the show: -2 strongly risk-off .. +2 strongly risk-on>,
  "key_catalysts": ["<=4 items, each <=8 words, dated if the show dates them>"],
  "top_drivers": [{{"theme": "<=6 words", "direction": "bullish | bearish | neutral", "weight": <int 0..100>}}],
  "summary": "<4-6 sentences in English covering: market indicators and their direction, what the Fed/rates picture is, the dominant narrative, and the tone. <=120 words>",
  "notable_quotes": ["<=2 short quotes, each <=25 words>"]
}}

TRANSCRIPT
==========
{transcript}
"""

TREND_MAP = {
    "up": 1, "higher": 1, "rising": 1, "steeper": 1, "widening": 1,
    "down": -1, "lower": -1, "falling": -1, "flatter": -1, "tightening": -1,
    "flat": 0, "unchanged": 0, "stable": 0,
}
MAG_MAP = {"sharp": 2.0, "moderate": 1.0, "slight": 0.5, "na": 0.0}
STANCE_MAP = {"hawkish": -1, "neutral": 0, "dovish": 1, "not_discussed": 0}
TONE_MAP = {"positive": 1, "strong": 1, "mixed": 0, "neutral": 0, "negative": -1,
            "weak": -1, "not_discussed": 0}
GEO_MAP = {"rising": -1, "stable": 0, "easing": 1, "not_discussed": 0}

TIME_HEADER = re.compile(r"^\[\d{2}:\d{2}:\d{2}\s*-\s*\d{2}:\d{2}:\d{2}\]\s*$")


def clean_transcript(raw: str) -> str:
    lines = [ln for ln in raw.splitlines() if not TIME_HEADER.match(ln.strip())]
    return re.sub(r"[ \t]+", " ", "\n".join(lines)).strip()


def brief_path(bvid: str) -> Path:
    BRIEFS.mkdir(parents=True, exist_ok=True)
    return BRIEFS / f"{bvid}.json"


def call_llm(llm, system: str, user: str, use_json_mode: bool) -> dict:
    payload = {
        "model": llm.model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.0,
        "max_tokens": 8000,
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


def numeric_features(brief: dict) -> dict:
    """Flatten the ordinal brief into transparent numbers a factor can use."""
    feats: dict[str, float] = {}
    indicators = brief.get("indicators", {}) or {}
    for name, block in indicators.items():
        if not isinstance(block, dict):
            continue
        trend = str(block.get("trend", "not_discussed")).lower()
        sign = TREND_MAP.get(trend)
        magnitude = MAG_MAP.get(str(block.get("magnitude", "na")).lower(), 0.0)
        if sign is None:
            feats[f"brf_{name}"] = float("nan")
        else:
            feats[f"brf_{name}"] = sign * magnitude

    # risk-on interpretation: equities up / credit tight / dollar down are all "good for QQQ"
    risk = []
    def add(key: str, weight: float = 1.0) -> None:
        value = feats.get(key)
        if value is not None and value == value:
            risk.append(weight * value)

    add("brf_equity_futures", 1.0)
    add("brf_credit_spreads", -1.0)      # widening = bad
    add("brf_dollar", -1.0)              # stronger dollar = bad for QQQ
    add("brf_oil", -1.0)                 # oil spike = bad
    add("brf_front_end_yields", -1.0)    # front-end up = hawkish
    add("brf_long_end_yields", -1.0)

    fed = brief.get("fed", {}) or {}
    risk.append(2.0 * STANCE_MAP.get(str(fed.get("stance", "neutral")).lower(), 0))
    ai = brief.get("earnings_ai", {}) or {}
    risk.append(float(TONE_MAP.get(str(ai.get("tone", "not_discussed")).lower(), 0)))
    consumer = brief.get("consumer", {}) or {}
    risk.append(float(TONE_MAP.get(str(consumer.get("tone", "not_discussed")).lower(), 0)))
    geo = brief.get("geopolitics", {}) or {}
    risk.append(2.0 * GEO_MAP.get(str(geo.get("escalation", "not_discussed")).lower(), 0))

    feats["brf_sentiment"] = float(brief.get("sentiment_score", 0) or 0)
    feats["brf_composite"] = float(sum(risk))
    feats["brf_composite_n"] = float(len(risk))
    return feats


def render_markdown(brief: dict, meta: dict) -> str:
    lines = [f"# {meta['show_date']} Bloomberg Surveillance — daily brief", ""]
    lines.append(f"**BVID**: {meta['bvid']}  ")
    lines.append(f"**Regime**: {brief.get('macro_regime', '')}  ")
    lines.append(f"**Sentiment**: {brief.get('sentiment_score', '')}  ")
    lines.append(f"**Model**: {meta['model']} / {meta['prompt_version']}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(str(brief.get("summary", "")))
    lines.append("")
    lines.append("## Indicators")
    lines.append("")
    lines.append("| indicator | trend | magnitude | note |")
    lines.append("|---|---|---|---|")
    for name, block in (brief.get("indicators") or {}).items():
        if not isinstance(block, dict):
            continue
        lines.append(f"| {name} | {block.get('trend','')} | {block.get('magnitude','')} | {block.get('note','')} |")
    fed = brief.get("fed") or {}
    lines.append("")
    lines.append("## Fed / rates")
    lines.append("")
    lines.append(f"- stance: **{fed.get('stance','')}**, expected path: **{fed.get('expected_path','')}**")
    lines.append(f"- pricing: {fed.get('market_pricing','')}")
    if fed.get("notable_speakers"):
        lines.append(f"- speakers: {', '.join(map(str, fed['notable_speakers']))}")
    lines.append("")
    lines.append("## Other blocks")
    lines.append("")
    for key in ("earnings_ai", "geopolitics", "consumer"):
        block = brief.get(key) or {}
        lines.append(f"- **{key}**: {block.get('tone', block.get('escalation',''))} — {block.get('note','')}")
    lines.append("")
    if brief.get("key_catalysts"):
        lines.append("## Catalysts")
        lines.append("")
        for item in brief["key_catalysts"]:
            lines.append(f"- {item}")
        lines.append("")
    if brief.get("top_drivers"):
        lines.append("## Drivers")
        lines.append("")
        lines.append("| theme | direction | weight |")
        lines.append("|---|---|---|")
        for d in brief["top_drivers"]:
            if isinstance(d, dict):
                lines.append(f"| {d.get('theme','')} | {d.get('direction','')} | {d.get('weight','')} |")
        lines.append("")
    if brief.get("notable_quotes"):
        lines.append("## Quotes")
        lines.append("")
        for q in brief["notable_quotes"]:
            lines.append(f"> {q}")
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="deepseek")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    llm = resolve_llm(args.model)
    use_json_mode = llm.provider in {"deepseek", "glm", "qwen"}
    episodes = pd.read_csv(FILES["episodes"])
    if args.limit:
        episodes = episodes.head(args.limit)

    made = 0
    for i, row in enumerate(episodes.itertuples(index=False), 1):
        path = brief_path(row.bvid)
        if path.is_file() and not args.force:
            print(f"[{i}/{len(episodes)}] {row.bvid} cached")
            continue
        transcript = clean_transcript(Path(row.transcript).read_text(encoding="utf-8", errors="replace"))
        user = USER_TEMPLATE.format(date_phrase=row.show_date, transcript=transcript)
        for attempt in range(1, 4):
            try:
                response = call_llm(llm, SYSTEM, user, use_json_mode)
                brief = parse_json(response["raw"])
                payload = {
                    "bvid": row.bvid,
                    "show_date": row.show_date,
                    "model": llm.model,
                    "prompt_version": PROMPT_VERSION,
                    "brief": brief,
                    "usage": response["usage"],
                }
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                meta = {"bvid": row.bvid, "show_date": row.show_date, "model": llm.model,
                        "prompt_version": PROMPT_VERSION}
                (BRIEFS / f"{row.bvid}.md").write_text(render_markdown(brief, meta), encoding="utf-8")
                made += 1
                print(f"[{i}/{len(episodes)}] {row.bvid} {row.show_date} "
                      f"regime={brief.get('macro_regime')} sent={brief.get('sentiment_score')}")
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 3:
                    print(f"[{i}/{len(episodes)}] {row.bvid} FAILED: {exc}")
                else:
                    time.sleep(2 * attempt)
    print(f"briefs written: {made}, total cached: {len(list(BRIEFS.glob('*.json')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

