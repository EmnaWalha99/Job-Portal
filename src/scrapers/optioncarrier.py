import time
import csv
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

# try to force stdout to utf-8 so prints with unicode don't raise on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--start-maximized")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

BASE_URL = "https://www.optioncarriere.tn"

CSV_FILE = 'src/Data/rawData/jobs_optioncarriere.csv'
RAW_COLUMNS = [
    "title",
    "company",
    "location",
    "contract",
    "work_type",
    "posted_relative",
    "raw_content",
    "detail_link",
    "source",
    "scraped_at"
]

def init_csv():
    """Create CSV with headers if it does not exist or is empty"""
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
    need_header = True
    if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
        need_header = False
    if need_header:
        with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=RAW_COLUMNS)
            writer.writeheader()
        print(f"[init_csv] header written to {os.path.abspath(CSV_FILE)}")

def save_to_csv(job):
    """Append a job row to CSV using DictWriter (robust to column order)"""
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
    file_empty = not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0
    with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_COLUMNS)
        if file_empty:
            writer.writeheader()
        row = {k: job.get(k, "") for k in RAW_COLUMNS}
        if not row.get("scraped_at"):
            row["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not row.get("source"):
            row["source"] = "optioncarriere"
        writer.writerow(row)
    print(f"[save_to_csv] appended title='{row.get('title','')}'")

def scrape_detail_page(url):
    try:
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

        try:
            items = driver.find_elements(By.CSS_SELECTOR, "article#job ul.details li")
            data["location"] = items[0].text if len(items) > 0 else ""
            data["contract"] = items[1].text if len(items) > 1 else ""
            data["work_type"] = items[2].text if len(items) > 2 else ""
        except:
            data["location"] = ""
            data["contract"] = ""
            data["work_type"] = ""

        try:
            data["posted_relative"] = driver.find_element(By.CSS_SELECTOR, ".badge-icon").text
        except:
            data["posted_relative"] = ""

        try:
            section = driver.find_element(By.CSS_SELECTOR, "section.content")
            data["raw_content"] = section.text.replace("\n", " ").strip()
        except:
            data["raw_content"] = ""

        data["source"] = "optioncarriere"
        data["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # safe print (stdout reconfigured to utf-8 above)
        print("[scrape_detail_page] extracted:", data.get("title", "")[:100])

        save_to_csv(data)
        return data
    except Exception as e:
        print("[scrape_detail_page] error:", str(e))
        return None

def scrape_page():
    jobs = driver.find_elements(By.CSS_SELECTOR, "ul.jobs > li article.job")
    print(f"[scrape_page] found {len(jobs)} jobs on page")
    for idx, job in enumerate(jobs, start=1):
        try:
            link = job.find_element(By.CSS_SELECTOR, "h2 a").get_attribute("href")
        except:
            continue

        if not link.startswith("http"):
            link = BASE_URL + link

        print(f"[scrape_page] ({idx}/{len(jobs)}) opening: {link}")
        scrape_detail_page(link)

        # return to list page
        try:
            driver.back()
            time.sleep(1)
        except:
            pass

if __name__ == "__main__":
    init_csv()

    driver.get("https://www.optioncarriere.tn/emploi?s=&l=Tunisie&nw=1")
    time.sleep(3)

    while True:
        print("\n[scraper] scraping job list page...")
        scrape_page()

        # next page
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "p.more button.next")
            next_value = next_button.get_attribute("data-value")
            next_url = f"{BASE_URL}/emploi?s=&l=Tunisie&nw=1&p={next_value}"

            print(f"[scraper] next page: {next_url}")
            driver.get(next_url)
            time.sleep(2)
        except Exception:
            print("[scraper] no more pages.")
            break

    driver.quit()
    print("\n[scraper] finished — data saved in:", os.path.abspath(CSV_FILE))