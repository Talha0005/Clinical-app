"""
Drop and recreate database tables for fresh start
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models.auth_models import Base
from config.database import get_database_url
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def recreate_database():
    """Drop and recreate all tables"""
    try:
        # Create engine
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        # Drop all tables
        logger.info("Dropping existing tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("Tables dropped successfully!")
        
        # Create all tables
        logger.info("Creating fresh database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Fresh database tables created successfully!")
        
        logger.info("🎉 Database recreation completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Database recreation failed: {e}")
        raise

if __name__ == "__main__":
    recreate_database()

