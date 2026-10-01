import time
import random
import logging
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
TimeoutException,
NoSuchElementException,
StaleElementReferenceException,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.naukrigulf.com/data-engineer-jobs"
PAGES_TO_SCRAPE = 3
OUTPUT_CSV = "data_engineer_jobs.csv"

CARD_SELECTOR = "div.srp-tuple"
TITLE_SELECTOR = "p.designation-title"
COMPANY_SELECTOR = "a.info-org"
LOCATION_SELECTOR = "li.info-loc"
EXPERIENCE_SELECTOR = "li.info-exp"
SNIPPET_SELECTOR = "p.description"
LINK_SELECTOR = "a.info-position"


def build_driver(headless: bool = False) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    return webdriver.Chrome(options=options)


def get_text(parent, selector):
    """Return the text of the first match, or '' if it's missing."""
    try:
        return parent.find_element(By.CSS_SELECTOR, selector).text.strip()
    except (NoSuchElementException, StaleElementReferenceException):
        return ""


def get_link(parent):
    try:
        return parent.find_element(By.CSS_SELECTOR, LINK_SELECTOR).get_attribute("href")
    except (NoSuchElementException, StaleElementReferenceException):
        return ""


def scrape_page(driver, wait, page_num):
    logger.info(f"Scraping page {page_num}...")
    try:
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, CARD_SELECTOR)) > 0)
    except TimeoutException:
        logger.warning(f"No job cards found on page {page_num}.")
        return []

    cards = driver.find_elements(By.CSS_SELECTOR, CARD_SELECTOR)
    logger.info(f"  Found {len(cards)} job card(s)")

    rows = []
    for card in cards:
        rows.append(
            {
                "Job Title": get_text(card, TITLE_SELECTOR),
                "Company Name": get_text(card, COMPANY_SELECTOR),
                "Job Location": get_text(card, LOCATION_SELECTOR),
                "Required Experience": get_text(card, EXPERIENCE_SELECTOR),
                "Full Job Description": get_text(card, SNIPPET_SELECTOR),
                "Job Link": get_link(card),
            }
        )
    return rows


def get_full_description(driver, url):
    driver.get(url)
    time.sleep(random.uniform(2, 3))
    parts = driver.find_elements(By.CSS_SELECTOR, ".job-description")
    return "\n".join(p.text.strip() for p in parts if p.text.strip())


def main():
    driver = build_driver(headless=False)
    wait = WebDriverWait(driver, 15)
    all_rows = []

    try:
        # 1) Collect the cards from pages 1-3
        for page_num in range(1, PAGES_TO_SCRAPE + 1):
            url = SEARCH_URL if page_num == 1 else f"{SEARCH_URL}-{page_num}"
            logger.info(f"Opening {url}")
            driver.get(url)
            all_rows.extend(scrape_page(driver, wait, page_num))
            time.sleep(random.uniform(1.5, 3.0))

        # 2) Open each job to get the full description
        logger.info("Fetching full descriptions...")
        for i, row in enumerate(all_rows, start=1):
            if row["Job Link"]:
                logger.info(f"  Job {i}/{len(all_rows)}")
                full = get_full_description(driver, row["Job Link"])
                if full:
                    row["Full Job Description"] = full

    finally:
        driver.quit()

    df = pd.DataFrame(all_rows)
    before = len(df)
    df = df.drop_duplicates()
    logger.info(f"Collected {before} rows, {len(df)} after removing duplicates")

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    logger.info(f"Saved results to {OUTPUT_CSV}")
    return df


if __name__ == "__main__":
    main()