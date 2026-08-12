"""評価済み記事のキャッシュ。同じ記事を何度もLLM評価しないための仕組み。

data/seen.json に {topic_id: analysis_dict} を保存し、
次回以降は同一IDの分析結果を再利用する。
"""
from __future__ import annotations

import json
from pathlib import Path

from .config import ROOT


class SeenCache:
    def __init__(self, rel_path: str):
        self.path = ROOT / rel_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001  壊れていても続行
                self._data = {}

    def has(self, key: str) -> bool:
        return key in self._data

    def get(self, key: str):
        return self._data.get(key)

    def set(self, key: str, value: dict) -> None:
        self._data[key] = value

    def save(self) -> None:
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
