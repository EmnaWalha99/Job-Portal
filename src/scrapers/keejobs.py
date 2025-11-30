from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime

options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--start-maximized")
options.add_argument("--disable-notifications")
options.add_experimental_option("excludeSwitches", ["enable-automation", "disable-infobars"])

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

BASE_URL = "https://www.keejob.com"


# ---------------- COOKIE HANDLER ----------------

def accept_cookies():
    try:
        time.sleep(1)
        accept_btn = driver.find_element(By.ID, "cookieAccept")
        if accept_btn.is_displayed() and accept_btn.is_enabled():
            accept_btn.click()
            print("Cookies accepted.")
            time.sleep(1)
    except:
        pass


# ---------------- SCRAPE DETAILS PAGE ----------------

def scrape_details(detail_url):
    driver.get(detail_url)
    time.sleep(2)

    details = {
        "sector": None,
        "contract_type": None,
        "date_publication": None,
        "location": None,
        "salary": None,
        "study_level": None,
        "experience": None,
        "availability": None,
        "description": None
    }

    # --- Sector (dans la carte entreprise) ---
    try:
        sector_el = driver.find_element(By.XPATH, "//p[span[contains(.,'Secteur')]]")
        details["sector"] = sector_el.text.replace("Secteur:", "").strip()
    except:
        pass

    # --- Bloc infos (référence, date, contrat, lieu, etc.) ---
    try:
        info_blocks = driver.find_elements(By.CSS_SELECTOR, "div.p-6.space-y-4 > div")

        for block in info_blocks:
            try:
                label = block.find_element(By.TAG_NAME, "h3").text.strip()
            except:
                continue

            if "Date de publication" in label:
                details["date_publication"] = block.find_element(
                    By.TAG_NAME, "p"
                ).text.strip()

            elif "Type de contrat" in label:
                span = block.find_element(By.TAG_NAME, "span")
                details["contract_type"] = " ".join(span.text.split())

            elif "Lieu de travail" in label:
                details["location"] = block.find_element(
                    By.TAG_NAME, "p"
                ).text.strip()

            elif "Expérience requise" in label:
                details["experience"] = block.find_element(
                    By.TAG_NAME, "p"
                ).text.strip()

            elif "Niveau d'études" in label:
                details["study_level"] = block.find_element(
                    By.TAG_NAME, "p"
                ).text.strip()

            elif "Salaire proposé" in label:
                span = block.find_element(By.CSS_SELECTOR, "span")
                details["salary"] = " ".join(span.text.split())

            elif "Disponibilité" in label:
                details["availability"] = block.find_element(
                    By.TAG_NAME, "p"
                ).text.strip()

    except Exception as e:
        print("Error parsing info blocks:", e)

    # --- Description ---
    try:
        desc_el = driver.find_element(By.CSS_SELECTOR, "div.prose")
        details["description"] = desc_el.text.strip()
    except:
        pass

    return details


# ---------------- SCRAPE LIST PAGE ----------------

def scrape_page(url):
    driver.get(url)
    time.sleep(3)
    accept_cookies()

    job_listings = []

    jobs = driver.find_elements(By.CSS_SELECTOR, "article")
    print("Jobs found on page:", len(jobs))

    for job in jobs:
        try:
            title_el = job.find_element(By.CSS_SELECTOR, "h2 a")
            title = title_el.text.strip()
            detail_link = title_el.get_attribute("href")

            job_listings.append({
                "title": title,
                "detail_link": detail_link
            })
        except:
            pass

    return job_listings


# ---------------- MAIN PROGRAM ----------------
csvfilePath ='src/Data/rawData/job_keejobs.csv'
def scrape_all_pages():
    base_url = "https://www.keejob.com/offres-emploi/?page="
    page = 1

    with open(csvfilePath, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            "title", "detail_link",
            "sector", "contract_type", "date_publication",
            "location", "salary", "study_level",
            "experience", "availability", "description",
            "source" ,"scraped_at"
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        while page<=3 :
            url = base_url + str(page)
            print(f"Scraping page {page}...")
            job_listings = scrape_page(url)

            if not job_listings:
                print("No more jobs found. Exiting.")
                break

            for job in job_listings:
                print(f"   Scraping details for: {job['title']}")
                details = scrape_details(job["detail_link"])
                job.update(details)
                
                # on ajoute source et scraped_at timestamp
                job["source"] ="keejob"
                job["scraped_at"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow(job)

            
            page += 1
            

scrape_all_pages()
driver.quit()
