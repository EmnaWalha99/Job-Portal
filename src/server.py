# server.py
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import sessionmaker
from db.db_session import engine
from db.models import Job
from datetime import datetime

app = FastAPI(
    title="Job Aggregator API",
    description="API pour le Job Board Angular 19",
    version="1.0.0"
)

# Configuration CORS pour Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],#URL angular
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SessionLocal = sessionmaker(bind=engine)


class JobOut(BaseModel):
    id: int
    job_id: str
    source: str
    title: Optional[str] = None
    detail_link: Optional[str] = None
    company: Optional[str] = None
    date_publication: Optional[str] = None  # ISO date string
    sector: Optional[str] = None
    contract_type: Optional[str] = None
    study_level: Optional[str] = None
    experience: Optional[str] = None
    availability: Optional[str] = None
    location: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: Optional[str] = None
    skills: Optional[str] = None
    scraped_at: Optional[str] = None

    class Config:
        from_attributes = True


@app.get("/jobs", response_model=List[JobOut])
def get_jobs(
    search: Optional[str] = Query(None, description="Recherche dans titre, entreprise, compétences"),
    country: Optional[str] = Query(None, description="Filtrer par pays (ex: France)"),
    limit: int = Query(50, ge=1, le=200, description="Nombre max d'offres"),
    offset: int = Query(0, ge=0, description="Pagination")
):
    session = SessionLocal()
    try:
        query = session.query(Job)

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                Job.title.ilike(pattern) |
                Job.company.ilike(pattern) |
                Job.city.ilike(pattern) |
                Job.skills.ilike(pattern) |
                Job.sector.ilike(pattern)
            )

        if country:
            query = query.filter(Job.country.ilike(f"%{country}%"))

        # Tri par date décroissante
        query = query.order_by(Job.date_publication.desc().nulls_last())

        total = query.count()
        jobs = query.offset(offset).limit(limit).all()

        # Conversion en dictionnaires pour la sérialisation
        jobs_data = []
        for job in jobs:
            job_dict = {
                "id": job.id,
                "job_id": job.job_id,
                "source": job.source,
                "title": job.title,
                "detail_link": job.detail_link,
                "company": job.company,
                "date_publication": job.date_publication.isoformat() if job.date_publication else None,
                "sector": job.sector,
                "contract_type": job.contract_type,
                "study_level": job.study_level,
                "experience": job.experience,
                "availability": job.availability,
                "location": job.location,
                "region": job.region,
                "city": job.city,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "description": job.description,
                "skills": job.skills,
                "scraped_at": job.scraped_at.isoformat() if job.scraped_at else None
            }
            jobs_data.append(job_dict)

        print(f"[DEBUG] Returning {len(jobs_data)} jobs out of {total} total")  # Debug
        
        return jobs_data

    except Exception as e:
        print(f"[ERROR] {str(e)}")  # Debug
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
    finally:
        session.close()


# Route de test rapide
@app.get("/")
def root():
    return {"message": "Job Aggregator API est en ligne !", "docs": "/docs"}


@app.get("/health")
def health():
    session = SessionLocal()
    try:
        count = session.query(Job).count()
        return {"status": "ok", "jobs_count": count}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )
    finally:
        session.close()

# to run the server :
# uvicorn server:app --reload