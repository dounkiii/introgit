"""analyzer のファクトリ。

provider の決定順:
  1. 環境変数 ANALYZER_PROVIDER
  2. settings.yaml の analyzer.provider
LLM プロバイダ指定でも API キーが無ければ heuristic に自動フォールバック。
"""
from __future__ import annotations

import os

from .base import BaseAnalyzer
from .heuristic import HeuristicAnalyzer
from .llm import LLMAnalyzer

_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def build_analyzer(cfg: dict, logger) -> BaseAnalyzer:
    provider = (os.environ.get("ANALYZER_PROVIDER") or cfg["analyzer"]["provider"]).lower()

    if provider == "heuristic":
        logger.info("[analyzer] provider=heuristic（LLM未使用・無料モード）")
        return HeuristicAnalyzer(cfg, logger)

    key = os.environ.get(_KEY_ENV.get(provider, ""), "")
    if not key:
        logger.warning(
            f"[analyzer] provider={provider} だが APIキー未設定 -> heuristic にフォールバック"
        )
        return HeuristicAnalyzer(cfg, logger)

    logger.info(f"[analyzer] provider={provider} model={cfg['analyzer']['models'].get(provider)}")
    return LLMAnalyzer(cfg, logger, provider, key)


__all__ = ["build_analyzer", "BaseAnalyzer", "HeuristicAnalyzer", "LLMAnalyzer"]
