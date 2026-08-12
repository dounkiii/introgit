"""collector の基底クラス。

新しい情報源を追加するには BaseCollector を継承して collect() を実装し、
collectors/__init__.py の build_collectors() に登録するだけ。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..utils.models import Item


class BaseCollector(ABC):
    name = "base"

    def __init__(self, cfg: dict, logger):
        self.cfg = cfg
        self.logger = logger
        self.timeout = cfg["collection"]["request_timeout"]
        self.user_agent = cfg["collection"]["user_agent"]
        self.max_items = cfg["collection"]["max_items_per_source"]
        self.ai_keywords = [k.lower() for k in cfg["genres"]["ai_keywords"]]

    @abstractmethod
    def collect(self) -> list[Item]:
        """候補 Item のリストを返す。失敗しても例外はここでは投げず空を返すのが理想。"""
        raise NotImplementedError

    def is_ai_related(self, *texts: str) -> bool:
        """与えたテキスト群のどこかにAIキーワードが含まれるか。"""
        blob = " ".join(t for t in texts if t).lower()
        return any(kw in blob for kw in self.ai_keywords)
