#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import queue
import time
from multiprocessing.managers import BaseManager
from pathlib import Path
from urllib.request import Request, urlopen

from lab8_shared_downloader import safe_filename_from_url


class QueueManager(BaseManager):
    pass


QueueManager.register("get_task_queue")
QueueManager.register("get_result_queue")
QueueManager.register("get_stop_event")
QueueManager.register("get_start_event")
QueueManager.register("get_no_more_tasks_event")


def download_url(url: str, timeout: float) -> tuple[int, bytes]:
    req = Request(url, headers={"User-Agent": "Lab8Downloader/1.0"})
    with urlopen(req, timeout=timeout) as response:
        status_code = getattr(response, "status", 200)
        content = response.read()
    return status_code, content


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ЛР8: исполнитель задач скачивания информации из сети."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50010)
    parser.add_argument("--authkey", default="lab8down")
    parser.add_argument("--name", default="worker")
    parser.add_argument("--connect-retries", type=int, default=15)
    parser.add_argument("--retry-delay", type=float, default=1.0)
    args = parser.parse_args()

    manager = QueueManager(address=(args.host, args.port), authkey=args.authkey.encode("utf-8"))

    connected = False
    for attempt in range(1, args.connect_retries + 1):
        try:
            manager.connect()
            connected = True
            break
        except ConnectionRefusedError:
            print(f"{args.name}: сервер ещё недоступен, попытка {attempt}/{args.connect_retries}...")
            time.sleep(args.retry_delay)

    if not connected:
        raise ConnectionRefusedError(
            f"{args.name}: не удалось подключиться к серверу {args.host}:{args.port}. "
            f"Проверь, что сервер запущен и порт совпадает."
        )

    task_queue = manager.get_task_queue()
    result_queue = manager.get_result_queue()
    stop_event = manager.get_stop_event()
    start_event = manager.get_start_event()
    no_more_tasks_event = manager.get_no_more_tasks_event()

    print(f"{args.name}: подключён к серверу {args.host}:{args.port}")
    result_queue.put({"type": "ready", "worker": args.name})
    print(f"{args.name}: ожидает общий старт...")

    while not start_event.is_set():
        if stop_event.is_set():
            print(f"{args.name}: сервер остановлен до старта.")
            return
        time.sleep(0.1)

    print(f"{args.name}: старт обработки задач.")

    while not stop_event.is_set():
        try:
            task = task_queue.get(timeout=1.0)
        except queue.Empty:
            # Если новых задач больше не будет и очередь уже пуста,
            # исполнитель завершает работу корректно.
            if no_more_tasks_event.is_set():
                break
            continue

        if task is None:
            break

        task_id = task["task_id"]
        url = task["url"]
        output_dir = Path(task["output_dir"])
        timeout = float(task["timeout"])

        t1 = time.perf_counter()
        try:
            status_code, content = download_url(url, timeout=timeout)
            filename = safe_filename_from_url(url)
            save_path = output_dir / filename
            save_path.write_bytes(content)

            elapsed = time.perf_counter() - t1
            result_queue.put({
                "type": "result",
                "task_id": task_id,
                "worker": args.name,
                "url": url,
                "ok": True,
                "status_code": status_code,
                "size": len(content),
                "saved_path": str(save_path),
                "elapsed": elapsed,
                "error": "",
            })
        except Exception as e:
            elapsed = time.perf_counter() - t1
            result_queue.put({
                "type": "result",
                "task_id": task_id,
                "worker": args.name,
                "url": url,
                "ok": False,
                "status_code": "",
                "size": 0,
                "saved_path": "",
                "elapsed": elapsed,
                "error": str(e),
            })

    result_queue.put({"type": "finished", "worker": args.name})
    print(f"{args.name}: завершение.")


if __name__ == "__main__":
    main()
