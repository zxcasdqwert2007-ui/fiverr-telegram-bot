from aiogram.dispatcher.filters.state import State, StatesGroup

class ParseSettings(StatesGroup):
    waiting_for_keywords = State()
    waiting_for_exclude_countries = State()
    parsing_active = State()