# -*- coding: utf-8 -*-
"""Точка входа. Хостинг запускает именно этот файл.

Главное: приложение поднимается ВСЕГДА, даже если бот не настроен.
Раньше этот файл падал без BOT_TOKEN — процесс сразу завершался, хостинг
отдавал Bad Gateway и гасил контейнер по SIGTERM, а в логах не было ничего.

    py -3 bot.py            порт 3000 (или из PORT)
    py -3 bot.py 9000       другой порт

Бот с кнопкой «Справочник» — необязательная надстройка. Он запустится рядом,
только если заданы BOT_TOKEN и адрес приложения (WEBAPP_URL или APP_LINK)
и установлен aiogram (строка в requirements.txt).
"""
import os
import threading

import server

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
WEBAPP_URL = (os.environ.get("WEBAPP_URL")
              or (f"https://{os.environ['DOMAIN']}" if os.environ.get("DOMAIN") else "")).strip()
# Ссылка на мини-приложение из BotFather (/newapp) — открывается в любом чате
APP_LINK = os.environ.get("APP_LINK", "").strip()


def _build_bot():
    """Собирает бота. Всё, что связано с aiogram, импортируется только здесь."""
    from aiogram import Bot, Dispatcher, F
    from aiogram.filters import Command
    from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, Message,
                               MenuButtonWebApp, WebAppInfo)

    dp = Dispatcher()

    def keyboard() -> "InlineKeyboardMarkup":
        """В личке — кнопка WebApp, в группе — ссылка на мини-приложение."""
        if APP_LINK:
            return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📘 Открыть справочник", url=APP_LINK)]
            ])
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📘 Открыть справочник",
                                  web_app=WebAppInfo(url=WEBAPP_URL))]
        ])

    @dp.message(Command("start", "bb", "справочник"), F.chat.type == "private")
    async def start_private(message: Message) -> None:
        await message.answer(
            "Справочник опергруппы по Boom Beach: операции и их базы, войска, "
            "прототипы, оборона, статуи и калькулятор канонерки.",
            reply_markup=keyboard(),
        )

    @dp.message(Command("start", "bb", "справочник"))
    async def start_group(message: Message) -> None:
        if not APP_LINK:
            await message.answer(
                "Чтобы кнопка работала в группе, создай мини-приложение через "
                "BotFather (/newapp) и положи его ссылку в переменную APP_LINK."
            )
            return
        await message.answer("Справочник опергруппы:", reply_markup=keyboard())

    async def run() -> None:
        bot = Bot(BOT_TOKEN)
        if WEBAPP_URL:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(text="Справочник",
                                             web_app=WebAppInfo(url=WEBAPP_URL))
            )
        await dp.start_polling(bot)

    return run


def start_bot_in_background() -> None:
    """Поднимает бота в отдельном потоке. Любая его беда не трогает сайт."""
    if not BOT_TOKEN:
        print("BOT_TOKEN не задан — работает только мини-приложение", flush=True)
        return
    if not WEBAPP_URL and not APP_LINK:
        print("Нет WEBAPP_URL и APP_LINK — бот не запущен, мини-приложение работает",
              flush=True)
        return
    try:
        run = _build_bot()
    except Exception as e:
        print(f"Бот не запущен ({e.__class__.__name__}: {e}). "
              f"Для него нужен aiogram — раскомментируй строку в requirements.txt.",
              flush=True)
        return

    def target() -> None:
        import asyncio
        try:
            asyncio.run(run())
        except BaseException as e:
            print(f"Бот остановился: {e.__class__.__name__}: {e}", flush=True)

    threading.Thread(target=target, name="bot", daemon=True).start()
    print("Бот запущен рядом с мини-приложением", flush=True)


def main() -> None:
    start_bot_in_background()
    server.main()          # блокирующий вызов, он же ловит SIGTERM


if __name__ == "__main__":
    main()
