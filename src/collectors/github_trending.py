"""GitHub 新着人気リポジトリ collector（公式 REST Search API / 未認証で利用可）。

スクレイピングを避け、公式 API で「最近作成された AI 関連リポジトリ」を
star 数順に取得する。未認証はレート制限が厳しいため件数は控えめ。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..utils.http import get_json
from ..utils.models import Item
from .base import BaseCollector

API = "https://api.github.com/search/repositories"


class GitHubTrendingCollector(BaseCollector):
    name = "GitHub Trending"

    def collect(self) -> list[Item]:
        items: list[Item] = []
        window_days = max(1, self.cfg["collection"]["max_window_hours"] // 24)
        since = (datetime.now(timezone.utc) - timedelta(days=window_days)).strftime("%Y-%m-%d")
        query = self.cfg["sources"]["github_trending"].get("query", "AI")
        q = f"{query} created:>{since}"

        headers_ua = self.user_agent
        try:
            data = get_json(
                API,
                user_agent=headers_ua,
                timeout=self.timeout,
                params={
                    "q": q,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": min(self.max_items, 30),
                },
            )
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(f"[{self.name}] 取得失敗: {exc}")
            return items

        for repo in data.get("items", []):
            title = repo.get("full_name", "")
            desc = repo.get("description") or ""
            if not self.is_ai_related(title, desc):
                continue
            created = repo.get("created_at")
            published = (
                datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if created
                else datetime.now(timezone.utc)
            )
            items.append(
                Item(
                    title=f"{title} — {desc}"[:200] if desc else title,
                    url=repo.get("html_url", ""),
                    source=self.name,
                    published_at=published,
                    author=(repo.get("owner") or {}).get("login", ""),
                    summary=desc,
                    metrics={
                        "stars": repo.get("stargazers_count", 0) or 0,
                        "comments": repo.get("open_issues_count", 0) or 0,
                    },
                )
            )
        self.logger.info(f"[{self.name}] {len(items)} 件")
        return items
