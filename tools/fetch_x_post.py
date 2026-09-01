"""X(Twitter) の投稿URLから本文・作者・日時・メディア等を取得して表示する。

Xは未ログインのHTTP取得を拒否する（402/404）ため、本文を直接スクレイピングできない。
本ツールは埋め込みウィジェット（publish.x.com の Embedded Tweet）が公開利用している
`cdn.syndication.twimg.com/tweet-result` エンドポイントを使う。認証キーは不要。

使い方:
  python tools/fetch_x_post.py https://x.com/<user>/status/<id>
  python tools/fetch_x_post.py <id> --json
  python tools/fetch_x_post.py <url> --lang en

制限:
  - 非公開(鍵)アカウント・削除済み・年齢制限付き投稿は取得できない（404）。
  - X Articles（長文記事）はタイトルと冒頭プレビューのみ公開されており、
    本文全体はログインが必要なため取得できない。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests  # noqa: E402

from src.utils.http import get_json  # noqa: E402

SYNDICATION_URL = "https://cdn.syndication.twimg.com/tweet-result"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_ID_RE = re.compile(r"(?:status(?:es)?|/i/web/status)/(\d+)")
_BARE_ID_RE = re.compile(r"^\d{1,25}$")


def extract_tweet_id(url_or_id: str) -> str:
    """投稿URL（x.com / twitter.com / i/web/status）またはID文字列からIDを取り出す。"""
    s = url_or_id.strip()
    if _BARE_ID_RE.match(s):
        return s
    m = _ID_RE.search(s)
    if not m:
        raise ValueError(f"投稿IDを判別できません: {url_or_id!r}")
    return m.group(1)


def build_token(tweet_id: str) -> str:
    """埋め込みAPIが要求する token を投稿IDから算出する（クライアント側と同じ計算）。

    JS: ((id / 1e15) * Math.PI).toString(36).replace(/(0+|\\.)/g, "")
    """
    value = (int(tweet_id) / 1e15) * math.pi
    return re.sub(r"(0+|\.)", "", _to_base36(value))


def _to_base36(value: float) -> str:
    """Number.prototype.toString(36) と同じ文字列を作る（V8 DoubleToRadixCString 相当）。

    JS実装は「最短表現」ではなく丸め誤差(delta)を基準に桁を打ち切るため、
    単純な基数変換では末尾1桁がずれる。tokenを一致させるため手順を再現する。
    """
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    integer = math.floor(value)
    fraction = value - integer
    delta = max(math.nextafter(0.0, 1.0),
                0.5 * (math.nextafter(value, math.inf) - value))

    tail: list[str] = []
    if fraction >= delta:
        while True:
            fraction *= 36
            delta *= 36
            digit = int(fraction)
            tail.append(digits[digit])
            fraction -= digit
            if fraction > 0.5 or (fraction == 0.5 and digit & 1):
                if fraction + delta > 1:
                    if _carry(tail, digits):
                        integer += 1
                    break
            if fraction < delta:
                break

    head = ""
    n = int(integer)
    if n == 0:
        head = "0"
    while n:
        head = digits[n % 36] + head
        n //= 36
    return head + ("." + "".join(tail) if tail else "")


def _carry(tail: list[str], digits: str) -> bool:
    """最下位桁からの桁上げを伝播させる。整数部へ繰り上がる場合 True を返す。"""
    while tail:
        d = digits.index(tail[-1]) + 1
        if d < 36:
            tail[-1] = digits[d]
            return False
        tail.pop()
    return True


def fetch_post(tweet_id: str, lang: str = "ja") -> dict:
    """埋め込みAPIから投稿データ(JSON)を取得する。

    404（削除済み・非公開など）は再試行しても結果が変わらないため即座に投げ返し、
    通信レベルの一時的な失敗だけを再試行する。
    """
    params = {"id": tweet_id, "token": build_token(tweet_id), "lang": lang}
    try:
        return get_json(SYNDICATION_URL, user_agent=USER_AGENT, params=params, retries=0)
    except requests.HTTPError:
        raise
    except requests.RequestException:
        return get_json(SYNDICATION_URL, user_agent=USER_AGENT, params=params, retries=1)


def _expanded_text(data: dict) -> str:
    """t.co の短縮URLを展開した本文を返す。長文投稿は note_tweet 側を優先する。"""
    note = (data.get("note_tweet") or {}).get("note_tweet_results", {}).get("result", {})
    text = note.get("text") or data.get("text") or ""
    for u in (data.get("entities") or {}).get("urls", []):
        if u.get("url") and u.get("expanded_url"):
            text = text.replace(u["url"], u["expanded_url"])
    return text.strip()


def _media_lines(data: dict) -> list[str]:
    lines = []
    for m in (data.get("mediaDetails") or []):
        kind = m.get("type", "media")
        url = m.get("media_url_https", "")
        if kind in ("video", "animated_gif"):
            variants = (m.get("video_info") or {}).get("variants", [])
            mp4 = [v for v in variants if v.get("content_type") == "video/mp4"]
            if mp4:
                url = max(mp4, key=lambda v: v.get("bitrate", 0))["url"]
        lines.append(f"  - {kind}: {url}")
    return lines


def render(data: dict) -> str:
    """人が読める形に整形する。"""
    user = data.get("user") or {}
    out = [
        f"投稿者 : {user.get('name', '?')} (@{user.get('screen_name', '?')})",
        f"日時   : {data.get('created_at', '?')}",
        f"URL    : https://x.com/{user.get('screen_name', 'i')}/status/{data.get('id_str', '')}",
        f"反応   : ♥{data.get('favorite_count', 0)} / 返信・引用 {data.get('conversation_count', 0)}",
        "",
        "--- 本文 ---",
        _expanded_text(data) or "(本文なし)",
    ]

    media = _media_lines(data)
    if media:
        out += ["", "--- メディア ---", *media]

    poll = data.get("card", {}).get("binding_values") if data.get("card") else None
    if poll:
        choices = [f"  - {v.get('string_value')}" for k, v in poll.items()
                   if k.endswith("_label") and isinstance(v, dict)]
        if choices:
            out += ["", "--- 投票 ---", *choices]

    article = data.get("article") or {}
    if article:
        out += [
            "",
            "--- 添付記事 (X Articles) ---",
            f"タイトル : {article.get('title', '?')}",
            f"記事URL  : https://x.com/i/article/{article.get('rest_id', '')}",
            "冒頭プレビュー:",
            *[f"  {line}" for line in (article.get("preview_text") or "").splitlines()],
            "※ 記事本文の全文はログインが必要なため未ログインでは取得できません。",
        ]

    quoted = data.get("quoted_tweet")
    if quoted:
        qu = quoted.get("user") or {}
        out += [
            "",
            f"--- 引用元 (@{qu.get('screen_name', '?')}) ---",
            _expanded_text(quoted) or "(本文なし)",
        ]

    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="X(Twitter) の投稿URLから内容を取得する")
    ap.add_argument("url", help="投稿URL または 投稿ID")
    ap.add_argument("--json", action="store_true", help="整形せずJSONをそのまま出力")
    ap.add_argument("--lang", default="ja", help="取得言語（既定: ja）")
    args = ap.parse_args(argv)

    try:
        tweet_id = extract_tweet_id(args.url)
    except ValueError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 2

    try:
        data = fetch_post(tweet_id, lang=args.lang)
    except Exception as exc:  # noqa: BLE001
        print(f"取得に失敗しました (id={tweet_id}): {exc}", file=sys.stderr)
        print("鍵アカウント・削除済み・年齢制限付きの投稿は取得できません。", file=sys.stderr)
        return 1

    if not data or data.get("__typename") == "TweetTombstone":
        print(f"投稿を取得できませんでした (id={tweet_id})。"
              "削除済み・非公開・年齢制限のいずれかの可能性があります。", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
