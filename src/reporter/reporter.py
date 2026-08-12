"""出力（Markdown レポート + JSON データ）。

- output/YYYY-MM-DD.md : 人が読むレポート（TOP5）
- data/YYYY-MM-DD.json : 機械可読データ（要件のフィールドを網羅）
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..utils.config import ROOT


def _bullets(items) -> str:
    if not items:
        return "  * （情報なし）\n"
    return "".join(f"  * {x}\n" for x in items)


class Reporter:
    def __init__(self, cfg: dict, logger):
        self.cfg = cfg
        self.logger = logger
        self.md_dir = ROOT / cfg["output"]["markdown_dir"]
        self.json_dir = ROOT / cfg["output"]["json_dir"]
        self.md_dir.mkdir(parents=True, exist_ok=True)
        self.json_dir.mkdir(parents=True, exist_ok=True)

    def build_records(self, ranked: list) -> list[dict]:
        """ranked: (topic, analysis, scores) のタプル列 -> JSON用レコード。"""
        records = []
        for rank, (topic, analysis, scores) in enumerate(ranked, start=1):
            records.append(
                {
                    "rank": rank,
                    "title": topic.title,
                    "summary": analysis.get("summary", ""),
                    "suggested_title": analysis.get("suggested_title", ""),
                    "score_total": scores["score_total"],
                    "score_freshness": scores["score_freshness"],
                    "score_demand": scores["score_demand"],
                    "score_japanese_competition": scores["score_japanese_competition"],
                    "score_monetization": scores["score_monetization"],
                    "score_content_potential": scores["score_content_potential"],
                    "reasons": analysis.get("reasons", []),
                    "monetization_ideas": analysis.get("monetization_ideas", []),
                    "content_ideas": analysis.get("content_ideas", []),
                    "risks": analysis.get("risks", []),
                    "sources": topic.sources,
                    "source_urls": topic.source_urls,
                    "discovered_at": topic.discovered_at.astimezone(timezone.utc).isoformat(),
                    "published_at": topic.published_at.astimezone(timezone.utc).isoformat(),
                }
            )
        return records

    def write_json(self, records: list[dict], date_str: str, meta: dict) -> Path:
        path = self.json_dir / f"{date_str}.json"
        payload = {"generated_at": datetime.now(timezone.utc).isoformat(),
                   "meta": meta, "top": records}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.logger.info(f"[reporter] JSON 出力: {path}")
        return path

    def write_markdown(self, records: list[dict], date_str: str, meta: dict) -> Path:
        path = self.md_dir / f"{date_str}.md"
        lines = []
        lines.append(f"# AIコンテンツ収益化 候補 TOP{len(records)}（{date_str}）\n")
        lines.append(
            f"> 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')} / "
            f"分析エンジン: `{meta.get('provider')}`\n"
        )
        lines.append(
            f"> 収集 {meta.get('collected')} 件 → 統合後 {meta.get('after_dedup')} テーマ "
            f"→ 評価 {meta.get('analyzed')} 件\n"
        )
        lines.append("\n---\n")

        for r in records:
            lines.append(f"\n## 順位：{r['rank']}位　（総合スコア：{r['score_total']} / 100）\n")
            lines.append(f"\n**テーマ：**\n{r['title']}\n")
            lines.append(f"\n**概要：**\n{r['summary']}\n")

            lines.append("\n**スコア内訳：**\n")
            lines.append(f"  * 鮮度: {r['score_freshness']} / 20\n")
            lines.append(f"  * 需要・話題性: {r['score_demand']} / 20\n")
            lines.append(f"  * 日本語競合の弱さ: {r['score_japanese_competition']} / 15\n")
            lines.append(f"  * 収益性: {r['score_monetization']} / 25\n")
            lines.append(f"  * コンテンツ化しやすさ: {r['score_content_potential']} / 20\n")

            lines.append("\n**なぜ今狙い目か：**\n")
            lines.append(_bullets(r["reasons"]))

            lines.append("\n**想定コンテンツ：**\n")
            lines.append(_bullets(r["content_ideas"]))

            if r.get("suggested_title"):
                lines.append(f"\n**想定タイトル：**\n「{r['suggested_title']}」\n")

            lines.append("\n**収益化方法：**\n")
            lines.append(_bullets(r["monetization_ideas"]))

            lines.append("\n**リスク：**\n")
            lines.append(_bullets(r["risks"]))

            lines.append("\n**参照URL：**\n")
            lines.append(_bullets(r["source_urls"]))
            lines.append("\n---\n")

        path.write_text("".join(lines), encoding="utf-8")
        self.logger.info(f"[reporter] Markdown 出力: {path}")
        return path
