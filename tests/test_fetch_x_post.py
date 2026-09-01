"""tools/fetch_x_post.py のオフライン検証（ネットワーク不要）。

実行:
  python tests/test_fetch_x_post.py     # そのまま実行
  pytest tests/test_fetch_x_post.py     # pytest でも動く
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.fetch_x_post import (  # noqa: E402
    api_error_hint,
    build_token,
    content_state_to_text,
    extract_tweet_id,
    normalize_api,
    normalize_embed,
    render,
)


def test_extract_tweet_id():
    cases = {
        "https://x.com/user/status/2094379745777684618": "2094379745777684618",
        "https://twitter.com/user/status/123456789012345?s=20&t=abc": "123456789012345",
        "https://x.com/i/web/status/123456789012345": "123456789012345",
        "x.com/user/statuses/123456789012345": "123456789012345",
        "123456789012345": "123456789012345",
    }
    for url, expected in cases.items():
        assert extract_tweet_id(url) == expected, url

    for bad in ["https://example.com/foo", "https://x.com/user", ""]:
        try:
            extract_tweet_id(bad)
        except ValueError:
            continue
        raise AssertionError(f"例外が出るべき入力: {bad!r}")


def test_build_token():
    """埋め込みAPIが要求する token（JS の toString(36) 相当）と一致すること。"""
    assert build_token("20") == "6dq1a2xwd93"
    assert build_token("1") == "bhi2ay3f28n"
    assert build_token("2094379745777684618") == "52roroepmqq"
    assert build_token("1234567890123456789") == "2zqic77uqyk"


def test_normalize_embed():
    raw = {
        "id_str": "999",
        "created_at": "2026-08-31T11:00:17.000Z",
        "favorite_count": 12,
        "conversation_count": 3,
        "text": "詳しくはこちら https://t.co/abc",
        "entities": {"urls": [{"url": "https://t.co/abc",
                               "expanded_url": "https://example.com/article"}]},
        "user": {"name": "テスト", "screen_name": "test_user"},
        "article": {"title": "記事タイトル", "rest_id": "777", "preview_text": "冒頭だけ"},
        "mediaDetails": [
            {"type": "photo", "media_url_https": "https://pbs.twimg.com/x.jpg"},
            {"type": "video", "media_url_https": "https://pbs.twimg.com/thumb.jpg",
             "video_info": {"variants": [
                 {"content_type": "video/mp4", "bitrate": 100, "url": "low.mp4"},
                 {"content_type": "video/mp4", "bitrate": 900, "url": "high.mp4"},
             ]}},
        ],
        "quoted_tweet": {"user": {"screen_name": "quoted_user"}, "text": "引用元の本文"},
    }
    post = normalize_embed(raw)
    assert post["source"] == "embed"
    assert post["author_handle"] == "test_user"
    assert post["text"] == "詳しくはこちら https://example.com/article"
    assert post["media"] == [
        {"kind": "photo", "url": "https://pbs.twimg.com/x.jpg"},
        {"kind": "video", "url": "high.mp4"},
    ]
    assert post["article"]["url"] == "https://x.com/i/article/777"
    assert post["article"]["body"] is None          # embed経路は本文を返さない
    assert post["quoted"]["author"] == "@quoted_user"

    out = render(post)
    assert "https://t.co/abc" not in out
    assert "記事タイトル" in out and "冒頭だけ" in out
    assert "high.mp4" in out


def test_normalize_embed_prefers_long_form_text():
    raw = {
        "id_str": "1",
        "text": "短縮された本文…",
        "note_tweet": {"note_tweet_results": {"result": {"text": "長文投稿の全文"}}},
        "user": {"name": "n", "screen_name": "n"},
    }
    assert normalize_embed(raw)["text"] == "長文投稿の全文"


def test_normalize_api_with_article_body():
    raw = {
        "data": {
            "id": "999",
            "author_id": "42",
            "created_at": "2026-08-31T11:00:17.000Z",
            "text": "記事を書きました https://t.co/abc",
            "entities": {"urls": [{"url": "https://t.co/abc",
                                   "expanded_url": "https://x.com/i/article/777"}]},
            "public_metrics": {"like_count": 5, "retweet_count": 1,
                               "reply_count": 2, "impression_count": 100},
            "attachments": {"media_keys": ["k1"]},
            "referenced_posts": [{"type": "quoted", "id": "555"}],
            "article": {
                "id": "777",
                "title": "記事タイトル",
                "content_state": {
                    "blocks": [
                        {"type": "header-one", "text": "見出し"},
                        {"type": "unstyled", "text": "本文の段落"},
                        {"type": "unordered-list-item", "text": "箇条書き"},
                        {"type": "atomic", "text": " ",
                         "entity_ranges": [{"key": 0, "offset": 0, "length": 1}]},
                    ],
                    "entities": [
                        {"key": "0", "value": {"type": "markdown",
                                               "data": {"markdown": "```py\\nprint(1)\\n```"}}},
                    ],
                },
            },
        },
        "includes": {
            "users": [{"id": "42", "name": "テスト", "username": "test_user"},
                      {"id": "43", "name": "引用", "username": "quoted_user"}],
            "media": [{"media_key": "k1", "type": "photo",
                       "url": "https://pbs.twimg.com/x.jpg"}],
            "tweets": [{"id": "555", "author_id": "43", "text": "引用元の本文"}],
        },
    }
    post = normalize_api(raw)
    assert post["source"] == "api"
    assert post["author_handle"] == "test_user"
    assert post["text"] == "記事を書きました https://x.com/i/article/777"
    assert post["metrics"]["♥"] == 5
    assert post["media"] == [{"kind": "photo", "url": "https://pbs.twimg.com/x.jpg"}]
    assert post["article"]["title"] == "記事タイトル"
    assert post["article"]["url"] == "https://x.com/i/article/777"
    assert "# 見出し" in post["article"]["body"]
    assert "- 箇条書き" in post["article"]["body"]
    assert "print(1)" in post["article"]["body"]
    assert post["article"]["raw"] is None           # 本文が取れたので生データは持たない
    assert post["quoted"] == {"author": "@quoted_user", "text": "引用元の本文"}
    assert "記事本文" in render(post)


def test_normalize_api_unknown_article_shape_keeps_raw():
    """article の構造が想定外でも落ちず、中身を確認できる形で残すこと。"""
    raw = {"data": {"id": "1", "text": "t",
                    "article": {"something_new": {"nested": 1}}},
           "includes": {}}
    post = normalize_api(raw)
    assert post["article"]["body"] is None
    assert post["article"]["raw"] == {"something_new": {"nested": 1}}
    assert "article の中身" in render(post)


def test_api_error_hint():
    """踏んだエラーごとに、次にやることが分かる文言を返すこと。"""
    assert "Bearer Token を再生成" in api_error_hint(401, "Unauthorized")
    body = ('{"client_id":"1","detail":"you must use keys and tokens from a '
            'developer App that is attached to a Project."}')
    assert "プロジェクト" in api_error_hint(403, body)
    # GET /2/tweets/{id} はプロジェクト未紐付けでも 503 を返す
    assert "紐付いていない" in api_error_hint(503, '{"detail":"Service Unavailable"}')
    assert "クレジット" in api_error_hint(402, '{"detail":"insufficient credit"}')


def test_content_state_to_text_atomic_entities():
    cs = {
        "blocks": [
            {"type": "atomic", "text": " ", "entity_ranges": [{"key": 0}]},
            {"type": "atomic", "text": " ", "entity_ranges": [{"key": 1}]},
            {"type": "atomic", "text": " ", "entity_ranges": [{"key": 2}]},
            {"type": "blockquote", "text": "引用"},
        ],
        "entities": [
            {"key": "0", "value": {"type": "image", "data": {"caption": "図1"}}},
            {"key": "1", "value": {"type": "post", "data": {"post_id": "123"}}},
            {"key": "2", "value": {"type": "divider", "data": {}}},
        ],
    }
    text = content_state_to_text(cs)
    assert "![図1]" in text
    assert "123" in text
    assert "---" in text
    assert "> 引用" in text


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
