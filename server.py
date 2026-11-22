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
import json
import os
import re
import signal
import socket
import sys
import threading
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE_DIR, "webapp")

# bothost передаёт порт в PORT и по умолчанию ждёт 3000; аргумент командной
# строки важнее — им удобно пользоваться локально
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT") or 3000)

# --- ИИ-помощник (api.groq.com). Ключ живёт на сервере, в приложение не попадает ---
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "").strip()
GROQ_API = "https://api.groq.com/openai/v1"

AI_SYSTEM = (
    "Ты — игровой помощник в справочнике опергруппы Boom Beach (Telegram-мини-приложение). "
    "Отвечай по-русски, коротко и по делу: несколько предложений или компактный список. "
    "Темы: связки войск и мета, оборона своей базы, операции и силовые базы, прототипы и герои, "
    "статуи, энергия канонерки, экономика. Используй русские названия юнитов из чата игроков: "
    "гора (Heavy), базука (Zooka), огневик (Scorcher), заморозка (Cryoneer), смек (Smokey Warriors) и подобные. "
    "Не выдумывай точные цифры урона и прочности; если не уверен — так и скажи. "
    "Если вопрос совсем не про Boom Beach — мягко верни разговор к игре."
)

_groq_model = {"picked": ""}

# --- база знаний: ИИ получает выдержки из нашего же справочника, чтобы не фантазировал ---
KB = {"chunks": [], "ready": False}


def _c(*name):
    path = os.path.join(ROOT, "content", *name)
    try:
        return json.load(open(path, encoding="utf-8"))
    except OSError:
        return None


def _build_kb():
    if KB["ready"]:
        return
    chunks = []

    def add(title, searchable, text, cap=900):
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            head = (title + " " + searchable).lower()
            chunks.append({"title": title, "head": head,
                           "find": head + " " + text.lower(), "text": text[:cap]})

    ru_text = _c("ru_text.json") or {}
    ru_wiki = _c("ru_wiki.json") or {}
    for group in ("troops", "proto_troops", "gunboat", "defenses", "proto_defenses", "heroes", "buildings", "meta"):
        arr = _c(group + ".json")
        if not arr:
            continue
        for e in arr:
            key = f"{group}:{e.get('id', '')}"
            title = f"{e.get('ru', '')} ({e.get('en', '')})"
            t = ru_text.get(key) or {}
            parts = []
            if t.get("s"):
                parts.append(t["s"])
            for u in (t.get("u") or [])[:3]:
                parts.append(u)
            w = ru_wiki.get(key) or {}
            for sect, lines in w.items():
                parts.append(sect + ": " + " ".join(lines[:3]))
            add(title, " ".join(e.get("alias") or []), title + ". " + " ".join(parts))
    guide = _c("guide.json")
    for a in (guide or {}).get("articles", []):
        txt = []
        for b in a.get("blocks", []):
            if b.get("t") in ("p", "tip", "warn"):
                txt.append(b["v"])
            elif b.get("t") in ("ul", "ol"):
                txt.extend(b["v"])
            elif b.get("t") == "h":
                txt.append(b["v"])
        add("Гайд: " + a.get("title", ""), "", " ".join(txt), cap=1400)
    for u in (_c("updates.json") or [])[:6]:
        lines = []
        for s in u.get("s", []):
            lines.append((s.get("h", "") + ": " if s.get("h") else "") + " ".join(s.get("v", [])[:8]))
        add("Обновление игры: " + u.get("t", ""), u.get("d", ""), u.get("d", "") + ". " + " ".join(lines), cap=1200)
    KB["chunks"] = chunks
    KB["ready"] = True
    print(f"База знаний ИИ: {len(chunks)} выдержек", flush=True)


def _kb_context(question, limit=5):
    """Топ выдержек по совпадению слов вопроса. Нет совпадений — нет контекста."""
    _build_kb()
    words = [w for w in re.findall(r"[а-яёa-z0-9]{4,}", question.lower())]
    if not words:
        return ""
    # грубый стемминг: отрезаем окончания, чтобы «заморозки» находила «заморозка»
    stems = [w if len(w) <= 4 else w[:len(w) - (2 if len(w) > 6 else 1)] for w in words]
    scored = []
    for c in KB["chunks"]:
        score = 0
        for st in stems:
            n = c["find"].count(st)
            if n:
                score += n + (2 if st in c["head"] else 0)
        if score:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return ""
    return "\n\n".join(f"[{c['title']}]\n{c['text']}" for _, c in scored[:limit])


def _pick_groq_model():
    """Groq регулярно выводит модели из строя — берём первую живую из списка.
    Список доступных скачивается один раз и запоминается."""
    if _groq_model["picked"]:
        return _groq_model["picked"]
    pref = ([GROQ_MODEL] if GROQ_MODEL else []) + [
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-120b",
        "llama-3.1-8b-instant",
        "moonshotai/kimi-k2-instruct",
    ]
    ids = []
    try:
        req = urllib.request.Request(GROQ_API + "/models",
                                     headers={"Authorization": "Bearer " + GROQ_KEY,
                                              "User-Agent": "bb-miniapp"})
        with urllib.request.urlopen(req, timeout=15) as r:
            ids = [m.get("id", "") for m in json.load(r).get("data", [])]
    except Exception as e:
        print(f"Список моделей Groq не получился ({e.__class__.__name__}), идём по умолчанию", flush=True)
    for p in pref:
        if p and p in ids:
            _groq_model["picked"] = p
            break
    else:
        _groq_model["picked"] = next((i for i in ids if "llama" in i.lower()), pref[1] if len(pref) > 1 else pref[0])
    print(f"ИИ-помощник: модель {_groq_model['picked']}", flush=True)
    return _groq_model["picked"]

# Данные и разметка должны обновляться сразу, картинки можно держать в кеше долго
NO_CACHE = (".html", ".json")
LONG_CACHE = (".webp", ".png", ".jpg", ".jpeg", ".svg", ".ico")


class Handler(http.server.SimpleHTTPRequestHandler):
    # HTTP/1.1 — соединение переиспользуется. На мобильной связи это заметно:
    # приложение тянет десяток файлов сразу, и рукопожатие на каждый дорого
    protocol_version = "HTTP/1.1"
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

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.split("?")[0] != "/api/ask":
            self._json(404, {"error": "такого запроса нет"})
            return
        try:
            size = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(size).decode("utf-8") or "{}")
        except Exception:
            self._json(400, {"error": "не понял запрос"})
            return
        if not GROQ_KEY:
            self._json(503, {"error": "ИИ не настроен: на сервере не задан GROQ_API_KEY"})
            return
        question = str(body.get("q") or "").strip()[:1200]
        if not question:
            self._json(400, {"error": "пустой вопрос"})
            return
        # историю шлёт приложение; системную инструкцию добавляет только сервер,
        # чтобы её нельзя было подменить с клиента
        system = AI_SYSTEM
        ctx = _kb_context(question)
        if ctx:
            system += ("\n\nНиже — выдержки из справочника этого приложения. Если они относятся к вопросу, "
                       "отвечай строго по ним: точные цифры, уровни и названия приводи только из выдержек. "
                       "Если нужного в выдержках нет — скажи прямо, что точных данных в справочнике нет, "
                       "и дай общий совет без выдуманных цифр.\n\n" + ctx)
        msgs = [{"role": "system", "content": system}]
        for m in (body.get("history") or [])[-12:]:
            if isinstance(m, dict) and m.get("role") in ("user", "assistant") \
                    and isinstance(m.get("content"), str) and m["content"].strip():
                msgs.append({"role": m["role"], "content": m["content"][:1500]})
        msgs.append({"role": "user", "content": question})
        try:
            payload = json.dumps({
                "model": _pick_groq_model(),
                "messages": msgs,
                "temperature": 0.4,
                "max_tokens": 700,
            }).encode("utf-8")
            req = urllib.request.Request(GROQ_API + "/chat/completions", data=payload, headers={
                "Authorization": "Bearer " + GROQ_KEY,
                "Content-Type": "application/json",
                "User-Agent": "bb-miniapp",
            })
            with urllib.request.urlopen(req, timeout=45) as r:
                out = json.load(r)
            reply = out["choices"][0]["message"]["content"].strip()
            self._json(200, {"reply": reply})
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = json.load(e).get("error", {}).get("message", "")[:200]
            except Exception:
                pass
            print(f"Groq ответил ошибкой {e.code}: {detail}", flush=True)
            self._json(502, {"error": "ИИ временно недоступен, попробуй ещё раз минут через пять"})
        except Exception as e:
            print(f"Запрос к Groq сорвался: {e.__class__.__name__}: {e}", flush=True)
            self._json(502, {"error": "ИИ не ответил — проверь связь и попробуй ещё раз"})

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
        elif name.endswith(".html") or name.endswith("/"):
            # разметку не кешируем совсем: webview Telegram цепко держит
            # старую страницу, и обновление до людей не доезжает
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        elif name.endswith(NO_CACHE):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):
        # Пишем все запросы: по логам видно, доходит ли вообще обращение
        # с телефона и какие файлы он успевает забрать
        ua = self.headers.get("User-Agent", "")[:60]
        sys.stdout.write(f"{self.address_string()} {fmt % args} | {ua}\n")
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
    print("ИИ-помощник: " + ("включён, ключ Groq на месте" if GROQ_KEY
                            else "выключен — задай переменную GROQ_API_KEY, чтобы кнопка заработала"),
          flush=True)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
        print("Сервер остановлен", flush=True)


if __name__ == "__main__":
    main()
