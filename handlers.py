import re
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from states import ParseSettings
from parser import FiverrParser
import asyncio
from loader import bot

def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("/start"))
    kb.add(KeyboardButton("/set_keywords"))
    kb.add(KeyboardButton("/set_exclude_countries"))
    kb.add(KeyboardButton("/set_proxy"))
    kb.add(KeyboardButton("/start_parsing"))
    kb.add(KeyboardButton("/stop"))
    return kb

async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я помогу искать новых продавцов на Fiverr.\n\n"
        "Команды:\n"
        "/set_keywords — задать ключевые слова (через запятую)\n"
        "/set_exclude_countries — исключить страны (через запятую)\n"
        "/set_proxy — установить HTTP/SOCKS5 прокси (формат: ip:port или с протоколом)\n"
        "/start_parsing — запустить парсинг\n"
        "/stop — остановить",
        reply_markup=get_main_keyboard()
    )

# ===== Ключевые слова =====
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
    await state.set_state(None)

# ===== Исключаемые страны =====
async def cmd_set_exclude_countries(message: types.Message):
    await message.answer("Введите страны для исключения через запятую (например: Russia, China):")
    await ParseSettings.waiting_for_exclude_countries.set()

async def process_exclude_countries(message: types.Message, state: FSMContext):
    countries = [c.strip() for c in message.text.split(',') if c.strip()]
    await state.update_data(exclude_countries=countries)
    await message.answer(f"✅ Исключаемые страны сохранены: {', '.join(countries) if countries else 'нет'}")
    await state.set_state(None)

# ===== Прокси =====
async def cmd_set_proxy(message: types.Message):
    await message.answer(
        "🔌 Отправьте строку прокси. Можно в любом формате:\n"
        "• `ip:port` (будет добавлено http://)\n"
        "• `http://ip:port`\n"
        "• `socks5://user:pass@ip:port`\n\n"
        "Если прокси не нужен, отправьте /skip_proxy"
    )
    await ParseSettings.waiting_for_proxy.set()

async def process_proxy(message: types.Message, state: FSMContext):
    proxy_input = message.text.strip()
    # Если нет протокола, добавляем http://
    if '://' not in proxy_input:
        proxy_url = f"http://{proxy_input}"
    else:
        proxy_url = proxy_input

    # Простейшая проверка наличия протокола
    if not re.match(r'^(http|https|socks5)://', proxy_url):
        await message.answer("❌ Неверный формат. Попробуйте ещё раз или /skip_proxy")
        return

    await state.update_data(proxy_url=proxy_url)
    await message.answer("✅ Прокси сохранён.")
    await state.set_state(None)

async def skip_proxy(message: types.Message, state: FSMContext):
    await state.update_data(proxy_url=None)
    await message.answer("✅ Прокси не используется.")
    await state.set_state(None)

# ===== Запуск парсинга =====
async def cmd_start_parsing(message: types.Message, state: FSMContext):
    data = await state.get_data()
    keywords = data.get('keywords', [])
    exclude_countries = data.get('exclude_countries', [])
    proxy_url = data.get('proxy_url')

    if not keywords:
        await message.answer("❌ Сначала задайте ключевые слова через /set_keywords")
        return

    proxy_status = f"✅ Используется прокси: {proxy_url}" if proxy_url else "⚠️ Прокси не задан (возможны блокировки)"
    await message.answer(
        f"🔍 Парсинг запущен!\n"
        f"Ключевые слова: {', '.join(keywords)}\n"
        f"Исключаемые страны: {', '.join(exclude_countries) if exclude_countries else 'нет'}\n"
        f"{proxy_status}\n"
        f"⚙️ Фильтр: только новые продавцы, сортировка — новинки"
    )

    await state.update_data(parsing_active=True)
    asyncio.create_task(run_parser(message.chat.id, state, keywords, exclude_countries, proxy_url))

async def run_parser(chat_id: int, state: FSMContext, keywords: list, exclude_countries: list, proxy_url: str):
    async with FiverrParser(exclude_countries=exclude_countries, proxy_url=proxy_url) as parser:
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

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands=['start'])
    dp.register_message_handler(cmd_set_keywords, commands=['set_keywords'])
    dp.register_message_handler(cmd_set_exclude_countries, commands=['set_exclude_countries'])
    dp.register_message_handler(cmd_set_proxy, commands=['set_proxy'])
    dp.register_message_handler(skip_proxy, commands=['skip_proxy'], state=ParseSettings.waiting_for_proxy)
    dp.register_message_handler(cmd_start_parsing, commands=['start_parsing'])
    dp.register_message_handler(cmd_stop, commands=['stop'])

    dp.register_message_handler(process_keywords, state=ParseSettings.waiting_for_keywords)
    dp.register_message_handler(process_exclude_countries, state=ParseSettings.waiting_for_exclude_countries)
    dp.register_message_handler(process_proxy, state=ParseSettings.waiting_for_proxy)