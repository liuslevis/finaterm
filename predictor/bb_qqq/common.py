"""Shared paths / env / config for the bb_qqq LLM factor study."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
REPORTS = HERE / "reports"
DATA.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)

# --- upstream artifacts -------------------------------------------------
DEEPFIND_RAG = Path(r"C:\Users\david\dev\deepfind-rag")
BILI_ROOT = DEEPFIND_RAG / "video" / "bili"
# The episode universe was enumerated with `opencli bilibili user-videos`.
MANIFEST = BILI_ROOT / ".listing" / "surveillance-manifest.csv"

# --- env ----------------------------------------------------------------
ENV_FILES = [
    Path(r"C:\Users\david\dev\deepfind-cli\.env"),  # has all provider keys
    DEEPFIND_RAG / ".env",
    Path(r"C:\Users\david\dev\finance\.env"),
]

FILES = {
    "episodes": DATA / "episodes.csv",
    "prices": DATA / "qqq_daily.csv",
    "scores": DATA / "llm_scores.csv",
    "panel": DATA / "factor_panel.csv",
}


def load_env() -> dict[str, str]:
    """Minimal .env reader (no python-dotenv dependency)."""
    env: dict[str, str] = {}
    for path in ENV_FILES:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            env.setdefault(key, value)
    for key, value in os.environ.items():
        env.setdefault(key, value)
    return env


@dataclass(frozen=True)
class LLM:
    provider: str
    base_url: str
    api_key: str
    model: str

    @property
    def endpoint(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/v1"):
            return base + "/chat/completions"
        return base + "/v1/chat/completions"


def resolve_llm(name: str = "deepseek") -> LLM:
    env = load_env()
    name = name.lower()
    prefixes = {
        "deepseek": "DEEPSEEK",
        "glm": "GLM",
        "minimax": "MINIMAX",
        "mimo": "MIMO",
        "qwen": "QWEN",
    }
    prefix = prefixes[name]
    key = env.get(f"{prefix}_API_KEY", "")
    model = env.get(f"{prefix}_MODEL_NAME", "")
    base = env.get(f"{prefix}_BASE_URL", "")
    if not key or not model:
        raise SystemExit(f"missing {prefix}_API_KEY / {prefix}_MODEL_NAME")
    if not base:
        base = {
            "deepseek": "https://api.deepseek.com",
            "glm": "https://open.bigmodel.cn/api/paas/v4",
            "minimax": "https://api.minimax.chat",
            "mimo": "https://api.xiaomi.com",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        }[name]
    return LLM(provider=name, base_url=base, api_key=key, model=model)
