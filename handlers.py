from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import BOT_TOKEN
from parser import FiverrParser
import asyncio

# Класс состояний для настройки парсинга
class ParseSettings(StatesGroup):
    waiting_for_countries = State()
    parsing_active = State()

# Клавиатура
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("/start"))
    keyboard.add(KeyboardButton("/stop"))
    keyboard.add(KeyboardButton("/set_countries"))
    return keyboard

async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    await message.answer(
        "Привет! Я бот для поиска новых продавцов на Fiverr.\n"
        "Команды:\n"
        "/set_countries - Установить страны для поиска\n"
        "/start_parsing - Начать поиск\n"
        "/stop - Остановить поиск",
        reply_markup=get_main_keyboard()
    )

async def cmd_set_countries(message: types.Message):
    """Начало установки стран"""
    await message.answer("Введите список стран через запятую (например: United States, Canada):")
    await ParseSettings.waiting_for_countries.set()

async def process_countries(message: types.Message, state: FSMContext):
    """Сохранение списка стран"""
    countries = [c.strip() for c in message.text.split(',')]
    await state.update_data(allowed_countries=countries)
    await message.answer(f"Страны сохранены: {', '.join(countries)}")
    await state.finish()

async def cmd_start_parsing(message: types.Message, state: FSMContext):
    """Запуск парсинга"""
    user_data = await state.get_data()
    allowed_countries = user_data.get('allowed_countries', [])

    await message.answer(f"Парсинг запущен для стран: {allowed_countries if allowed_countries else 'Все'}")

    # Сохраняем состояние, что парсинг активен для этого пользователя
    async with state.proxy() as data:
        data['parsing_active'] = True

    # Запускаем парсер в фоне (нужен будет цикл)
    # В реальности нужно запускать это как отдельную таску
    asyncio.create_task(run_parser(message.chat.id, state))

async def run_parser(chat_id: int, state: FSMContext):
    """Основной цикл парсера (запускается в фоне)"""
    async with FiverrParser() as parser:
        while True:
            # Проверяем, не остановлен ли парсинг
            current_state = await state.get_data()
            if not current_state.get('parsing_active', False):
                break

            # URL категории для парсинга (нужно настраивать)
            test_url = "https://www.fiverr.com/categories/graphics-design"

            profiles = await parser.search_profiles(test_url, max_pages=1)

            for profile in profiles:
                # Тут нужно будет отправить сообщение пользователю
                # Для этого нужен доступ к боту. Оставим заглушку.
                print(f"Найден профиль: {profile}")
                # await bot.send_message(chat_id, f"Новый продавец: {profile['inbox_url']}")

            # Пауза между циклами
            await asyncio.sleep(60)

async def cmd_stop(message: types.Message, state: FSMContext):
    """Остановка парсинга"""
    async with state.proxy() as data:
        data['parsing_active'] = False
    await message.answer("Парсинг остановлен.")