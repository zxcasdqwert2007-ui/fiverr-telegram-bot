import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from parser import parse_fiverr

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    gigs = parse_fiverr("logo design")

    if not gigs:
        await msg.answer("Ничего не найдено 😢")
        return

    for g in gigs:
        text = f"""
📦 Товар: {g['title']}
💵 Цена: {g['price']}

🔗 Объявление: {g['link']}
"""
        await msg.answer(text)


if __name__ == "__main__":
    print("🚀 Бот запущен...")
    executor.start_polling(dp)