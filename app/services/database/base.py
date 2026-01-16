"""
Base Database Service
=====================
Abstract base class for all database adapters.

All database implementations must inherit from this class
and implement all abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class BaseDatabaseService(ABC):
    """Abstract base class for database services"""
    
    @abstractmethod
    async def connect(self) -> None:
        """Open database connection"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection"""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if database is connected"""
        pass
    
    @abstractmethod
    async def execute(self, query: str, params: Tuple = ()) -> None:
        """Execute a query without returning results"""
        pass
    
    @abstractmethod
    async def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single row"""
        pass
    
    @abstractmethod
    async def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows"""
        pass
    
    @abstractmethod
    async def fetch_scalar(self, query: str, params: Tuple = ()) -> Any:
        """Fetch a single value"""
        pass
    
    @abstractmethod
    async def bulk_insert(self, table_name: str, rows: List[Dict[str, Any]], 
                          company_name: str = None) -> int:
        """Insert multiple rows efficiently"""
        pass
    
    @abstractmethod
    async def truncate_table(self, table_name: str, company_name: str = None) -> None:
        """Delete all rows from a table (optionally filtered by company)"""
        pass
    
    @abstractmethod
    async def truncate_all_tables(self, company_name: str = None) -> None:
        """Delete all data from all tables (optionally filtered by company)"""
        pass
    
    @abstractmethod
    async def get_table_count(self, table_name: str, company_name: str = None) -> int:
        """Get row count for a table"""
        pass
    
    @abstractmethod
    async def get_all_table_counts(self, company_name: str = None) -> Dict[str, int]:
        """Get row counts for all tables"""
        pass
    
    @abstractmethod
    async def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        pass
    
    @abstractmethod
    async def get_database_size(self) -> int:
        """Get database size in bytes"""
        pass
    
    @abstractmethod
    async def initialize_schema(self) -> None:
        """Create all required tables"""
        pass
    
    @abstractmethod
    async def ensure_company_config_table(self) -> None:
        """Ensure company_config table exists"""
        pass
    
    @abstractmethod
    async def ensure_alterid_column_exists(self) -> None:
        """Add alterid column to all tables for incremental sync support"""
        pass
    
    @abstractmethod
    async def update_company_config(self, company_name: str, **kwargs) -> None:
        """Update or insert company config record"""
        pass
    
    @abstractmethod
    async def get_company_config(self, company_name: str) -> Optional[Dict[str, Any]]:
        """Get company config by name"""
        pass
    
    @abstractmethod
    async def get_synced_companies(self) -> List[Dict[str, Any]]:
        """Get list of synced companies"""
        pass
    
    @abstractmethod
    async def delete_company_data(self, company_name: str) -> int:
        """Delete all data for a specific company"""
        pass
    
    def get_placeholder(self) -> str:
        """Get parameter placeholder for this database type"""
        return '?'
    
    def get_table_quote(self) -> str:
        """Get quote character for table/column names"""
        return '"'
