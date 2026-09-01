# 保存したアーティファクト

claude.ai のアーティファクトはアカウントに紐付いており、別アカウントへ移行できない。
旧アカウントで読み出せるうちに中身をHTMLとして保存したもの。
公開時に注入される frame-runtime のスクリプトは除去し、著者が書いた内容だけを残している。

| ファイル | タイトル | 元アーティファクトID | サイズ |
|---|---|---|---|
| `a8-partner-applications.html` | A8 提携申請5枠 | `66ae1c56-6264-4027-b94b-70a0cba57b85` | 17 KB |
| `ccna-manga-illustrated.html` | マンガと図解でわかるCCNA | `be05062c-9a0e-439f-a854-59527241dce8` | 1254 KB |
| `ccna-gyaru.html` | ギャルでもわかるCCNA | `172d3222-f6f2-45ba-a042-1abd40eaf9d0` | 2587 KB |
| `ccna-quest.html` | CCNA Quest — ゲームで学ぶCCNA | `101e686e-1918-4e54-bb45-8b246ee4268b` | 620 KB |

## 新アカウントで再公開する

各HTMLをそのまま Artifact として publish すれば同じページが復元できる。
画像はすべて data: URI で埋め込まれているため、外部ファイルへの依存はない。

```
（新アカウントのセッションで）このHTMLをアーティファクトとして公開して:
docs/artifacts/<ファイル名>
```

ブラウザでローカルに開くだけでも内容は読める（`file://` で開けば動く）。
