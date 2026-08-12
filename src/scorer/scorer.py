"""採点（合計100点）。

- freshness : 公開からの経過時間の閾値で決定論的に算出
- demand    : 各ソースのエンゲージメント指標を正規化
- japanese_competition / monetization / content_potential :
              analyzer が返した subscore(0〜1) × 重み
配点は settings.yaml の scoring.weights で変更可能。
"""
from __future__ import annotations

from ..utils.models import Topic


class Scorer:
    def __init__(self, cfg: dict, logger):
        s = cfg["scoring"]
        self.weights = s["weights"]
        self.freshness_thresholds = s["freshness_thresholds"]
        self.demand_ref = s["demand_reference"]
        self.logger = logger

    def _freshness(self, topic: Topic) -> float:
        age = topic.age_hours
        for th in self.freshness_thresholds:
            if age <= th["max_hours"]:
                return float(th["points"])
        return 0.0

    def _demand(self, topic: Topic) -> float:
        """指標を満点相当値で正規化し、重みを掛ける。複数指標は最大寄与を採用。"""
        m = topic.metrics or {}
        ref = self.demand_ref
        ratios = []
        if ref.get("hackernews_points"):
            ratios.append(m.get("points", 0) / ref["hackernews_points"])
        if ref.get("reddit_score"):
            ratios.append(m.get("score", 0) / ref["reddit_score"])
        if ref.get("github_stars"):
            ratios.append(m.get("stars", 0) / ref["github_stars"])
        if ref.get("comments"):
            ratios.append(m.get("comments", 0) / ref["comments"])
        # 主指標(最大) + コメント等の副次的な寄与を少し加味
        top = max(ratios) if ratios else 0.0
        # 複数ソースに載っている話題は話題性ボーナス（最大 +0.15）
        multi_bonus = min(0.15, 0.05 * (len(topic.sources) - 1))
        ratio = min(1.0, top + multi_bonus)
        return ratio * self.weights["demand"]

    def score(self, topic: Topic, analysis: dict) -> dict:
        sub = analysis.get("subscores", {})
        freshness = self._freshness(topic)
        demand = self._demand(topic)
        jp = sub.get("japanese_competition", 0.5) * self.weights["japanese_competition"]
        mon = sub.get("monetization", 0.5) * self.weights["monetization"]
        content = sub.get("content_potential", 0.5) * self.weights["content_potential"]

        scores = {
            "score_freshness": round(freshness, 1),
            "score_demand": round(demand, 1),
            "score_japanese_competition": round(jp, 1),
            "score_monetization": round(mon, 1),
            "score_content_potential": round(content, 1),
        }
        scores["score_total"] = round(sum(scores.values()), 1)
        return scores
