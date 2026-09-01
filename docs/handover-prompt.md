# 新しいアカウントの最初のメッセージに貼る命令文

## A. 全体を引き継ぐ（最初の1通目）

新しいアカウントで `dounkiii/introgit` を開き、以下をそのまま貼る。

---

前のClaudeアカウントから作業を引き継ぎます。会話は移行できないので、必要なことは
すべてこのリポジトリに書き出してあります。

  リポジトリ: dounkiii/introgit
  ブランチ  : claude/ai-content-monetization-research-qa5ne4（デフォルト。`main` は存在しません）

まず次の3つを読んでください。

  docs/session-inventory.md          旧アカウントの全セッション棚卸し。どの作業がどのリポジトリの
                                     どのブランチにあるか、未消化のタスクは何か
  docs/handover.md                   XのURLを読む仕組みの技術資料（実装・トークン設定・落とし穴）
  docs/claude-account-migration.md   アカウント移行で作り直す必要があるものの一覧

注意: `dounkiii/introgit`（ハイフン無し）と `dounkiii/intro-git`（ハイフン有り）は
別のリポジトリです。両方実在します。ファイルが見つからないときは、作業が存在しないと
判断する前にリポジトリ名を確認してください。

読んだら、次の順で確認して報告してください。

1. `python3 tests/test_fetch_x_post.py` → 9件パスするか
2. `python3 .claude/skills/read-x-post/read_x_post.py --check` → トークンとAPI経路の状態
3. 2 が `API経路: NG` なら、`docs/handover.md` の「トークンの設定」に沿って
   **私が何をすればよいか**を具体的に指示してください
   （あなたはアカウント設定を操作できないので、代行しようとしないこと）
4. `docs/session-inventory.md` の「要対応/要判断」のうち、いま再開すべきものを
   優先度つきで3つ提案してください

以後、私がXのURLを貼ったら、WebFetchやcurlで直接取得しようとせず、必ず
`.claude/skills/read-x-post/read_x_post.py` を使ってください。XはログインなしのHTTP取得を
拒否するため（投稿ページは402、記事ページは404）、URLを直接開いても読めません。

---

## B. アーティファクトを再公開する（必要になったときだけ）

旧アカウントのアーティファクト4件は `docs/artifacts/` にHTMLとして保存済み。
新アカウントで復活させたいものがあるときに貼る。

---

`docs/artifacts/README.md` を読んで、次のファイルをアーティファクトとして公開してください。

  docs/artifacts/<ファイル名>

中身は旧アカウントで公開していたページそのままです。画像は data: URI で埋め込まれて
いるので外部依存はありません。内容を書き換えず、そのまま公開してください。

---

## C. 他のリポジトリの作業を再開する

`docs/session-inventory.md` の表からブランチを選び、そのリポジトリを開いたセッションで貼る。

---

前のClaudeアカウントから引き継いだ作業を再開します。

  リポジトリ: <dounkiii/intro-git など>
  ブランチ  : <claude/... >

このブランチの作業内容をコードとコミット履歴から把握して、現状と残りタスクを
報告してください。会話ログは引き継げていないので、リポジトリの内容だけが手がかりです。
`dounkiii/introgit` の `docs/session-inventory.md` にこのブランチの状態メモがあります
（そのリポジトリも参照できるなら見てください）。
