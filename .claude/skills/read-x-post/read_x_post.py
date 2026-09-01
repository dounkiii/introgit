"""X(Twitter) の投稿URLから本文・作者・日時・メディア・添付記事を取得して表示する。

標準ライブラリのみで動くため、どのリポジトリ・どのセッションからでも実行できる。

取得経路（既定 auto は上から順に試す）:
  api   : X API v2 `GET /2/tweets/{id}`。X Articles の本文全文が取れる唯一の経路。
          認証は次のどちらでもよい:
            - 環境変数 X_BEARER_TOKEN（または .env）を Authorization に付ける
            - クラウド環境の API credential に api.x.com を登録しておき、
              エージェントプロキシに Authorization を注入させる（セッションに鍵が渡らない）
          従量課金: Post read 1件 $0.005 / 同一リソースは24時間UTC内で重複課金なし。
  embed : `cdn.syndication.twimg.com/tweet-result`（埋め込みウィジェットの公開API）。
          キー不要・無料。X Articles はタイトルと冒頭プレビューまで。

使い方:
  python3 read_x_post.py https://x.com/<user>/status/<id>
  python3 read_x_post.py <id> --source embed
  python3 read_x_post.py <id> --json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SYNDICATION_URL = "https://cdn.syndication.twimg.com/tweet-result"
API_URL = "https://api.x.com/2/tweets/{id}"
BEARER_ENV = "X_BEARER_TOKEN"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

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


def bearer_token() -> tuple[str | None, str]:
    """(トークン, 見つけた場所) を返す。見つからない場合は (None, 説明) を返す。

    探索順:
      1. 環境変数 X_BEARER_TOKEN
         （Claude Code の settings.json の `env` もここに現れる）
      2. 作業ディレクトリから上へ辿って最初に見つかった .env
      3. ~/.claude/.env （マシン全体で1か所にまとめたい場合）

    クラウド環境の API credential を使う構成ではトークンは存在しない。
    その場合はプロキシが Authorization を注入するため、None でもAPIを試す。
    """
    token = (os.getenv(BEARER_ENV) or "").strip()
    if token:
        return token, f"環境変数 {BEARER_ENV}"

    candidates = [d / ".env" for d in [Path.cwd(), *Path.cwd().parents]]
    candidates.append(Path.home() / ".claude" / ".env")
    for env_file in candidates:
        value = _read_env_file(env_file)
        if value:
            return value, str(env_file)
    return None, "未設定（クラウド環境の API credential があればプロキシが付与）"


def _read_env_file(env_file: Path) -> str | None:
    """.env から X_BEARER_TOKEN の値を読む。読めない場合は None。"""
    try:
        if not env_file.is_file():
            return None
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == BEARER_ENV:
                return value.strip().strip('"').strip("'") or None
    except OSError:
        return None
    return None


# --------------------------------------------------------------------------- #
# HTTP（標準ライブラリのみ）
# --------------------------------------------------------------------------- #
def _get_json(url: str, params: dict, headers: dict, timeout: int = 25) -> tuple[int, str]:
    """(ステータス, 本文) を返す。HTTPエラーでも例外にせず本文を読む。"""
    req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def fetch_embed(tweet_id: str, lang: str = "ja") -> dict:
    """埋め込みAPIから投稿データを取得する。"""
    status, body = _get_json(
        SYNDICATION_URL,
        {"id": tweet_id, "token": build_token(tweet_id), "lang": lang},
        {"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    if status != 200:
        raise RuntimeError(f"埋め込みAPI {status}: 削除済み・非公開・年齢制限の可能性があります。")
    return json.loads(body)


def fetch_api(tweet_id: str, token: str | None) -> dict:
    """X API v2 の単一Post取得。article を含む全フィールドを要求する。

    token が None の場合は Authorization を付けずに送る。クラウド環境の
    API credential が設定されていれば、プロキシがヘッダを注入して成功する。
    """
    headers = {"User-Agent": "read-x-post/1.0", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, body = _get_json(
        API_URL.format(id=tweet_id),
        {
            "tweet.fields": API_POST_FIELDS,
            "expansions": API_EXPANSIONS,
            "media.fields": API_MEDIA_FIELDS,
            "user.fields": API_USER_FIELDS,
        },
        headers,
    )
    if status != 200:
        raise RuntimeError(f"X API {status}: {body[:300]}\n  → {api_error_hint(status, body)}")
    return json.loads(body)


def api_error_hint(status: int, body: str) -> str:
    """X API のエラーに対して、実際に踏んだ原因と対処を返す。"""
    if status == 401:
        return (f"認証されていません。{BEARER_ENV} を設定するか、クラウド環境の "
                "API credential に api.x.com を登録してください。")
    if "attached to a Project" in body:
        return ("アプリがプロジェクトに紐付いていません。console.x.com の「プロジェクト」で "
                "Pay Per Use のプロジェクトにアプリを接続してください。")
    if status == 503:
        # GET /2/tweets/{id} はプロジェクト未紐付けでも 403 ではなく 503 を返す。
        return ("一時的な障害か、アプリがプロジェクトに紐付いていない可能性があります。"
                "`curl https://api.x.com/2/usage/tweets` で本当の原因を確認できます。")
    if status in (402, 403, 429) or "credit" in body.lower() or "usage" in body.lower():
        return ("クレジット残高または利用上限に達している可能性があります。"
                "console.x.com の残高と支出上限を確認してください。")
    return "詳細は https://docs.x.com/x-api/fundamentals/errors を参照してください。"


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
            "code_blocks": [],
            "embedded_posts": [],
            "media_count": 0,
            "raw": None,
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
    """API の article オブジェクトからタイトル・本文・付随要素を取り出す。

    実測したレスポンスは title / plain_text / preview_text / cover_media /
    media_entities / entities{code,tweets,urls} を返す。plain_text が本文全文だが
    コードブロックは含まれず entities.code 側に分離されている（位置情報は無い）。
    OpenAPI 上 article は `type: object`（未定義）なので、他の形が返ってきても
    落ちないように content_state / blocks / text も受け付ける。
    """
    art = data.get("article")
    art = art if isinstance(art, dict) else {}
    title_obj = data.get("article_title")
    title = (art.get("title")
             or (title_obj.get("title") if isinstance(title_obj, dict) else title_obj))

    body = None
    if isinstance(art.get("plain_text"), str):
        body = art["plain_text"].strip()
    else:
        content_state = art.get("content_state") or art.get("contentState")
        if isinstance(content_state, dict):
            body = content_state_to_text(content_state)
        elif isinstance(art.get("blocks"), list):
            body = content_state_to_text(art)
        elif isinstance(art.get("text"), str):
            body = art["text"]

    art_entities = art.get("entities") if isinstance(art.get("entities"), dict) else {}
    code_blocks = [c.get("content") or c.get("code", "")
                   for c in art_entities.get("code", []) if isinstance(c, dict)]
    embedded = [t.get("id") for t in art_entities.get("tweets", [])
                if isinstance(t, dict) and t.get("id")]

    return {
        "title": title,
        "url": _article_url(art, data),
        "body": body,
        "preview": art.get("preview_text"),
        "code_blocks": code_blocks,
        "embedded_posts": embedded,
        "media_count": len(art.get("media_entities") or []),
        # 本文が取れなかった場合に中身を確認できるよう、生の article を残す。
        "raw": None if body else (art or None),
    }


def _article_url(art: dict, data: dict) -> str | None:
    """記事URLを決める。article に ID が無い場合は本文中のリンクから拾う。"""
    art_id = art.get("id") or art.get("rest_id")
    if art_id:
        return f"https://x.com/i/article/{art_id}"
    for u in (data.get("entities") or {}).get("urls", []):
        expanded = u.get("expanded_url") or ""
        if "/i/article/" in expanded:
            return expanded
    return None


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
        if btype == "atomic":
            lines.append(_atomic_to_text(block, by_key))
            continue
        lines.append(_BLOCK_PREFIX.get(btype, "") + block.get("text", ""))
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
            return f"![{edata.get('caption') or '画像'}]"
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
            for i, code in enumerate(article.get("code_blocks") or [], 1):
                out += ["", f"--- 記事内のコードブロック {i} ---", code]
            extra = []
            if article.get("media_count"):
                extra.append(f"画像・動画 {article['media_count']}点")
            if article.get("embedded_posts"):
                extra.append("埋め込み投稿 " + ", ".join(
                    f"https://x.com/i/status/{pid}" for pid in article["embedded_posts"]))
            if extra:
                out += ["", "--- 記事内のメディア ---", *[f"  {e}" for e in extra]]
        else:
            if article.get("preview"):
                out += ["冒頭プレビュー:",
                        *[f"  {ln}" for ln in article["preview"].splitlines()]]
            out.append("※ 記事本文の全文は取得できていません"
                       "（embed経路の制限。X API経路なら本文全文が取れます）。")
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
    """(正規化済みデータ, 生レスポンス) を返す。source は auto / api / embed。

    auto はまずAPIを試す。トークンが無くてもプロキシがヘッダを注入する構成があるため、
    「トークン未設定＝API不可」とは判断しない。
    """
    if source in ("auto", "api"):
        try:
            raw = fetch_api(tweet_id, bearer_token()[0])
            if raw.get("data"):
                return normalize_api(raw), raw
            raise RuntimeError(
                f"X API がPostを返しませんでした: {json.dumps(raw, ensure_ascii=False)[:300]}")
        except Exception as exc:  # noqa: BLE001
            if source == "api":
                raise
            print(f"注記: X API 経路が使えないため埋め込みAPIに切り替えます: {exc}",
                  file=sys.stderr)

    raw = fetch_embed(tweet_id, lang=lang)
    if not raw or raw.get("__typename") == "TweetTombstone":
        raise RuntimeError("投稿を取得できませんでした（削除済み・非公開・年齢制限の可能性）。")
    return normalize_embed(raw), raw


def check_setup() -> int:
    """いまこのセッションで記事本文まで読めるかを実際に叩いて確かめる。"""
    token, where = bearer_token()
    print(f"トークン : {where}")
    print("API経路  : ", end="", flush=True)
    try:
        # 記事付きの投稿ではなく軽い既知の投稿で認証だけを確認する。
        fetch_api("20", token)
        print("OK（X API v2 が使える → X Articles の本文全文まで読めます）")
        api_ok = True
    except Exception as exc:  # noqa: BLE001
        print(f"NG\n  {exc}")
        api_ok = False

    print("無料経路 : ", end="", flush=True)
    try:
        fetch_embed("20", lang="en")
        print("OK（通常の投稿は読めます。記事は冒頭プレビューまで）")
    except Exception as exc:  # noqa: BLE001
        print(f"NG\n  {exc}")
        return 1

    if not api_ok:
        print("\n記事本文まで読めるようにするには、次のどれか1つを設定してください:")
        print("  - クラウド環境の API credential: Bearer / api.x.com / "
              "Authorization + Bearer（セッションに鍵が渡らない）")
        print(f"  - クラウド環境の Environment variables に {BEARER_ENV}=...")
        print(f"  - ローカル: ~/.claude/settings.json の env、または ~/.claude/.env に "
              f"{BEARER_ENV}=...")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="X(Twitter) の投稿URLから内容を取得する")
    ap.add_argument("url", nargs="?", help="投稿URL または 投稿ID")
    ap.add_argument("--check", action="store_true",
                    help="取得経路と認証の状態を診断する（URLは不要）")
    ap.add_argument("--source", choices=("auto", "api", "embed"), default="auto",
                    help="取得経路（既定: auto = API を試し、失敗したら embed）")
    ap.add_argument("--json", action="store_true", help="整形せずJSONをそのまま出力")
    ap.add_argument("--lang", default="ja", help="embed経路の取得言語（既定: ja）")
    args = ap.parse_args(argv)

    if args.check:
        return check_setup()
    if not args.url:
        ap.error("投稿URL または 投稿ID を指定してください（診断は --check）")

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
