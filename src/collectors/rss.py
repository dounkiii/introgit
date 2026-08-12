"""RSS collector（feedparser 使用 / キー不要）。

config の sources.rss.feeds に列挙した各フィードを取得する。
Product Hunt も RSS として同じ仕組みで取得する（別クラス）。
新しいメディアを足したいときは settings.yaml にURLを1行追加するだけ。
"""
from __future__ import annotations

import calendar
from datetime import datetime, timezone

import feedparser

from ..utils.models import Item
from .base import BaseCollector


def _parse_published(entry) -> datetime:
    for key in ("published_parsed", "updated_parsed"):
        tm = getattr(entry, key, None) or entry.get(key)
        if tm:
            return datetime.fromtimestamp(calendar.timegm(tm), tz=timezone.utc)
    return datetime.now(timezone.utc)


def _clean(text: str, limit: int = 500) -> str:
    import re

    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


class RSSCollector(BaseCollector):
    name = "RSS"

    def _fetch_feed(self, feed_name: str, url: str, require_ai: bool) -> list[Item]:
        items: list[Item] = []
        try:
            parsed = feedparser.parse(
                url, agent=self.user_agent, request_headers={"User-Agent": self.user_agent}
            )
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(f"[{feed_name}] 取得失敗: {exc}")
            return items

        entries = parsed.entries[: self.max_items]
        for e in entries:
            title = getattr(e, "title", "") or ""
            summary = _clean(getattr(e, "summary", "") or getattr(e, "description", ""))
            link = getattr(e, "link", "") or ""
            if require_ai and not self.is_ai_related(title, summary):
                continue
            items.append(
                Item(
                    title=title,
                    url=link,
                    source=feed_name,
                    published_at=_parse_published(e),
                    summary=summary,
                    author=getattr(e, "author", "") or "",
                    metrics={},
                )
            )
        self.logger.info(f"[{feed_name}] {len(items)} 件")
        return items

    def collect(self) -> list[Item]:
        items: list[Item] = []
        for feed in self.cfg["sources"]["rss"].get("feeds", []):
            # AI専門メディアが多いが、総合メディアもあるためAIフィルタは有効にする
            items.extend(self._fetch_feed(feed["name"], feed["url"], require_ai=True))
        return items


class ProductHuntCollector(BaseCollector):
    name = "Product Hunt"

    def collect(self) -> list[Item]:
        url = self.cfg["sources"]["producthunt"].get("rss_url")
        if not url:
            return []
        # Product Hunt は新規プロダクトが並ぶので、AI以外も混じる -> フィルタON
        rss = RSSCollector(self.cfg, self.logger)
        return rss._fetch_feed(self.name, url, require_ai=True)
