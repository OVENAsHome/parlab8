#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import queue
import threading
import time
from multiprocessing.managers import BaseManager
from pathlib import Path

from lab8_shared_downloader import build_urls_from_range, ensure_dir, read_url_list


task_queue = queue.Queue()
result_queue = queue.Queue()
stop_event = threading.Event()
start_event = threading.Event()
no_more_tasks_event = threading.Event()


def get_task_queue():
    return task_queue


def get_result_queue():
    return result_queue


def get_stop_event():
    return stop_event


def get_start_event():
    return start_event


def get_no_more_tasks_event():
    return no_more_tasks_event


class QueueManager(BaseManager):
    pass


QueueManager.register("get_task_queue", callable=get_task_queue)
QueueManager.register("get_result_queue", callable=get_result_queue)
QueueManager.register("get_stop_event", callable=get_stop_event)
QueueManager.register("get_start_event", callable=get_start_event)
QueueManager.register("get_no_more_tasks_event", callable=get_no_more_tasks_event)


CSV_FIELDS = [
    "task_id", "worker", "url", "ok", "status_code",
    "size", "saved_path", "elapsed", "error"
]


def load_urls(args) -> list[str]:
    if args.url_file:
        return read_url_list(args.url_file)
    return build_urls_from_range(args.base_url, args.start_id, args.end_id)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ЛР8: сервер очереди задач для скачивания информации из сети."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50010)
    parser.add_argument("--authkey", default="lab8down")
    parser.add_argument("--url-file", help="Файл со списком URL, по одному на строку.")
    parser.add_argument("--base-url", help='Шаблон URL, например: "http://127.0.0.1:8000/page_{id}.html"')
    parser.add_argument("--start-id", type=int)
    parser.add_argument("--end-id", type=int)
    parser.add_argument("--output-dir", default="downloads")
    parser.add_argument("--summary-csv", default="downloads_summary.csv")
    parser.add_argument("--expected-workers", type=int, default=2)
    parser.add_argument("--wait-workers-timeout", type=float, default=30.0)
    parser.add_argument("--request-timeout", type=float, default=10.0)
    args = parser.parse_args()

    use_file_mode = bool(args.url_file)
    use_range_mode = args.base_url is not None and args.start_id is not None and args.end_id is not None

    if not (use_file_mode or use_range_mode):
        raise ValueError("Нужно указать либо --url-file, либо --base-url с --start-id и --end-id.")

    urls = load_urls(args)
    if not urls:
        raise ValueError("Список URL пуст.")

    ensure_dir(args.output_dir)
    stop_event.clear()
    start_event.clear()
    no_more_tasks_event.clear()

    print("Запуск сервера задач...")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Количество URL: {len(urls)}")
    print(f"Каталог загрузки: {Path(args.output_dir).resolve()}")
    print("Первые URL в очереди:")
    for u in urls[:5]:
        print(" ", u)

    manager = QueueManager(address=(args.host, args.port), authkey=args.authkey.encode("utf-8"))
    server = manager.get_server()

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    time.sleep(1.0)
    print("Сервер задач готов принимать подключения.")
    print(f"Ожидание {args.expected_workers} исполнителей...")

    ready_workers = set()
    wait_started = time.perf_counter()

    try:
        while len(ready_workers) < args.expected_workers:
            if time.perf_counter() - wait_started > args.wait_workers_timeout:
                raise TimeoutError(
                    f"Не дождались нужного числа исполнителей. "
                    f"Подключено: {len(ready_workers)} из {args.expected_workers}"
                )

            try:
                message = result_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if message.get("type") == "ready":
                worker_name = message["worker"]
                if worker_name not in ready_workers:
                    ready_workers.add(worker_name)
                    print(f"[ready] Подключился исполнитель: {worker_name} ({len(ready_workers)}/{args.expected_workers})")

        print("Все исполнители подключились. Выдаём задачи и запускаем общую обработку.")

        for idx, url in enumerate(urls, start=1):
            task_queue.put({
                "task_id": idx,
                "url": url,
                "output_dir": str(Path(args.output_dir).resolve()),
                "timeout": args.request_timeout,
            })

        # Все задачи уже помещены в очередь. Новых задач больше не будет.
        no_more_tasks_event.set()

        start_time = time.perf_counter()
        start_event.set()

        received_results = 0
        finished_workers = set()
        rows = []

        while True:
            if received_results >= len(urls) and len(finished_workers) >= args.expected_workers:
                break

            try:
                message = result_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            msg_type = message.get("type")

            if msg_type == "result":
                received_results += 1
                rows.append(message)

                status = "OK" if message["ok"] else "ERROR"
                if message["ok"]:
                    print(
                        f"[{received_results}/{len(urls)}] {status} | "
                        f"{message['worker']:<10} | "
                        f"{message['url']} | "
                        f"size={message.get('size', 0)} | "
                        f"time={message.get('elapsed', 0):.3f}s"
                    )
                else:
                    print(
                        f"[{received_results}/{len(urls)}] {status} | "
                        f"{message['worker']:<10} | "
                        f"{message['url']} | "
                        f"error={message.get('error', '')} | "
                        f"time={message.get('elapsed', 0):.3f}s"
                    )

            elif msg_type == "finished":
                worker_name = message["worker"]
                if worker_name not in finished_workers:
                    finished_workers.add(worker_name)
                    print(
                        f"[finished] {worker_name} завершил работу "
                        f"({len(finished_workers)}/{args.expected_workers})"
                    )

        elapsed = time.perf_counter() - start_time

        with open(args.summary_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        success_count = sum(1 for row in rows if row["ok"])
        print("\nИтог сервера:")
        print(f"Всего задач: {len(urls)}")
        print(f"Получено результатов: {received_results}")
        print(f"Завершивших исполнителей: {len(finished_workers)}")
        print(f"Успешно скачано: {success_count}")
        print(f"Ошибок: {len(urls) - success_count}")
        print(f"Время работы: {elapsed:.3f} c")
        print(f"Сводка сохранена в: {Path(args.summary_csv).resolve()}")

    finally:
        stop_event.set()
        start_event.set()
        no_more_tasks_event.set()
        print("Сервер завершён.")


if __name__ == "__main__":
    main()
