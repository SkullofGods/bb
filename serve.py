# -*- coding: utf-8 -*-
"""Локальный сервер для проверки мини-приложения.

    py -3 serve.py            # http://localhost:8765
    py -3 serve.py 9000       # другой порт

Это только для проверки на компьютере. Telegram открывает мини-приложения
исключительно по https — как выложить приложение в сеть, написано в README.md.
"""
import http.server
import os
import socket
import socketserver
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = dict(http.server.SimpleHTTPRequestHandler.extensions_map)
    extensions_map.update({
        ".webp": "image/webp",
        ".json": "application/json; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".html": "text/html; charset=utf-8",
    })

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        # во время правки удобнее без кеша
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        if "200" not in fmt % args:
            super().log_message(fmt, *args)


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
        print(f"Мини-приложение:  http://localhost:{PORT}")
        print(f"С телефона в той же сети:  http://{local_ip()}:{PORT}")
        print("Остановить — Ctrl+C")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nОстановлено.")
