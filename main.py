"""AIコンテンツ収益化リサーチ - エントリポイント（Phase 1）。

パイプライン:
  収集 → 期間フィルタ → 重複統合 → 事前選別 → AI分析(キャッシュ) → 採点
        → TOP5抽出 → Markdown/JSON出力 → ログ

使い方:
  python main.py                 # 通常実行（当日の日付で出力）
  python main.py --date 2026-08-13
  python main.py --dry-run       # 収集・統合まで（分析/出力なし）
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# src をインポート可能に
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.analyzer import build_analyzer            # noqa: E402
from src.collectors import collect_all, collect_from_fixture  # noqa: E402
from src.deduplicator import Deduplicator          # noqa: E402
from src.reporter import Reporter                  # noqa: E402
from src.scorer import Scorer                      # noqa: E402
from src.utils.cache import SeenCache              # noqa: E402
from src.utils.config import load_config, load_env  # noqa: E402
from src.utils.logging_setup import setup_logger   # noqa: E402


def _within_window(items, max_hours, logger):
    kept = [i for i in items if i.age_hours <= max_hours]
    dropped = len(items) - len(kept)
    if dropped:
        logger.info(f"[filter] 期間外({max_hours}h超) {dropped} 件を除外")
    return kept


def _preselect(topics, cfg, max_n):
    """LLMコスト抑制のため、鮮度+話題性の簡易スコアで上位のみ分析対象にする。"""
    fresh_th = cfg["scoring"]["freshness_thresholds"]

    def rough(t):
        age = t.age_hours
        fresh = next((th["points"] for th in fresh_th if age <= th["max_hours"]), 0)
        eng = sum(v for v in t.metrics.values() if isinstance(v, int))
        return fresh + min(20, eng / 20.0) + 3 * (len(t.sources) - 1)

    return sorted(topics, key=rough, reverse=True)[:max_n]


def run(date_str: str | None = None, dry_run: bool = False, demo: str | None = None) -> int:
    logger = setup_logger()
    load_env()
    cfg = load_config()

    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    logger.info("=" * 60)
    logger.info(f"リサーチ開始 {date_str}" + ("  [DEMOモード]" if demo else ""))
    logger.info("=" * 60)

    # 1) 収集
    if demo:
        items = collect_from_fixture(demo, cfg, logger)
    else:
        items = collect_all(cfg, logger)
    collected = len(items)
    logger.info(f"[集計] 取得できた記事数: {collected}")

    # 2) 期間フィルタ
    items = _within_window(items, cfg["collection"]["max_window_hours"], logger)
    before_dedup = len(items)
    logger.info(f"[集計] 重複削除前の件数: {before_dedup}")

    if before_dedup == 0:
        logger.warning("候補が0件でした。ネットワークやソース設定を確認してください。")
        # 空でもレポートは生成する
        if not dry_run:
            _write_empty(cfg, logger, date_str, collected)
        return 0

    # 3) 重複統合
    topics = Deduplicator(cfg, logger).merge(items)
    after_dedup = len(topics)
    logger.info(f"[集計] 重複削除後の件数: {after_dedup}")

    if dry_run:
        logger.info("[dry-run] 分析・出力はスキップします")
        for t in topics[:10]:
            logger.info(f"  - ({'/'.join(t.sources)}) {t.title[:80]}")
        return 0

    # 4) 事前選別（分析件数の上限）
    max_analyze = cfg["analyzer"]["max_analyze"]
    selected = _preselect(topics, cfg, max_analyze)

    # 5) AI分析（キャッシュで再評価を防止）
    analyzer = build_analyzer(cfg, logger)
    scorer = Scorer(cfg, logger)
    cache = SeenCache(cfg["output"]["seen_db"])

    scored = []
    newly_analyzed = 0
    errors = 0
    for topic in selected:
        try:
            cached = cache.get(topic.id)
            if cached:
                analysis = cached
                logger.info(f"[cache] 既評価を再利用: {topic.title[:50]}")
            else:
                analysis = analyzer.analyze(topic)
                cache.set(topic.id, analysis)
                newly_analyzed += 1
            scores = scorer.score(topic, analysis)
            scored.append((topic, analysis, scores))
        except Exception as exc:  # noqa: BLE001
            errors += 1
            logger.error(f"[analyze] 失敗: {topic.title[:50]} : {exc}")

    cache.save()
    logger.info(f"[集計] AI評価した件数: {len(scored)}（うち新規 {newly_analyzed}）")
    if errors:
        logger.warning(f"[集計] エラー: {errors} 件")

    # 6) 採点順に TOP5
    scored.sort(key=lambda x: x[2]["score_total"], reverse=True)
    top_n = cfg["output"]["top_n"]
    ranked = scored[:top_n]

    # 7) 出力
    reporter = Reporter(cfg, logger)
    meta = {
        "provider": analyzer.provider,
        "collected": collected,
        "before_dedup": before_dedup,
        "after_dedup": after_dedup,
        "analyzed": len(scored),
        "errors": errors,
    }
    records = reporter.build_records(ranked)
    reporter.write_json(records, date_str, meta)
    reporter.write_markdown(records, date_str, meta)

    # 8) 最終TOP5をログ
    logger.info("-" * 60)
    logger.info("最終 TOP5:")
    for r in records:
        logger.info(f"  {r['rank']}位 [{r['score_total']:>5}点] {r['title'][:70]}")
    logger.info("-" * 60)
    logger.info("完了")
    return 0


def _write_empty(cfg, logger, date_str, collected):
    reporter = Reporter(cfg, logger)
    meta = {"provider": "n/a", "collected": collected, "before_dedup": 0,
            "after_dedup": 0, "analyzed": 0, "errors": 0}
    reporter.write_json([], date_str, meta)
    reporter.write_markdown([], date_str, meta)


def main():
    parser = argparse.ArgumentParser(description="AIコンテンツ収益化リサーチ (Phase 1)")
    parser.add_argument("--date", help="出力日付 YYYY-MM-DD（省略時は本日）")
    parser.add_argument("--dry-run", action="store_true", help="収集・統合のみ実行")
    parser.add_argument(
        "--demo",
        nargs="?",
        const="tests/fixtures/sample_items.json",
        help="ネットワーク不要のフィクスチャで全パイプラインを実行（オフライン検証用）",
    )
    args = parser.parse_args()
    return run(date_str=args.date, dry_run=args.dry_run, demo=args.demo)


if __name__ == "__main__":
    raise SystemExit(main())
