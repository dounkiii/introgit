---
name: read-x-post
description: X(Twitter) の投稿・ツイートURLが共有されたら、その中身（本文・作者・日時・画像/動画・引用元・添付されたX Articlesの本文全文）を取得して読む。x.com / twitter.com のURL、`x.com/i/web/status/...`、投稿IDが会話に出てきたとき、また「このポスト読んで」「このツイート要約して/翻訳して」と頼まれたときに使う。Xは未ログインのHTTP取得を拒否するため、URLを直接fetchしても読めない。
allowed-tools: Bash
---

# XのポストをURLから読む

X(Twitter) は未ログインのHTTP取得を拒否する（投稿ページは `402`、記事ページは `404`）。
WebFetch や curl でURLを開いても中身は取れないので、**必ず同梱のスクリプトを使う**。

## 使い方

```bash
python3 "$CLAUDE_SKILL_DIR/read_x_post.py" <投稿URL>
```

`$CLAUDE_SKILL_DIR` が使えない場合は、このSKILL.mdと同じディレクトリの
`read_x_post.py` を絶対パスで指定する。標準ライブラリだけで動くので追加インストールは不要。

主なオプション:

| オプション | 用途 |
|---|---|
| `--source embed` | X API を使わず無料経路に固定する（課金を避けたいとき）|
| `--source api` | API 経路に固定し、失敗を隠さず出す（切り分け用）|
| `--json` | 生レスポンスをそのまま出す（表示が想定と違うときの確認用）|

入力は `https://x.com/<user>/status/<id>` / `twitter.com/...` /
`x.com/i/web/status/<id>` / 数値IDのみ、いずれも可（クエリ文字列付きも可）。

複数URLが共有されたら、1件ずつ順に実行する。

## 出力の読み方

本文は `t.co` を展開済み、長文投稿（note post）は全文が出る。
添付記事（X Articles）がある投稿は `--- 記事本文 ---` に全文が続き、その後ろに
`--- 記事内のコードブロック N ---` が並ぶ。**コードブロックは本文中の元の位置には
戻せない**（API が位置情報を返さない）ので、要約するときは「本文の該当箇所で使う
プロンプト」として扱う。

## 2つの取得経路

既定（`auto`）は X API を試し、失敗したら埋め込みAPIに落ちる。

| 経路 | 認証 | 費用 | X Articles |
|---|---|---|---|
| X API v2 `GET /2/tweets/{id}` | 下記のいずれか | $0.005 / Post | **本文全文が取れる** |
| `cdn.syndication.twimg.com` | 不要 | 無料 | タイトルと冒頭プレビューのみ |

API 経路の認証は2通りある。どちらも無い環境では自動的に無料経路になる。

1. **クラウド環境の API credential**（推奨・セッションに鍵が渡らない）
   claude.ai/code の環境編集 → **API credentials** → Add credential →
   種別 Bearer / Allowed websites `api.x.com` / ヘッダ `Authorization` +
   prefix `Bearer` + 値にトークン。以後そのenv内の全セッションで有効。
2. **環境変数 `X_BEARER_TOKEN`**（ローカル）
   シェルの環境変数、または作業ディレクトリから上へ探索して見つかる `.env`。

## つまずいたときの判断

スクリプトは HTTP ステータスから原因を出す（`api_error_hint`）。要点だけ:

- `401` … 認証なし。上記1か2を設定する。未設定なら無料経路の結果をそのまま使えばよい
- `403` に `attached to a Project` … アプリが **Pay Per Use** のプロジェクトに
  接続されていない。Free プランのプロジェクトでは投稿の読み取りができない
- `503`（`/2/tweets/{id}` のみ）… 障害か、上のプロジェクト未接続。
  `curl https://api.x.com/2/usage/tweets` を叩くと本当の原因が分かる
- `402` / `429` … クレジット残高切れ・利用上限

**取れないもの**: 非公開(鍵)アカウント・削除済み・年齢制限付きの投稿、
リプライツリーやスレッド全体（単一投稿＋引用/返信元まで）。
これらは推測で埋めず、取れなかったと伝える。
