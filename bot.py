import logging
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import BOT_TOKEN
from handlers import (
    cmd_start, cmd_set_countries,
    process_countries, cmd_start_parsing,
    cmd_stop, ParseSettings
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Регистрация обработчиков
dp.register_message_handler(cmd_start, commands=['start'])
dp.register_message_handler(cmd_set_countries, commands=['set_countries'])
dp.register_message_handler(process_countries, state=ParseSettings.waiting_for_countries)
dp.register_message_handler(cmd_start_parsing, commands=['start_parsing'])
dp.register_message_handler(cmd_stop, commands=['stop'])

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)