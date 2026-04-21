Лабораторная работа №8 — вариант 1
Скачивание информации из сети через сервер задач и исполнителей

Почему решение соответствует методичке:
- реализовано приложение-сервер, раздающее задачи через очередь;
- реализовано приложение-исполнитель, получающее задачи и выполняющее скачивание;
- задачи можно распределять в пределах одного компьютера или локальной сети;
- исполнителям можно передавать либо список адресов, либо диапазон числовых id.

Файлы:
- lab8_shared_downloader.py
- lab8_server_downloader.py
- lab8_worker_downloader.py
- lab8_demo_http_server.py
- lab8_sample_urls.txt

Вариант A. Полностью локальная демонстрация на одном компьютере

1) Запустить локальный HTTP-сервер с тестовыми страницами:
python lab8_demo_http_server.py --host 127.0.0.1 --port 8000 --dir lab8_demo_site --start-id 1 --end-id 20

2) В новом терминале запустить сервер очереди задач:
python lab8_server_downloader.py --host 127.0.0.1 --port 50010 --authkey lab8down --base-url http://127.0.0.1:8000/page_{id}.html --start-id 1 --end-id 20 --output-dir downloads --summary-csv downloads_summary.csv --expected-workers 2

3) В двух других терминалах запустить исполнителей:
python lab8_worker_downloader.py --host 127.0.0.1 --port 50010 --authkey lab8down --name worker_1
python lab8_worker_downloader.py --host 127.0.0.1 --port 50010 --authkey lab8down --name worker_2

Вариант B. Передача списка адресов файлом

1) Подготовить текстовый файл, где на каждой строке один URL.
Можно использовать готовый lab8_sample_urls.txt

2) Запустить сервер:
python lab8_server_downloader.py --host 127.0.0.1 --port 50010 --authkey lab8down --url-file lab8_sample_urls.txt --output-dir downloads --summary-csv downloads_summary.csv --expected-workers 2

3) Запустить исполнителей:
python lab8_worker_downloader.py --host 127.0.0.1 --port 50010 --authkey lab8down --name worker_1
python lab8_worker_downloader.py --host 127.0.0.1 --port 50010 --authkey lab8down --name worker_2

Что делает программа:
- сервер формирует очередь задач;
- каждая задача содержит URL и параметры сохранения;
- исполнитель скачивает страницу по URL;
- результат отправляется обратно серверу;
- сервер сохраняет общую CSV-сводку по всем скачиваниям.
