"""ログ設定。コンソールとファイル(logs/)の両方へ出力する。"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from .config import ROOT


def setup_logger(name: str = "research") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:  # 二重登録防止
        return logger
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")

    # コンソール
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # ファイル（logs/YYYY-MM-DD.log）
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    fh = logging.FileHandler(logs_dir / f"{today}.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)

    return logger
