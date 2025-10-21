"""
Database configuration for DigiClinic.
MYSQL ONLY CONFIGURATION - NO SQLITE FALLBACK
"""

import os
from typing import Optional
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv
from fastapi import HTTPException

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
MYSQL_USER: Optional[str] = os.getenv("MYSQL_USER")
MYSQL_PASSWORD: Optional[str] = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST: Optional[str] = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT: Optional[str] = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB: Optional[str] = os.getenv("MYSQL_DB", "digiclinic")

# Default MySQL configuration for testing/development
if not MYSQL_USER:
    MYSQL_USER = "root"
    MYSQL_PASSWORD = ""
    MYSQL_HOST = "localhost"
    MYSQL_PORT = "3306" 
    MYSQL_DB = "digiclinic"

def get_database_url() -> str:
    """Get database URL - MYSQL ONLY."""
    if DATABASE_URL:
        if "sqlite" in DATABASE_URL.lower():
            raise ValueError("❌ SQLITE NOT ALLOWED! System configured for MySQL only.")
        return DATABASE_URL
    
    # MySQL configuration
    password_part = f":{MYSQL_PASSWORD}" if MYSQL_PASSWORD else ""
    mysql_url = f"mysql+pymysql://{MYSQL_USER}{password_part}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    
    print(f"Using MySQL database: {MYSQL_DB} on {MYSQL_HOST}")
    return mysql_url

def get_engine():
    """Get SQLAlchemy engine - MYSQL ONLY."""
    try:
        database_url = get_database_url()
        
        # Ensure no SQLite usage
        if database_url.startswith("sqlite"):
            raise ValueError("❌ SQLITE DETECTED! System is configured for MySQL only.")
        
        # MySQL configuration only
        if not database_url.startswith("mysql"):
            raise ValueError("❌ Only MySQL databases are supported!")
        
        engine = create_engine(
            database_url,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=10,
            max_overflow=20
        )
        
        # Test connection
        connection = engine.connect()
        connection.close()
        print("MySQL connection successful")
        
        return engine
        
    except Exception as e:
        print(f"MySQL connection failed: {e}")
        print("Creating fallback configuration...")
        
        # Create a simple fallback for development that will fail gracefully
        return create_engine("mysql+pymysql://test:test@localhost:3306/testdb")

# Create engine and session
try:
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    metadata = MetaData()
    Base = declarative_base()
except Exception as e:
    print(f"Database initialization failed: {e}")
    # Create empty session factory for development
    SessionLocal = None
    Base = None

# Simple dependency function
def get_db():
    """Get database session dependency"""
    if SessionLocal is None:
        # Fallback for when MySQL is not available
        raise HTTPException(status_code=503, detail="Database not available")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()