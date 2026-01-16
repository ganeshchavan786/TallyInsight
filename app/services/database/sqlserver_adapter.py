"""
SQL Server Database Adapter
===========================
SQL Server implementation of the database service using pyodbc.

Prerequisites:
- Install ODBC Driver 17 for SQL Server
- pip install pyodbc

Configuration (config.yaml):
    database:
      type: sqlserver
      host: localhost
      port: 1433
      database: TallyDB
      username: sa
      password: YourPassword
      driver: "ODBC Driver 17 for SQL Server"
"""

import pyodbc
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .base import BaseDatabaseService
from ...config import config
from ...utils.logger import logger
from ...utils.decorators import timed
from ...utils.constants import ALL_TABLES, MASTER_TABLES, TRANSACTION_TABLES


class SQLServerDatabaseService(BaseDatabaseService):
    """SQL Server implementation of database service"""
    
    def __init__(self):
        self._connection: Optional[pyodbc.Connection] = None
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        # Get config values
        db_config = config.database
        self.host = getattr(db_config, 'host', 'localhost')
        self.port = getattr(db_config, 'port', 1433)
        self.database = getattr(db_config, 'database', 'TallyDB')
        self.username = getattr(db_config, 'username', 'sa')
        self.password = getattr(db_config, 'password', '')
        self.driver = getattr(db_config, 'driver', 'ODBC Driver 17 for SQL Server')
        self.trusted_connection = getattr(db_config, 'trusted_connection', False)
    
    def _get_connection_string(self) -> str:
        """Build SQL Server connection string"""
        if self.trusted_connection:
            return (
                f"DRIVER={{{self.driver}}};"
                f"SERVER={self.host},{self.port};"
                f"DATABASE={self.database};"
                f"Trusted_Connection=yes;"
            )
        else:
            return (
                f"DRIVER={{{self.driver}}};"
                f"SERVER={self.host},{self.port};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
            )
    
    async def _run_sync(self, func, *args, **kwargs):
        """Run synchronous function in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, lambda: func(*args, **kwargs))
    
    async def connect(self) -> None:
        """Open database connection"""
        if self._connection is None:
            try:
                conn_str = self._get_connection_string()
                self._connection = await self._run_sync(pyodbc.connect, conn_str)
                self._connection.autocommit = False
                logger.info(f"Connected to SQL Server: {self.host}/{self.database}")
            except Exception as e:
                logger.error(f"SQL Server connection failed: {e}")
                raise
    
    async def disconnect(self) -> None:
        """Close database connection"""
        if self._connection:
            try:
                await self._run_sync(self._connection.close)
            except:
                pass
            self._connection = None
            logger.info("SQL Server connection closed")
    
    async def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._connection is not None
    
    async def execute(self, query: str, params: Tuple = ()) -> int:
        """Execute a query and return affected rows"""
        if not self._connection:
            await self.connect()
        
        def _execute():
            cursor = self._connection.cursor()
            cursor.execute(query, params)
            self._connection.commit()
            return cursor.rowcount
        
        try:
            return await self._run_sync(_execute)
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query[:200]}...")
            raise
    
    async def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows from query"""
        if not self._connection:
            await self.connect()
        
        def _fetch():
            cursor = self._connection.cursor()
            cursor.execute(query, params)
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        
        try:
            return await self._run_sync(_fetch)
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            raise
    
    async def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch single row from query"""
        if not self._connection:
            await self.connect()
        
        def _fetch():
            cursor = self._connection.cursor()
            cursor.execute(query, params)
            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else None
        
        try:
            return await self._run_sync(_fetch)
        except Exception as e:
            logger.error(f"Fetch one failed: {e}")
            raise
    
    async def fetch_scalar(self, query: str, params: Tuple = ()) -> Any:
        """Fetch single value from query"""
        result = await self.fetch_one(query, params)
        if result:
            return list(result.values())[0]
        return None
    
    @timed
    async def bulk_insert(self, table_name: str, rows: List[Dict[str, Any]], 
                          company_name: str = None) -> int:
        """Bulk insert rows into table"""
        if not rows:
            return 0
        
        if not self._connection:
            await self.connect()
        
        if company_name:
            for row in rows:
                row['_company'] = company_name
        
        columns = list(rows[0].keys())
        await self._ensure_columns_exist(table_name, columns)
        
        placeholders = ', '.join(['?' for _ in columns])
        column_names = ', '.join([f'[{col}]' for col in columns])
        
        # Use MERGE for upsert (SQL Server equivalent of INSERT OR REPLACE)
        # For simplicity, using DELETE + INSERT approach
        query = f"INSERT INTO [{table_name}] ({column_names}) VALUES ({placeholders})"
        
        params_list = [tuple(row.get(col) for col in columns) for row in rows]
        
        def _bulk_insert():
            cursor = self._connection.cursor()
            total_inserted = 0
            batch_size = config.sync.batch_size
            
            for i in range(0, len(params_list), batch_size):
                batch = params_list[i:i + batch_size]
                cursor.executemany(query, batch)
                total_inserted += len(batch)
            
            self._connection.commit()
            return total_inserted
        
        try:
            total = await self._run_sync(_bulk_insert)
            logger.debug(f"Inserted {total} rows into {table_name}")
            return total
        except Exception as e:
            logger.error(f"Bulk insert failed for {table_name}: {e}")
            raise
    
    async def truncate_table(self, table_name: str, company_name: str = None) -> None:
        """Delete all rows from a table"""
        if company_name:
            has_company_col = await self._has_column(table_name, '_company')
            if has_company_col:
                await self.execute(f"DELETE FROM [{table_name}] WHERE [_company] = ?", (company_name,))
            else:
                await self.execute(f"DELETE FROM [{table_name}]")
        else:
            await self.execute(f"DELETE FROM [{table_name}]")
    
    async def truncate_all_tables(self, company_name: str = None) -> None:
        """Truncate all tables"""
        for table in ALL_TABLES:
            try:
                await self.truncate_table(table, company_name)
            except Exception as e:
                logger.warning(f"Could not truncate {table}: {e}")
    
    async def get_table_count(self, table_name: str, company_name: str = None) -> int:
        """Get row count for a table"""
        try:
            if not await self.table_exists(table_name):
                return 0
            
            if company_name and await self._has_column(table_name, '_company'):
                result = await self.fetch_scalar(
                    f"SELECT COUNT(*) FROM [{table_name}] WHERE [_company] = ?",
                    (company_name,)
                )
            else:
                result = await self.fetch_scalar(f"SELECT COUNT(*) FROM [{table_name}]")
            
            return result or 0
        except:
            return 0
    
    async def get_all_table_counts(self, company_name: str = None) -> Dict[str, int]:
        """Get row counts for all tables"""
        counts = {}
        for table in ALL_TABLES:
            counts[table] = await self.get_table_count(table, company_name)
        return counts
    
    async def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        result = await self.fetch_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?",
            (table_name,)
        )
        return result > 0
    
    async def get_database_size(self) -> int:
        """Get database size in bytes"""
        try:
            result = await self.fetch_scalar(
                "SELECT SUM(size * 8 * 1024) FROM sys.database_files"
            )
            return result or 0
        except:
            return 0
    
    async def initialize_schema(self) -> None:
        """Create all required tables"""
        await self.create_tables()
    
    async def _has_column(self, table_name: str, column_name: str) -> bool:
        """Check if column exists in table"""
        result = await self.fetch_scalar(
            """SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
               WHERE TABLE_NAME = ? AND COLUMN_NAME = ?""",
            (table_name, column_name)
        )
        return result > 0
    
    async def _ensure_columns_exist(self, table_name: str, columns: List[str]) -> None:
        """Auto-add missing columns to table"""
        if not self._connection:
            await self.connect()
        
        for col in columns:
            if not await self._has_column(table_name, col):
                try:
                    await self.execute(
                        f"ALTER TABLE [{table_name}] ADD [{col}] NVARCHAR(MAX) DEFAULT ''"
                    )
                    logger.debug(f"Added column '{col}' to table '{table_name}'")
                except Exception as e:
                    logger.warning(f"Could not add column {col}: {e}")
    
    @timed
    async def create_tables(self, incremental: bool = None) -> None:
        """Create all database tables"""
        if not self._connection:
            await self.connect()
        
        schema_sql = self._get_schema_sql()
        
        def _create():
            cursor = self._connection.cursor()
            statements = [s.strip() for s in schema_sql.split('GO') if s.strip()]
            for stmt in statements:
                if stmt.strip():
                    try:
                        cursor.execute(stmt)
                    except Exception as e:
                        logger.debug(f"Statement skipped: {e}")
            self._connection.commit()
        
        try:
            await self._run_sync(_create)
            logger.info("Database tables created successfully")
            await self._ensure_company_column_exists()
            await self.ensure_audit_tables()
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    async def _ensure_company_column_exists(self) -> None:
        """Add _company column to all tables"""
        for table in ALL_TABLES:
            if not await self._has_column(table, '_company'):
                try:
                    await self.execute(
                        f"ALTER TABLE [{table}] ADD [_company] NVARCHAR(256) DEFAULT ''"
                    )
                except:
                    pass
    
    async def ensure_audit_tables(self) -> None:
        """Create audit trail tables"""
        audit_sql = """
        IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'audit_log')
        CREATE TABLE audit_log (
            id INT IDENTITY(1,1) PRIMARY KEY,
            sync_session_id NVARCHAR(100),
            sync_type NVARCHAR(50),
            table_name NVARCHAR(100) NOT NULL,
            record_guid NVARCHAR(100),
            record_name NVARCHAR(256),
            action NVARCHAR(50) NOT NULL,
            old_data NVARCHAR(MAX),
            new_data NVARCHAR(MAX),
            changed_fields NVARCHAR(MAX),
            company NVARCHAR(256) NOT NULL,
            tally_alter_id INT,
            created_at DATETIME DEFAULT GETDATE(),
            status NVARCHAR(50) DEFAULT 'SUCCESS',
            message NVARCHAR(MAX)
        )
        """
        try:
            await self.execute(audit_sql)
        except Exception as e:
            logger.warning(f"Could not create audit_log: {e}")
    
    async def ensure_company_config_table(self) -> None:
        """Ensure company_config table exists"""
        sql = """
        IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'company_config')
        CREATE TABLE company_config (
            id INT IDENTITY(1,1) PRIMARY KEY,
            company_name NVARCHAR(256) NOT NULL UNIQUE,
            company_guid NVARCHAR(100) DEFAULT '',
            company_alterid INT DEFAULT 0,
            last_alter_id_master INT DEFAULT 0,
            last_alter_id_transaction INT DEFAULT 0,
            books_from NVARCHAR(20) DEFAULT '',
            books_to NVARCHAR(20) DEFAULT '',
            last_sync_at DATETIME,
            last_sync_type NVARCHAR(50),
            sync_count INT DEFAULT 0,
            created_at DATETIME DEFAULT GETDATE(),
            updated_at DATETIME DEFAULT GETDATE()
        )
        """
        try:
            await self.execute(sql)
            
            # Create _diff and _delete tables
            await self.execute("""
                IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '_diff')
                CREATE TABLE _diff (guid NVARCHAR(100) PRIMARY KEY, alterid NVARCHAR(50) DEFAULT '')
            """)
            await self.execute("""
                IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '_delete')
                CREATE TABLE _delete (guid NVARCHAR(100) PRIMARY KEY)
            """)
        except Exception as e:
            logger.warning(f"Could not ensure company_config table: {e}")
    
    async def ensure_alterid_column_exists(self) -> None:
        """Add alterid column to all tables for incremental sync support"""
        if not self._connection:
            await self.connect()
        
        added_count = 0
        for table in ALL_TABLES:
            try:
                # Check if column exists
                result = await self.fetch_scalar(f"""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = '{table}' AND COLUMN_NAME = 'alterid'
                """)
                if result == 0:
                    await self.execute(f"ALTER TABLE [{table}] ADD alterid INT DEFAULT 0")
                    added_count += 1
            except Exception as e:
                logger.debug(f"Could not add alterid to {table}: {e}")
        
        if added_count > 0:
            logger.info(f"Added alterid column to {added_count} tables for incremental sync")
    
    async def update_company_config(self, company_name: str, company_guid: str = "",
                                     company_alterid: int = 0, last_alter_id_master: int = 0,
                                     last_alter_id_transaction: int = 0, sync_type: str = "full",
                                     books_from: str = "", books_to: str = "", **kwargs) -> None:
        """Update or insert company config record"""
        if not self._connection:
            await self.connect()
        
        existing = await self.fetch_one(
            "SELECT id, sync_count FROM company_config WHERE company_name = ?",
            (company_name,)
        )
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if existing:
            sync_count = (existing.get('sync_count') or 0) + 1
            await self.execute('''
                UPDATE company_config SET
                    company_guid = CASE WHEN ? != '' THEN ? ELSE company_guid END,
                    company_alterid = CASE WHEN ? > 0 THEN ? ELSE company_alterid END,
                    last_alter_id_master = ?,
                    last_alter_id_transaction = ?,
                    books_from = CASE WHEN ? != '' THEN ? ELSE books_from END,
                    books_to = CASE WHEN ? != '' THEN ? ELSE books_to END,
                    last_sync_at = ?,
                    last_sync_type = ?,
                    sync_count = ?,
                    updated_at = ?
                WHERE company_name = ?
            ''', (company_guid, company_guid, company_alterid, company_alterid,
                  last_alter_id_master, last_alter_id_transaction,
                  books_from, books_from, books_to, books_to,
                  now, sync_type, sync_count, now, company_name))
        else:
            await self.execute('''
                INSERT INTO company_config 
                (company_name, company_guid, company_alterid, last_alter_id_master, 
                 last_alter_id_transaction, books_from, books_to, last_sync_at, 
                 last_sync_type, sync_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            ''', (company_name, company_guid, company_alterid, last_alter_id_master,
                  last_alter_id_transaction, books_from, books_to, now, sync_type, now, now))
    
    async def get_company_config(self, company_name: str) -> Optional[Dict[str, Any]]:
        """Get company config by name"""
        return await self.fetch_one(
            "SELECT * FROM company_config WHERE company_name = ?",
            (company_name,)
        )
    
    async def get_synced_companies(self) -> List[Dict[str, Any]]:
        """Get list of synced companies"""
        try:
            return await self.fetch_all(
                "SELECT company_name, company_guid, company_alterid, last_alter_id_master, "
                "last_alter_id_transaction, books_from, books_to, last_sync_at, sync_count "
                "FROM company_config ORDER BY company_name"
            )
        except Exception as e:
            logger.error(f"Failed to get synced companies: {e}")
            return []
    
    async def delete_company_data(self, company_name: str) -> int:
        """Delete all data for a specific company"""
        if not self._connection:
            await self.connect()
        
        total_deleted = 0
        
        for table in ALL_TABLES:
            try:
                if not await self.table_exists(table):
                    continue
                
                if await self._has_column(table, '_company'):
                    count = await self.fetch_scalar(
                        f"SELECT COUNT(*) FROM [{table}] WHERE [_company] = ?",
                        (company_name,)
                    )
                    await self.execute(
                        f"DELETE FROM [{table}] WHERE [_company] = ?",
                        (company_name,)
                    )
                    total_deleted += count or 0
            except Exception as e:
                logger.warning(f"Error deleting from {table}: {e}")
        
        # Delete from company_config
        await self.execute(
            "DELETE FROM company_config WHERE company_name = ?",
            (company_name,)
        )
        total_deleted += 1
        
        logger.info(f"Deleted company '{company_name}': {total_deleted} total rows")
        return total_deleted
    
    def _get_schema_sql(self) -> str:
        """Get SQL Server schema SQL"""
        return '''
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'config')
CREATE TABLE config (
    name NVARCHAR(100) PRIMARY KEY,
    value NVARCHAR(MAX) NOT NULL DEFAULT ''
)
GO

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'mst_group')
CREATE TABLE mst_group (
    guid NVARCHAR(100) PRIMARY KEY,
    name NVARCHAR(256) NOT NULL DEFAULT '',
    parent NVARCHAR(256) NOT NULL DEFAULT '',
    primary_group NVARCHAR(256) NOT NULL DEFAULT '',
    is_revenue INT NOT NULL DEFAULT 0,
    is_deemedpositive INT NOT NULL DEFAULT 0,
    is_subledger INT NOT NULL DEFAULT 0,
    sort_position INT NOT NULL DEFAULT 0
)
GO

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'mst_ledger')
CREATE TABLE mst_ledger (
    guid NVARCHAR(100) PRIMARY KEY,
    name NVARCHAR(256) NOT NULL DEFAULT '',
    parent NVARCHAR(256) NOT NULL DEFAULT '',
    alias NVARCHAR(256) NOT NULL DEFAULT '',
    opening_balance DECIMAL(18,2) NOT NULL DEFAULT 0,
    description NVARCHAR(MAX) NOT NULL DEFAULT '',
    mailing_name NVARCHAR(256) NOT NULL DEFAULT '',
    mailing_address NVARCHAR(MAX) NOT NULL DEFAULT '',
    mailing_state NVARCHAR(100) NOT NULL DEFAULT '',
    mailing_country NVARCHAR(100) NOT NULL DEFAULT '',
    mailing_pincode NVARCHAR(20) NOT NULL DEFAULT '',
    email NVARCHAR(256) NOT NULL DEFAULT '',
    phone NVARCHAR(50) NOT NULL DEFAULT '',
    mobile NVARCHAR(50) NOT NULL DEFAULT '',
    contact NVARCHAR(256) NOT NULL DEFAULT '',
    pan NVARCHAR(20) NOT NULL DEFAULT '',
    gstin NVARCHAR(20) NOT NULL DEFAULT '',
    gst_registration_type NVARCHAR(50) NOT NULL DEFAULT '',
    is_bill_wise INT NOT NULL DEFAULT 0,
    is_cost_centre INT NOT NULL DEFAULT 0
)
GO

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'mst_vouchertype')
CREATE TABLE mst_vouchertype (
    guid NVARCHAR(100) PRIMARY KEY,
    name NVARCHAR(256) NOT NULL DEFAULT '',
    parent NVARCHAR(256) NOT NULL DEFAULT '',
    numbering_method NVARCHAR(50) NOT NULL DEFAULT '',
    is_active INT NOT NULL DEFAULT 1
)
GO

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'mst_stock_item')
CREATE TABLE mst_stock_item (
    guid NVARCHAR(100) PRIMARY KEY,
    name NVARCHAR(256) NOT NULL DEFAULT '',
    parent NVARCHAR(256) NOT NULL DEFAULT '',
    category NVARCHAR(256) NOT NULL DEFAULT '',
    alias NVARCHAR(256) NOT NULL DEFAULT '',
    uom NVARCHAR(50) NOT NULL DEFAULT '',
    opening_quantity DECIMAL(18,4) NOT NULL DEFAULT 0,
    opening_rate DECIMAL(18,4) NOT NULL DEFAULT 0,
    opening_value DECIMAL(18,2) NOT NULL DEFAULT 0,
    gst_applicable NVARCHAR(50) NOT NULL DEFAULT '',
    hsn_code NVARCHAR(20) NOT NULL DEFAULT '',
    gst_rate DECIMAL(5,2) NOT NULL DEFAULT 0
)
GO

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'trn_voucher')
CREATE TABLE trn_voucher (
    guid NVARCHAR(100) PRIMARY KEY,
    date NVARCHAR(20) NOT NULL DEFAULT '',
    voucher_type NVARCHAR(100) NOT NULL DEFAULT '',
    voucher_number NVARCHAR(100) NOT NULL DEFAULT '',
    reference_number NVARCHAR(100) NOT NULL DEFAULT '',
    reference_date NVARCHAR(20),
    narration NVARCHAR(MAX) NOT NULL DEFAULT '',
    party_name NVARCHAR(256) NOT NULL DEFAULT '',
    place_of_supply NVARCHAR(100) NOT NULL DEFAULT '',
    is_invoice INT NOT NULL DEFAULT 0,
    is_accounting_voucher INT NOT NULL DEFAULT 0,
    is_inventory_voucher INT NOT NULL DEFAULT 0,
    is_order_voucher INT NOT NULL DEFAULT 0,
    is_cancelled INT NOT NULL DEFAULT 0,
    is_optional INT NOT NULL DEFAULT 0
)
GO

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'trn_accounting')
CREATE TABLE trn_accounting (
    id INT IDENTITY(1,1) PRIMARY KEY,
    guid NVARCHAR(100) NOT NULL,
    ledger NVARCHAR(256) NOT NULL DEFAULT '',
    amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    amount_forex DECIMAL(18,2) NOT NULL DEFAULT 0,
    currency NVARCHAR(10) NOT NULL DEFAULT '',
    is_party_ledger INT NOT NULL DEFAULT 0
)
GO

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'trn_inventory')
CREATE TABLE trn_inventory (
    id INT IDENTITY(1,1) PRIMARY KEY,
    guid NVARCHAR(100) NOT NULL,
    stock_item NVARCHAR(256) NOT NULL DEFAULT '',
    quantity DECIMAL(18,4) NOT NULL DEFAULT 0,
    rate DECIMAL(18,4) NOT NULL DEFAULT 0,
    amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    godown NVARCHAR(256) NOT NULL DEFAULT '',
    tracking_number NVARCHAR(100) NOT NULL DEFAULT ''
)
GO
'''
    
    def get_placeholder(self) -> str:
        """SQL Server uses ? as placeholder with pyodbc"""
        return '?'
    
    def get_table_quote(self) -> str:
        """SQL Server uses square brackets"""
        return '['
