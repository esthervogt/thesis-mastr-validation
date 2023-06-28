from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from config import DB_CONN

engine = create_engine(DB_CONN, echo=True)
Base = declarative_base()
