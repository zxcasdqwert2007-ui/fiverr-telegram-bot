import aiohttp
from bs4 import BeautifulSoup
import asyncio
import re
from typing import List, Dict

class FiverrParser:
    def __init__(self, allowed_countries: List[str] = None):
        self.base_url = "https://www.fiverr.com"
        self.allowed_countries = [c.lower() for c in allowed_countries] if allowed_countries else []
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    async def search_profiles(self, category_url: str, max_pages: int = 3) -> List[Dict]:
        """Поиск профилей по категории."""
        found_profiles = []

        for page in range(1, max_pages + 1):
            url = f"{category_url}?page={page}--{page}"
            print(f"Парсинг страницы: {url}")

            try:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        print(f"Ошибка {response.status} на странице {page}")
                        continue

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Жесткий парсинг: ищем карточки продавцов (селекторы нужно уточнять!)
                    # На Fiverr структура постоянно меняется.
                    seller_cards = soup.find_all('div', class_=re.compile('seller-card|freelancer-card'))

                    for card in seller_cards:
                        # Парсинг имени и профиля
                        username_tag = card.find('a', href=re.compile('/[^/]+$'))
                        if not username_tag:
                            continue

                        username = username_tag['href'].strip('/')
                        profile_url = f"{self.base_url}{username_tag['href']}"

                        # Парсинг страны
                        country_tag = card.find('span', class_=re.compile('country|location'))
                        country = country_tag.text.strip() if country_tag else "Unknown"

                        # Парсинг количества отзывов
                        reviews_tag = card.find('span', class_=re.compile('reviews|rating-count'))
                        reviews = 0
                        if reviews_tag:
                            reviews_text = reviews_tag.text.strip('()').replace(',', '')
                            reviews = int(reviews_text) if reviews_text.isdigit() else 0

                        # Фильтрация по стране
                        if self.allowed_countries and country.lower() not in self.allowed_countries:
                            continue

                        # Условия: 0 отзывов и есть гиги (проверим наличие гигов)
                        if reviews == 0:
                            # Проверка на наличие гигов (очень упрощенно)
                            # В реальности нужно парсить профиль или искать кнопку гигов
                            gigs_exist = card.find('a', href=re.compile('/gigs')) is not None

                            if gigs_exist:
                                profile_data = {
                                    'username': username,
                                    'profile_url': profile_url,
                                    'inbox_url': f"{self.base_url}/inbox/{username}",
                                    'country': country,
                                    'reviews': reviews,
                                    # Онлайн статус через парс HTML определить невозможно
                                    # 'is_online': False
                                }
                                found_profiles.append(profile_data)

                    # Задержка между страницами
                    await asyncio.sleep(5)

            except Exception as e:
                print(f"Ошибка при парсинге: {e}")
                continue

        return found_profiles

    # TODO: Функция проверки онлайн-статуса через WebSocket или отдельный запрос
    # Это самая сложная часть, так как Fiverr грузит это через JavaScript.