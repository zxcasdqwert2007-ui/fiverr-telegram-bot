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
            # ✅ Правильные параметры из рабочей ссылки
            url = (f"{self.base_url}/search/gigs?query={keyword}&page={page}"
                   f"&sort=newest_arrivals&seller_level=new&source=sorting_by"
                   f"&ref=seller_level%3Ana&filter=new")
            print(f"🌐 Парсинг страницы {page} для '{keyword}': {url}")

            try:
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    print(f"📡 Статус ответа: {response.status}")
                    if response.status != 200:
                        print(f"❌ Ошибка {response.status} на странице {page}")
                        # Читаем немного ответа для диагностики
                        text_sample = await response.text()
                        print(f"📄 Первые 500 символов ответа:\n{text_sample[:500]}")
                        continue

                    html = await response.text()
                    print(f"📄 Первые 500 символов HTML:\n{html[:500]}")

                    soup = BeautifulSoup(html, 'html.parser')

                    # 🔍 Несколько вариантов поиска карточек продавцов
                    seller_cards = []

                    # Вариант 1: data-testid (современный Fiverr)
                    seller_cards = soup.find_all('div', attrs={'data-testid': 'seller-card'})
                    if seller_cards:
                        print(f"✅ Найдено карточек по data-testid: {len(seller_cards)}")

                    # Вариант 2: общие классы
                    if not seller_cards:
                        seller_cards = soup.find_all('div', class_=re.compile('seller-card|freelancer-card|seller-info'))
                        if seller_cards:
                            print(f"✅ Найдено карточек по class: {len(seller_cards)}")

                    # Вариант 3: ищем любые ссылки на профили и собираем контейнеры-родители
                    if not seller_cards:
                        profile_links = soup.find_all('a', href=re.compile(r'^/[^/]+$'))
                        if profile_links:
                            print(f"🔗 Найдено {len(profile_links)} прямых ссылок на профили")
                            # Для каждой ссылки берём родительский div как карточку
                            for link in profile_links:
                                parent = link.find_parent('div', class_=re.compile('card|item|result'))
                                if parent and parent not in seller_cards:
                                    seller_cards.append(parent)
                            print(f"📦 Собрано {len(seller_cards)} родительских контейнеров")

                    if not seller_cards:
                        print("⚠️ Карточки продавцов не найдены. Возможно, структура изменилась.")
                        continue

                    for card in seller_cards:
                        # Извлекаем имя пользователя из ссылки
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

                        # Наличие гигов (ищем ссылку на гиги)
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

                    print(f"✅ Найдено профилей на странице {page}: {len(found_profiles)}")

                    # Пауза между страницами
                    await asyncio.sleep(3)

            except asyncio.TimeoutError:
                print(f"⏰ Таймаут при загрузке страницы {page}")
                continue
            except Exception as e:
                print(f"❌ Ошибка при парсинге: {e}")
                continue

        return found_profiles