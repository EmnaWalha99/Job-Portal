from sqlalchemy import Column, String, Integer, Date, DateTime, Float, Text
from sqlalchemy.sql import func
from .db_session import Base

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(255), unique=True, index=True, nullable=False)
    source = Column(String, nullable=False)
    title = Column(String)
    detail_link = Column(String)
    company = Column(String)
    date_publication = Column(Date, nullable=True)
    sector = Column(String)
    contract_type = Column(String)
    study_level = Column(Text)
    experience = Column(String)
    availability = Column(Text)
    location = Column(String)
    region = Column(String)
    city = Column(String)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    description = Column(Text)
    skills = Column(Text)
    
    # stores timestamps automatically
    scraped_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
