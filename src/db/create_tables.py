from db_session import Base,engine
from models import Job

# Create all tables based on models
Base.metadata.create_all(bind=engine)
print("All tables created successfully (if they did not exist).")
