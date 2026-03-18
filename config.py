import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
# API ID и Hash для Telethon (если будем проверять онлайн через Telegram - это сложно, пока опустим)
# TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
# TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")