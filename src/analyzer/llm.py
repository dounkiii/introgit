"""LLM 分析器（OpenAI / Gemini / Anthropic を切り替え可能）。

- API キーは .env から読み込む（ソースに直書きしない）。
- ライブラリは遅延 import（未インストールでも他プロバイダ/heuristic は動く）。
- 呼び出し失敗時は heuristic 分析へフォールバックし、全体を止めない。
"""
from __future__ import annotations

import json

from ..utils.models import Topic
from .base import BaseAnalyzer
from .heuristic import HeuristicAnalyzer

PROMPT = """あなたはAIコンテンツ収益化の専門リサーチャーです。
以下のトピックを、日本語ブログ/有料note/アフィリエイト観点で評価してください。

タイトル: {title}
概要: {summary}
情報源: {sources}
参照URL: {urls}
経過時間: 約{age}時間前

次のJSONだけを厳密に出力してください（前後に文章を付けない）:
{{
  "summary": "何が起きたのかを3〜5行で日本語で説明",
  "reasons": ["なぜ今狙い目かの箇条書き", "..."],
  "monetization_ideas": ["収益化方法の箇条書き", "..."],
  "content_ideas": ["想定コンテンツ形式", "..."],
  "suggested_title": "読者がクリックしたくなる日本語タイトル案",
  "risks": ["リスクの箇条書き", "..."],
  "subscores": {{
    "japanese_competition": 0.0,
    "monetization": 0.0,
    "content_potential": 0.0
  }}
}}

subscores は各 0.0〜1.0:
- japanese_competition: 日本語の競合記事が少ないほど高い（海外で話題だが日本語情報が無い=高)
- monetization: アフィリエイト/SaaS課金/有料note化のしやすさ
- content_potential: 使い方・比較・レビューなど記事化のしやすさ
"""


class LLMAnalyzer(BaseAnalyzer):
    provider = "llm"

    def __init__(self, cfg: dict, logger, provider: str, api_key: str):
        super().__init__(cfg, logger)
        self.provider = provider
        self.api_key = api_key
        self.model = cfg["analyzer"]["models"].get(provider, "")
        self._fallback = HeuristicAnalyzer(cfg, logger)
        self._client = None

    # -- 各プロバイダ呼び出し ------------------------------------------------
    def _call_openai(self, prompt: str) -> str:
        from openai import OpenAI

        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content

    def _call_gemini(self, prompt: str) -> str:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        resp = model.generate_content(
            prompt, generation_config={"response_mime_type": "application/json"}
        )
        return resp.text

    def _call_anthropic(self, prompt: str) -> str:
        import anthropic

        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text

    def _call(self, prompt: str) -> str:
        if self.provider == "openai":
            return self._call_openai(prompt)
        if self.provider == "gemini":
            return self._call_gemini(prompt)
        if self.provider == "anthropic":
            return self._call_anthropic(prompt)
        raise ValueError(f"未知のプロバイダ: {self.provider}")

    # -- 分析 ---------------------------------------------------------------
    def analyze(self, topic: Topic) -> dict:
        prompt = PROMPT.format(
            title=topic.title,
            summary=topic.summary or "(概要なし)",
            sources="、".join(topic.sources),
            urls=" , ".join(topic.source_urls[:4]),
            age=int(topic.age_hours),
        )
        try:
            raw = self._call(prompt)
            data = json.loads(_extract_json(raw))
            return self._validate(data, topic)
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(
                f"[analyzer:{self.provider}] LLM失敗のためheuristicで代替: {exc}"
            )
            return self._fallback.analyze(topic)

    def _validate(self, data: dict, topic: Topic) -> dict:
        fb = None
        sub = data.get("subscores") or {}
        # 欠損時はheuristicで補完
        if not all(k in sub for k in ("japanese_competition", "monetization", "content_potential")):
            fb = self._fallback.analyze(topic)
            sub = {**fb["subscores"], **sub}
        clean = {
            "summary": data.get("summary") or topic.summary or topic.title,
            "reasons": _as_list(data.get("reasons")),
            "monetization_ideas": _as_list(data.get("monetization_ideas")),
            "content_ideas": _as_list(data.get("content_ideas")),
            "suggested_title": data.get("suggested_title") or topic.title,
            "risks": _as_list(data.get("risks")),
            "subscores": {
                "japanese_competition": _clip(sub.get("japanese_competition", 0.5)),
                "monetization": _clip(sub.get("monetization", 0.5)),
                "content_potential": _clip(sub.get("content_potential", 0.5)),
            },
        }
        return clean


def _as_list(v) -> list:
    if isinstance(v, list):
        return [str(x) for x in v if x]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


def _clip(v) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return 0.5


def _extract_json(text: str) -> str:
    """LLM出力からJSON部分を抜き出す（```で囲まれていても対応）。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        return text[start : end + 1]
    return text
