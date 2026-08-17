# 性格・恋愛観アンケート（15問）

スマホ向けの静的Webアプリです。全15問の選択式＋最後に1問だけ任意の自由記述。
回答は端末の `localStorage` に保存されます。既定では外部へ一切送信せず、
`config.js` で送信先を設定したときだけ送信します。

## いちばん簡単な公開方法：Googleフォームにする

`gas/CreateForm.gs` を Apps Script に貼って `createQuiz` を1回実行すると、
15問ぶんのGoogleフォームが自動で作られます。回答は同時に作られる
スプレッドシートにたまります。ログイン不要のURLが即発行され、
ホスティングの設定は一切不要です。

1. https://script.google.com/home/projects/create を開く
2. エディタの中身を消して `gas/CreateForm.gs` を貼り付け、保存
3. 関数 `createQuiz` を選んで「実行」（初回は承認）
4. 実行ログに出る「回答用URL」を送る

`gas/CreateForm.gs` は生成物です。質問を変えたら作り直してください。

```bash
node quiz/gas/build-createform.js
```

1問ずつページを分ける／分けないは、生成物の先頭 `ONE_QUESTION_PER_PAGE` で切り替えられます。

## 公開する（自作HTMLをApps Scriptで配信する方法）

**ログイン不要のURL** と **回答の自動記録** を、Googleアカウントだけで両方まかなえます。
Apps Script のウェブアプリはページ自体を配信できるので、他のホスティングは不要です。

必要なファイルは `gas/` に入っています。手順は `gas/Code.gs` の先頭コメントに
そのまま書いてありますが、要点は次の6つです。

1. Googleスプレッドシートを新規作成
2. **拡張機能 → Apps Script**
3. `コード.gs` の中身を消して `gas/Code.gs` を貼り付け
4. 左の「ファイル」＋ → **HTML** → 名前を `index` にして `gas/index.html` を貼り付け
5. **デプロイ → 新しいデプロイ → ウェブアプリ**
   - 次のユーザーとして実行: **自分**
   - アクセスできるユーザー: **全員** ← これでログイン不要になる
6. 出てきた `https://script.google.com/macros/s/..../exec` が公開URL

回答が終わると、そのスプレッドシートに1行ずつ自動で追記されます（列見出しは質問文）。

`gas/index.html` は生成物です。質問を変えたら次のコマンドで作り直してください。

```bash
python3 quiz/build-standalone.py --submit-mode apps-script -o gas/index.html
```

## 公開する（GitHub Pages を使う場合）

このリポジトリは公開設定なので、GitHub Pages を有効にすればそのまま誰でも開けます。

1. GitHub の **Settings → Pages** を開く
2. Source を **Deploy from a branch**
3. Branch に公開したいブランチ、フォルダは **/ (root)** を選んで **Save**
4. 1〜2分待つと公開される

```
https://dounkiii.github.io/introgit/quiz/
```

Claudeのログインは不要で、LINEでそのまま送れます。
ただし GitHub Pages は静的配信のみなので、回答をこちらに集めたい場合は
下の「回答を手元に集めたい場合」の **B（スプレッドシート）** を併用してください。
（Netlify Forms は Netlify に置いた場合だけ使えます）

## 使い方（ローカル）

`quiz/index.html` をブラウザで開くだけで動きます（ビルド不要・依存ライブラリなし）。

```bash
cd quiz
python3 -m http.server 8000
# → http://localhost:8000/
```

`file://` で直接開いても動作します（その場合コピーは `execCommand` にフォールバックします）。

## ファイル構成

| ファイル | 役割 |
| --- | --- |
| `index.html` | 画面の骨組み（トップ / 設問 / 任意の自由記述 / 完了） |
| `styles.css` | デザイン。ライト・ダーク両対応、スマホファースト |
| `questions.js` | **質問データ**。ここだけ編集すれば設問を差し替えられる |
| `config.js` | **回答の送信先設定**。既定は送信なし |
| `app.js` | 進行・保存・出力・送信のロジック |
| `build-standalone.py` | 上記を1枚のHTMLにまとめる（`standalone.html` を生成） |
| `gas/CreateForm.gs` | **Googleフォームを自動生成**するスクリプト（生成物） |
| `gas/build-createform.js` | 上記を `questions.js` から生成する |
| `gas/Code.gs` | Apps Script用。自作HTMLの配信＋スプレッドシートへの記録 |
| `gas/index.html` | Apps Scriptに貼る単一HTML（生成物） |
| `server/apps-script.gs` | 外部ホスティングから回答を受け取る場合の受け口（任意） |

## 質問の変更

`questions.js` の `QUESTIONS` 配列を編集します。

```js
{
  id: 'Q1',                       // 出力の見出しに使う識別子
  scene: ['友達との旅行。'],       // 状況説明（1要素 = 1行、無ければ []）
  ask: '予定を決めるなら一番近いのは？',
  options: ['…', '…', '…', '…']   // 選択肢は何個でも可
}
```

- 設問数を増減しても進捗表示（`n / 15`）は自動で追従します。
- コピー用テキストの見出しは `scene` と `ask` を連結して自動生成されます。
  例）`【Q2 ちょっと嫌なことがあった日に恋人と会いました。一番嬉しいのは？】`
- 途中で挟む一言は `MILESTONES`（キーは「何問目か」）で変更できます。
- 最後の任意質問は `OPTIONAL_QUESTION` で変更できます。

**設問の内容を変えたときは `app.js` の `SCHEMA_VERSION` を上げてください。**
保存済みの古い回答は読み込まれずに破棄され、新しい設問で最初から始まります。

## 機能

- 1画面1問 / タップで自動的に次へ / 戻って回答変更も可能
- 1問ごとに `localStorage` へ自動保存 → 再訪時に「続きから」「最初からやり直す」
- 完了後に **回答をコピー / JSONをコピー / TXTで保存**
- ダークモード、`prefers-reduced-motion`、セーフエリアに対応

## 出力形式

「回答をコピー」および TXT は次の形式です。

```
【Q1 友達との旅行。予定を決めるなら一番近いのは？】
メインだけ決めて、あとはその場で

【Q2 ちょっと嫌なことがあった日に恋人と会いました。一番嬉しいのは？】
「なんかあった？」と気づいてくれる

…

【任意】
（未記入）
```

JSON は設問ID・質問文・選択肢一覧・選んだindex・選んだ本文と、任意回答を含みます。

このアプリは回答の判定や分類、診断ラベルの表示は一切行いません。
記録した回答をそのまま書き出すだけです。

## 保存データ

- キー: `love-quiz.state.v3`
- 起動時に旧バージョンのキー（`LEGACY_KEYS`）は削除されます。

---

## 回答を手元に集めたい場合（任意）

既定（`config.js` の `mode: 'off'`）では、回答は答えた人の端末から外に出ません。
別の人に答えてもらってその回答を集めたい場合は、送信先を設定します。

送信を有効にすると、トップ画面の注意書きは自動で
「回答は最後にまとめて送られます。」に変わります。
送信に失敗した回答は端末に残り、**次にページを開いたときに自動で再送**されます。

> 注意: claude.ai の Artifact として公開したページは、CSPにより外部への送信が
> すべてブロックされます。送信を使う場合は通常のホスティング（GitHub Pages、
> Netlify、Cloudflare Pages など）に置いてください。

| 置き場所 | ログイン不要のURL | 回答の保存 |
| --- | --- | --- |
| Googleフォーム | ○ | スプレッドシートに自動記録 |
| Apps Script ウェブアプリ | ○ | スプレッドシートに自動記録 |
| GitHub Pages | ○ | B（スプレッドシート）のみ |
| Netlify | ○ | A・B どちらも可 |
| claude.ai の Artifact | × | 不可（外部送信がブロックされる） |

### A. Netlify に置く場合（最短）

1. `python3 quiz/build-standalone.py` で `standalone.html` を生成
2. `index.html` という名前でフォルダに入れ、[Netlify Drop](https://app.netlify.com/drop) にドラッグ&ドロップ
3. `config.js`（standalone.html なら該当箇所）を次のように変更して再デプロイ

```js
const SUBMIT_CONFIG = { mode: 'netlify', endpoint: '', formName: 'quiz-answers' };
```

回答は Netlify の管理画面 **Forms → quiz-answers** に1件ずつ溜まります。
`answers` 欄に質問文つきの全文、`json` 欄に構造化データが入ります。
Site settings → Forms → Form notifications でメール通知も設定できます。

### B. スプレッドシートに記録する場合

`server/apps-script.gs` の手順どおりに Google Apps Script をデプロイし、
発行されたURLを設定します。

```js
const SUBMIT_CONFIG = { mode: 'endpoint', endpoint: 'https://script.google.com/macros/s/..../exec', formName: '' };
```

1回答 = スプレッドシート1行として追記されます（列見出しは質問文）。
