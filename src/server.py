# server.py
from fastapi import FastAPI, Query
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

SessionLocal = sessionmaker(bind=engine)


# Pydantic model 100% compatible avec le frontend Angular
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
    salary_min: Optional[int] = None      # ← int ou null
    salary_max: Optional[int] = None      # ← int ou null
    description: Optional[str] = None
    skills: Optional[str] = None          # ← string séparée par virgules
    scraped_at: Optional[str] = None

    class Config:
        from_attributes = True  # Remplace orm_mode (obsolète en Pydantic v2)


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

        # Ajout d'un header utile pour la pagination
        response_headers = {
            "X-Total-Count": str(total),
            "X-Has-More": str(offset + limit < total)
        }

        return JSONResponse(content=[job.__dict__ for job in jobs], headers=response_headers)

    finally:
        session.close()


# Route de test rapide
@app.get("/")
def root():
    return {"message": "Job Aggregator API est en ligne !", "docs": "/docs"}
# to run the server :
# uvicorn server:app --reload
