"""X(Twitter) の投稿URLから内容を取得する（実装は .claude/skills/read-x-post/ に同梱）。

スキルは他リポジトリのセッションからも使えるよう単独で完結させてあるため、
本ファイルは互換用の入口として実装をそのまま読み込むだけにしている。

  python tools/fetch_x_post.py <投稿URL> [--source auto|api|embed] [--json]
"""
from __future__ import annotations

import sys
from pathlib import Path

_SKILL_DIR = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "read-x-post"
sys.path.insert(0, str(_SKILL_DIR))

from read_x_post import (  # noqa: E402,F401  (再エクスポート)
    api_error_hint,
    build_token,
    content_state_to_text,
    extract_tweet_id,
    fetch_api,
    fetch_embed,
    load_post,
    main,
    normalize_api,
    normalize_embed,
    render,
)

if __name__ == "__main__":
    raise SystemExit(main())
