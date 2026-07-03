from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

raw_database_url = next(
    (
        os.getenv(variable_name, "").strip()
        for variable_name in ("DATABASE_URL", "MYSQL_URL", "MYSQL_PUBLIC_URL")
        if os.getenv(variable_name, "").strip()
    ),
    "",
)

if raw_database_url:
    DATABASE_URL = make_url(raw_database_url)
    if DATABASE_URL.drivername == "mysql":
        DATABASE_URL = DATABASE_URL.set(drivername="mysql+pymysql")
else:
    db_port = os.getenv("MYSQLPORT") or os.getenv("DB_PORT", "3306")
    if not db_port or db_port.lower() == "none":
        db_port = "3306"

    DATABASE_URL = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("MYSQLUSER") or os.getenv("DB_USER", "root"),
        password=os.getenv("MYSQLPASSWORD") or os.getenv("DB_PASSWORD", ""),
        host=os.getenv("MYSQLHOST") or os.getenv("DB_HOST", "localhost"),
        port=int(db_port),
        database=os.getenv("MYSQLDATABASE") or os.getenv("DB_NAME", "finance_analyzer"),
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
