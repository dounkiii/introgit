# 新しいアカウントの最初のメッセージに貼る命令文

以下をそのままコピーして、新しいClaudeアカウントの最初のセッションに貼る。

**先に確認**: セッションが開いているリポジトリが `dounkiii/introgit` であること。
別のリポジトリ（名前の似た `intro-git` など）を開いていると、資料が見つからず
「作業が存在しない」と誤判定される。

---

このリポジトリの引き継ぎをします。対象は次のとおりです。

  リポジトリ: dounkiii/introgit
  ブランチ  : claude/ai-content-monetization-research-qa5ne4（デフォルト。`main` は存在しません）
  資料      : docs/handover.md

セッションが別のリポジトリを開いている場合は、まず dounkiii/introgit を
セッションに追加してください（名前の似た別リポジトリと混同しないこと）。
資料が見つからない場合、作業が存在しないと判断してゼロから作り直す前に、
リポジトリ名とブランチ名が上記と一致しているか確認してください。

まず `docs/handover.md` を読んでください。前のアカウントで
「XのURLを貼るだけで投稿・記事本文を読める仕組み」を作ったところまで完了しています。

読んだうえで、次をこの順で実行してください。

1. `python3 tests/test_fetch_x_post.py` を実行し、9件パスすることを確認
2. `python3 .claude/skills/read-x-post/read_x_post.py --check` を実行し、
   トークンとAPI経路の状態を報告
3. `--check` が `API経路: NG` だった場合は、`docs/handover.md` の
   「トークンの設定」に沿って**私が何をすればよいか**を具体的に指示してください
   （あなたはアカウント設定を操作できないので、代行しようとしないこと）
4. `API経路: OK` だった場合は、
   `python3 .claude/skills/read-x-post/read_x_post.py https://x.com/noukin_AIgori/status/2094379745777684618`
   を実行して、X Articles の本文全文まで取得できることを確認して報告

以後、私がXのURLを貼ったら、WebFetchやcurlで直接取得しようとせず、
必ず `.claude/skills/read-x-post/read_x_post.py` を使ってください。
XはログインなしのHTTP取得を拒否するため、URLを直接開いても読めません。
