import requests
from bs4 import BeautifulSoup


def parse_fiverr(query="logo design"):
    url = f"https://www.fiverr.com/search/gigs?query={query.replace(' ', '%20')}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        gigs = []

        # Fiverr часто меняет классы, но сейчас работает так:
        items = soup.find_all("div", class_="gig-card-layout")

        for item in items[:5]:  # берем первые 5
            try:
                title = item.find("h3").text.strip()
                link = "https://www.fiverr.com" + item.find("a")["href"]

                price_tag = item.find("span", class_="price")
                price = price_tag.text.strip() if price_tag else "Не указана"

                gigs.append({
                    "title": title,
                    "price": price,
                    "link": link
                })

            except Exception:
                continue

        return gigs

    except Exception as e:
        print("Ошибка парсинга:", e)
        return []