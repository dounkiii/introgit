#!/usr/bin/env python3
"""index.html / styles.css / questions.js / app.js を1枚のHTMLにまとめる。

    python3 quiz/build-standalone.py            -> quiz/standalone.html（完全なHTML）
    python3 quiz/build-standalone.py --fragment -> 同じ内容を <html>/<head>/<body> 抜きで標準出力

配布やホスティングでファイルを1つにまとめたいときだけ使います。
編集するのは常に元の4ファイルで、standalone.html は生成物です。
"""

import argparse
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent


def read(name: str) -> str:
    return (HERE / name).read_text(encoding="utf-8")


def build() -> str:
    html = read("index.html")

    html = html.replace(
        '<link rel="stylesheet" href="styles.css">',
        "<style>\n" + read("styles.css") + "</style>",
    )
    for src in ("config.js", "questions.js", "app.js"):
        html = html.replace(
            '<script src="%s"></script>' % src,
            "<script>\n" + read(src) + "</script>",
        )
    return html


def to_fragment(html: str) -> str:
    """<html>/<head>/<body> を取り除き、中身だけを残す。"""
    head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
    body = re.search(r"<body>(.*?)</body>", html, re.S).group(1)

    keep = []
    title = re.search(r"<title>.*?</title>", head, re.S)
    if title:
        keep.append(title.group(0))
    style = re.search(r"<style>.*?</style>", head, re.S)
    if style:
        keep.append(style.group(0))
    return "\n".join(keep) + "\n" + body.strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fragment", action="store_true",
                        help="<html>/<head>/<body> を含めずに標準出力へ書き出す")
    args = parser.parse_args()

    html = build()
    if args.fragment:
        print(to_fragment(html))
        return

    out = HERE / "standalone.html"
    out.write_text(html, encoding="utf-8")
    print("wrote %s (%.1f KB)" % (out, out.stat().st_size / 1024))


if __name__ == "__main__":
    main()
