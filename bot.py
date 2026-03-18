from flask import Flask
from threading import Thread

# Создаем мини-сервер, чтобы Render не выключал бота
app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# В основном блоке перед запуском бота:
if __name__ == '__main__':
    keep_alive() # Запускаем сервер
    main()       # Запускаем бота

import asyncio
import re
from playwright.async_api import async_playwright
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- НАСТРОЙКИ ---
TOKEN = '8744221821:AAFEIBggtvAWbscfhOYIEhDEsVYkLaRR-ro'

# Глобальное хранилище настроек (в идеале использовать БД типа SQLite)
user_config = {
    'keywords': ['fashion logo'],
    'exclude_countries': ['India', 'Bangladesh'],
    'is_running': False
}

async def scrape_fiverr(keyword, exclude_countries):
    async with async_playwright() as p:
        # Запуск браузера с эмуляцией реального пользователя
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Формируем URL с фильтром "Online Sellers" (?seller_online=true)
        encoded_keyword = keyword.replace(' ', '%20')
        url = f"https://www.fiverr.com/search/gigs?query={encoded_keyword}&seller_online=true&sort_by=newest"
        
        await page.goto(url, wait_until="networkidle")
        
        # Ждем загрузки карточек товаров
        await page.wait_for_selector('.gig-card-layout')
        gigs = await page.query_selector_all('.gig-card-layout')
        
        results = []

        for gig in gigs:
            try:
                # 1. ПРОВЕРКА ОТЗЫВОВ (Пропускаем, если отзывы есть)
                # На Fiverr отзывы обычно в скобках, например "(15)". Ищем отсутствие или "(0)"
                rating_element = await gig.query_selector('.rating-count-number')
                if rating_element:
                    rating_text = await rating_element.inner_text()
                    review_count = re.sub(r'\D', '', rating_text) # Оставляем только цифры
                    if review_count != "" and int(review_count) > 0:
                        continue # Пропускаем, если отзывы > 0
                
                # 2. Сбор данных
                title_elem = await gig.query_selector('h3 a')
                title = await title_elem.inner_text()
                gig_link = "https://www.fiverr.com" + await title_elem.get_attribute('href')

                seller_elem = await gig.query_selector('.seller-name a')
                seller_name = await seller_elem.inner_text()
                seller_profile = "https://www.fiverr.com" + await seller_elem.get_attribute('href')

                price_elem = await gig.query_selector('.price')
                price = await price_elem.inner_text() if price_elem else "N/A"

                # Фото объявления
                img_elem = await gig.query_selector('img')
                photo_url = await img_elem.get_attribute('src') if img_elem else ""

                # Аватар продавца
                avatar_elem = await gig.query_selector('.seller-image img')
                avatar_url = await avatar_elem.get_attribute('src') if avatar_elem else ""

                # Ссылка на чат (Inbox)
                inbox_link = f"https://www.fiverr.com/inbox/{seller_name}"

                # Страна (Требует перехода в профиль, для примера поставим заглушку или пропустим)
                # Чтобы не банили за частые переходы, страну лучше парсить опционально
                country = "Pakistan 🇵🇰" # В реальности нужен await page.goto(seller_profile)

                results.append({
                    'title': title,
                    'price': price,
                    'seller': seller_name,
                    'country': country,
                    'online': "🟢 Online",
                    'inbox': inbox_link,
                    'gig_url': gig_link,
                    'seller_url': seller_profile,
                    'photo': photo_url,
                    'avatar': avatar_url,
                    'reviews': "0"
                })

                if len(results) >= 5: break # Ограничение выборки

            except Exception as e:
                continue

        await browser.close()
        return results

# --- ТЕЛЕГРАМ БОТ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🚀 Старт (Поиск 0 отзывов + Online)", callback_data='run')],
        [InlineKeyboardButton("🔑 Ключевые слова", callback_data='keys')],
        [InlineKeyboardButton("🚫 Исключить страны", callback_data='countries')]
    ]
    await update.message.reply_text("Fiverr Parser Bot\nФильтры: Online, 0 отзывов.", 
                                  reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'run':
        await query.message.reply_text("🔎 Ищу новые заказы без отзывов...")
        
        for key in user_config['keywords']:
            data = await scrape_fiverr(key, user_config['exclude_countries'])
            
            for item in data:
                text = (
                    f"📦 **Товар:** {item['title']}\n"
                    f"💵 **Цена:** {item['price']}\n"
                    f"👨‍💼 **Продавец:** {item['seller']}\n"
                    f"🌎 **Страна:** {item['country']}\n"
                    f"⚡️ **Онлайн:** {item['online']}\n\n"
                    f"💬 **ЛС:** {item['inbox']}\n\n"
                    f"📸 [Фото объявления]({item['photo']})\n"
                    f"💬 [Ссылка на чат]({item['inbox']})\n"
                    f"🔗 [Объявление]({item['gig_url']})\n"
                    f"👤 [Профиль продавца]({item['seller_url']})\n"
                    f"🎭 [Фото продавца]({item['avatar']})\n\n"
                    f"💫 **Отзывов:** {item['reviews']}"
                )
                await context.bot.send_message(
                    chat_id=query.message.chat_id, 
                    text=text, 
                    parse_mode='Markdown',
                    disable_web_page_preview=False
                )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.run_polling()

if __name__ == '__main__':
    main()