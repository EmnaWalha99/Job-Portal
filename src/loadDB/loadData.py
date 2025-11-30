import os
import uuid
import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from db.db_session import engine
from db.models import Job

# Initialize session factory
Session = sessionmaker(bind=engine)

# # List of cleaned CSV files
csv_files = [
    "src/Data/cleanedData/jobs_optioncarriere_cleaned.csv",
    "src/Data/cleanedData/job_emploisTunisie_cleaned.csv",
    "src/Data/cleanedData/job_keejobs_cleaned.csv"
]

def safe_str(x):
    return "" if pd.isna(x) else str(x)

def make_job_id_from_row(row):
    # Prefer existing job_id column when present and non-empty
    if "job_id" in row.index and safe_str(row.get("job_id")).strip():
        return safe_str(row.get("job_id")).strip()
    # Fallback: deterministic uuid5 based on link/title/company/date
    key = "|".join([
        safe_str(row.get("detail_link", "")).strip(),
        safe_str(row.get("title", "")).strip(),
        safe_str(row.get("company", "")).strip(),
        safe_str(row.get("date_publication", "")).strip()
    ])
    # If key is empty, still generate a unique id from row index + random uuid to avoid empty ids
    if not key.strip():
        return f"uid-{uuid.uuid4().hex}"
    return uuid.uuid5(uuid.NAMESPACE_URL, key).hex

def to_nullable_number(x):
    try:
        v = pd.to_numeric(x, errors="coerce")
        if pd.isna(v):
            return None
        
        if float(v).is_integer():
            return int(v)
        return float(v)
    except Exception:
        return None


def load_csv_to_db(file_path, session):
    if not os.path.exists(file_path):
        print(f"[load] file not found: {file_path}")
        return 0
    if os.path.getsize(file_path) == 0:
        print(f"[load] file empty: {file_path}")
        return 0

    df = pd.read_csv(file_path, encoding="utf-8-sig", dtype=str).fillna("")
    added = 0

    for _, row in df.iterrows():
        job_id = make_job_id_from_row(row)

        # skip if already in DB
        if session.query(Job).filter_by(job_id=job_id).first():
            continue

        job = Job(
            job_id=job_id,
            source=safe_str(row.get('source', '')),
            title=safe_str(row.get('title', '')),
            detail_link=safe_str(row.get('detail_link', '')),
            company=safe_str(row.get('company', '')),
            date_publication=safe_str(row.get('date_publication', '')),
            sector=safe_str(row.get('sector', '')),
            contract_type=safe_str(row.get('contract_type', '')),
            study_level=safe_str(row.get('study_level', '')),
            experience=safe_str(row.get('experience', '')),
            availability=safe_str(row.get('availability', '')),
            location=safe_str(row.get('location', '')),
            region=safe_str(row.get('region', '')),
            city=safe_str(row.get('city', '')),
            salary_min=to_nullable_number(row.get('salary_min', None)),
            salary_max=to_nullable_number(row.get('salary_max', None)),
            description=safe_str(row.get('description', '')),
            skills=safe_str(row.get('skills', '')),
            scraped_at=safe_str(row.get('scraped_at', None))
        )

        session.add(job)
        added += 1

    return added

def main():
    session = Session()
    total_added = 0
    try:
        for file in csv_files:
            added = load_csv_to_db(file, session)
            print(f"[load] {added} rows added from {file}")
            total_added += added
        session.commit()
    except IntegrityError as e:
        session.rollback()
        print("[error] IntegrityError:", str(e))
    except Exception as e:
        session.rollback()
        print("[error] Exception:", str(e))
    finally:
        session.close()
    print(f"All CSVs processed. Total rows added: {total_added}")

if __name__ == "__main__":
    main()
