# AIコンテンツ収益化 リサーチ自動化システム（Phase 1）

毎日1回スクリプトを実行すると、Web上の最新情報から「いま書く価値が高く、
アフィリエイト・有料note・SaaS紹介につながりやすいネタ」を収集・重複統合・
採点し、**TOP5** を Markdown と JSON で出力します。

> このシステムの目的は「記事を大量自動生成すること」ではありません。
> **人間が毎日大量のWebを巡回しなくても、いま収益化価値の高い候補だけを発見できる状態**を作ることです。
> 記事を書く最終判断は人間が行います。

---

## 特徴（Phase 1）

- 収集 → 期間フィルタ → **重複統合** → AI分析 → **100点満点採点** → TOP5出力 → 保存
- **APIキーなしで動く**（`heuristic` モード）。LLMキーを入れれば分析品質が向上
- 情報源は **公開API / RSS のみ**（スクレイピングやTOS違反の取得はしない）
- 1つの情報源が落ちても**全体は止まらない**（エラー隔離）
- **同じ記事を何度も評価しない**（`data/seen.json` キャッシュ）
- 設定はすべて `config/settings.yaml`。**コードを触らずジャンル・情報源・配点を変更可能**

## ディレクトリ構成

```
.
├── README.md
├── .env.example              # 環境変数サンプル（APIキーはここには書かない）
├── requirements.txt
├── main.py                   # エントリポイント
├── config/
│   └── settings.yaml         # すべての設定（ジャンル/情報源/採点/出力）
├── src/
│   ├── collectors/           # 情報源ごとの収集 (HN/Reddit/GitHub/ProductHunt/RSS)
│   ├── deduplicator/         # 重複統合（同一テーマにまとめ参照URLを複数残す）
│   ├── analyzer/             # AI分析（heuristic / openai / gemini / anthropic 切替）
│   ├── scorer/               # 100点満点の採点
│   ├── reporter/             # Markdown / JSON 出力
│   └── utils/                # 設定・ログ・HTTP・キャッシュ・データモデル
├── tests/fixtures/           # オフライン検証用のサンプルデータ
├── data/                     # JSON出力・キャッシュ（gitignore）
├── output/                   # Markdownレポート（gitignore）
└── logs/                     # 実行ログ（gitignore）
```

---

## 1. セットアップ方法

Python 3.11+ を推奨。

```bash
# 依存インストール（最小構成はキー不要で動作）
pip install -r requirements.txt

# 環境変数ファイルを用意
cp .env.example .env
```

## 2. APIキー設定

**Phase 1 はキーなしでも動きます**（`heuristic` モード）。
LLMで分析品質を上げたい場合のみ、`.env` に使うプロバイダのキーを設定します。

```dotenv
# .env（例: Gemini を使う場合）
ANALYZER_PROVIDER=gemini
GEMINI_API_KEY=xxxxxxxx
```

- 対応プロバイダ: `heuristic`（デフォルト・無料） / `openai` / `gemini` / `anthropic`
- キーは**必ず `.env` で管理**（`.env` は `.gitignore` 済み。ソースに直書きしない）
- LLM用ライブラリは任意インストール（使うものだけ）:
  ```bash
  pip install openai              # openai を使う場合
  pip install google-generativeai # gemini を使う場合
  pip install anthropic           # anthropic を使う場合
  ```
- LLM指定でもキーが無い／呼び出しに失敗した場合は **自動的に heuristic にフォールバック**します。

## 3. 実行方法

```bash
# 通常実行（本日の日付で output/ と data/ に出力）
python main.py

# 日付を指定
python main.py --date 2026-08-13

# 収集・統合まで確認（分析/出力なし）
python main.py --dry-run

# ネットワーク不要のサンプル実行（オフライン検証・デモ）
python main.py --demo
```

出力例:
- `output/2026-08-13.md` … 人が読むTOP5レポート
- `data/2026-08-13.json` … 機械可読データ（`rank`, `title`, `summary`, 各スコア,
  `reasons`, `monetization_ideas`, `content_ideas`, `risks`, `source_urls`,
  `discovered_at` などを網羅）
- `logs/2026-08-13.log` … 取得件数/重複前後/評価件数/エラー/最終TOP5のログ

> ネットワークが制限された環境では外部ソースへ接続できないことがあります。
> その場合でも `python main.py --demo` でパイプライン全体を検証できます。

## 4. 定期実行方法

**cron（Linux/macOS）** で毎朝7時に実行する例:

```bash
crontab -e
# 毎日 07:00 に実行（パスは環境に合わせて調整）
0 7 * * * cd /path/to/project && /usr/bin/python3 main.py >> logs/cron.log 2>&1
```

**launchd / タスクスケジューラ / GitHub Actions** でも同様に `python main.py` を1日1回叩くだけです。

## 5. 情報源の追加方法

すべて `config/settings.yaml` の `sources:` で管理します。

- **RSSメディアを足す**（最も簡単）: `sources.rss.feeds` に1行追加するだけ
  ```yaml
  sources:
    rss:
      feeds:
        - { name: "新しいAIメディア", url: "https://example.com/feed" }
  ```
- **Reddit のサブレを足す**: `sources.reddit.subreddits` に追記
- **ソースのON/OFF**: 各ソースの `enabled: true/false`
- **新種のソース（新しいAPI）を足す**:
  1. `src/collectors/` に `BaseCollector` を継承したクラスを作り `collect()` を実装
  2. `src/collectors/__init__.py` の `REGISTRY` に登録
  3. `settings.yaml` の `sources` に設定を追加

  収集結果は共通の `Item` を返すだけで、後続（統合・分析・採点・出力）は変更不要です。

## 6. 採点基準の変更方法

`config/settings.yaml` の `scoring:` で調整します（コード変更不要）。

- **配点の変更**: `scoring.weights`（`freshness:20, demand:20,
  japanese_competition:15, monetization:25, content_potential:20`。合計100）
- **鮮度の閾値**: `scoring.freshness_thresholds`（何時間以内で何点か）
- **需要の基準値**: `scoring.demand_reference`（HNスコア/Redditスコア/GitHub star
  が「満点相当」とみなす値）
- **ヒューリスティックの判定語**: `scoring.heuristic`
  - `monetization_signals` … 収益性を上げる語
  - `content_signals` … コンテンツ化しやすさを上げる語
  - `negative_signals` … 政治/炎上/芸能など減点する語
- **対象ジャンル**: `genres.ai_keywords`（AI関連と見なすキーワード。将来ジャンル追加はここ）
- **重複統合の感度**: `deduplication`（タイトル類似度/トークン重なりの閾値）
- **分析プロバイダ / 分析件数上限**: `analyzer`

---

## 採点ルール（100点満点）

| 項目 | 配点 | 算出方法 |
|---|---|---|
| 鮮度 | 20 | 公開からの経過時間（24h以内=20, 3日=15, 7日=10, それ以上=5）|
| 需要・話題性 | 20 | HN points / Reddit score / GitHub star / コメント数を正規化 + 複数ソースボーナス |
| 日本語競合の弱さ | 15 | 海外発で日本語情報が薄いほど高い（AI分析）|
| 収益性 | 25 | アフィリエイト/SaaS課金/有料note化のしやすさ（AI分析）|
| コンテンツ化しやすさ | 20 | 使い方・比較・レビュー・実際に試せるか（AI分析）|

鮮度・需要は指標から決定論的に算出し、残り3項目を分析エンジン（heuristic/LLM）が
0.0〜1.0で評価して配点を掛けます。

## 情報源（Phase 1・すべて無料 / キー不要 / TOS準拠）

| ソース | 取得方法 |
|---|---|
| Hacker News | Algolia HN Search API（公開JSON）|
| Reddit | 公開 `.json` エンドポイント（適切なUA付与）|
| GitHub | 公式 REST Search API（最近作成されたAIリポジトリをstar順）|
| Product Hunt | 公開RSSフィード |
| AI系メディア/公式ブログ | RSS（TechCrunch, VentureBeat, Hugging Face, Google AI 等）|

## Phase 1 でやらないこと

WordPress/note/X への自動投稿、記事全文の自動生成、完全自動アフィリエイト、
NotebookLM連携、複雑なダッシュボード、有料APIへの過剰依存 —— これらは対象外です。
まずは「良いネタが見つかるか」の検証を最優先しています。
