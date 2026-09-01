# Claude アカウント移行チェックリスト（会社アカウント → 個人アカウント）

このリポジトリの作業を、別のClaudeアカウントで再開できるようにするための手順。
**アカウント間の自動移行機能は存在しない**ので、「ファイルとして持ち出せるもの」と
「新アカウントで作り直すもの」を分けて扱う。

## 最初に押さえること

| 項目 | 可否 |
|---|---|
| 会話・セッションの別アカウントへの移行 | **不可**（公式に非サポート）|
| 会話のエクスポート（自分用の控え）| 可。Settings → Privacy → Export data。リンクは**24時間で失効** |
| Team/Enterprise アカウントのエクスポート | **Primary Owner のみ**実行できる |
| スキル | 可（ファイルなので zip で持ち出せる）|
| GitHub連携・MCPコネクタ | 新アカウントで**再認可**（設定値の移行不可）|
| クラウド環境（環境変数・API credential・ネットワーク設定）| 手で作り直す。**保存済みトークンの値は読み出せない** |
| リポジトリのコード | アカウント非依存。GitHubにあるものはそのまま使える |

会社の Team / Enterprise アカウント上のデータは会社の管理下にある。持ち出す前に、
社内の方針と管理者の許可を確認する。

## 持ち出すもの / 作り直すもの

| 対象 | 現在の場所 | 移行方法 |
|---|---|---|
| `read-x-post` スキル | このリポジトリの `.claude/skills/read-x-post/` | `cd .claude/skills && zip -r ../../read-x-post-skill.zip read-x-post -x '*__pycache__*'` して新アカウントにアップロード |
| Xポスト読み取りの実装・手順 | このリポジトリ（`README.md` の付録、`tools/`, `tests/`）| git 上にあるので移行不要 |
| X API のトークン | 会社アカウントのクラウド環境の環境変数 | **値は読み出せない。console.x.com で再生成**して新環境に入れる |
| X API のプロジェクト設定 | console.x.com（Xのアカウント側、Claudeとは独立）| 移行不要。ただしアプリが **Pay Per Use** のプロジェクトに接続されていること |
| GitHub連携 | 会社アカウントのコネクタ | 新アカウントで Settings → Connectors → GitHub を接続し、`dounkiii/introgit` へのアクセスを許可 |
| MCPコネクタ（Supermetrics 等）| 会社アカウントのコネクタ | 新アカウントで再接続。各サービス側の認可もやり直し |
| 過去の会話 | 会社アカウント | エクスポートして控えを保存（**インポートはできない**ので参照用）|

## 新アカウント側の手順（この順番で）

1. 個人メールで claude.ai のアカウントを作成し、プラン（Pro / Max）を契約
2. **GitHub連携**: Settings → Connectors → GitHub を接続 → `dounkiii/introgit` を許可
3. **クラウド環境を作成** → 次のどちらかでXのトークンを設定
   - Environment variables に `X_BEARER_TOKEN=...`（簡単。値はセッションから見える）
   - API credentials に Bearer / `api.x.com` / ヘッダ `Authorization` + prefix `Bearer`
     （安全。セッションに鍵が渡らない。org admin 権限が必要）
4. **スキルをアップロード**: Settings → Features で**コード実行を有効化** → 上の zip を選択
5. **MCPコネクタ**を必要な分だけ再接続
6. **検証**: 新しいセッションで次を実行し、`API経路: OK` になることを確認

   ```bash
   python3 .claude/skills/read-x-post/read_x_post.py --check
   ```

環境変数と API credential は**セッション起動時に一度だけ読み込まれる**。設定を変えたら
新しいセッションを開く。

## 旧アカウントを離れる前にやること

- [ ] **X API のトークンを再生成**（旧アカウントのセッションログに残っているため）
- [ ] 必要な会話をエクスポート（リンクは24時間で失効するのですぐ保存する）
- [ ] このリポジトリの作業ブランチが push 済みか確認（`git status` / `git log origin/<branch>..HEAD`）
- [ ] 旧アカウントのクラウド環境・スキル・コネクタを削除するかは会社の方針に従う
