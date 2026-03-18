from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from states import ParseSettings
from parser import FiverrParser
import asyncio

# Клавиатура главного меню
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("/start"))
    keyboard.add(KeyboardButton("/set_keywords"))
    keyboard.add(KeyboardButton("/set_exclude_countries"))
    keyboard.add(KeyboardButton("/start_parsing"))
    keyboard.add(KeyboardButton("/stop"))
    return keyboard

async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я помогу искать новых продавцов на Fiverr.\n\n"
        "Команды:\n"
        "/set_keywords — задать ключевые слова для поиска (через запятую)\n"
        "/set_exclude_countries — задать страны, которые нужно исключить (через запятую)\n"
        "/start_parsing — запустить парсинг\n"
        "/stop — остановить парсинг",
        reply_markup=get_main_keyboard()
    )

# Установка ключевых слов
async def cmd_set_keywords(message: types.Message):
    await message.answer("Введите ключевые слова через запятую (например: logo design, web development, seo):")
    await ParseSettings.waiting_for_keywords.set()

async def process_keywords(message: types.Message, state: FSMContext):
    keywords = [kw.strip() for kw in message.text.split(',') if kw.strip()]
    if not keywords:
        await message.answer("Список ключевых слов пуст. Попробуйте снова.")
        return
    await state.update_data(keywords=keywords)
    await message.answer(f"✅ Ключевые слова сохранены: {', '.join(keywords)}")
    await state.finish()

# Установка исключаемых стран
async def cmd_set_exclude_countries(message: types.Message):
    await message.answer("Введите страны, которые нужно исключить, через запятую (например: Russia, China, India):")
    await ParseSettings.waiting_for_exclude_countries.set()

async def process_exclude_countries(message: types.Message, state: FSMContext):
    countries = [c.strip() for c in message.text.split(',') if c.strip()]
    await state.update_data(exclude_countries=countries)
    await message.answer(f"✅ Исключаемые страны сохранены: {', '.join(countries) if countries else 'нет'}")
    await state.finish()

# Запуск парсинга
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
        f"Исключаемые страны: {', '.join(exclude_countries) if exclude_countries else 'нет'}\n"
        f"Буду искать профили с 0 отзывами, наличием гигов и не из исключённых стран."
    )

    # Сохраняем флаг активности парсинга
    await state.update_data(parsing_active=True)

    # Запускаем фоновую задачу
    asyncio.create_task(run_parser(message.chat.id, state, keywords, exclude_countries))

async def run_parser(chat_id: int, state: FSMContext, keywords: list, exclude_countries: list):
    """Фоновая задача парсинга"""
    from bot import bot  # импортируем экземпляр бота (нужно будет добавить в bot.py)

    async with FiverrParser(exclude_countries=exclude_countries) as parser:
        for keyword in keywords:
            # Проверяем, не остановлен ли парсинг
            current_state = await state.get_data()
            if not current_state.get('parsing_active', False):
                await bot.send_message(chat_id, "⏹ Парсинг остановлен пользователем.")
                return

            await bot.send_message(chat_id, f"🔎 Ищу профили по слову: {keyword}")

            profiles = await parser.search_profiles(keyword, max_pages=15)

            if profiles:
                for profile in profiles:
                    # Проверка на остановку между отправками
                    current_state = await state.get_data()
                    if not current_state.get('parsing_active', False):
                        await bot.send_message(chat_id, "⏹ Парсинг остановлен пользователем.")
                        return

                    text = (
                        f"🎯 Найден новый продавец!\n"
                        f"Слово: {profile['keyword']}\n"
                        f"Страна: {profile['country']}\n"
                        f"Отзывы: {profile['reviews']}\n"
                        f"📬 Ссылка на инбокс: {profile['inbox_url']}"
                    )
                    await bot.send_message(chat_id, text)
                    await asyncio.sleep(1)  # небольшая задержка между отправками
            else:
                await bot.send_message(chat_id, f"❌ По слову '{keyword}' ничего не найдено.")

        await bot.send_message(chat_id, "✅ Парсинг всех ключевых слов завершён.")

async def cmd_stop(message: types.Message, state: FSMContext):
    await state.update_data(parsing_active=False)
    await message.answer("⏹ Команда остановки принята. Парсинг скоро завершится.")

# Регистрация обработчиков
def register_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands=['start'])
    dp.register_message_handler(cmd_set_keywords, commands=['set_keywords'])
    dp.register_message_handler(cmd_set_exclude_countries, commands=['set_exclude_countries'])
    dp.register_message_handler(cmd_start_parsing, commands=['start_parsing'])
    dp.register_message_handler(cmd_stop, commands=['stop'])

    dp.register_message_handler(process_keywords, state=ParseSettings.waiting_for_keywords)
    dp.register_message_handler(process_exclude_countries, state=ParseSettings.waiting_for_exclude_countries)