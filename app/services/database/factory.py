"""
Database Factory
================
Factory for creating database service instances based on configuration.
"""

from enum import Enum
from typing import Optional

from ...config import config
from ...utils.logger import logger
from .base import BaseDatabaseService


class DatabaseType(Enum):
    """Supported database types"""
    SQLITE = "sqlite"
    SQLSERVER = "sqlserver"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"


# Singleton instance
_database_service: Optional[BaseDatabaseService] = None


def get_database_service() -> BaseDatabaseService:
    """
    Get database service instance based on configuration.
    
    Returns singleton instance of the appropriate database adapter.
    
    Usage:
        from app.services.database import get_database_service
        
        db = get_database_service()
        await db.connect()
    """
    global _database_service
    
    if _database_service is not None:
        return _database_service
    
    # Get database type from config
    db_type = getattr(config.database, 'type', 'sqlite').lower()
    
    logger.info(f"Initializing database service: {db_type}")
    
    if db_type == DatabaseType.SQLITE.value:
        from .sqlite_adapter import SQLiteDatabaseService
        _database_service = SQLiteDatabaseService()
        
    elif db_type == DatabaseType.SQLSERVER.value:
        from .sqlserver_adapter import SQLServerDatabaseService
        _database_service = SQLServerDatabaseService()
        
    elif db_type == DatabaseType.POSTGRESQL.value:
        from .postgresql_adapter import PostgreSQLDatabaseService
        _database_service = PostgreSQLDatabaseService()
        
    elif db_type == DatabaseType.MYSQL.value:
        from .mysql_adapter import MySQLDatabaseService
        _database_service = MySQLDatabaseService()
        
    elif db_type == DatabaseType.MONGODB.value:
        from .mongodb_adapter import MongoDBDatabaseService
        _database_service = MongoDBDatabaseService()
        
    else:
        # Default to SQLite
        logger.warning(f"Unknown database type '{db_type}', defaulting to SQLite")
        from .sqlite_adapter import SQLiteDatabaseService
        _database_service = SQLiteDatabaseService()
    
    return _database_service


def reset_database_service() -> None:
    """Reset the singleton instance (useful for testing)"""
    global _database_service
    _database_service = None
