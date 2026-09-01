"""tools/fetch_x_post.py のオフライン検証（ネットワーク不要）。

実行:
  python tests/test_fetch_x_post.py     # そのまま実行
  pytest tests/test_fetch_x_post.py     # pytest でも動く
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.fetch_x_post import build_token, extract_tweet_id, render  # noqa: E402


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


def test_render_expands_urls_and_article():
    data = {
        "id_str": "999",
        "created_at": "2026-08-31T11:00:17.000Z",
        "favorite_count": 12,
        "conversation_count": 3,
        "text": "詳しくはこちら https://t.co/abc",
        "entities": {"urls": [{"url": "https://t.co/abc",
                               "expanded_url": "https://example.com/article"}]},
        "user": {"name": "テスト", "screen_name": "test_user"},
        "article": {"title": "記事タイトル", "rest_id": "777", "preview_text": "冒頭だけ"},
        "mediaDetails": [{"type": "photo", "media_url_https": "https://pbs.twimg.com/x.jpg"}],
    }
    out = render(data)
    assert "https://example.com/article" in out
    assert "https://t.co/abc" not in out
    assert "@test_user" in out
    assert "記事タイトル" in out
    assert "https://pbs.twimg.com/x.jpg" in out


def test_render_prefers_long_form_text():
    data = {
        "id_str": "1",
        "text": "短縮された本文…",
        "note_tweet": {"note_tweet_results": {"result": {"text": "長文投稿の全文"}}},
        "user": {"name": "n", "screen_name": "n"},
    }
    assert "長文投稿の全文" in render(data)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
