import aiohttp
from aiohttp_socks import ProxyConnector
from bs4 import BeautifulSoup
import asyncio
import re
from typing import List, Dict, Optional

class FiverrParser:
    def __init__(self, exclude_countries: List[str] = None, proxy_url: Optional[str] = None):
        self.base_url = "https://www.fiverr.com"
        self.exclude_countries = [c.strip().lower() for c in exclude_countries] if exclude_countries else []
        self.proxy_url = proxy_url
        self.session = None

    async def __aenter__(self):
        if self.proxy_url:
            connector = ProxyConnector.from_url(self.proxy_url)
        else:
            connector = aiohttp.TCPConnector()

        self.session = aiohttp.ClientSession(
            connector=connector,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    async def search_profiles(self, keyword: str, max_pages: int = 15) -> List[Dict]:
        found_profiles = []

        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/search/gigs?query={keyword}&page={page}"
            print(f"Парсинг страницы {page} для '{keyword}': {url}")

            try:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        print(f"Ошибка {response.status} на странице {page}")
                        continue

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Селекторы (подберите под текущую версию Fiverr)
                    seller_cards = soup.find_all('div', attrs={'data-testid': 'seller-card'})
                    if not seller_cards:
                        seller_cards = soup.find_all('div', class_=re.compile('seller-info|freelancer-card'))

                    if not seller_cards:
                        print(f"Нет карточек на странице {page}")
                        continue

                    for card in seller_cards:
                        username_tag = card.find('a', href=re.compile(r'^/[^/]+$'))
                        if not username_tag:
                            continue
                        username = username_tag['href'].strip('/')
                        profile_url = f"{self.base_url}/{username}"

                        # Страна
                        country_tag = card.find('span', class_=re.compile('country|location'))
                        country = country_tag.text.strip() if country_tag else "Unknown"

                        if self.exclude_countries and country.lower() in self.exclude_countries:
                            continue

                        # Отзывы
                        reviews_tag = card.find('span', class_=re.compile('reviews|rating-count'))
                        reviews = 0
                        if reviews_tag:
                            reviews_text = reviews_tag.text.strip('()').replace(',', '')
                            reviews = int(reviews_text) if reviews_text.isdigit() else 0

                        if reviews != 0:
                            continue

                        # Наличие гигов
                        gigs_exist = bool(card.find('a', href=re.compile(r'/gigs')))
                        if not gigs_exist:
                            continue

                        found_profiles.append({
                            'username': username,
                            'profile_url': profile_url,
                            'inbox_url': f"{self.base_url}/inbox/{username}",
                            'country': country,
                            'reviews': reviews,
                            'keyword': keyword
                        })

                    await asyncio.sleep(3)  # Пауза между страницами

            except Exception as e:
                print(f"Ошибка: {e}")
                continue

        return found_profiles