"""Reddit collector（公開 .json エンドポイント / キー不要）。

各 subreddit の /new と /top(day) を取得。適切な User-Agent を付与し、
robots/TOSに沿った公開JSONのみ利用する。
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..utils.http import get_json
from ..utils.models import Item
from .base import BaseCollector


class RedditCollector(BaseCollector):
    name = "Reddit"

    def collect(self) -> list[Item]:
        items: list[Item] = []
        subs = self.cfg["sources"]["reddit"].get("subreddits", [])
        per_sub = max(5, self.max_items // max(1, len(subs)))

        for sub in subs:
            url = f"https://www.reddit.com/r/{sub}/hot.json"
            try:
                data = get_json(
                    url,
                    user_agent=self.user_agent,
                    timeout=self.timeout,
                    params={"limit": per_sub, "raw_json": 1},
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.warning(f"[{self.name}] r/{sub} 取得失敗: {exc}")
                continue

            for child in data.get("data", {}).get("children", []):
                d = child.get("data", {})
                if d.get("stickied"):
                    continue
                title = d.get("title", "")
                # 外部リンクがあればそれを、無ければ Reddit のパーマリンク
                url_out = d.get("url_overridden_by_dest") or (
                    "https://www.reddit.com" + d.get("permalink", "")
                )
                selftext = (d.get("selftext") or "")[:500]
                if not self.is_ai_related(title, selftext, sub):
                    continue
                published = datetime.fromtimestamp(
                    d.get("created_utc", 0), tz=timezone.utc
                )
                items.append(
                    Item(
                        title=title,
                        url=url_out,
                        source=f"{self.name} r/{sub}",
                        published_at=published,
                        author=d.get("author", ""),
                        summary=selftext,
                        metrics={
                            "score": d.get("score", 0) or 0,
                            "comments": d.get("num_comments", 0) or 0,
                        },
                    )
                )
        self.logger.info(f"[{self.name}] {len(items)} 件")
        return items
