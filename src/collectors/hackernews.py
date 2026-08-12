"""Hacker News collector（Algolia HN Search API / 公開・キー不要）。

直近の story を新着順で取得し、AI関連のみ抽出する。
API: https://hn.algolia.com/api
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..utils.http import get_json
from ..utils.models import Item
from .base import BaseCollector

API = "https://hn.algolia.com/api/v1/search_by_date"


class HackerNewsCollector(BaseCollector):
    name = "Hacker News"

    def collect(self) -> list[Item]:
        items: list[Item] = []
        try:
            data = get_json(
                API,
                user_agent=self.user_agent,
                timeout=self.timeout,
                params={
                    "tags": "story",
                    "hitsPerPage": self.max_items,
                    # 質の低い投稿を除くため最低ポイントを設定
                    "numericFilters": "points>10",
                },
            )
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(f"[{self.name}] 取得失敗: {exc}")
            return items

        for hit in data.get("hits", []):
            title = hit.get("title") or ""
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            if not self.is_ai_related(title):
                continue
            ts = hit.get("created_at_i")
            published = (
                datetime.fromtimestamp(ts, tz=timezone.utc) if ts else datetime.now(timezone.utc)
            )
            items.append(
                Item(
                    title=title,
                    url=url,
                    source=self.name,
                    published_at=published,
                    author=hit.get("author", ""),
                    metrics={
                        "points": hit.get("points", 0) or 0,
                        "comments": hit.get("num_comments", 0) or 0,
                    },
                )
            )
        self.logger.info(f"[{self.name}] {len(items)} 件")
        return items
