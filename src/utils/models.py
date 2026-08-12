"""共通データモデル。

収集した1件の候補を表す Item と、複数ソースを統合した Topic を定義します。
どの collector も最終的に Item を返すことで、後続処理を統一します。
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _norm_title(title: str) -> str:
    """タイトルを正規化（小文字化・記号除去）して比較用キーにする。"""
    t = (title or "").lower()
    t = re.sub(r"[^a-z0-9぀-ヿ一-鿿]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


@dataclass
class Item:
    """収集した候補1件。"""

    title: str
    url: str
    source: str
    published_at: datetime            # UTC aware
    summary: str = ""
    author: str = ""
    metrics: dict = field(default_factory=dict)   # points / score / stars / comments 等
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        # published_at が naive の場合は UTC とみなす
        if self.published_at and self.published_at.tzinfo is None:
            self.published_at = self.published_at.replace(tzinfo=timezone.utc)

    @property
    def id(self) -> str:
        """URL（無ければ正規化タイトル）を基にした安定ID。"""
        basis = (self.url or "").strip().lower() or _norm_title(self.title)
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]

    @property
    def norm_title(self) -> str:
        return _norm_title(self.title)

    @property
    def age_hours(self) -> float:
        delta = datetime.now(timezone.utc) - self.published_at
        return max(0.0, delta.total_seconds() / 3600.0)

    def engagement(self) -> int:
        """代表的なエンゲージメント値（needでの並び替えに使用）。"""
        m = self.metrics or {}
        return int(m.get("points", 0)) + int(m.get("score", 0)) + int(m.get("stars", 0))


@dataclass
class Topic:
    """重複統合後の1テーマ（複数 Item をまとめたもの）。"""

    title: str
    summary: str
    source_urls: list                      # 参照URL（複数）
    sources: list                          # ソース名のリスト
    published_at: datetime
    metrics: dict = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    items: list = field(default_factory=list)   # 元 Item 群

    @property
    def id(self) -> str:
        basis = (self.source_urls[0] if self.source_urls else _norm_title(self.title))
        return hashlib.sha1(str(basis).encode("utf-8")).hexdigest()[:16]

    @property
    def age_hours(self) -> float:
        delta = datetime.now(timezone.utc) - self.published_at
        return max(0.0, delta.total_seconds() / 3600.0)
