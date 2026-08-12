"""設定ファイル(YAML)と環境変数(.env)の読み込み。"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv 未インストールでも動くように
    def load_dotenv(*_args, **_kwargs):
        return False

# プロジェクトルート（このファイルから見て2つ上: src/utils -> src -> root）
ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | None = None) -> dict:
    """settings.yaml を読み込んで dict で返す。"""
    cfg_path = Path(path) if path else ROOT / "config" / "settings.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_env() -> None:
    """.env を読み込む（存在すれば）。"""
    load_dotenv(ROOT / ".env")


def get_env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)
