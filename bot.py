import logging
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import BOT_TOKEN
from handlers import register_handlers

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Регистрация обработчиков
register_handlers(dp)

# Сохраняем бота в глобальной переменной для доступа из run_parser
# (в handlers.py мы импортируем bot из этого модуля)
__all__ = ['bot', 'dp']

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)