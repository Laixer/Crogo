from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


from app.config import SettingsLocal


engine = create_engine(SettingsLocal.database_url)
SessionLocal = sessionmaker(bind=engine)
