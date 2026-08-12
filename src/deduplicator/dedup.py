"""重複統合。

同一ニュース/サービスが複数ソースに出ている場合、1テーマに統合し、
参照URLを複数残す。判定材料:
  - URL（正規化して一致）
  - タイトル類似度（difflib）
  - ドメイン/サービス名
削除するのではなく統合するのがポイント。
"""
from __future__ import annotations

from datetime import timezone
from difflib import SequenceMatcher
from urllib.parse import urlparse

from ..utils.models import Item, Topic


def _domain(url: str) -> str:
    try:
        net = urlparse(url).netloc.lower()
        return net[4:] if net.startswith("www.") else net
    except Exception:  # noqa: BLE001
        return ""


def _norm_url(url: str) -> str:
    """クエリ・フラグメントを除いた正規化URL。"""
    try:
        p = urlparse(url)
        net = p.netloc.lower()
        net = net[4:] if net.startswith("www.") else net
        return f"{net}{p.path.rstrip('/')}"
    except Exception:  # noqa: BLE001
        return url


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


# ごく一般的な語（これだけ一致しても同一テーマとは言えない）
_STOPWORDS = {
    "the", "a", "an", "to", "of", "and", "for", "with", "is", "are", "was",
    "in", "on", "at", "by", "it", "its", "this", "that", "your", "you", "own",
    "here", "new", "how", "i", "show", "hn", "we", "my", "from", "get", "now",
}


def _tokens(norm_title: str) -> set:
    """正規化タイトルから意味のあるトークン集合を作る。

    バージョン番号（"3", "4o" 等）は同一テーマ判定の重要シグナルなので保持し、
    一般語(stopwords)のみ除外する。
    """
    return {t for t in norm_title.split() if t and t not in _STOPWORDS}


def _overlap_coeff(a: set, b: set) -> float:
    """オーバーラップ係数 = |A∩B| / min(|A|,|B|)。言い回しが違う同一ニュースに強い。"""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


class Deduplicator:
    def __init__(self, cfg: dict, logger):
        d = cfg["deduplication"]
        self.threshold = d["title_similarity_threshold"]
        self.overlap_threshold = d.get("token_overlap_threshold", 0.6)
        self.min_shared_tokens = d.get("min_shared_tokens", 3)
        self.logger = logger

    def _same_topic(self, item: Item, topic: Topic) -> bool:
        # 1) URL 完全一致（正規化後）
        item_nurl = _norm_url(item.url)
        for u in topic.source_urls:
            if item_nurl and item_nurl == _norm_url(u):
                return True
        # 2) タイトル類似度 / トークンオーバーラップ
        item_tokens = _tokens(item.norm_title)
        for it in topic.items:
            if _similar(item.norm_title, it.norm_title) >= self.threshold:
                return True
            other = _tokens(it.norm_title)
            shared = len(item_tokens & other)
            if shared >= self.min_shared_tokens and _overlap_coeff(item_tokens, other) >= self.overlap_threshold:
                return True
        return False

    def merge(self, items: list[Item]) -> list[Topic]:
        # エンゲージメントが高い順に処理すると、代表タイトルが良質になりやすい
        items = sorted(items, key=lambda i: i.engagement(), reverse=True)
        topics: list[Topic] = []

        for item in items:
            placed = False
            for topic in topics:
                if self._same_topic(item, topic):
                    self._absorb(topic, item)
                    placed = True
                    break
            if not placed:
                topics.append(self._new_topic(item))

        self.logger.info(f"[dedup] {len(items)} 件 -> {len(topics)} テーマ")
        return topics

    @staticmethod
    def _new_topic(item: Item) -> Topic:
        return Topic(
            title=item.title,
            summary=item.summary,
            source_urls=[item.url] if item.url else [],
            sources=[item.source],
            published_at=item.published_at,
            metrics=dict(item.metrics),
            items=[item],
        )

    @staticmethod
    def _absorb(topic: Topic, item: Item) -> None:
        topic.items.append(item)
        if item.url and item.url not in topic.source_urls:
            topic.source_urls.append(item.url)
        if item.source not in topic.sources:
            topic.sources.append(item.source)
        # 概要は長い方を採用
        if len(item.summary) > len(topic.summary):
            topic.summary = item.summary
        # メトリクスは合算（話題性の集約とみなす）
        for k, v in (item.metrics or {}).items():
            topic.metrics[k] = topic.metrics.get(k, 0) + (v or 0)
        # 公開日時は最も新しいものを採用
        if item.published_at.astimezone(timezone.utc) > topic.published_at.astimezone(timezone.utc):
            topic.published_at = item.published_at
