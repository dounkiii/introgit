"""collector の登録・実行。

build_collectors() が settings.yaml の sources を見て有効な collector を組み立て、
collect_all() が各 collector を隔離実行（1つ落ちても全体は継続）する。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..utils.models import Item
from .github_trending import GitHubTrendingCollector
from .hackernews import HackerNewsCollector
from .reddit import RedditCollector
from .rss import ProductHuntCollector, RSSCollector

# ソースキー -> collector クラス
REGISTRY = {
    "hackernews": HackerNewsCollector,
    "reddit": RedditCollector,
    "github_trending": GitHubTrendingCollector,
    "producthunt": ProductHuntCollector,
    "rss": RSSCollector,
}


def build_collectors(cfg: dict, logger) -> list:
    collectors = []
    for key, cls in REGISTRY.items():
        src_cfg = cfg["sources"].get(key, {})
        if src_cfg.get("enabled", False):
            collectors.append(cls(cfg, logger))
    return collectors


def collect_from_fixture(path: str, cfg: dict, logger) -> list[Item]:
    """オフライン検証用: フィクスチャJSONから Item を生成する（--demo）。

    ネットワークに依存せず、収集→統合→分析→採点→出力の全パイプラインを
    検証できる。published_hours_ago から現在時刻基準で公開日時を復元する。
    """
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    items: list[Item] = []
    for r in raw:
        items.append(
            Item(
                title=r["title"],
                url=r.get("url", ""),
                source=r.get("source", "fixture"),
                published_at=now - timedelta(hours=r.get("published_hours_ago", 0)),
                summary=r.get("summary", ""),
                author=r.get("author", ""),
                metrics=r.get("metrics", {}),
            )
        )
    logger.info(f"[fixture] {len(items)} 件をロード ({p.name})")
    return items


def collect_all(cfg: dict, logger) -> list[Item]:
    """全 collector を実行して Item を集約。各 collector はエラー隔離。"""
    all_items: list[Item] = []
    for collector in build_collectors(cfg, logger):
        try:
            all_items.extend(collector.collect())
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[{collector.name}] 予期せぬエラー: {exc}")
    return all_items
