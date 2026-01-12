"""
Database Module
===============
Multi-database support for Tally FastAPI Database Loader.

Supported Databases:
- SQLite (default)
- SQL Server
- PostgreSQL
- MySQL
- MongoDB

Usage:
    from app.services.database import get_database_service
    
    db = get_database_service()
    await db.connect()
    await db.bulk_insert('table_name', rows)
"""

from .factory import get_database_service, DatabaseType
from .base import BaseDatabaseService

__all__ = ['get_database_service', 'DatabaseType', 'BaseDatabaseService']
