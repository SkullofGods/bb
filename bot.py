# -*- coding: utf-8 -*-
"""Необязательный бот-обёртка для мини-приложения.

Нужен только если хочется кнопку «Справочник» в меню бота и команду /bb.
Само приложение работает и без бота: ссылку вида
https://t.me/ИМЯ_БОТА/ИМЯ_ПРИЛОЖЕНИЯ можно просто закрепить в группе.

Запуск:
    py -3 -m pip install aiogram
    set BOT_TOKEN=123:ABC
    set WEBAPP_URL=https://ваш-домен/
    py -3 bot.py
"""
import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, Message,
                           MenuButtonWebApp, WebAppInfo)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")
# Ссылка на мини-приложение, созданное через BotFather (/newapp).
# Она открывается в любом чате, в том числе в группе.
APP_LINK = os.environ.get("APP_LINK", "")

dp = Dispatcher()


def keyboard() -> InlineKeyboardMarkup:
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
        "Справочник опергруппы по Boom Beach: операции, войска, прототипы, "
        "оборона, статуи и калькулятор канонерки.",
        reply_markup=keyboard(),
    )


@dp.message(Command("start", "bb", "справочник"))
async def start_group(message: Message) -> None:
    if not APP_LINK:
        await message.answer(
            "Чтобы кнопка работала в группе, создай мини-приложение через BotFather "
            "(/newapp) и положи его ссылку в переменную APP_LINK."
        )
        return
    await message.answer("Справочник опергруппы:", reply_markup=keyboard())


async def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("Не задан BOT_TOKEN")
    if not WEBAPP_URL and not APP_LINK:
        raise SystemExit("Задай WEBAPP_URL (https-адрес приложения) или APP_LINK")
    bot = Bot(BOT_TOKEN)
    if WEBAPP_URL:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Справочник",
                                         web_app=WebAppInfo(url=WEBAPP_URL))
        )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
