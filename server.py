# -*- coding: utf-8 -*-
"""Веб-сервер мини-приложения: отдаёт папку webapp.

На хостинге (bothost) порт приходит в переменной PORT, слушать нужно 0.0.0.0 —
иначе прокси хостинга не достучится и отдаст Bad Gateway, а контейнер получит
SIGTERM. Локально порт можно задать аргументом:

    py -3 server.py           # http://localhost:3000
    py -3 server.py 9000      # другой порт

Точка входа на хостинге — bot.py: он поднимает этот сервер, а бота добавляет
только если тот настроен.
"""
import http.server
import os
import signal
import socket
import sys
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE_DIR, "webapp")

# bothost передаёт порт в PORT и по умолчанию ждёт 3000; аргумент командной
# строки важнее — им удобно пользоваться локально
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT") or 3000)

# Данные и разметка должны обновляться сразу, картинки можно держать в кеше долго
NO_CACHE = (".html", ".json")
LONG_CACHE = (".webp", ".png", ".jpg", ".jpeg", ".svg", ".ico")


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = dict(http.server.SimpleHTTPRequestHandler.extensions_map)
    extensions_map.update({
        ".webp": "image/webp",
        ".json": "application/json; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".svg": "image/svg+xml",
    })

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def do_GET(self):
        # Проверка живости для хостинга
        if self.path.split("?")[0] in ("/health", "/healthz"):
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def send_head(self):
        """Неизвестный путь отдаём как index.html — приложение одностраничное."""
        path = self.translate_path(self.path)
        if not os.path.exists(path) and "." not in os.path.basename(path):
            self.path = "/"
        return super().send_head()

    def end_headers(self):
        name = self.path.split("?")[0].lower()
        if name.endswith(LONG_CACHE):
            self.send_header("Cache-Control", "public, max-age=604800")
        elif name.endswith(NO_CACHE) or name.endswith("/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):
        msg = fmt % args
        if " 200 " not in msg and " 304 " not in msg:
            sys.stdout.write(f"{self.address_string()} {msg}\n")
            sys.stdout.flush()


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def main():
    if not os.path.isdir(ROOT):
        raise SystemExit(f"Нет папки с приложением: {ROOT}")

    httpd = Server(("0.0.0.0", PORT), Handler)

    def shutdown(signum, _frame):
        print(f"Получен сигнал {signum}, останавливаюсь", flush=True)
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, shutdown)
        except (ValueError, AttributeError, OSError):
            pass  # сигналы ставятся только из главного потока

    # Короткая опись того, что реально доехало до контейнера: если какой-то
    # папки нет, это сразу видно в логах, а не по россыпи 404
    try:
        parts = []
        for name in sorted(os.listdir(ROOT)):
            full = os.path.join(ROOT, name)
            parts.append(f"{name}/{len(os.listdir(full))}" if os.path.isdir(full) else name)
        print(f"Содержимое {ROOT}: {', '.join(parts)}", flush=True)
    except OSError as e:
        print(f"Не смог прочитать {ROOT}: {e}", flush=True)

    print(f"Мини-приложение слушает 0.0.0.0:{PORT}", flush=True)
    print(f"Локально: http://localhost:{PORT}  ·  в сети: http://{local_ip()}:{PORT}", flush=True)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
        print("Сервер остановлен", flush=True)


if __name__ == "__main__":
    main()
