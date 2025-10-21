"""
Manual database cleanup and recreation
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

def manual_cleanup_database():
    """Manually clean up database"""
    try:
        # Create engine
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Disable foreign key checks
            logger.info("Disabling foreign key checks...")
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            
            # Drop tables in correct order
            tables_to_drop = [
                "audit_logs",
                "chat_messages", 
                "chat_sessions",
                "users",
                "admins"
            ]
            
            for table in tables_to_drop:
                try:
                    logger.info(f"Dropping table: {table}")
                    conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                except Exception as e:
                    logger.warning(f"Could not drop table {table}: {e}")
            
            # Re-enable foreign key checks
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            conn.commit()
            
        logger.info("Manual cleanup completed!")
        
        # Create fresh tables
        logger.info("Creating fresh database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Fresh database tables created successfully!")
        
        logger.info("🎉 Database manual cleanup and recreation completed!")
        
    except Exception as e:
        logger.error(f"❌ Manual cleanup failed: {e}")
        raise

if __name__ == "__main__":
    manual_cleanup_database()

