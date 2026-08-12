"""ヒューリスティック分析（LLM不要・完全無料）。

キーワードマッチとメタデータから、収益性・コンテンツ化しやすさ・日本語競合の
弱さを推定し、物語部分（理由・アイデア・リスク）をテンプレートで生成する。
LLM が使えないとき、または LLM 呼び出しが失敗したときのフォールバックにもなる。
"""
from __future__ import annotations

import re

from ..utils.models import Topic
from .base import BaseAnalyzer

_JP_RE = re.compile(r"[぀-ヿ一-鿿]")
# タイトル先頭のノイズprefix（Show HN: など）
_PREFIX_RE = re.compile(r"^\s*(show hn|ask hn|tell hn|launch hn)\s*[:：\-–—]\s*", re.I)
# 先頭の [P] [R] [News] などのタグ
_TAG_RE = re.compile(r"^\s*\[[^\]]+\]\s*")


def _count_hits(text: str, signals: list[str]) -> list[str]:
    low = text.lower()
    return [s for s in signals if s.lower() in low]


def _shorten(text: str, limit: int) -> str:
    """語境界で切り詰め、切った場合は末尾に … を付ける。"""
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,.-–—:：") + "…"


class HeuristicAnalyzer(BaseAnalyzer):
    provider = "heuristic"

    def __init__(self, cfg: dict, logger):
        super().__init__(cfg, logger)
        h = cfg["scoring"]["heuristic"]
        self.mon_signals = h["monetization_signals"]
        self.content_signals = h["content_signals"]
        self.neg_signals = h["negative_signals"]

    def analyze(self, topic: Topic) -> dict:
        text = f"{topic.title} {topic.summary}"
        has_jp = bool(_JP_RE.search(text))

        mon_hits = _count_hits(text, self.mon_signals)
        content_hits = _count_hits(text, self.content_signals)
        neg_hits = _count_hits(text, self.neg_signals)

        # --- 日本語競合の弱さ（海外話題で日本語が少なそうなほど高い） ---
        if has_jp:
            jp_score = 0.4          # 既に日本語テキストがある = 競合が存在しがち
        else:
            jp_score = 0.6
            if any(s in topic.sources for s in ("GitHub Trending", "Product Hunt")) or any(
                "GitHub" in s or "Product Hunt" in s for s in topic.sources
            ):
                jp_score += 0.2     # ニッチな新興サービスは日本語情報が薄い傾向
            jp_score = min(1.0, jp_score + 0.15)

        # --- 収益性 ---
        mon_score = min(1.0, 0.35 + 0.15 * len(mon_hits))
        # SaaS/課金系の強シグナルは上乗せ
        if any(k in text.lower() for k in ("saas", "subscription", "pricing", "有料", "課金")):
            mon_score = min(1.0, mon_score + 0.15)

        # --- コンテンツ化しやすさ ---
        content_score = min(1.0, 0.35 + 0.13 * len(content_hits))
        if "GitHub Trending" in topic.sources or "Product Hunt" in topic.sources:
            content_score = min(1.0, content_score + 0.1)  # 実際に試せる

        # --- ネガティブ（政治・炎上等）は全体的に減点 ---
        if neg_hits:
            penalty = 0.25 * len(neg_hits)
            mon_score = max(0.0, mon_score - penalty)
            content_score = max(0.0, content_score - penalty)
            jp_score = max(0.0, jp_score - penalty)

        return {
            "summary": self._summary(topic),
            "reasons": self._reasons(topic, has_jp, mon_hits, content_hits),
            "monetization_ideas": self._monetization_ideas(mon_hits),
            "content_ideas": self._content_ideas(content_hits, topic),
            "suggested_title": self._title(topic),
            "risks": self._risks(topic, neg_hits),
            "subscores": {
                "japanese_competition": round(jp_score, 3),
                "monetization": round(mon_score, 3),
                "content_potential": round(content_score, 3),
            },
        }

    # ---- テンプレート生成 -------------------------------------------------
    @staticmethod
    def _summary(topic: Topic) -> str:
        base = topic.summary.strip() or topic.title.strip()
        srcs = "、".join(topic.sources[:3])
        return f"{base[:280]}（情報源: {srcs}）"

    @staticmethod
    def _reasons(topic: Topic, has_jp: bool, mon_hits, content_hits) -> list[str]:
        reasons = []
        if topic.age_hours <= 24:
            reasons.append("公開されたばかり（24時間以内）")
        elif topic.age_hours <= 72:
            reasons.append("直近3日以内の新しい話題")
        if not has_jp:
            reasons.append("海外発で日本語情報が少ない可能性が高い")
        if len(topic.sources) >= 2:
            reasons.append(f"複数ソースで言及されている（{len(topic.sources)}ソース）")
        eng = sum(v for v in topic.metrics.values() if isinstance(v, int))
        if eng >= 100:
            reasons.append(f"コミュニティで反応が大きい（指標合計 {eng}）")
        if mon_hits:
            reasons.append("収益化と相性の良いキーワードを含む")
        return reasons or ["新規性のある話題"]

    @staticmethod
    def _monetization_ideas(mon_hits) -> list[str]:
        ideas = ["関連ツール・サービスのアフィリエイト紹介", "有料noteでの深掘り解説"]
        if any(k in [m.lower() for m in mon_hits] for k in ("saas", "subscription", "api", "platform")):
            ideas.append("継続課金SaaSの紹介・比較（月額サービスの成約狙い）")
        ideas.append("関連書籍・オンライン講座の紹介")
        return ideas

    @staticmethod
    def _content_ideas(content_hits, topic: Topic) -> list[str]:
        ideas = ["無料ブログ記事", "X（旧Twitter）投稿"]
        low = " ".join(content_hits).lower()
        if "GitHub Trending" in topic.sources or "Product Hunt" in topic.sources or "tried" in low:
            ideas.append("実際に試したレビュー記事")
        if "vs" in low or "comparison" in low or "比較" in low:
            ideas.append("競合比較記事")
        ideas.append("「使い方」解説（有料note化も可能）")
        return ideas

    @staticmethod
    def _title(topic: Topic) -> str:
        name = topic.title
        # 先頭のノイズ（Show HN: / [P] 等）を除去してから整形する
        name = _PREFIX_RE.sub("", name)
        name = _TAG_RE.sub("", name)
        # GitHub の "owner/repo — 説明" などは前半（サービス名側）を採用
        name = name.split(" — ")[0].strip()
        name = _shorten(name, 48)
        return f"{name} を実際に試してみた｜使い方と収益化のヒント"

    @staticmethod
    def _risks(topic: Topic, neg_hits) -> list[str]:
        risks = []
        if len(topic.sources) < 2:
            risks.append("情報源が単一でまだ裏取りが少ない")
        if topic.age_hours <= 24:
            risks.append("一時的な話題で終わる可能性がある")
        if neg_hits:
            risks.append("炎上・政治性などノイズ要素を含む可能性")
        return risks or ["情報が新しく、今後の展開が不確実"]
