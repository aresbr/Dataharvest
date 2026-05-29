"""
Scrape all books from https://books.toscrape.com/
Outputs: books.csv with columns title, price, rating, availability, category

Usage:
    python scrape_books.py              # writes books.csv
    python scrape_books.py output.csv   # custom output path

Requirements:
    pip install requests beautifulsoup4
"""

import csv
import sys
import time
import re

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com"

RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def get_soup(url: str, session: requests.Session, retries: int = 3) -> BeautifulSoup:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BookScraper/1.0)"}
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as exc:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            print(f"\n  Retry {attempt + 1}/{retries} after {wait}s ({exc})")
            time.sleep(wait)


def get_categories(session: requests.Session) -> dict[str, str]:
    """Return {category_name: first_page_url} for every category."""
    soup = get_soup(BASE_URL, session)
    links = soup.select("ul.nav-list > li > ul > li > a")
    return {
        a.get_text(strip=True): f"{BASE_URL}/{a['href']}"
        for a in links
    }


def parse_price(raw: str) -> str:
    """Extract the numeric price string, stripping currency symbols."""
    match = re.search(r"[\d]+\.[\d]+", raw)
    return match.group() if match else raw.strip()


def scrape_page(url: str, category: str, session: requests.Session) -> tuple[list[dict], str | None]:
    """Scrape one listing page; return (books, next_page_url or None)."""
    soup = get_soup(url, session)
    books = []

    for article in soup.select("article.product_pod"):
        title = article.select_one("h3 > a")["title"]
        price = parse_price(article.select_one("p.price_color").get_text())
        rating_el = article.select_one("p.star-rating")
        rating = RATING_MAP.get(rating_el["class"][1] if rating_el else "", 0)
        availability = article.select_one("p.availability").get_text(strip=True)

        books.append({
            "title": title,
            "price": price,
            "rating": rating,
            "availability": availability,
            "category": category,
        })

    next_btn = soup.select_one("li.next > a")
    if next_btn:
        # next_btn["href"] is relative (e.g. "page-2.html"); resolve against current dir
        base_dir = url.rsplit("/", 1)[0]
        next_url = f"{base_dir}/{next_btn['href']}"
    else:
        next_url = None

    return books, next_url


def scrape_all(output_file: str = "books.csv") -> list[dict]:
    session = requests.Session()

    print("Fetching category list...")
    categories = get_categories(session)
    print(f"Found {len(categories)} categories\n")

    all_books: list[dict] = []

    for idx, (category, start_url) in enumerate(categories.items(), 1):
        print(f"[{idx:>2}/{len(categories)}] {category:<30}", end="", flush=True)
        page_url: str | None = start_url
        cat_books: list[dict] = []

        while page_url:
            page_books, page_url = scrape_page(page_url, category, session)
            cat_books.extend(page_books)
            print(".", end="", flush=True)
            time.sleep(0.3)

        all_books.extend(cat_books)
        print(f" {len(cat_books)} books")

    print(f"\nTotal: {len(all_books)} books")

    fieldnames = ["title", "price", "rating", "availability", "category"]
    with open(output_file, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_books)

    print(f"Saved → {output_file}")
    return all_books


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "books.csv"
    scrape_all(out)
