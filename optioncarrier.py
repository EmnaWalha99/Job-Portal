from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
import os

options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--start-maximized")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

BASE_URL = "https://www.optioncarriere.tn"

CSV_FILE = "jobs_optioncarriere.csv"


# ---------------- CSV INITIALISATION ----------------

def init_csv():
    """Create CSV with headers if it does not exist"""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "title",
                "company",
                "location",
                "contract",
                "work_type",
                "posted_relative",
                "raw_content",
                "detail_link"
            ])


def save_to_csv(job):
    """Append a job row to CSV"""
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", ""),
            job.get("contract", ""),
            job.get("work_type", ""),
            job.get("posted_relative", ""),
            job.get("raw_content", ""),
            job.get("detail_link", "")
        ])


# ---------------- SCRAPING DETAIL PAGE ----------------

def scrape_detail_page(url):
    driver.get(url)
    time.sleep(2)

    data = {"detail_link": url}

    try:
        data["title"] = driver.find_element(By.CSS_SELECTOR, "article#job h1").text
    except:
        data["title"] = ""

    try:
        data["company"] = driver.find_element(By.CSS_SELECTOR, "article#job p.company").text
    except:
        data["company"] = ""

    # header details
    try:
        items = driver.find_elements(By.CSS_SELECTOR, "article#job ul.details li")
        data["location"] = items[0].text if len(items) > 0 else ""
        data["contract"] = items[1].text if len(items) > 1 else ""
        data["work_type"] = items[2].text if len(items) > 2 else ""
    except:
        data["location"] = ""
        data["contract"] = ""
        data["work_type"] = ""

    # relative date
    try:
        data["posted_relative"] = driver.find_element(By.CSS_SELECTOR, ".badge-icon").text
    except:
        data["posted_relative"] = ""

    # full ANETI-style content
    try:
        section = driver.find_element(By.CSS_SELECTOR, "section.content")
        data["raw_content"] = section.text.replace("\n", " ").strip()
    except:
        data["raw_content"] = ""

    print("\n📌 Extracted:")
    print(data)

    save_to_csv(data)

    return data


# ---------------- SCRAPING LIST PAGE ----------------

def scrape_page():
    jobs = driver.find_elements(By.CSS_SELECTOR, "ul.jobs > li article.job")

    for job in jobs:
        # link of detail page
        try:
            link = job.find_element(By.CSS_SELECTOR, "h2 a").get_attribute("href")
        except:
            continue

        if not link.startswith("http"):
            link = BASE_URL + link

        print(f"\n Opening job: {link}")
        scrape_detail_page(link)

        # return to list page
        driver.back()
        time.sleep(2)


# ---------------- PROGRAM START ----------------

init_csv()

driver.get("https://www.optioncarriere.tn/emploi?s=&l=Tunisie&nw=1")
time.sleep(3)

while True:
    print("\n🔍 Scraping job list page...\n")
    scrape_page()

    # next page
    try:
        next_button = driver.find_element(By.CSS_SELECTOR, "p.more button.next")
        next_value = next_button.get_attribute("data-value")
        next_url = f"{BASE_URL}/emploi?s=&l=Tunisie&nw=1&p={next_value}"

        print(f"\n➡️ Next page: {next_url}\n")
        driver.get(next_url)
        time.sleep(2)
    except:
        print("\n❌ No more pages.")
        break

driver.quit()

print("\n🎉 SCRAPING FINISHED — data saved in:", CSV_FILE)
