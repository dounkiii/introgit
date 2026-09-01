# 旧アカウントのセッション棚卸し（引き継ぎ用）

会話そのものは別アカウントへ移行できないが、**各セッションの成果はGitHubのブランチに残っている**。
新アカウントでは「リポジトリへのアクセスを回復する」だけで作業を再開できる。

環境は2つ使われていた: `env_01QcMeVQebtW8xoz4yax8wky` / `env_01RPaf5huqYj3jjAeBBtPb3Y`。
新アカウントでは作り直しになる（環境変数・API credential は移行不可）。

## 最初に注意：リポジトリが2つあり、名前が紛らわしい

| リポジトリ | 中身 |
|---|---|
| `dounkiii/introgit`（ハイフン無し）| AIコンテンツ収益化リサーチ、**Xポスト読み取りスキル**、ローカルフォルダ検証 |
| `dounkiii/intro-git`（ハイフン有り）| 副業・note収益、CCNA、Grok連携、社内向け調べ物など**大半のセッション** |
| `dounkiii/ccna-materials` | CCNA教材（問題2,729問）|

**この2つを混同すると「作業が存在しない」と誤判定する。** 実際に一度発生した。

## セッション一覧（新しい順）

| セッション | リポジトリ | ブランチ | 状態 / 次にやること |
|---|---|---|---|
| Memory and context export | introgit | `claude/memory-context-export-r44tm3` | **要対応**: メモリにアクセスできず。引き継ぎ資料で代替するか要判断 |
| X投稿の学習 | intro-git | `claude/x-post-learning-tayau0` | **要対応**: スレッドの続き（返信）が未取得。続きのURLか画像が必要 |
| X投稿の翻訳 | intro-git | `claude/translate-x-post-rg9ot4` | 完了: Claude+Amazonアフィリエイト戦略の翻訳・分析 |
| X_BEARER_TOKEN 設定確認 | introgit | `claude/ai-content-monetization-research-qa5ne4` | 完了: トークン116文字を検出、API経路OK、記事本文23.8K文字取得 |
| Xツイート学習（このセッション）| introgit | `claude/translate-x-post-yi8xeb` | 完了: Xポスト読み取りスキル一式。デフォルトブランチにも反映済み |
| ツイート読み込みと学習 | intro-git | `claude/tweet-loading-learning-m72cag` | **解決済み**: ドメイン許可を求めていたが、`read-x-post` スキルで不要になった |
| GWS依頼の確認 | intro-git | `claude/gws-request-check-l3x430` | 完了: prj-kintai グループのCSV一括登録手順 |
| MDM登録時の借用デバイス確認 | intro-git | `claude/mdm-borrowed-device-check-91hgb2` | 完了: 返信文（英/日）ドラフト |
| フォーム編集場所の確認 | intro-git | `claude/form-editing-location-t2ezgr` | 完了: Googleフォーム編集手順 |
| AliExpress無在庫出品ツール | intro-git | `claude/aliexpress-dropship-tool-n9kw0a` | 完了: 技術的には可能だが法的リスクありと結論 |
| Xみれるかな | intro-git | `claude/x-test-uv99tu` | **要判断**: 候補ツイートIDの発見経路（RSS/手動投入等）を決める必要あり |
| Claude Code と Grok 連携 | intro-git | `claude/claude-code-grok-integration-wzukpv` | 完了: X CDNエンドポイントの検証（今回のスキルの前身）|
| note収益 | intro-git | `claude/mobile-automation-side-income-59tccj` | **最大の資産**（累計$324）: note記事4本公開済み。承認修正後のサイト再ビルドが保留 |
| ローカルフォルダへのアクセス | introgit | `claude/local-folder-access-0z47t4` | **要対応**: クラウドからローカルは見えない。ローカルCLI/デスクトップ版が必要 |
| いけたかな | ccna-materials | `claude/iketa-kana-bhdqri` | 完了: ネットワーク問題14問追加、累計2,729問 |
| AI コンテンツ収益化リサーチシステム | introgit | `claude/ai-content-monetization-research-qa5ne4` | 完了: デモ実行、TOP5生成、バグ1件修正（このリポジトリの本体）|
| CCNA学習ゲーム化 | intro-git | `claude/ccna-gamified-learning-i7r8xb` | **要対応**: ローカルPCのCCNA md 150ファイルが未アップロード |
| 副業で稼ぐ方法 | intro-git | `claude/side-hustle-research-cpiwhn` | **要判断**: コンテンツパイプライン構築済み。日次Routine化するか等 |
| きみにはなにができる | intro-git | `claude/kimi-nani-dekiru-je7usf` | アーカイブ済み。Threads×note のニッチ未決定 |

## アーティファクト（アカウント紐付け。放置すると失う）

claude.ai のアーティファクトは**アカウントに紐付いており移行できない**。必要なものは
中身をリポジトリに保存しておく。

| タイトル | 元セッション |
|---|---|
| A8 提携申請5枠 | note収益 |
| マンガと図解でわかるCCNA | いけたかな |
| ギャルでもわかるCCNA | いけたかな |
| CCNA Quest — ゲームで学ぶCCNA | CCNA学習ゲーム化 |

## 新アカウントでやること

1. **GitHub連携**を接続し、3リポジトリすべてを許可
   （`dounkiii/introgit`, `dounkiii/intro-git`, `dounkiii/ccna-materials`）
2. クラウド環境を作成し、必要な環境変数を設定（Xを読むなら `X_BEARER_TOKEN`。
   詳細は `docs/handover.md`）
3. 再開したい作業のブランチを開いて続ける。上の表の「要対応/要判断」が未消化のタスク
4. アーティファクトが必要なら、旧アカウントでまだ開けるうちに中身を保存する

会話の文面自体は移行できない。**必要な結論は各ブランチのコードとドキュメントに残っている**ので、
そこから読み直すのが最短。
