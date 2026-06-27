"""
Scrape the full becarios listing from:
  https://becarios.fundacionlacaixa.org/es/web/guest/resultados-becarios

Outputs: becarios.csv  (name, url, programme, year, country, university)

Usage:
    pip install playwright
    playwright install chromium
    python scrape_becarios.py              # writes becarios.csv
    python scrape_becarios.py output.csv   # custom output path

The site is a Liferay portal with client-side pagination; Playwright drives
Chromium to click through every page and collect each scholar card.
"""

import csv
import sys
import time

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE_URL = "https://becarios.fundacionlacaixa.org"
START_URL = f"{BASE_URL}/es/web/guest/resultados-becarios"

# CSS selectors — adjust if the site ever redesigns
CARD_SEL      = ".scholar-card, .becario-card, article.portlet-body, " \
                ".search-results .result, li.scholar, .scholar-item, " \
                ".portlet-content li, .results-list li"
NAME_SEL      = "h2, h3, .name, .title, .scholar-name"
LINK_SEL      = "a"
NEXT_BTN_SEL  = "a[aria-label*='Next'], a[aria-label*='Siguiente'], " \
                "li.next > a, .pagination-next a, button.next, " \
                "a.next, [class*='next']:not([disabled])"


def _abs(href: str) -> str:
    if href.startswith("http"):
        return href
    return BASE_URL + href if href.startswith("/") else BASE_URL + "/" + href


def scrape(output_file: str = "becarios.csv") -> list[dict]:
    records: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (compatible; BecariosScraper/1.0)",
            locale="es-ES",
        )
        page = ctx.new_page()

        print(f"Opening {START_URL} …")
        page.goto(START_URL, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(2000)

        page_num = 1

        while True:
            print(f"  Scraping page {page_num} …", end=" ", flush=True)

            # --- collect cards on this page ---
            cards = page.query_selector_all(
                ".scholar-card, .becario-card, "
                ".search-results .result-item, "
                ".portlet-body .results li, "
                "article, .card"
            )

            if not cards:
                # Fallback: grab every link that points to a scholar profile
                links = page.query_selector_all("a[href*='becario'], a[href*='scholar']")
                for a in links:
                    href = a.get_attribute("href") or ""
                    name = (a.inner_text() or "").strip()
                    if href and name:
                        records.append({"name": name, "url": _abs(href),
                                        "programme": "", "year": "", "country": "", "university": ""})
                print(f"{len(links)} links (fallback)")
            else:
                page_records = 0
                for card in cards:
                    a_el    = card.query_selector(LINK_SEL)
                    name_el = card.query_selector(NAME_SEL)

                    href = (a_el.get_attribute("href") if a_el else None) or ""
                    name = (name_el.inner_text() if name_el else
                            (a_el.inner_text() if a_el else "")).strip()

                    if not name:
                        continue

                    # Extra metadata — best-effort
                    def txt(sel: str) -> str:
                        el = card.query_selector(sel)
                        return (el.inner_text() or "").strip() if el else ""

                    records.append({
                        "name":       name,
                        "url":        _abs(href) if href else "",
                        "programme":  txt(".programme, .beca, .scholarship-type"),
                        "year":       txt(".year, .convocatoria, .call"),
                        "country":    txt(".country, .pais"),
                        "university": txt(".university, .universidad, .institution"),
                    })
                    page_records += 1
                print(f"{page_records} becarios")

            # --- try to go to next page ---
            try:
                next_btn = page.query_selector(NEXT_BTN_SEL)
                if not next_btn:
                    break

                next_btn.scroll_into_view_if_needed()
                next_btn.click()
                page.wait_for_load_state("networkidle", timeout=20_000)
                page.wait_for_timeout(1500)
                page_num += 1
            except PWTimeout:
                print("\n  Timeout waiting for next page — stopping.")
                break
            except Exception as exc:
                print(f"\n  Could not advance to next page ({exc}) — stopping.")
                break

        browser.close()

    # De-duplicate by URL
    seen: set[str] = set()
    unique = []
    for r in records:
        key = r["url"] or r["name"]
        if key not in seen:
            seen.add(key)
            unique.append(r)

    print(f"\nTotal unique becarios found: {len(unique)}")

    fieldnames = ["name", "url", "programme", "year", "country", "university"]
    with open(output_file, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique)

    print(f"Saved → {output_file}")
    return unique


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "becarios.csv"
    scrape(out)
