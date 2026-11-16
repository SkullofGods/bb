# -*- coding: utf-8 -*-
"""Каталог силовых баз операций из скриншотов разведки в выгрузке чата.

    py -3 tools/build_bases.py [путь к ChatExport_...]

Список BASES ниже собран вручную: название, уровень и очки силы прочитаны
с самих скриншотов. Чтобы добавить базу — положи скрин в webapp/img/bases
и допиши запись в webapp/data/bases.json (формат описан в README).
"""
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "webapp")
OUTDIR = os.path.join(APP, "img", "bases")
THUMBS = os.path.join(OUTDIR, "t")

# файл из выгрузки -> (название базы, уровень базы, максимум очков силы, № операций)
# Номера операций проставлены там, где это прямо следует из переписки:
# 13.12.2024 — «скрины двойных баз из дуплексности» (операция 24).
BASES = [
    ("photo_21@13-10-2024_18-00-28.jpg",   "Долгопят",           125, 190, []),
    ("photo_22@13-10-2024_18-00-28.jpg",   "Механический хруст", 125, 190, []),
    ("photo_94@17-10-2024_08-28-19.jpg",   "Мантикора",          161, 300, []),
    ("photo_106@18-10-2024_16-37-51.jpg",  "Лабиринт",           161, 300, []),
    ("photo_164@22-10-2024_19-51-37.jpg",  "Лабиринт",           153, 251, []),
    ("photo_211@26-10-2024_17-25-34.jpg",  "Квота",               96,  94, []),
    ("photo_254@29-10-2024_17-56-25.jpg",  "Броненосец",         109, 185, []),
    ("photo_324@10-11-2024_17-50-54.jpg",  "Троица",             170, 320, []),
    ("photo_325@10-11-2024_17-50-54.jpg",  "Дежавю",             177, 330, []),
    ("photo_327@10-11-2024_17-50-54.jpg",  "Гармония",           183, 350, []),
    ("photo_333@13-11-2024_12-53-20.jpg",  "Квота",               79, 118, []),
    ("photo_417@13-12-2024_16-45-18.jpg",  "Гармония",           170, 320, [24]),
    ("photo_418@13-12-2024_16-45-18.jpg",  "Подбородок",         177, 330, [24]),
    ("photo_419@13-12-2024_16-45-18.jpg",  "Материнская плата",  158, 300, [24]),
    ("photo_420@13-12-2024_16-45-18.jpg",  "Позвоночник",        170, 320, [24]),
    ("photo_421@13-12-2024_16-45-18.jpg",  "Дежавю",             183, 350, [24]),
    ("photo_423@13-12-2024_16-45-18.jpg",  "ВПП",                183, 350, [24]),
    ("photo_436@17-12-2024_18-50-43.jpg",  "Орбифольд",          125, 190, []),
    ("photo_781@30-10-2025_19-16-37.jpg",  "Хардкор",            164, 292, []),
]

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e",
    "ю": "yu", "я": "ya", " ": "-", "-": "-",
}


def slug(name):
    s = "".join(TRANSLIT.get(ch, ch if ch.isalnum() else "-") for ch in name.lower())
    return re.sub(r"-+", "-", s).strip("-")


def find_export():
    for p in sorted(glob.glob(os.path.join(ROOT, "ChatExport_*")), reverse=True):
        if os.path.isdir(p):
            return p
    return ""


def main():
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("Нужен Pillow:  py -3 -m pip install pillow")
    export = sys.argv[1] if len(sys.argv) > 1 else find_export()
    if not export or not os.path.isdir(export):
        raise SystemExit("Не нашёл папку выгрузки чата рядом с проектом")

    os.makedirs(THUMBS, exist_ok=True)
    bases = {}
    for fname, name, lvl, fp, ops in BASES:
        src = os.path.join(export, "photos", fname)
        if not os.path.exists(src):
            print("  нет файла:", fname)
            continue
        key = slug(name)
        b = bases.setdefault(key, {"id": key, "name": name, "ops": [], "note": "", "shots": []})
        for o in ops:
            if o not in b["ops"]:
                b["ops"].append(o)
        out = f"{key}-{len(b['shots']) + 1}"
        im = Image.open(src).convert("RGB")
        big = im.copy()
        big.thumbnail((1600, 1600), Image.LANCZOS)
        big.save(os.path.join(OUTDIR, out + ".webp"), "WEBP", quality=80, method=5)
        sm = im.copy()
        sm.thumbnail((420, 420), Image.LANCZOS)
        sm.save(os.path.join(THUMBS, out + ".webp"), "WEBP", quality=70, method=5)
        date = re.search(r"@(\d{2}-\d{2}-\d{4})", fname)
        b["shots"].append({
            "img": "img/bases/" + out + ".webp",
            "thumb": "img/bases/t/" + out + ".webp",
            "lvl": lvl, "fp": fp,
            "date": date.group(1).replace("-", ".") if date else "",
        })

    out = sorted(bases.values(), key=lambda b: -max(s["fp"] for s in b["shots"]))
    json.dump(out, open(os.path.join(APP, "data", "bases.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"баз: {len(out)}, скринов: {sum(len(b['shots']) for b in out)} -> data/bases.json")
    for b in out:
        print(f"  {b['name']:22} {len(b['shots'])} скрин(ов), очки силы: "
              f"{', '.join(str(s['fp']) for s in b['shots'])}, операции: {b['ops'] or '—'}")


if __name__ == "__main__":
    main()
