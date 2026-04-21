#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


HTML_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Demo page {id}</title>
</head>
<body>
  <h1>Тестовая страница {id}</h1>
  <p>Эта страница создана для демонстрации лабораторной работы №8.</p>
  <p>ID страницы: {id}</p>
  <p>Содержимое можно безопасно скачивать локально.</p>
</body>
</html>
"""


def make_demo_pages(directory: Path, start_id: int, end_id: int) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for i in range(start_id, end_id + 1):
        path = directory / f"page_{i}.html"
        path.write_text(HTML_TEMPLATE.format(id=i), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Локальный HTTP-сервер с тестовыми страницами для ЛР8."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--dir", default="lab8_demo_site")
    parser.add_argument("--start-id", type=int, default=1)
    parser.add_argument("--end-id", type=int, default=20)
    args = parser.parse_args()

    site_dir = Path(args.dir).resolve()
    make_demo_pages(site_dir, args.start_id, args.end_id)

    handler = lambda *h_args, **h_kwargs: SimpleHTTPRequestHandler(*h_args, directory=str(site_dir), **h_kwargs)
    server = ThreadingHTTPServer((args.host, args.port), handler)

    print("Локальный demo HTTP сервер запущен.")
    print(f"Каталог: {site_dir}")
    print(f"Адрес: http://{args.host}:{args.port}")
    print(f"Пример страницы: http://{args.host}:{args.port}/page_{args.start_id}.html")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановка demo HTTP сервера...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
