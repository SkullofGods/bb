# -*- coding: utf-8 -*-
"""Сборка справочника мини-приложения с вики Boom Beach.

    py -3 tools/build.py

Кладёт данные в webapp/data и иконки в webapp/img.
Страницы вики кешируются в tools/cache — повторный запуск быстрый.
Чтобы перекачать вики заново, удали папку tools/cache.

Каталог силовых баз операций собирается отдельным скриптом:
    py -3 tools/build_bases.py
"""
import glob
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
from ru_names import RU, HDR, OPS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "webapp")
DATA = os.path.join(APP, "data")
IMG = os.path.join(APP, "img")
GAL = os.path.join(IMG, "gallery")
CACHE = os.path.join(ROOT, "tools", "cache")

API = "https://boombeach.fandom.com/api.php"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Referer": "https://boombeach.fandom.com/wiki/Boom_Beach_Wiki",
    "Accept": "image/avif,image/webp,image/png,*/*",
}

PAGES = {
    "troops": ["Rifleman", "Heavy", "Zooka", "Warrior", "Tank", "Medic", "Grenadier",
               "Scorcher", "Laser Ranger", "Cryoneer", "Bombardier", "Mech", "Rocket Choppa"],
    "proto_troops": ["Lazortron MK II.", "Rain Maker", "Critter Cannon MK II.", "Seeker",
                     "Heavy Choppa", "Turret Engineer", "Critter Engineer", "CryoBombardier",
                     "CryoTank", "Dr. Vitamin", "Hidden Warrior", "MegaScorcher",
                     "Melon Bombardier", "Protector", "Shockaneer", "Stunner",
                     "Undercover Rifleman", "Vampire Zooka", "Zombie Rifleman", "Clone Rifleman"],
    "gunboat": ["Artillery", "Flare", "Medkit", "Shock Bomb", "Barrage", "Smoke Screen",
                "Critters", "Gunboat"],
    "defenses": ["Sniper Tower", "Mortar", "Machine Gun", "Cannon", "Flamethrower",
                 "Boom Cannon", "Rocket Launcher", "Critter Launcher", "Shock Launcher",
                 "Mine", "Boom Mine", "Shock Mine", "Bunker", "Garrison", "Extra Garrison"],
    "proto_defenses": ["Boom Surprise", "Damage Amplifier", "Doom Cannon", "Flotsam Cannon",
                       "Grappler", "Hot Pot", "Lazor Beam", "Microwav'r", "S.I.M.O.",
                       "Shield Generator", "Shock Blaster", "Sky Shield"],
    "heroes": ["Sgt. Brick", "Cpt. Everspark", "Dr. Kavan", "Pvt. Bullit", "Cpt. Ruddero"],
    "buildings": ["Headquarters", "Landing Craft", "Armory", "Sculptor", "Vault", "Residence",
                  "Sawmill", "Quarry", "Iron Mine", "Radar", "Weapon Lab", "Proto Troop Workshop",
                  "Submarine", "Gold Storage", "Wood Storage", "Stone Storage", "Iron Storage",
                  "Statue Storage", "Engraver"],
    "meta": ["Operation", "Task Force", "Intel", "Force Point", "Power Core", "Statue",
             "Power Stone", "Abbreviations", "Attacking", "Defending", "Offensive Strategies",
             "Defensive Strategies", "Victory Point", "Matchmaking", "Blitz", "Warships",
             "Mega Crab", "Dr. T Threat Stages", "Imitation Game", "Boss Base", "Tribes",
             "Prototype Modules", "The War Factory", "Hammerman Strikes Back", "Sonar Ops",
             "Blackguard Base", "Mercenary Base", "Resource Base", "Tech Tree", "Barbed Wire",
             "Second Wind", "Player Guide"],
}

GROUP_RU = {
    "troops": "Войска", "proto_troops": "Прототипы войск", "gunboat": "Канонерка",
    "defenses": "Оборона", "proto_defenses": "Оборонные прототипы", "heroes": "Герои",
    "buildings": "Постройки", "meta": "Справочник",
}

SECTION_RU = {
    "Summary": "Коротко", "General Information": "Общая информация",
    "Offensive Strategy": "Как атаковать", "Offensive Strategies": "Как атаковать",
    "Defensive Strategy": "Как обороняться", "Defensive Strategies": "Как обороняться",
    "Trivia": "Интересное", "Upgrade Differences": "Что меняется с уровнем",
    "Statistics": "Характеристики", "Strategy": "Тактика", "Abilities": "Способности",
    "Attacking": "Атака", "Mechanics": "Механика", "History": "История",
    "Weaponry": "Вооружение", "Possible Statues": "Какие бывают статуи",
}

VAL_WORDS = [
    ("Not available at the moment!", "сейчас недоступно"),
    ("Very Fast", "очень быстрая"), ("Very Slow", "очень медленная"),
    ("Moderate", "средняя"), ("Medium", "средняя"), ("Slow", "медленная"),
    ("Fast", "быстрая"), ("Melee", "ближний бой"), ("Long", "длинная"),
    ("Short", "короткая"), ("Tiles", "кл."), ("Tile", "кл."), ("tiles", "кл."),
    ("Splash", "по площади"), ("Single", "по одной цели"),
    ("Ground and Air", "земля и воздух"), ("Ground", "земля"), ("Air", "воздух"),
    ("depends", "зависит"), ("None", "нет"), ("Yes", "да"), ("No", "нет"),
    ("Buildings", "постройки"), ("Troops", "войска"),
]
TIME_RE = [
    (re.compile(r"(\d)\s*d\b"), r"\1д"),
    (re.compile(r"(\d)\s*h\b"), r"\1ч"),
    (re.compile(r"(\d)\s*m\b"), r"\1м"),
    (re.compile(r"(\d)\s*s\b"), r"\1с"),
]


# ------------------------------------------------------------------ утилиты

def slug(s):
    s = unicodedata.normalize("NFKD", s)
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()


def tr(h):
    h = h.strip()
    if h in HDR:
        return HDR[h]
    for k, v in HDR.items():
        if h.lower() == k.lower():
            return v
    return h


def tr_val(v):
    s = str(v).strip()
    if s in ("N/A", "n/a", "-", "—", ""):
        return "—"
    for a, b in VAL_WORDS:
        s = s.replace(a, b)
    for rx, rep in TIME_RE:
        s = rx.sub(rep, s)
    return re.sub(r"(?<=\d),(?=\d{3}(\D|$))", "\u2009", s)


def api(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


# ------------------------------------------------------- разбор html-таблиц

class TableParser(HTMLParser):
    """Собирает таблицы страницы в матрицы с учётом rowspan/colspan."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.tables, self.skip = [], [], 0

    def cur(self):
        return self.stack[-1] if self.stack else None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self.stack.append({"r": -1, "cells": [], "cls": a.get("class", "")})
        elif tag == "tr" and self.cur():
            self.cur()["r"] += 1
        elif tag in ("td", "th") and self.cur():
            t = self.cur()
            t["cells"].append({"r": t["r"], "rs": int(a.get("rowspan") or 1),
                               "cs": int(a.get("colspan") or 1), "txt": []})
        elif tag == "br" and self.cur() and self.cur()["cells"]:
            self.cur()["cells"][-1]["txt"].append(" ")
        elif tag in ("style", "script"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag == "table" and self.stack:
            t = self.stack.pop()
            if not self.stack:
                self.tables.append(self.build(t))
        elif tag in ("style", "script") and self.skip:
            self.skip -= 1

    def handle_data(self, d):
        if self.skip or not self.cur():
            return
        c = self.cur()["cells"]
        if c:
            c[-1]["txt"].append(d)

    def build(self, t):
        grid, busy = {}, {}
        for cell in t["cells"]:
            r, col = cell["r"], 0
            while (r, col) in busy:
                col += 1
            txt = re.sub(r"\s+", " ", "".join(cell["txt"])).strip()
            for dr in range(cell["rs"]):
                for dc in range(cell["cs"]):
                    busy[(r + dr, col + dc)] = True
                    grid[(r + dr, col + dc)] = txt
        if not grid:
            return {"rows": [], "cls": t["cls"]}
        mr = max(k[0] for k in grid)
        mc = max(k[1] for k in grid)
        rows = [[grid.get((r, c), "") for c in range(mc + 1)] for r in range(mr + 1)]
        return {"rows": rows, "cls": t["cls"]}


def strip_html(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</(p|li|div|h2|h3)>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def page_sections(h):
    parts = re.split(r"<h([23])[^>]*>(.*?)</h\1>", h)
    out = []
    for i in range(1, len(parts), 3):
        title = strip_html(parts[i + 1]).strip()
        body = re.sub(r"<table[^>]*>.*?</table>", " ", parts[i + 2], flags=re.S)
        lines = [re.sub(r"\s+", " ", l).strip() for l in strip_html(body).split("\n")]
        lines = [l for l in lines if len(l) > 2 and not l.startswith("[")]
        if title and lines:
            out.append({"title": title, "lines": lines[:60]})
    return out


def main_image(h):
    m = re.search(r"<(?:aside|figure)[^>]*>.*?<img[^>]+src=\"([^\"]+)\"", h, re.S) or \
        re.search(r"<img[^>]+src=\"(https://static\.wikia[^\"]+)\"", h)
    if not m:
        return None
    u = re.sub(r"/revision/latest.*$", "", m.group(1))
    return re.sub(r"/scale-to-width-down/\d+", "", u)


def norm_table(rows):
    rows = [r for r in rows if any(c.strip() for c in r)]
    if len(rows) < 2:
        return None
    # строка-подпись на всю ширину (все ячейки одинаковые) — это заголовок таблицы
    caption = ""
    while len(rows) > 2 and len(set(c.strip() for c in rows[0])) == 1 and rows[0][0].strip():
        caption = tr(rows[0][0].strip())
        rows = rows[1:]
    head, start = rows[0], 1
    if len(rows) > 2 and rows[1][0].strip() == head[0].strip() and head[0].strip():
        merged = []
        for a, b in zip(head, rows[1]):
            a, b = a.strip(), b.strip()
            merged.append(tr(a) if a == b else (f"{tr(a)} · {tr(b)}" if a and b else tr(a or b)))
        head, start = merged, 2
    else:
        head = [tr(c) for c in head]
    body = rows[start:]
    keep = [i for i in range(len(head))
            if head[i].strip() or any(r[i].strip() for r in body if i < len(r))]
    head = [head[i] for i in keep]
    body = [[tr_val(r[i] if i < len(r) else "") for i in keep] for r in body]
    body = [r for r in body if any(c.strip() and c != "—" for c in r)]
    if not body:
        return None
    return {"title": caption, "headers": head, "rows": body}


SKIP_TABLE = re.compile(r"звук|sound|^deploy$|appearance|^level 1$", re.I)


def is_level_head(h):
    return h.strip().lower() in ("level", "mark number", "mark", "ур.", "марка")


def keep_extra(t):
    """Отсеивает таблицы-картинки и прочий мусор вики."""
    h = t["headers"]
    if len(h) < 2:
        return False
    flat = " ".join(h).lower()
    if "view full size" in flat or "full size image" in flat:
        return False
    if all(re.match(r"^level\s*\d", x.strip(), re.I) for x in h):
        return False
    if max(len(c) for r in t["rows"] for c in r) > 400:
        return False
    return True


def merge_early_access(levels, extras):
    """Приклеивает строки «раннего доступа» (минусовые уровни) к основной таблице."""
    if not levels:
        return levels, extras
    rest, early = [], None
    for t in extras:
        cap = (t.get("title") or "")
        if early is None and ("Ранний доступ" in cap or "Early Access" in cap) \
                and t["headers"] and is_level_head(t["headers"][0]):
            early = t
        else:
            rest.append(t)
    if not early:
        return levels, extras
    idx = {}
    for i, h in enumerate(early["headers"]):
        idx[tr(h)] = i
    added = []
    for r in early["rows"]:
        try:
            lvl = float(r[0].replace(" ", ""))
        except ValueError:
            continue
        if lvl >= 1:
            continue                      # дубли обычных уровней не нужны
        row = []
        for h in levels["headers"]:
            j = idx.get(h, -1)
            row.append(r[j] if 0 <= j < len(r) else "—")
        row[0] = r[0]
        added.append((lvl, row))
    if not added:
        return levels, rest
    added.sort(key=lambda x: x[0])
    levels = {"title": levels.get("title", ""), "headers": levels["headers"],
              "rows": [r for _, r in added] + levels["rows"]}
    return levels, rest


def pick_tables(tables):
    info, levels, extras = {}, None, []
    for t in tables:
        rows = t["rows"]
        if len(rows) < 2 or len(rows[0]) < 2:
            continue
        flat = " ".join(" ".join(r) for r in rows)
        if "•" in flat or "Wiki Navigation" in flat or len(flat) > 12000:
            continue
        head0 = " ".join(rows[0]).lower()
        if SKIP_TABLE.search(rows[0][0].strip()) or SKIP_TABLE.search(head0[:40]):
            continue
        if len(rows) == 2 and len(rows[0]) <= 12 and not is_level_head(rows[0][0]):
            for k, v in zip(rows[0], rows[1]):
                k, v = k.strip(), v.strip()
                if k and v and "+%" not in k and "Apply" not in k and "ApplyReset" not in v:
                    info[tr(k)] = tr_val(v)
            continue
        if is_level_head(rows[0][0]) and levels is None:
            nt = norm_table(rows)
            if nt:
                levels = nt
            continue
        if "hq level" in head0 and "number available" in " ".join(rows[1]).lower():
            avail = {k: v for k, v in zip(rows[0][1:], rows[1][1:]) if v.strip() not in ("", "0")}
            if avail:
                info["Доступно с уровня штаба"] = min(avail, key=lambda x: int(x) if x.isdigit() else 99)
                info["Максимум штук"] = max(avail.values(), key=lambda x: int(x) if x.isdigit() else 0)
            continue
        if "appearance" in head0 or "skin" in head0:
            continue
        nt = norm_table(rows)
        if nt and len(nt["rows"]) <= 40 and keep_extra(nt):
            extras.append(nt)
    levels, extras = merge_early_access(levels, extras)
    return info, levels, extras


# ------------------------------------------------------------------ загрузка

def fetch_page(title):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9_.-]", "_", title) + ".json")
    if os.path.exists(path) and os.path.getsize(path) > 500:
        return json.load(open(path, encoding="utf-8"))
    d = api({"action": "parse", "page": title, "prop": "text", "format": "json", "formatversion": "2"})
    if "error" in d:
        print("  нет страницы:", title)
        return None
    json.dump(d["parse"], open(path, "w", encoding="utf-8"), ensure_ascii=False)
    time.sleep(0.35)
    return d["parse"]


def dl_image(url, name):
    """Качает иконку и сразу жмёт в webp (если есть Pillow)."""
    os.makedirs(IMG, exist_ok=True)
    webp = os.path.join(IMG, name + ".webp")
    if os.path.exists(webp) and os.path.getsize(webp) > 300:
        return "img/" + name + ".webp"
    if not url:
        return None
    ext = ".png" if ".png" in url.lower() else ".jpg"
    raw = os.path.join(IMG, name + ext)
    try:
        data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        if len(data) < 300:
            return None
        open(raw, "wb").write(data)
        time.sleep(0.12)
    except Exception as e:
        print("  иконка не скачалась:", name, e)
        return None
    try:
        from PIL import Image
        im = Image.open(raw)
        im = im.convert("RGBA") if im.mode in ("P", "LA", "RGBA") else im.convert("RGB")
        if max(im.size) > 320:
            im.thumbnail((320, 320), Image.LANCZOS)
        im.save(webp, "WEBP", quality=82, method=6)
        os.remove(raw)
        return "img/" + name + ".webp"
    except ImportError:
        return "img/" + name + ext


# ------------------------------------------------------------------- сборка

def build_wiki():
    os.makedirs(DATA, exist_ok=True)
    ops_tables = None
    for group, titles in PAGES.items():
        arr = []
        for title in titles:
            parsed = fetch_page(title)
            if not parsed:
                continue
            h = parsed["text"]
            tp = TableParser()
            tp.feed(h)
            info, levels, extras = pick_tables(tp.tables)
            if title == "Operation":
                ops_tables = tp.tables
            sections = [{"title": SECTION_RU.get(s["title"], s["title"]),
                         "lines": [l for l in s["lines"] if len(l) > 15][:14]}
                        for s in page_sections(h) if s["title"] in SECTION_RU]
            sections = [s for s in sections if s["lines"]]
            ru = RU.get(title, (title, ""))[0]
            arr.append({
                "id": slug(title), "en": title, "ru": ru,
                "group": group, "groupRu": GROUP_RU.get(group, group),
                "img": dl_image(main_image(h), slug(title)),
                "info": info, "levels": levels, "extras": extras, "text": sections,
                "wiki": "https://boombeach.fandom.com/wiki/" + title.replace(" ", "_"),
            })
            print(f"  {group:15} {title:26} инфо={len(info):2} уровни={'да' if levels else '—'}")
        out = os.path.join(DATA, group + ".json")
        json.dump(arr, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print(f"{group}: {len(arr)} записей -> {os.path.basename(out)}")
    if ops_tables:
        build_ops(ops_tables)


def build_ops(tables):
    ops, sabotage = [], []
    for t in tables:
        rows = t["rows"]
        if not rows or len(rows[0]) < 2:
            continue
        head = " ".join(rows[0])
        if "Operation Name" in head:
            for r in rows[2:]:
                en = r[1].strip()
                ru, _, note = OPS.get(en, (en, "", ""))
                ops.append({
                    "n": int(re.sub(r"\D", "", r[0]) or 0), "en": en, "ru": ru,
                    "note": note,
                    "intel": {"5": r[2], "10": r[3], "25": r[4], "50": r[5]},
                    "fp": r[6].replace(",", "\u2009"), "bases": r[7],
                })
        elif "Sabotage Number" in head:
            sabotage = [{"n": r[0], "cost": r[1], "total": r[2]} for r in rows[1:]]
    out = os.path.join(DATA, "ops.json")
    json.dump({"ops": ops, "sabotage": sabotage}, open(out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"операции: {len(ops)} -> ops.json")


if __name__ == "__main__":
    build_wiki()
    print("Готово. Каталог баз операций собирается отдельно: py -3 tools/build_bases.py")
