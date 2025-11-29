from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
import os

BASE_URL = "https://www.tanitjobs.com/jobs"
CSV_FILE = "tanitjobs_details.csv"


# ---------------- CSV INITIALISATION ----------------

def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "title",
                "company",
                "location",
                "date_posted",
                "job_type",
                "experience",
                "education_level",
                "languages",
                "job_description",
                "requirements",
                "expiration_date",
                "company_logo",
                "tags",
                "link"
            ])


def save_row(data):
    with open(CSV_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            data.get("title", ""),
            data.get("company", ""),
            data.get("location", ""),
            data.get("date_posted", ""),
            data.get("job_type", ""),
            data.get("experience", ""),
            data.get("education_level", ""),
            data.get("languages", ""),
            data.get("job_description", ""),
            data.get("requirements", ""),
            data.get("expiration_date", ""),
            data.get("company_logo", ""),
            data.get("tags", ""),
            data.get("link", "")
        ])


# ---------------- SCRAPE JOB DETAIL ----------------

def scrape_job_detail(driver, job_url):
    driver.get(job_url)
    time.sleep(2)

    data = {}

    # Title
    try:
        data["title"] = driver.find_element(By.CSS_SELECTOR, ".details-header__title").text.strip()
    except:
        data["title"] = ""

    # Company
    try:
        data["company"] = driver.find_element(By.CSS_SELECTOR, ".listing-item__info--item-company").text.strip()
    except:
        data["company"] = ""

    # Location
    try:
        data["location"] = driver.find_element(By.CSS_SELECTOR, ".listing-item__info--item-location").text.strip()
    except:
        data["location"] = ""

    # Date Posted
    try:
        data["date_posted"] = driver.find_element(By.CSS_SELECTOR, ".listing-item__info--item-date").text.strip()
    except:
        data["date_posted"] = ""

    # Job Type (CDI, Temps plein, etc.)
    try:
        job_type = driver.find_element(By.XPATH, "//dl[dt[text()='Type d'emploi désiré :']]/dd").text.strip()
        data["job_type"] = job_type
    except:
        data["job_type"] = ""

    # Experience
    try:
        experience = driver.find_element(By.XPATH, "//dl[dt[text()='Experience :']]/dd").text.strip()
        data["experience"] = experience
    except:
        data["experience"] = ""

    # Education Level
    try:
        education_level = driver.find_element(By.XPATH, "//dl[dt[text()='Niveau d'étude :']]/dd").text.strip()
        data["education_level"] = education_level
    except:
        data["education_level"] = ""

    # Languages
    try:
        languages = driver.find_element(By.XPATH, "//dl[dt[text()='Langue :']]/dd").text.strip()
        data["languages"] = languages
    except:
        data["languages"] = ""

    # Job Description
    try:
        data["job_description"] = driver.find_element(By.CSS_SELECTOR, ".details-body__content.content-text").text.strip()
    except:
        data["job_description"] = ""

    # Requirements
    try:
        data["requirements"] = driver.find_element(By.XPATH, "//h3[text()='Exigences de l\'emploi']/following-sibling::div").text.strip()
    except:
        data["requirements"] = ""

    # Expiration Date
    try:
        data["expiration_date"] = driver.find_element(By.XPATH, "//h3[text()='Date d'expiration']/following-sibling::div").text.strip()
    except:
        data["expiration_date"] = ""

    # Company Logo
    try:
        data["company_logo"] = driver.find_element(By.CSS_SELECTOR, ".profile__img-company").get_attribute("src")
    except:
        data["company_logo"] = ""

    # Tags (Skills, Technologies)
    try:
        tags = driver.find_element(By.CSS_SELECTOR, ".bootstrap-tagsinput").text.strip()
        data["tags"] = tags
    except:
        data["tags"] = ""

    data["link"] = job_url

    print("\n📌 Job Detail Scraped\n", data)
    save_row(data)


# ---------------- SCRAPE MAIN JOB LISTING ----------------

def scrape_main_page(driver, page_url):
    driver.get(page_url)
    time.sleep(2)

    job_links = []

    # Scrape job links
    jobs = driver.find_elements(By.CSS_SELECTOR, ".listing-item__title a.link")
    for job in jobs:
        job_url = job.get_attribute("href")
        job_links.append(job_url)
    
    print(f"\n🚀 Found {len(job_links)} job links on this page.")
    return job_links


# ---------------- MAIN SCRAPER ----------------

def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )

    init_csv()

    # Page URL to scrape job listings
    page_url = BASE_URL + "?searchId=1764161141.6781&action=search&page=1"
    
    # Scrape the job links from the main page
    job_urls = scrape_main_page(driver, page_url)

    # Scrape details for each job
    for url in job_urls:
        scrape_job_detail(driver, url)

    driver.quit()
    print("\n🎉 Done. Results saved in:", CSV_FILE)


if __name__ == "__main__":
    main()
