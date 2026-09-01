"""X(Twitter) の投稿URLから本文・作者・日時・メディア・添付記事を取得して表示する。

取得経路は2つあり、既定では使える方を自動選択する（--source で固定可）。

  api   : X API v2 `GET /2/tweets/{id}`（環境変数 X_BEARER_TOKEN が必要）
          X Articles の本文取得を狙う経路。従量課金（Post read 1件あたり $0.005、
          同一リソースは24時間UTC内で重複課金なし）。
  embed : 埋め込みウィジェットが公開利用している
          `cdn.syndication.twimg.com/tweet-result`。キー不要・無料。
          ただし X Articles はタイトルと冒頭プレビューまで。

使い方:
  python tools/fetch_x_post.py https://x.com/<user>/status/<id>
  python tools/fetch_x_post.py <id> --source api        # API を明示
  python tools/fetch_x_post.py <id> --json              # 生JSONをそのまま出力

制限:
  - 非公開(鍵)アカウント・削除済み・年齢制限付き投稿は取得できない。
  - embed 経路では X Articles の記事本文の全文は取得できない（ログインが必要）。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests  # noqa: E402

from src.utils.config import load_env  # noqa: E402
from src.utils.http import get_json  # noqa: E402

SYNDICATION_URL = "https://cdn.syndication.twimg.com/tweet-result"
API_URL = "https://api.x.com/2/tweets/{id}"
BEARER_ENV = "X_BEARER_TOKEN"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# API から要求するフィールド。article / article_title が X Articles 用。
API_POST_FIELDS = (
    "article,article_title,created_at,display_text_range,entities,lang,note_post,"
    "possibly_sensitive,public_metrics,referenced_posts"
)
API_EXPANSIONS = (
    "author_id,attachments.media_keys,referenced_posts,article.cover_media,"
    "article.media_entities"
)
API_MEDIA_FIELDS = "type,url,variants,preview_image_url,alt_text"
API_USER_FIELDS = "name,username"

_ID_RE = re.compile(r"(?:status(?:es)?|/i/web/status)/(\d+)")
_BARE_ID_RE = re.compile(r"^\d{1,25}$")


# --------------------------------------------------------------------------- #
# URL / token
# --------------------------------------------------------------------------- #
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


def bearer_token() -> str | None:
    """X API のトークンを .env / 環境変数から取得する。"""
    load_env()
    token = (os.getenv(BEARER_ENV) or "").strip()
    return token or None


# --------------------------------------------------------------------------- #
# 取得（embed 経路）
# --------------------------------------------------------------------------- #
def fetch_embed(tweet_id: str, lang: str = "ja") -> dict:
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


# --------------------------------------------------------------------------- #
# 取得（X API v2 経路）
# --------------------------------------------------------------------------- #
def fetch_api(tweet_id: str, token: str) -> dict:
    """X API v2 の単一Post取得。article を含む全フィールドを要求する。"""
    resp = requests.get(
        API_URL.format(id=tweet_id),
        headers={"Authorization": f"Bearer {token}", "User-Agent": "fetch-x-post/1.0"},
        params={
            "tweet.fields": API_POST_FIELDS,
            "expansions": API_EXPANSIONS,
            "media.fields": API_MEDIA_FIELDS,
            "user.fields": API_USER_FIELDS,
        },
        timeout=25,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"X API {resp.status_code}: {resp.text[:300]}")
    return resp.json()


# --------------------------------------------------------------------------- #
# 正規化（両経路を同じ形に揃える）
# --------------------------------------------------------------------------- #
def _expand_urls(text: str, entities: dict | None) -> str:
    """t.co の短縮URLを展開する。"""
    for u in (entities or {}).get("urls", []):
        short, full = u.get("url"), u.get("expanded_url")
        if short and full:
            text = text.replace(short, full)
    return text


def normalize_embed(raw: dict) -> dict:
    """埋め込みAPIのレスポンスを共通形式に変換する。"""
    user = raw.get("user") or {}
    note = (raw.get("note_tweet") or {}).get("note_tweet_results", {}).get("result", {})
    text = note.get("text") or raw.get("text") or ""

    media = []
    for m in raw.get("mediaDetails") or []:
        kind = m.get("type", "media")
        url = m.get("media_url_https", "")
        if kind in ("video", "animated_gif"):
            mp4 = [v for v in (m.get("video_info") or {}).get("variants", [])
                   if v.get("content_type") == "video/mp4"]
            if mp4:
                url = max(mp4, key=lambda v: v.get("bitrate", 0))["url"]
        media.append({"kind": kind, "url": url})

    article = None
    if raw.get("article"):
        a = raw["article"]
        article = {
            "title": a.get("title"),
            "url": f"https://x.com/i/article/{a.get('rest_id', '')}",
            "body": None,
            "preview": a.get("preview_text"),
        }

    quoted = None
    if raw.get("quoted_tweet"):
        q = raw["quoted_tweet"]
        qu = q.get("user") or {}
        quoted = {
            "author": f"@{qu.get('screen_name', '?')}",
            "text": _expand_urls(q.get("text") or "", q.get("entities")),
        }

    return {
        "source": "embed",
        "id": raw.get("id_str", ""),
        "author_name": user.get("name"),
        "author_handle": user.get("screen_name"),
        "created_at": raw.get("created_at"),
        "text": _expand_urls(text, raw.get("entities")).strip(),
        "metrics": {"♥": raw.get("favorite_count"),
                    "返信・引用": raw.get("conversation_count")},
        "media": media,
        "article": article,
        "quoted": quoted,
    }


def normalize_api(raw: dict) -> dict:
    """X API v2 のレスポンスを共通形式に変換する。"""
    data = raw.get("data") or {}
    includes = raw.get("includes") or {}
    users = {u["id"]: u for u in includes.get("users", [])}
    media_by_key = {m["media_key"]: m for m in includes.get("media", [])}
    posts_by_id = {p["id"]: p for p in includes.get("tweets", [])
                   or includes.get("posts", [])}

    author = users.get(data.get("author_id"), {})
    note = data.get("note_post") or data.get("note_tweet") or {}
    text = note.get("text") or data.get("text") or ""

    media = []
    for key in (data.get("attachments") or {}).get("media_keys", []):
        m = media_by_key.get(key, {})
        kind = m.get("type", "media")
        url = m.get("url") or m.get("preview_image_url", "")
        if kind in ("video", "animated_gif"):
            mp4 = [v for v in m.get("variants", []) if v.get("content_type") == "video/mp4"]
            if mp4:
                url = max(mp4, key=lambda v: v.get("bit_rate", 0)).get("url", url)
        media.append({"kind": kind, "url": url})

    article = None
    if data.get("article") or data.get("article_title"):
        article = _normalize_api_article(data)

    quoted = None
    for ref in data.get("referenced_posts") or data.get("referenced_tweets") or []:
        if ref.get("type") in ("quoted", "replied_to"):
            q = posts_by_id.get(ref.get("id"))
            if q:
                qa = users.get(q.get("author_id"), {})
                quoted = {
                    "author": "@" + qa.get("username", "?"),
                    "text": _expand_urls(q.get("text") or "", q.get("entities")),
                }
            break

    metrics = data.get("public_metrics") or {}
    return {
        "source": "api",
        "id": data.get("id", ""),
        "author_name": author.get("name"),
        "author_handle": author.get("username"),
        "created_at": data.get("created_at"),
        "text": _expand_urls(text, data.get("entities")).strip(),
        "metrics": {"♥": metrics.get("like_count"),
                    "リポスト": metrics.get("retweet_count"),
                    "返信": metrics.get("reply_count"),
                    "表示": metrics.get("impression_count")},
        "media": media,
        "article": article,
        "quoted": quoted,
    }


def _normalize_api_article(data: dict) -> dict:
    """API の article オブジェクトからタイトルと本文を取り出す。

    article の内部構造は OpenAPI 上 `type: object`（未定義）なので、
    公開されている content_state 形式と素朴な形の両方を受けられるようにする。
    """
    art = data.get("article")
    art = art if isinstance(art, dict) else {}
    title_obj = data.get("article_title")
    title = (art.get("title")
             or (title_obj.get("title") if isinstance(title_obj, dict) else title_obj))

    content_state = art.get("content_state") or art.get("contentState")
    body = None
    if isinstance(content_state, dict):
        body = content_state_to_text(content_state)
    elif isinstance(art.get("blocks"), list):
        body = content_state_to_text(art)
    elif isinstance(art.get("text"), str):
        body = art["text"]

    art_id = art.get("id") or art.get("rest_id")
    return {
        "title": title,
        "url": f"https://x.com/i/article/{art_id}" if art_id else None,
        "body": body,
        "preview": art.get("preview_text"),
        # 本文が取れなかった場合に中身を確認できるよう、生の article を残す。
        "raw": None if body else (art or None),
    }


_BLOCK_PREFIX = {
    "header-one": "# ",
    "header-two": "## ",
    "header-three": "### ",
    "unordered-list-item": "- ",
    "ordered-list-item": "1. ",
    "blockquote": "> ",
}


def content_state_to_text(content_state: dict) -> str:
    """Articles の content_state（DraftJS形式）をMarkdown風テキストに変換する。"""
    entities = content_state.get("entities") or []
    by_key: dict[str, dict] = {}
    for e in entities:
        if isinstance(e, dict) and "key" in e:
            by_key[str(e["key"])] = e.get("value") or {}

    lines: list[str] = []
    for block in content_state.get("blocks") or []:
        btype = block.get("type", "unstyled")
        text = block.get("text", "")
        if btype == "atomic":
            lines.append(_atomic_to_text(block, by_key))
            continue
        lines.append(_BLOCK_PREFIX.get(btype, "") + text)
    return "\n".join(lines).strip()


def _atomic_to_text(block: dict, by_key: dict[str, dict]) -> str:
    """atomic ブロック（画像・埋め込み投稿・Markdown・区切り線など）を文字列にする。"""
    for rng in block.get("entity_ranges") or []:
        value = by_key.get(str(rng.get("key")), {})
        etype = value.get("type")
        edata = value.get("data") or {}
        if etype == "markdown":
            return edata.get("markdown", "")
        if etype == "image":
            caption = edata.get("caption") or "画像"
            return f"![{caption}]"
        if etype == "post":
            return f"[埋め込み投稿 https://x.com/i/status/{edata.get('post_id', '')}]"
        if etype == "link":
            return edata.get("url", "")
        if etype == "divider":
            return "---"
        if etype == "latex":
            return f"$$ {block.get('text', '').strip()} $$"
    return block.get("text", "").strip()


# --------------------------------------------------------------------------- #
# 表示
# --------------------------------------------------------------------------- #
def render(post: dict) -> str:
    """正規化済みデータを人が読める形に整形する。"""
    handle = post.get("author_handle") or "i"
    metrics = " / ".join(f"{k} {v}" for k, v in (post.get("metrics") or {}).items()
                         if v is not None)
    out = [
        f"投稿者 : {post.get('author_name') or '?'} (@{handle})",
        f"日時   : {post.get('created_at') or '?'}",
        f"URL    : https://x.com/{handle}/status/{post.get('id', '')}",
    ]
    if metrics:
        out.append(f"反応   : {metrics}")
    out += ["取得元 : " + ("X API v2" if post.get("source") == "api"
                          else "埋め込みAPI (cdn.syndication.twimg.com)"),
            "", "--- 本文 ---", post.get("text") or "(本文なし)"]

    if post.get("media"):
        out += ["", "--- メディア ---"]
        out += [f"  - {m['kind']}: {m['url']}" for m in post["media"]]

    article = post.get("article")
    if article:
        out += ["", "--- 添付記事 (X Articles) ---",
                f"タイトル : {article.get('title') or '?'}"]
        if article.get("url"):
            out.append(f"記事URL  : {article['url']}")
        if article.get("body"):
            out += ["", "--- 記事本文 ---", article["body"]]
        else:
            if article.get("preview"):
                out += ["冒頭プレビュー:",
                        *[f"  {ln}" for ln in article["preview"].splitlines()]]
            out.append("※ 記事本文の全文は取得できていません"
                       "（embed経路の制限。X API経路なら article フィールドを参照）。")
            if article.get("raw"):
                out += ["  APIが返した article の中身:",
                        *[f"  {ln}" for ln in
                          json.dumps(article["raw"], ensure_ascii=False,
                                     indent=1).splitlines()[:40]]]

    if post.get("quoted"):
        out += ["", f"--- 引用元 ({post['quoted']['author']}) ---",
                post["quoted"]["text"] or "(本文なし)"]

    return "\n".join(out)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def load_post(tweet_id: str, source: str = "auto", lang: str = "ja") -> tuple[dict, dict]:
    """(正規化済みデータ, 生レスポンス) を返す。source は auto / api / embed。"""
    token = bearer_token()

    if source == "api" or (source == "auto" and token):
        if not token:
            raise RuntimeError(
                f"X API を使うには環境変数 {BEARER_ENV} が必要です（.env に設定可）。")
        try:
            raw = fetch_api(tweet_id, token)
            if raw.get("data"):
                return normalize_api(raw), raw
            detail = json.dumps(raw, ensure_ascii=False)[:300]
            raise RuntimeError(f"X API がPostを返しませんでした: {detail}")
        except Exception as exc:  # noqa: BLE001
            if source == "api":
                raise
            print(f"警告: X API 経路が失敗したため埋め込みAPIに切り替えます: {exc}",
                  file=sys.stderr)

    raw = fetch_embed(tweet_id, lang=lang)
    if not raw or raw.get("__typename") == "TweetTombstone":
        raise RuntimeError("投稿を取得できませんでした（削除済み・非公開・年齢制限の可能性）。")
    return normalize_embed(raw), raw


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="X(Twitter) の投稿URLから内容を取得する")
    ap.add_argument("url", help="投稿URL または 投稿ID")
    ap.add_argument("--source", choices=("auto", "api", "embed"), default="auto",
                    help="取得経路（既定: auto = トークンがあれば api、無ければ embed）")
    ap.add_argument("--json", action="store_true", help="整形せずJSONをそのまま出力")
    ap.add_argument("--lang", default="ja", help="embed経路の取得言語（既定: ja）")
    args = ap.parse_args(argv)

    try:
        tweet_id = extract_tweet_id(args.url)
    except ValueError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 2

    try:
        post, raw = load_post(tweet_id, source=args.source, lang=args.lang)
    except Exception as exc:  # noqa: BLE001
        print(f"取得に失敗しました (id={tweet_id}): {exc}", file=sys.stderr)
        return 1

    print(json.dumps(raw, ensure_ascii=False, indent=2) if args.json else render(post))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
