from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
from datetime import datetime
from selenium.common.exceptions import NoSuchElementException

options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--start-maximized")
options.add_argument("--disable-notifications")
options.add_experimental_option("excludeSwitches", ["enable-automation", "disable-infobars"])

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

BASE_URL = "https://www.emploitunisie.com"


# ---------------- COOKIE HANDLER ----------------

def deny_cookies():
    try:
        time.sleep(1)
        close_btn = driver.find_element(By.CSS_SELECTOR, "#cookie-consent .close-cookie-consent")

        if close_btn.is_displayed() and close_btn.is_enabled():
            close_btn.click()
            print("Cookies denied.")
            
    except:
        pass


# ---------------- SCRAPE DETAILS PAGE ----------------

def scrape_details(detail_url):
    driver.get(detail_url)
    time.sleep(2)

    details = {
        "sector": None,
        "contract_type": None,
        "location": None,
        "region": None,
        "city": None,
        "salary": None,
        "study_level": None,
        "experience": None,
        "remote": None,
        "description": None,
        "skills": None
    }

    # ---------- DESCRIPTION ----------
    try:
        desc_el = driver.find_element(By.CSS_SELECTOR, ".job-description")
        details["description"] = desc_el.text.strip()
    except:
        pass

    # ---------- QUALIFICATIONS (optional) ----------
    try:
        qualif_el = driver.find_element(By.CSS_SELECTOR, ".job-qualifications")
        # not mandatory but parsed above description anyway
    except:
        pass

    # ---------- CRITERIA LIST ----------
    try:
        criteria_items = driver.find_elements(By.CSS_SELECTOR, "ul.arrow-list > li")

        for item in criteria_items:
            text = item.text.lower()

            # Sector
            if "secteur d´activité" in text or "secteur d'activité" in text:
                details["sector"] = item.find_element(By.TAG_NAME, "span").text.strip()

            # Contract type
            if "type de contrat" in text:
                details["contract_type"] = item.find_element(By.TAG_NAME, "span").text.strip()

            # Region
            if text.startswith("région"):
                details["region"] = item.find_element(By.TAG_NAME, "span").text.strip()

            # City
            if text.startswith("ville"):
                details["city"] = item.find_element(By.TAG_NAME, "span").text.strip()

            # Experience
            if "niveau d'expérience" in text:
                details["experience"] = item.find_element(By.TAG_NAME, "span").text.strip()

            # Study level
            if "niveau d'études" in text:
                details["study_level"] = item.find_element(By.TAG_NAME, "span").text.strip()

            # Remote work
            if "travail à distance" in text:
                details["remote"] = item.find_element(By.TAG_NAME, "span").text.strip()

            # Salary (not always present)
            if "salaire" in text:
                details["salary"] = item.find_element(By.TAG_NAME, "span").text.strip()

    except Exception as e:
        print("Error parsing criteria:", e)

    # ---------- SKILLS ----------
    try:
        skills = driver.find_elements(By.CSS_SELECTOR, "ul.skills > li")
        details["skills"] = ", ".join([s.text for s in skills])
    except:
        pass

    return details


# ---------------- SCRAPE LIST PAGE ----------------

def scrape_page(url):
    driver.get(url)
    
    deny_cookies()
    job_listings = []

    jobs = driver.find_elements(By.CSS_SELECTOR, "div.card.card-job")
    print("Jobs found on page:", len(jobs))

    for job in jobs:
        try:
            title_el = job.find_element(By.CSS_SELECTOR, "div.card-job-detail > h3 > a")
            title = title_el.text.strip()
            detail_link = title_el.get_attribute("href")
            company = job.find_element(By.CSS_SELECTOR, ".card-job-company.company-name").text.strip()
            time_posted = job.find_element(By.CSS_SELECTOR, "div.card-job-detail > time").text.strip()
            
            job_listings.append({
                "title": title,
                "detail_link": detail_link,
                "company": company,
                "date_publication": time_posted
            })
        except:
            pass

    return job_listings


csvfilePath = 'src/Data/rawData/job_emploisTunisie.csv'

def scrape_all_pages():
    base_url = "https://www.emploitunisie.com/recherche-jobs-tunisie"
    
    with open(csvfilePath, 'w', newline='', encoding='utf-8') as csvfile:
        #source et scraped_at dans les fieldnames
        fieldnames = [
            "title", "detail_link", "company", "date_publication",
            "sector", "contract_type", "location", "region", "city", 
            "salary", "study_level", "experience", "remote", 
            "description", "skills",
            "source", "scraped_at"
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        page = 1
        
        while page <= 1:
            print(f"Scraping page {page}...")
            job_listings = scrape_page(base_url)

            if not job_listings:
                print("No more jobs found. Exiting.")
                break

            for job in job_listings:
                print(f"Scraping details for: {job['title']}")
                details = scrape_details(job["detail_link"])
                job.update(details)
                
                # source et scraped_at avant d'écrire
                job["source"] = "emploitunisie"
                job["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                writer.writerow(job)

            page += 1
            base_url = base_url + f"?page={page-1}"

scrape_all_pages()
driver.quit()