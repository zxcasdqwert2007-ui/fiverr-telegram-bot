from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from states import ParseSettings
from parser import FiverrParser
import asyncio

# Импортируем бота для отправки сообщений из фоновой задачи
from bot import bot

def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("/start"))
    kb.add(KeyboardButton("/set_keywords"))
    kb.add(KeyboardButton("/set_exclude_countries"))
    kb.add(KeyboardButton("/start_parsing"))
    kb.add(KeyboardButton("/stop"))
    return kb

async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я помогу искать новых продавцов на Fiverr.\n\n"
        "Команды:\n"
        "/set_keywords — задать ключевые слова (через запятую)\n"
        "/set_exclude_countries — исключить страны (через запятую)\n"
        "/start_parsing — запустить парсинг\n"
        "/stop — остановить",
        reply_markup=get_main_keyboard()
    )

async def cmd_set_keywords(message: types.Message):
    await message.answer("Введите ключевые слова через запятую (например: logo design, web development):")
    await ParseSettings.waiting_for_keywords.set()

async def process_keywords(message: types.Message, state: FSMContext):
    keywords = [kw.strip() for kw in message.text.split(',') if kw.strip()]
    if not keywords:
        await message.answer("Список пуст. Попробуйте снова.")
        return
    await state.update_data(keywords=keywords)
    await message.answer(f"✅ Ключевые слова сохранены: {', '.join(keywords)}")
    # Сбрасываем состояние, но данные остаются
    await state.set_state(None)

async def cmd_set_exclude_countries(message: types.Message):
    await message.answer("Введите страны для исключения через запятую (например: Russia, China):")
    await ParseSettings.waiting_for_exclude_countries.set()

async def process_exclude_countries(message: types.Message, state: FSMContext):
    countries = [c.strip() for c in message.text.split(',') if c.strip()]
    await state.update_data(exclude_countries=countries)
    await message.answer(f"✅ Исключаемые страны сохранены: {', '.join(countries) if countries else 'нет'}")
    await state.set_state(None)

async def cmd_start_parsing(message: types.Message, state: FSMContext):
    data = await state.get_data()
    keywords = data.get('keywords', [])
    exclude_countries = data.get('exclude_countries', [])

    if not keywords:
        await message.answer("❌ Сначала задайте ключевые слова через /set_keywords")
        return

    await message.answer(
        f"🔍 Парсинг запущен!\n"
        f"Ключевые слова: {', '.join(keywords)}\n"
        f"Исключаемые страны: {', '.join(exclude_countries) if exclude_countries else 'нет'}"
    )

    await state.update_data(parsing_active=True)
    asyncio.create_task(run_parser(message.chat.id, state, keywords, exclude_countries))

async def run_parser(chat_id: int, state: FSMContext, keywords: list, exclude_countries: list):
    async with FiverrParser(exclude_countries=exclude_countries) as parser:
        for keyword in keywords:
            current = await state.get_data()
            if not current.get('parsing_active', False):
                await bot.send_message(chat_id, "⏹ Парсинг остановлен.")
                return

            await bot.send_message(chat_id, f"🔎 Ищу по слову: {keyword}")
            profiles = await parser.search_profiles(keyword, max_pages=15)

            if profiles:
                for prof in profiles:
                    current = await state.get_data()
                    if not current.get('parsing_active', False):
                        await bot.send_message(chat_id, "⏹ Остановлено.")
                        return
                    text = (
                        f"🎯 Найден продавец\n"
                        f"Слово: {prof['keyword']}\n"
                        f"Страна: {prof['country']}\n"
                        f"Отзывы: {prof['reviews']}\n"
                        f"📬 Инбокс: {prof['inbox_url']}"
                    )
                    await bot.send_message(chat_id, text)
                    await asyncio.sleep(1)
            else:
                await bot.send_message(chat_id, f"❌ Ничего не найдено по слову '{keyword}'.")

        await bot.send_message(chat_id, "✅ Парсинг всех ключевых слов завершён.")

async def cmd_stop(message: types.Message, state: FSMContext):
    await state.update_data(parsing_active=False)
    await message.answer("⏹ Команда остановки принята. Парсинг скоро завершится.")

def register_handlers(dp):
    dp.register_message_handler(cmd_start, commands=['start'])
    dp.register_message_handler(cmd_set_keywords, commands=['set_keywords'])
    dp.register_message_handler(cmd_set_exclude_countries, commands=['set_exclude_countries'])
    dp.register_message_handler(cmd_start_parsing, commands=['start_parsing'])
    dp.register_message_handler(cmd_stop, commands=['stop'])

    dp.register_message_handler(process_keywords, state=ParseSettings.waiting_for_keywords)
    dp.register_message_handler(process_exclude_countries, state=ParseSettings.waiting_for_exclude_countries)