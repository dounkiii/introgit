#!/usr/bin/env python3
"""index.html / styles.css / questions.js / app.js を1枚のHTMLにまとめる。

    python3 quiz/build-standalone.py            -> quiz/standalone.html（完全なHTML）
    python3 quiz/build-standalone.py --fragment -> 同じ内容を <html>/<head>/<body> 抜きで標準出力
    python3 quiz/build-standalone.py --submit-mode apps-script -o gas/index.html
                                                -> 保存先を切り替えた版を任意の場所へ出力

配布やホスティングでファイルを1つにまとめたいときだけ使います。
編集するのは常に元の4ファイルで、standalone.html は生成物です。
"""

import argparse
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent


def read(name: str) -> str:
    return (HERE / name).read_text(encoding="utf-8")


def build(submit_mode: str = "") -> str:
    html = read("index.html")
    config = read("config.js")

    if submit_mode:
        config = re.sub(r"mode: '[^']*'", "mode: '%s'" % submit_mode, config, count=1)

    html = html.replace(
        '<link rel="stylesheet" href="styles.css">',
        "<style>\n" + read("styles.css") + "</style>",
    )
    html = html.replace(
        '<script src="config.js"></script>',
        "<script>\n" + config + "</script>",
    )
    for src in ("questions.js", "app.js"):
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
    parser.add_argument("--submit-mode", default="",
                        help="config.js の mode を上書きする（off / apps-script / netlify / endpoint）")
    parser.add_argument("-o", "--out", default="standalone.html",
                        help="出力先（quiz/ からの相対パス）")
    args = parser.parse_args()

    html = build(args.submit_mode)
    if args.fragment:
        print(to_fragment(html))
        return

    out = HERE / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print("wrote %s (%.1f KB)" % (out, out.stat().st_size / 1024))


if __name__ == "__main__":
    main()
