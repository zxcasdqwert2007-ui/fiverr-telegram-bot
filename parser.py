import requests
from bs4 import BeautifulSoup

def parse_fiverr(query="logo design"):
    url = f"https://www.fiverr.com/search/gigs?query={query.replace(' ', '%20')}"
    
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    gigs = []

    for item in soup.select("div[data-testid='gig-card']")[:5]:
        try:
            title = item.select_one("h3").text.strip()
            price = item.select_one("[data-testid='price']").text.strip()
            link = "https://www.fiverr.com" + item.select_one("a")["href"]

            gigs.append({
                "title": title,
                "price": price,
                "link": link
            })
        except:
            continue

    return gigs