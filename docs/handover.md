# 引き継ぎ資料：XのURLを読めるようにする仕組み

新しいClaudeアカウント／新しいセッションがこの作業を引き継ぐための資料。
**このファイルを読めば、前のセッションの会話を読まなくても続きができる**ことを目標にしている。

## このリポジトリは何か

主目的は「AIコンテンツ収益化リサーチ自動化（Phase 1）」。毎日実行して収益化価値の高いネタを
収集・採点・TOP5出力するパイプライン（`main.py` / `src/` / `config/settings.yaml`）。詳細は `README.md`。

そこに後から追加されたのが、**X(Twitter) の投稿URLを読む仕組み**。この資料はその部分の話。

## 何を作ったか

XのURLを会話に貼るだけで、投稿の中身（本文・作者・日時・画像/動画・引用元・添付記事の本文全文）を
取得して読めるようにした。

| ファイル | 役割 |
|---|---|
| `.claude/skills/read-x-post/SKILL.md` | スキル定義。XのURLが会話に出たら自動で発火する |
| `.claude/skills/read-x-post/read_x_post.py` | 実装本体。**標準ライブラリのみ**（他リポジトリにコピーしても動く）|
| `tools/fetch_x_post.py` | 上記への互換CLI入口（`python tools/fetch_x_post.py <URL>`）|
| `tests/test_fetch_x_post.py` | オフラインテスト9件（ネットワーク不要）|
| `README.md` の付録 | 使い方・取得経路・トークンの置き場所 |
| `docs/claude-account-migration.md` | アカウント移行のチェックリスト |

ブランチ: デフォルトは `claude/ai-content-monetization-research-qa5ne4`（**`main` は存在しない**）。
作業ブランチ `claude/translate-x-post-yi8xeb` も同じ内容。両方にpush済み。

## なぜ必要だったか（同じ失敗をしないために）

**XのURLは WebFetch や curl で直接取得できない。** 投稿ページは `402`、記事ページは `404` を返す。
fxtwitter などのミラーもクラウド環境のネットワークポリシーで拒否される。
だから**必ずこのスクリプトを使う**こと。URLを直接fetchしようとして失敗する、を繰り返さない。

## 2つの取得経路

`--source auto`（既定）は API を試して、失敗したら無料経路に落ちる。

| 経路 | 認証 | 費用 | X Articles（長文記事）|
|---|---|---|---|
| X API v2 `GET /2/tweets/{id}` | 下記参照 | $0.005 / Post read | **本文全文が取れる** |
| `cdn.syndication.twimg.com/tweet-result` | 不要 | 無料 | タイトルと冒頭プレビューのみ |

無料経路は埋め込みウィジェットの公開APIで、投稿IDから算出した `token` を要求する。
JS の `Number.prototype.toString(36)` は最短表現ではなく丸め誤差基準で桁を打ち切るため、
V8 の変換手順を Python で再現している（`_to_base36`）。**ここは触らない**。
node と400件のIDで一致を確認済み。

## X Articles の本文について（実測済み）

X公式のOpenAPIでは `article` は `{type: object}` で中身が未定義だが、実測すると次を返す。

| キー | 内容 |
|---|---|
| `title` | 記事タイトル |
| `plain_text` | **本文全文**（実測 7,831文字）|
| `preview_text` | 冒頭プレビュー |
| `entities.code[]` | コードブロック。**`plain_text` には含まれず、位置情報も無い** |
| `entities.tweets[]` / `urls[]` | 埋め込み投稿ID / 記事内リンク |
| `cover_media` / `media_entities[]` | カバー画像 / 記事内メディア |

そのため本文の後ろにコードブロックを列挙する形で出力している。
**コードブロックを本文中の元の位置に戻すことはできない**（APIが位置を返さないため）。

## トークンの設定（記事本文を読むために必要）

置き場所は3通り。**どれか1つでよい**。探索順は ①環境変数 → ②作業ディレクトリから上へ辿った
`.env` → ③`~/.claude/.env`。

| 環境 | 置き方 |
|---|---|
| クラウド環境（安全）| claude.ai/code の環境編集 → **API credentials** → Bearer / `api.x.com` / ヘッダ `Authorization` + prefix `Bearer` + 値。セッションに鍵が渡らない（プロキシが注入）。org admin 権限が必要 |
| クラウド環境（簡単）| 同画面の **Environment variables** に `X_BEARER_TOKEN=...` を1行。権限不要だが値はセッションから見える |
| ローカル | `~/.claude/settings.json` の `env`、または `~/.claude/.env` に `X_BEARER_TOKEN=...` |

**環境変数・credential はセッション起動時に一度だけ読み込まれる。設定を変えたら新しいセッションを開く。**
API credential 方式ではスクリプトは `Authorization` を付けずに送るので、
「トークン未設定＝API不可」と判断してはいけない（常にAPIを試してから無料経路に落ちる実装）。

トークンの発行は https://console.x.com（アプリ → キーとトークン → Bearer Token）。

## X側（console.x.com）で踏んだ落とし穴

1. **アプリが単独だと v2 が使えない** → プロジェクトに接続する必要がある
2. **Free プランのプロジェクトでは投稿の読み取りができない** → **Pay Per Use** のプロジェクトに
   アプリを接続する。`403 client-not-enrolled` が出るのはこれ
3. `GET /2/tweets/{id}` はプロジェクト未接続でも **403 ではなく紛らわしい 503** を返す。
   本当の原因は `curl -H "Authorization: Bearer $X_BEARER_TOKEN" https://api.x.com/2/usage/tweets`
   を叩けば分かる
4. クレジット残高が 0 だと弾かれる。従量課金（サブスク契約は不要）

## 動作確認のしかた

```bash
# いま記事本文まで読める状態かを診断（URL不要。API疎通に $0.005 かかる）
python3 .claude/skills/read-x-post/read_x_post.py --check

# 実際に読む
python3 .claude/skills/read-x-post/read_x_post.py https://x.com/<user>/status/<id>

# オフラインテスト（ネットワーク不要）
python3 tests/test_fetch_x_post.py
```

`--check` の期待出力（トークン設定済みの場合）:

```
トークン : 環境変数 X_BEARER_TOKEN
API経路  : OK（X API v2 が使える → X Articles の本文全文まで読めます）
無料経路 : OK（通常の投稿は読めます。記事は冒頭プレビューまで）
```

## 引き継ぎ時点で未完了のこと

- [ ] **新アカウントでのトークン設定**。旧アカウント（会社アカウント）のクラウド環境の
      環境変数に設定したが、旧セッションのログにトークンが残っているため、
      **console.x.com で再生成してから**新アカウントの環境に入れる
- [ ] `--check` で `API経路: OK` を確認（設定後の新しいセッションで実行すること）
- [ ] 他リポジトリのセッションでも使いたい場合は、スキルを claude.ai にアップロード
      （Settings → Features、コード実行を有効化）。zipは
      `cd .claude/skills && zip -r ../../read-x-post-skill.zip read-x-post -x '*__pycache__*'` で作れる

トークン未設定でも**通常の投稿は問題なく読める**（記事本文だけ冒頭プレビューまで）。急がなくてよい。

## 取れないもの（推測で埋めないこと）

- 非公開(鍵)アカウント・削除済み・年齢制限付きの投稿
- リプライツリーやスレッド全体（単一投稿＋引用/返信元まで）
- X Articles の本文（無料経路のみの場合）

取れなかったときは「取れなかった」と伝える。内容を推測して書かない。
