import aiohttp
from bs4 import BeautifulSoup
import asyncio
import re
from typing import List, Dict

class FiverrParser:
    def __init__(self, exclude_countries: List[str] = None):
        self.base_url = "https://www.fiverr.com"
        # Приводим страны к нижнему регистру для удобства сравнения
        self.exclude_countries = [c.strip().lower() for c in exclude_countries] if exclude_countries else []
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    async def search_profiles(self, keyword: str, max_pages: int = 15) -> List[Dict]:
        """
        Поиск профилей по ключевому слову с пролистыванием до max_pages страниц.
        Возвращает список профилей, удовлетворяющих условиям:
        - 0 отзывов
        - наличие гигов
        - страна не в списке исключённых
        """
        found_profiles = []

        for page in range(1, max_pages + 1):
            # Формируем URL поиска (пример: https://www.fiverr.com/search/gigs?query=word&page=1)
            url = f"{self.base_url}/search/gigs?query={keyword}&page={page}"
            print(f"Парсинг страницы {page} для слова '{keyword}': {url}")

            try:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        print(f"Ошибка {response.status} на странице {page}")
                        continue

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Поиск карточек продавцов (селекторы могут меняться, нужно уточнять!)
                    # На Fiverr часто используется data-testid="seller-card" или подобное
                    seller_cards = soup.find_all('div', attrs={'data-testid': 'seller-card'})
                    if not seller_cards:
                        # Запасной вариант
                        seller_cards = soup.find_all('div', class_=re.compile('seller-info|freelancer-card'))

                    if not seller_cards:
                        print(f"На странице {page} нет карточек продавцов, возможно, структура изменилась")
                        continue

                    for card in seller_cards:
                        # Извлекаем имя пользователя из ссылки на профиль
                        username_tag = card.find('a', href=re.compile(r'^/[^/]+$'))
                        if not username_tag:
                            continue
                        username = username_tag['href'].strip('/')
                        profile_url = f"{self.base_url}/{username}"

                        # Парсим страну
                        country_tag = card.find('span', class_=re.compile('country|location'))
                        country = country_tag.text.strip() if country_tag else "Unknown"

                        # Проверяем, исключена ли страна
                        if self.exclude_countries and country.lower() in self.exclude_countries:
                            continue

                        # Парсим количество отзывов
                        reviews_tag = card.find('span', class_=re.compile('reviews|rating-count'))
                        reviews = 0
                        if reviews_tag:
                            reviews_text = reviews_tag.text.strip('()').replace(',', '')
                            reviews = int(reviews_text) if reviews_text.isdigit() else 0

                        # Условие: 0 отзывов
                        if reviews != 0:
                            continue

                        # Проверяем наличие гигов (упрощённо: есть ссылка на гиги или кнопка "My Gigs")
                        gigs_exist = False
                        gigs_link = card.find('a', href=re.compile(r'/gigs'))
                        if gigs_link:
                            gigs_exist = True

                        # Если гигов нет — пропускаем
                        if not gigs_exist:
                            continue

                        # Онлайн-статус через HTML определить невозможно, поэтому пока опускаем
                        # (можно будет добавить позже через отдельный запрос)

                        profile_data = {
                            'username': username,
                            'profile_url': profile_url,
                            'inbox_url': f"{self.base_url}/inbox/{username}",
                            'country': country,
                            'reviews': reviews,
                            'keyword': keyword
                        }
                        found_profiles.append(profile_data)

                    # Задержка между страницами, чтобы не нагружать сервер
                    await asyncio.sleep(3)

            except Exception as e:
                print(f"Ошибка при парсинге страницы {page} для слова {keyword}: {e}")
                continue

        return found_profiles