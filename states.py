from aiogram.dispatcher.filters.state import State, StatesGroup

class ParseSettings(StatesGroup):
    waiting_for_keywords = State()       # Ожидание ввода ключевых слов
    waiting_for_exclude_countries = State()  # Ожидание ввода исключаемых стран
    parsing_active = State()              # Флаг активного парсинга (для остановки)