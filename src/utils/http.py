"""HTTP 取得の共通ヘルパー。タイムアウト・UA・簡易リトライを一元管理。"""
from __future__ import annotations

import time

import requests


def get_json(url: str, *, user_agent: str, timeout: int = 20, params: dict | None = None,
             retries: int = 2):
    """JSON を取得して返す。失敗時は例外を投げる（呼び出し側で捕捉）。"""
    headers = {"User-Agent": user_agent, "Accept": "application/json"}
    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last_exc


def get_text(url: str, *, user_agent: str, timeout: int = 20, retries: int = 2) -> str:
    headers = {"User-Agent": user_agent}
    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last_exc
