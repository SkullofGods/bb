# -*- coding: utf-8 -*-
"""Сборка справочника мини-приложения с вики Boom Beach.

    py -3 tools/build.py

Кладёт данные в webapp/content и иконки в webapp/img.
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
DATA = os.path.join(APP, "content")
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

# Целые значения-предложения: точное совпадение до всех остальных правил.
SENTENCES = {
    "If destroyed, the battle ends.": "Если разрушен — бой заканчивается.",
    "If all Power Cores are destroyed, the battle ends.": "Если разрушены все сердца силы — бой заканчивается.",
    "Spawns Critters": "Выпускает криттеров",
    "Immobilizes Troops": "Обездвиживает войска",
    "Spawns Garrison Units after getting destroyed": "При разрушении выпускает гарнизонные войска",
    "Summoned Units": "Призванные войска",
    "Grabs an enemy unit and drags it next to the Grappler": "Хватает юнита гарпуном и подтаскивает к себе",
    "Damages all units within range at the same time Ignores Smoke Screens":
        "Бьёт всех в радиусе одновременно; игнорирует дымовую завесу",
    "Can target troops under Smoke Screens Prioritizes targets with lower health.":
        "Стреляет по войскам под дымом; добивает цели с наименьшим здоровьем.",
    "Creates a shield around the Headquarters, Power Core, Mega Core or Engine Rooms.":
        "Ставит щит вокруг штаба, сердца силы или машинных отделений.",
    "Creates a shield around itself against Gunboat Weaponry":
        "Купол вокруг себя, блокирующий оружие канонерки",
    "Boosts the amount of damage that defenses near it deal. Does not deal damage by itself.":
        "Усиливает урон соседних оборонок. Сам урона не наносит.",
    "Prioritises Core Buildings over everything.": "Бьёт в первую очередь по ключевым постройкам.",
    "Prioritise Core Buildings over everything.": "Бьёт в первую очередь по ключевым постройкам.",
    "Yes, Promote up to Co-leaders and Demote Officers to Members":
        "да — повышать до соруководителя, понижать офицеров",
    "Yes, only Officers and Members": "да — только офицеров и участников",
    "Yes, only Members once every 20 min": "да — участников, раз в 20 мин",
    "Yes, only Members once every 20 minutes": "да — участников, раз в 20 мин",
    "no change": "без изменений",
    "Training Screen": "Экран обучения",
    "Storage Screen": "Экран хранилища",
    "No Proto Troop available": "нет готовых прототипов",
    "Grenade Spammer": "Гранатный шквал",
    "Robot Overlord": "Владыка роботов",
    "Galvanizing Presence": "Воодушевляющее присутствие",
    "Pain Tolerance": "Толстая шкура",
    "Wingmen": "Напарники",
    "Wingman Rush": "Рывок напарников",
    "Bombing Run": "Бомбовый удар",
    "Seeker Shot": "Выстрел искателя",
    # способности героев (имена — по русской вики, где она есть)
    "Cluster Grenade": "Кассетная граната",
    "Iron Will": "Железная воля",
    "Battle Orders": "Боевые приказы",
    "Critter Swarm": "Рой криттеров",
    "Explosive Charges": "Взрывной заряд",
    "Universal Remote": "Суперпульт",
    "Crystal Critters": "Крискриттеры",
    "Ice Shields": "Ледяные щиты",
    "Second Wind": "Второе дыхание",
    "Taunt": "Провокация",
    "Energy Drink": "Бодрящий напиток",
    "Shock Knuckles": "Кастет-шокер",
    # остальное
    "Blackguard or Mercenary Invasion": "Вторжение Стражей Тьмы или наёмников",
    "Boss Base Destroyed": "База босса разрушена",
    "Chest Found by Exploring (when opened, first time only)":
        "Сундук найден при исследовании (при первом открытии)",
    "Colonel Gearheart's level 90 War Factory event":
        "Событие «Военная фабрика» полковника Гирхарт, 90 ур.",
    "Dr. T Event Base Destroyed": "База события Доктора Т разрушена",
    "Home Base Destroyed": "Домашняя база разрушена",
    "Imitation Stage cleared": "Стадия имитации пройдена",
    "Initiate Friendly Challenges": "Устраивать дружеские вызовы",
    "Manage Pinned Messages": "Закреплять сообщения",
    "Report other Users": "Жаловаться на игроков",
    "Mega Crab or Mega Turtle Stage cleared": "Стадия Мегакраба или Мегачерепахи пройдена",
    "NPC Blackguard Base Destroyed": "База Стражей Тьмы (NPC) разрушена",
    "Player Mercenary Base Destroyed": "База наёмников разрушена",
    "Power Base destroyed": "Силовая база разрушена",
    "No change": "без изменений",
    "Time Savers": "Ускорители времени",
    "Unknown Prototroop using Zooka as a Placeholder": "Неизвестный прототип (заглушка — Базука)",
    "Special Buildings³": "Особые постройки³",
    "Stealth": "Невидимость",
    "Classified Items": "Секретные предметы",
    "Lab Level": "Ур. лаборатории",
    "Garrison Units attack enemy troops that are within the Garrison's range. "
    "Additionally, a new Garrison Unit is spawned whenever one is defeated.":
        "Гарнизонные войска атакуют врагов в радиусе гарнизона; "
        "за каждого убитого появляется новый.",
    "Continues to burn units for 5 seconds after they have received damage from it.^":
        "Подожжённые войска горят ещё 5 с после попадания.^",
    "distinct between 40s and 6m (based on level)": "40 с — 6 мин, зависит от уровня",
    "Defensive Buildings": "Оборонные постройки",
    "Prototype Defenses": "Прототипы обороны",
    "Special Buildings": "Особые постройки",
    "Traps": "Ловушки",
    # описания оружия канонерки (таблица «Вооружение»)
    "A single shot that damages enemy Buildings and triggers Mines":
        "Одиночный выстрел: повреждает постройки и подрывает мины",
    "Once one lands temporarily on the battlefield, Troops move towards it but cannot attack while doing so. "
    "If it hits a building, troops will walk to it until they are in range to attack it.":
        "Войска идут к точке падения и не атакуют на ходу. "
        "Если ракета попала в постройку — идут, пока не окажутся в радиусе атаки.",
    "Creates a temporary ring of healing that restores the health of Troops within its area of effect":
        "Временное кольцо лечения: восстанавливает здоровье войск в зоне действия",
    "Temporarily prevents enemy Defensive Buildings within its area of effect from firing, but does nothing to Mines":
        "Временно отключает оборонки в зоне действия; на мины не действует",
    "A volley of 15 smaller shots that damage enemy Buildings and trigger Mines in a small area":
        "Залп из 15 мелких снарядов по небольшой площади: повреждает постройки и подрывает мины",
    "Troops within its area of effect cannot be attacked by enemy Defensive Buildings but cannot attack either":
        "Войска в дыму не видны обороне, но и сами не атакуют",
    "A cluster of small blue robots that can distract enemy Defensive Buildings and trigger Mines":
        "Стая мелких роботов: отвлекает оборону и подрывает мины",
    # роли в опергруппе
    "Promote/Demote Members": "Повышать/понижать участников",
    "Edit Task Force Info": "Править информацию ОПГ",
    "Kick Members": "Исключать участников",
    "Start Operations": "Запускать операции",
    "Sabotage": "Саботаж",
    "Invite Friends": "Приглашать друзей",
    "Post/Edit Notes on Power Bases": "Писать/править заметки на базах",
    "Accept/Deny Membership Requests": "Принимать/отклонять заявки",
    "Chat/Share Replays": "Писать в чат и делиться реплеями",
    "Attack in Operations": "Атаковать в операциях",
    "да, Promote up to Co-leaders and Demote Officers to Members":
        "да — повышать до соруководителя, понижать офицеров",
    "да, only Officers and Members": "да — только офицеров и участников",
    "да, only Members once every 20 мин": "да — участников, раз в 20 мин",
    # бонусы статуй
    "Gold production increase": "Добыча золота",
    "Wood , Stone or Iron production increase": "Добыча дерева, камня или железа",
    "All Resources Production increase": "Добыча всех ресурсов",
    "Building Health increase": "Прочность построек",
    "Defensive Building Damage increase": "Урон обороны",
    "Troop Health increase": "Прочность войск",
    "Troop Damage increase": "Урон войск",
    "Gunboat Energy increase": "Энергия канонерки",
    "Resource Reward increase": "Награда ресурсами",
    "Power Stone chance increase": "Шанс камней силы",
    # гравировки: имена и описания
    "Power Surge": "Скачок энергии",
    "Ordnance": "Боеприпасы",
    "Adrenaline": "Адреналин",
    "Insulation": "Изоляция",
    "Rally": "Сбор",
    "Leech": "Пиявка",
    "Interference": "Помехи",
    "Armor": "Броня",
    "Triage": "Триаж",
    "Alchemy": "Алхимия",
    "Grounding": "Заземление",
    "Shielding": "Экранирование",
    "Overdrive": "Разгон",
    "Life Drain": "Похищение жизни",
    "Hardening": "Закалка",
    "Overheat": "Перегрев",
    "Support": "Поддержка",
    "Mind Fog": "Туман разума",
    "Tinkering": "Ремонт",
    "Disruption": "Срыв",
    "Mind Control": "Контроль разума",
    "Insurance": "Страховка",
    "Gives additional Gunboat energy for each destroyed building.":
        "Дополнительная энергия канонерки за каждое разрушенное здание.",
    "Increases damage for Barrage and Artillery abilities.":
        "Усиливает обстрел и артиллерию.",
    "Increases your units' movement and attack speed.":
        "Ускоряет движение и атаку войск.",
    "Reduces the duration of inhibiting effects, such as stun and freeze, on your troops.":
        "Сокращает оглушение и заморозку своих войск.",
    "Boosts your remaining units' speed each time you lose a unit. Bigger units give more boost.":
        "Ускоряет оставшихся войск после каждой потери: чем крупнее юнит, тем сильнее рывок.",
    "All units heal themselves of the damage they do.":
        "Войска лечатся на часть нанесённого урона.",
    "Slows down enemy defenses.": "Замедляет вражескую оборону.",
    "Decreases enemy defensive Statues' effectiveness.":
        "Ослабляет действие оборонных статуй врага.",
    "Decreases the base damage per shot of enemy defenses.":
        "Снижает базовый урон выстрелов вражеской обороны.",
    "Your troops gain a portion of the opponent's offensive statue boosts.":
        "Войска получают часть атакующих бонусов статуй противника.",
    "Restores a portion of lost units after a battle.":
        "Возвращает часть потерянных войск после боя.",
    "Increases loot gained and converts looted construction resources to resource types you are missing.":
        "Больше добычи; лишние ресурсы конвертируются в недостающие.",
    "Reduces the amount of Gunboat energy opponents gain for each destroyed building.":
        "Противник получает меньше энергии за разрушенные здания.",
    "Reduces the duration of inhibiting effects, such as stun and freeze, on your buildings.":
        "Сокращает оглушение и заморозку своих построек.",
    "Increases the attack speed of your defenses .": "Ускоряет атаку своей обороны.",
    "Deals damage to attacking units each second equal to a certain percentage of their base max health.":
        "Каждую секунду наносит атакующим урон в проценте от их максимального здоровья.",
    "Reduces the damage of opponents' Gunboat abilities.":
        "Снижает урон способностей канонерки противника.",
    "Gives opponent's heroes and leaders a cooldown on their abilities.":
        "Способности героев противника уходят на перезарядку.",
    "Buildings transfer an amount of damage taken to nearby buildings.":
        "Постройки передают часть полученного урона соседним.",
    "Reduces the movement and attack speed of opponents' troops.":
        "Замедляет движение и атаку войск противника.",
    "You gain an additional prototype defense slot and Gunboat damage taken by prototypes is reduced.":
        "Дополнительный слот оборонного прототипа; прототипы получают меньше урона от канонерки.",
    "Reduces the effect of opponents' offensive statues.":
        "Ослабляет атакующие статуи противника.",
    "You gain an amount of energy per second. At 20 energy resurrects fallen opponents to defend you.":
        "Энергия накапливается сама; на 20 энергии воскрешает павших врагов на своей стороне.",
    "Returns an amount of the resources lost due to base being raided.":
        "Возвращает часть ресурсов, потерянных при разграблении базы.",
}

# Многословные фразы — заменяются целиком, с границами слов, без учёта регистра.
PHRASES = [
    ("between shots in salvo", "между выстрелами очереди"),
    ("between shots in burst", "между выстрелами очереди"),
    ("between shots at the same target", "между выстрелами по одной цели"),
    ("between salvos of", "между очередями по"),
    ("between each salvo", "между залпами"),
    ("between each Critter", "между криттерами"),
    ("reload time after", "перезарядка после"),
    ("electric pulses every", "электрических импульса каждые"),
    ("freezing pulses every", "морозных импульсов каждые"),
    ("then reload", "затем перезарядка"),
    ("based on level", "зависит от уровня"),
    ("distinct between", "различается: от"),
    ("Not available at the moment", "сейчас недоступно"),
    ("Very Fast", "очень быстрая"), ("Very Slow", "очень медленная"),
    ("Very Long", "очень длинная"), ("Very Short", "очень короткая"),
    ("Ground and Air", "земля и воздух"),
    ("every second day for Free", "через день — бесплатно"),
    ("every second day", "через день"),
    ("Coming soon", "скоро"),
    ("Level ", "Ур. "),
    ("Field Manuals", "полевых уставов"), ("Field Manual", "полевой устав"),
    ("Action Reports", "боевых отчётов"), ("Action Report", "боевой отчёт"),
    ("Builder Tokens", "жетонов строителя"), ("Builder Token", "жетон строителя"),
    ("Reset Tokens", "жетонов сброса"), ("Reset Token", "жетон сброса"),
    ("Mercenary Contracts", "контрактов наёмника"), ("Mercenary Contract", "контракт наёмника"),
    ("Power Powder", "энергетик"),
    ("keys every", "ключей каждые"),
    ("Better Chest value", "сундуки выгоднее"),
    ("Better Starting Rank", "лучший стартовый ранг"),
    ("All players start with", "все игроки начинают с"),
]

# Однословные замены — только по границам слова, чтобы «Grounded»
# не превращался в «земляed», а «November» — в «нетvember».
WORD_MAP = {
    "Moderate": "средняя", "Medium": "средняя", "Slow": "медленная",
    "Fast": "быстрая", "Melee": "ближний бой", "Long": "длинная",
    "Short": "короткая", "Tiles": "кл.", "Tile": "кл.",
    "Splash": "по площади", "Single": "по одной цели",
    "Ground": "земля", "Air": "воздух",
    "Buildings": "постройки", "Troops": "войска", "Units": "юниты",
    "depends": "зависит", "None": "нет", "Yes": "да", "No": "нет",
    "Free": "бесплатно", "seconds": "с", "second": "с", "sec": "с",
    "minutes": "мин", "minute": "мин", "min": "мин",
    "days": "дн.", "day": "дн.", "hours": "ч", "hour": "ч",
    "gained": "получено", "lost": "потеряно", "formerly": "раньше",
    "keys": "ключей", "Free": "бесплатно",
    "Crystal": "кристалл", "Crystals": "кристаллов",
    "Shard": "осколок", "Shards": "осколков",
    "Fragment": "фрагмент", "Fragments": "фрагментов",
    "Module": "модулей", "Modules": "модулей",
    "Keycard": "ключ-карт", "Keycards": "ключ-карт",
    "Protos": "прото", "Proto": "прото",
    "shots": "выстрелов", "shot": "выстрел",
    "Orbit": "патрулирование", "Alone": "без патрулирования",
    "Defensive": "оборонные", "Traps": "ловушки",
    "Life": "Жизнь", "Ice": "Лёд", "Magma": "Магма", "Dark": "Тьма",
    "Total": "Итого", "Idol": "Идол", "Guardian": "Страж",
    "Masterpiece": "Шедевр", "Diamonds": "Алмазы",
    "Attack": "Атака", "Defense": "Оборона", "Unprotected": "без прикрытия",
    "Depends": "Зависит", "level": "ур.", "Defeat": "поражение",
    "Victory": "победа", "Resources": "Ресурсы",
    "Available": "доступно", "Added": "добавлено",
}
WORD_RE = re.compile(
    r"\b(" + "|".join(sorted(WORD_MAP, key=len, reverse=True)) + r")\b", re.I)

TIME_RE = [
    (re.compile(r"\bthen\s+(\d+)\s*s\b\s*reload", re.I), r"затем перезарядка \1 с"),
    (re.compile(r"\bHQ level (\d+)", re.I), r"штаб ур. \1"),
    (re.compile(r"\bRadar level\b", re.I), "уровень радара"),
    (re.compile(r"\b1 or 2\b"), r"1–2"),
    (re.compile(r"(\d)\s*min\b"), r"\1 мин"),
    (re.compile(r"(\d)\s*d\b"), r"\1д"),
    (re.compile(r"(\d)\s*h\b"), r"\1ч"),
    (re.compile(r"(\d)\s*m\b"), r"\1м"),
    (re.compile(r"(\d)\s*s\b"), r"\1с"),
]

RU_TEXT_GROUPS = {"troops", "proto_troops", "gunboat", "defenses",
                  "proto_defenses", "heroes"}


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
    if h in ALL_NAMES:
        return ALL_NAMES[h]
    m = re.match(r"^(Sgt\. Brick|Cpt\. Everspark|Dr\. Kavan|Pvt\. Bullit|Cpt\. Ruddero) Level · (\d+)$", h)
    if m:
        return "Ур. героя · " + m.group(2)
    m = re.match(r"^Armory Level · (\d+)$", h)
    if m:
        return "Ур. оружейной · " + m.group(1)
    m = re.match(r"^(.*?) Level$", h)
    if m and m.group(1) in SENTENCES:
        return SENTENCES[m.group(1)] + ", ур."
    if m and m.group(1) in ALL_NAMES:
        return ALL_NAMES[m.group(1)] + ", ур."
    return h


def tr_val(v):
    s = str(v).strip()
    if s in ("N/A", "n/a", "-", "—", ""):
        return "—"
    if s in SENTENCES:
        return SENTENCES[s]
    # игровые имена (войска, оборонки...) целиком; если после замены
    # всё ещё остаются английские слова — откат, чтобы не было смеси
    named = s
    for k, ru_rx in RU_NAMES_RX:
        named = ru_rx.sub(lambda m, r=ALL_NAMES[k]: r, named)
    if len(re.findall(r"[A-Za-z]{3,}", named)) < 2:
        s = named
    for a, b in PHRASES:
        s = re.sub(r"\b" + re.escape(a) + r"\b", b, s, flags=re.I)
    # длинное английское предложение не трогаем пословно: смесь языков
    # хуже, чем цельный английский за аккордеоном
    looks_sentence = len(s.split()) > 5 and (". " in s or s.endswith("."))
    if not looks_sentence:
        def word(m):
            for form in (m.group(0), m.group(0).title(), m.group(0).lower()):
                if form in WORD_MAP:
                    r = WORD_MAP[form]
                    if m.group(0)[0].isupper() and r[0].islower() and r not in ("кл.", "с", "дн."):
                        r = r[0].upper() + r[1:]
                    return r
            return m.group(0)
        s = WORD_RE.sub(word, s)
    for rx, rep in TIME_RE:
        s = rx.sub(rep, s)
    return re.sub(r"(?<=\d),(?=\d{3}(\D|$))", "\u2009", s)


# ² и ³ для python — «словесные» символы, поэтому \b не подходит:
# граница должна смотреть только на латинские буквы.
# Один общий словарь, длинные имена применяются первыми — иначе
# «Tank» успеет испортить «Tank Tango».
ALL_NAMES = {k: v[0] for k, v in RU.items()}
EXTRA_NAMES = {
    "Heavies": "Горы", "Zookas": "Базуки", "Riflemen": "Стрелки",
    "Warriors": "Воины", "Tanks": "Танки", "Medics": "Медики",
    "Grenadiers": "Гренадёры", "Scorchers": "Огневики", "Mechs": "Мехи",
    "Choppas": "вертолёты", "Laser Rangers": "Лазерщицы",
    "Cryoneers": "Заморозки", "Bombardiers": "Бомбардиры",
}
EXTRA_NAMES.update({en: v[0] for en, v in OPS.items()})
ALL_NAMES.update(EXTRA_NAMES)
RU_NAMES_RX = [
    (k, re.compile(r"(?<![A-Za-z])" + re.escape(k) + r"s?(?![A-Za-z])"))
    for k in sorted(ALL_NAMES, key=len, reverse=True)
]


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
        if not rows or len(rows[0]) < 2:
            continue
        flat = " ".join(" ".join(r) for r in rows)
        if "•" in flat or "Wiki Navigation" in flat or len(flat) > 12000:
            continue
        # таблицы звуков: почти все ячейки — ссылки на ogg-файлы
        if flat.count("File:") > 3 or flat.count(".ogg") > 3:
            continue
        head0 = " ".join(rows[0]).lower()
        if SKIP_TABLE.search(rows[0][0].strip()) or SKIP_TABLE.search(head0[:40]):
            continue
        if len(rows) == 2 and len(rows[0]) <= 12 and not is_level_head(rows[0][0]):
            for k, v in zip(rows[0], rows[1]):
                k, v = k.strip(), v.strip()
                if k and v and "+%" not in k and "Apply" not in k and "ApplyReset" not in v \
                        and not k.startswith("Figure"):
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
            # английское «Коротко» дублирует русское резюме из ru_text.json
            if group in RU_TEXT_GROUPS:
                sections = [s for s in sections if s["title"] != "Коротко"]
            sections = [s for s in sections if s["lines"]]
            ru, slang = RU.get(title, (title, ""))
            arr.append({
                "id": slug(title), "en": title, "ru": ru,
                "alias": [x.strip() for x in slang.split(",") if x.strip()],
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
                ru, chat, note = OPS.get(en, (en, "", ""))
                ops.append({
                    "n": int(re.sub(r"\D", "", r[0]) or 0), "en": en, "ru": ru,
                    "chat": chat, "note": note,
                    "intel": {"5": r[2], "10": r[3], "25": r[4], "50": r[5]},
                    "fp": r[6].replace(",", "\u2009"), "bases": r[7],
                })
        elif "Sabotage Number" in head:
            sabotage = [{"n": r[0], "cost": r[1], "total": r[2]} for r in rows[1:]]
    out = os.path.join(DATA, "ops.json")
    json.dump({"ops": ops, "sabotage": sabotage}, open(out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"операции: {len(ops)} -> ops.json")


# ------------------------------------------------------------------- обновления игры
# История обновлений живёт на вики одной большой страницей свёрнутых таблиц:
# свежайший патч сверху. Тянем верхние, переводим онлайн-переводчиком
# (Google gtx, фолбэк MyMemory), названия юнитов подставляем свои до перевода,
# чтобы «Rifleman» стал «Стрелком», а не «стрелком-винтовочником».

UPDATES_PAGE = "Version History"
UPDATES_KEEP = 8
MONTHS = {"January": "января", "February": "февраля", "March": "марта", "April": "апреля",
          "May": "мая", "June": "июня", "July": "июля", "August": "августа",
          "September": "сентября", "October": "октября", "November": "ноября", "December": "декабря"}
MONTHS_NOM = {"January": "январь", "February": "февраль", "March": "март", "April": "апрель",
              "May": "май", "June": "июнь", "July": "июль", "August": "август",
              "September": "сентябрь", "October": "октябрь", "November": "ноябрь", "December": "декабрь"}


def mt(text):
    """Онлайн-перевод EN->RU. None — если оба переводчика не ответили."""
    text = text.strip()
    if not text:
        return ""
    try:
        q = urllib.parse.quote(text)
        url = ("https://translate.googleapis.com/translate_a/single?client=gtx"
               "&sl=en&tl=ru&dt=t&q=" + q)
        req = urllib.request.Request(url, headers=UA)
        d = json.load(urllib.request.urlopen(req, timeout=25))
        out = "".join(s[0] for s in d[0] if s and s[0]).strip()
        if out:
            return out
    except Exception:
        pass
    try:
        q = urllib.parse.quote(text[:450])
        url = "https://api.mymemory.translated.net/get?q=" + q + "&langpair=en|ru"
        req = urllib.request.Request(url, headers=UA)
        d = json.load(urllib.request.urlopen(req, timeout=25))
        out = (d.get("responseData") or {}).get("translatedText", "")
        if out and "MYMEMORY WARNING" not in out:
            return out.strip()
    except Exception:
        pass
    return None


def _names_ru(text):
    """Английские названия из наших словарей -> русские, до машинного перевода."""
    for k, rx in RU_NAMES_RX:
        text = rx.sub(lambda m, r=ALL_NAMES[k]: r, text)
    return text


def _wiki_line(s):
    """Вики-разметку в текст: картинки и шаблоны прочь, [[A|B]]->B, [[A]]->A, теги и кавычки тоже."""
    s = re.sub(r"\[\[File:[^\]]*\]\]", "", s)
    s = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"\{\{Res\|RES=([^}|]+)[^}]*\}\}", r"\1", s)
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("'''", "").replace("''", "")
    s = re.sub(r"(?<=[!.,])\s*(?:center|thumb|left|right)\|\d+px\|link=\s*$", "", s)
    return re.sub(r"\s+", " ", s).strip(" :")


def _clean_body(body):
    """Тело таблицы до разбора по строкам: галереи, <center> и многострочные
    шаблоны {{...}} (внутри бывают [[File:...]] с собственными скобками)."""
    body = re.sub(r"<gallery[\s\S]*?</gallery>", "", body)
    body = re.sub(r"</?center>", "", body)
    for _ in range(3):  # один проход снимает один уровень вложенности скобок
        body = re.sub(r"\{\{[^{}]*\}\}", "", body)
    return body


def _ru_date(s):
    """«April 22, 2026» и «22nd April, 2026» -> «22 апреля 2026».
    «??? November, 2026» (день ещё не объявлен) -> «ноябрь 2026»."""
    m = re.search(r"(\d{1,2})\w*\s+(" + "|".join(MONTHS) + r")\w*,?\s+(20\d\d)", s)
    if m:
        return f"{m.group(1)} {MONTHS[m.group(2)]} {m.group(3)}"
    m = re.search(r"(" + "|".join(MONTHS) + r")\w*,?\s+(\d{1,2}),?\s+(20\d\d)", s)
    if m:
        return f"{m.group(2)} {MONTHS[m.group(1)]} {m.group(3)}"
    m = re.search(r"(" + "|".join(MONTHS) + r")\w*,?\s+(20\d\d)", s)
    if m:
        return MONTHS_NOM[m.group(1)] + " " + m.group(2)
    return s.strip()


def build_updates(refetch=False, retranslate=False):
    """Возвращает True, если файл updates.json реально переписан.

    refetch — перекачать страницу истории (иначе берём кеш).
    retranslate — переводить, даже если текст вики не менялся.
    Ежедневной проверке хватает refetch: пока хеш источника тот же,
    переводчик не дёргается вообще.
    """
    cachefile = os.path.join(CACHE, "Version_History_wt.json")
    os.makedirs(CACHE, exist_ok=True)
    if refetch and os.path.exists(cachefile):
        os.remove(cachefile)
    if os.path.exists(cachefile) and os.path.getsize(cachefile) > 500:
        wt = open(cachefile, encoding="utf-8").read()
    else:
        d = api({"action": "parse", "page": UPDATES_PAGE, "prop": "wikitext",
                 "format": "json", "formatversion": "2"})
        wt = d["parse"]["wikitext"]
        open(cachefile, "w", encoding="utf-8").write(wt)

    # не изменилась ли вики с прошлого раза
    import hashlib
    src_hash = hashlib.md5(wt.encode("utf-8")).hexdigest()
    out = os.path.join(DATA, "updates.json")
    old = None
    if os.path.exists(out):
        try:
            old = json.load(open(out, encoding="utf-8"))
        except OSError:
            old = None
    if not retranslate and isinstance(old, dict) and old.get("meta", {}).get("src") == src_hash:
        print("обновления: вики не менялась, перевод не нужен")
        return False

    updates = []
    for tb in re.split(r'\{\| class="wikitable', wt)[1:UPDATES_KEEP * 2 + 4]:
        lines = tb.split("\n")
        # строка заголовка идёт после атрибутов таблицы: «! scope="col" | Название (дата)»
        head = ""
        for ln in lines[:6]:
            m = re.match(r'\s*!(?:\s*scope="col"\s*)?\|\s*(.+)$', ln)
            if m:
                head = m.group(1)
                break
        if not head:
            continue
        head = _wiki_line(head)
        dm = re.search(r"\(([^()]*?20\d\d[^()]*?)\)\s*$", head)
        date_en = dm.group(1) if dm else ""
        title = _wiki_line(head[:dm.start()]) if dm else head
        if not title:
            continue
        # тело таблицы — после строки с «|-»
        try:
            body = tb.split("\n|-", 1)[1]
        except IndexError:
            continue
        body = _clean_body(body.rsplit("|}", 1)[0])

        sections, cur = [], {"h": "", "v": []}
        for raw in body.split("\n"):
            s = raw.strip()
            if s.startswith("==="):
                if cur["v"] or cur["h"]:
                    sections.append(cur)
                h = _wiki_line(s.strip("= "))
                cur = {"h": h, "v": []}
            elif s.startswith("*"):
                line = ("— " if s.startswith("**") else "") + _wiki_line(s.lstrip("*"))
                # обломки шаблонов и ссылок после чистки — мусор, не показываем
                if line and len(cur["v"]) < 30 and not re.search(r"\{\{|\[\[|link=", line):
                    cur["v"].append(line)
            elif s and not s.startswith(("{", "|", "!")) and len(s) > 25:
                line = _wiki_line(s)
                if line:
                    cur["v"].append(line)
        if cur["v"] or cur["h"]:
            sections.append(cur)
        sections = [x for x in sections if x["v"]]
        if not sections:
            continue

        # перевод
        t_ru = mt(_names_ru(title)) or title
        if t_ru.lower().rstrip(". ") in ("обновлять", "обновление"):
            t_ru = "Обновление игры"
        upd = {"t": t_ru, "d": _ru_date(date_en),
               "s": []}
        for sec in sections:
            h_ru = mt(_names_ru(sec["h"])) if sec["h"] else ""
            v_ru = []
            for line in sec["v"]:
                r = mt(_names_ru(line))
                v_ru.append(r if r else line + " (англ.)")
                time.sleep(0.12)
            upd["s"].append({"h": h_ru, "v": v_ru})
        updates.append(upd)
        print(f"  обновление: {t_ru[:60]} ({upd['d']}) — {sum(len(x['v']) for x in upd['s'])} строк")
        if len(updates) >= UPDATES_KEEP:
            break

    # если переводчик лёг, больше половины строк останутся английскими —
    # лучше оставить прошлую русскую версию, чем перезаписать сырьём
    total = sum(len(x["v"]) for u in updates for x in u["s"])
    raw = sum(1 for u in updates for x in u["s"] for l in x["v"] if l.endswith("(англ.)"))
    if total and raw / total > 0.5:
        print(f"обновления: переводчик недоступен ({raw}/{total} строк сырые) — оставляю прежний файл")
        return False

    data = {"meta": {"src": src_hash,
                     "built": time.strftime("%Y-%m-%d %H:%M")},
            "items": updates}
    json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"обновления: {len(updates)} -> {os.path.basename(out)}")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "updates":
        build_updates(refetch=True, retranslate=True)
    else:
        build_wiki()
        build_updates(refetch=True, retranslate=True)
        print("Готово. Каталог баз операций собирается отдельно: py -3 tools/build_bases.py")
