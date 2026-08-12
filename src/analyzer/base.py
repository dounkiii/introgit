"""analyzer の基底とデータ契約。

analyze(topic) は以下のキーを持つ dict を返す:
  summary              : 概要（3〜5行相当）
  reasons              : なぜ今狙い目か（list[str]）
  monetization_ideas   : 収益化方法（list[str]）
  content_ideas        : 想定コンテンツ（list[str]）
  suggested_title      : 想定タイトル（str）
  risks                : リスク（list[str]）
  subscores            : {japanese_competition, monetization, content_potential} 各 0.0〜1.0

鮮度(freshness)と需要(demand)は scorer が指標から決定論的に算出するため、
analyzer は「人間の判断が要る3項目」の相対値(0〜1)と物語部分を返す。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..utils.models import Topic


class BaseAnalyzer(ABC):
    provider = "base"

    def __init__(self, cfg: dict, logger):
        self.cfg = cfg
        self.logger = logger

    @abstractmethod
    def analyze(self, topic: Topic) -> dict:
        raise NotImplementedError
