"""
SQLite Database Adapter
=======================
SQLite implementation of the database service.

This is the default database adapter that provides all functionality
using SQLite with aiosqlite for async operations.
"""

import aiosqlite
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseDatabaseService
from ...config import config
from ...utils.logger import logger
from ...utils.decorators import timed
from ...utils.constants import ALL_TABLES, MASTER_TABLES, TRANSACTION_TABLES


class SQLiteDatabaseService(BaseDatabaseService):
    """SQLite implementation of database service"""
    
    def __init__(self):
        self.db_path = getattr(config.database, 'path', './tally.db')
        self._connection: Optional[aiosqlite.Connection] = None
        self._initialized = False
    
    async def _get_connection(self) -> aiosqlite.Connection:
        """Get or create database connection"""
        if self._connection is None:
            db_file = Path(self.db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            
            self._connection = await aiosqlite.connect(
                self.db_path,
                timeout=30.0
            )
            self._connection.row_factory = aiosqlite.Row
            
            if not self._initialized:
                await self._connection.execute("PRAGMA journal_mode=WAL")
                await self._connection.execute("PRAGMA busy_timeout=30000")
                await self._connection.execute("PRAGMA synchronous=NORMAL")
                await self._connection.execute("PRAGMA cache_size=-64000")
                await self._connection.execute("PRAGMA temp_store=MEMORY")
                self._initialized = True
            
            logger.info(f"Connected to SQLite database: {self.db_path}")
        
        return self._connection
    
    async def connect(self) -> None:
        """Open database connection"""
        await self._get_connection()
    
    async def disconnect(self) -> None:
        """Close database connection"""
        if self._connection:
            try:
                await self._connection.close()
            except:
                pass
            self._connection = None
            logger.info("Database connection closed")
    
    async def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._connection is not None
    
    async def execute(self, query: str, params: Tuple = ()) -> int:
        """Execute a query and return affected rows"""
        conn = await self._get_connection()
        
        try:
            cursor = await conn.execute(query, params)
            await conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query[:200]}...")
            raise
    
    async def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """Execute query with multiple parameter sets"""
        conn = await self._get_connection()
        
        try:
            cursor = await conn.executemany(query, params_list)
            await conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            raise
    
    async def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows from query"""
        conn = await self._get_connection()
        
        try:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            raise
    
    async def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch single row from query"""
        conn = await self._get_connection()
        
        try:
            cursor = await conn.execute(query, params)
            row = await cursor.fetchone()
            return dict(row) if row else None
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
        column_names = ', '.join(columns)
        query = f"INSERT OR REPLACE INTO {table_name} ({column_names}) VALUES ({placeholders})"
        
        params_list = [tuple(row.get(col) for col in columns) for row in rows]
        
        try:
            batch_size = config.sync.batch_size
            total_inserted = 0
            
            for i in range(0, len(params_list), batch_size):
                if not self._connection:
                    await self.connect()
                batch = params_list[i:i + batch_size]
                await self._connection.executemany(query, batch)
                total_inserted += len(batch)
            
            if self._connection:
                await self._connection.commit()
            logger.debug(f"Inserted {total_inserted} rows into {table_name}")
            return total_inserted
        except Exception as e:
            logger.error(f"Bulk insert failed for {table_name}: {e}")
            raise
    
    async def truncate_table(self, table_name: str, company_name: str = None) -> None:
        """Delete all rows from a table"""
        if company_name:
            conn = await self._get_connection()
            cursor = await conn.execute(f"PRAGMA table_info({table_name})")
            columns = await cursor.fetchall()
            has_company_col = any(col[1] == '_company' for col in columns)
            
            if has_company_col:
                await self.execute(f"DELETE FROM {table_name} WHERE _company = ?", (company_name,))
            else:
                await self.execute(f"DELETE FROM {table_name}")
        else:
            await self.execute(f"DELETE FROM {table_name}")
    
    async def truncate_all_tables(self, company_name: str = None, company: str = None) -> None:
        """Truncate all tables"""
        # Support both parameter names for backward compatibility
        company_filter = company_name or company
        for table in ALL_TABLES:
            try:
                await self.truncate_table(table, company_filter)
            except Exception as e:
                logger.warning(f"Could not truncate {table}: {e}")
    
    async def get_table_count(self, table_name: str, company_name: str = None) -> int:
        """Get row count for a table"""
        try:
            conn = await self._get_connection()
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            row = await cursor.fetchone()
            if not row or row[0] == 0:
                return 0
            
            if company_name:
                cursor = await conn.execute(f"PRAGMA table_info({table_name})")
                columns = await cursor.fetchall()
                if any(col[1] == '_company' for col in columns):
                    cursor = await conn.execute(
                        f"SELECT COUNT(*) FROM {table_name} WHERE _company = ?",
                        (company_name,)
                    )
                else:
                    cursor = await conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            else:
                cursor = await conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            
            row = await cursor.fetchone()
            return row[0] if row else 0
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
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return result > 0
    
    async def get_database_size(self) -> int:
        """Get database file size in bytes"""
        try:
            return Path(self.db_path).stat().st_size
        except:
            return 0
    
    async def initialize_schema(self) -> None:
        """Create all required tables"""
        await self.create_tables()
    
    @timed
    async def create_tables(self, incremental: bool = None) -> None:
        """Create all database tables"""
        conn = await self._get_connection()
        
        if incremental is None:
            incremental = config.sync.mode == "incremental"
        
        schema_sql = self._load_schema_from_file(incremental=incremental)
        if not schema_sql:
            schema_sql = self._get_schema_sql()
        
        schema_sql = self._convert_sql_for_sqlite(schema_sql)
        
        try:
            statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
            for stmt in statements:
                if stmt.strip():
                    await conn.execute(stmt)
            await conn.commit()
            logger.info("Database tables created successfully")
            
            await self._ensure_company_column_exists()
            await self.ensure_audit_tables()
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    async def _ensure_company_column_exists(self) -> None:
        """Add _company column to all tables"""
        conn = await self._get_connection()
        
        for table in ALL_TABLES:
            try:
                cursor = await conn.execute(f"PRAGMA table_info({table})")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                if "_company" not in column_names:
                    await conn.execute(f"ALTER TABLE {table} ADD COLUMN _company TEXT DEFAULT ''")
            except Exception as e:
                logger.debug(f"Could not add _company to {table}: {e}")
        
        await conn.commit()
    
    async def ensure_alterid_column_exists(self) -> None:
        """Add alterid column to all tables for incremental sync support"""
        conn = await self._get_connection()
        added_count = 0
        
        for table in ALL_TABLES:
            try:
                cursor = await conn.execute(f"PRAGMA table_info({table})")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                if "alterid" not in column_names:
                    await conn.execute(f"ALTER TABLE {table} ADD COLUMN alterid INTEGER DEFAULT 0")
                    added_count += 1
                    logger.debug(f"Added alterid column to {table}")
            except Exception as e:
                logger.debug(f"Could not add alterid to {table}: {e}")
        
        await conn.commit()
        if added_count > 0:
            logger.info(f"Added alterid column to {added_count} tables for incremental sync")
    
    async def _ensure_columns_exist(self, table_name: str, columns: List[str]) -> None:
        """Auto-add missing columns to table"""
        conn = await self._get_connection()
        
        try:
            cursor = await conn.execute(f"PRAGMA table_info({table_name})")
            existing_columns = await cursor.fetchall()
            existing_column_names = [col[1] for col in existing_columns]
            
            for col in columns:
                if col not in existing_column_names:
                    await conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} TEXT DEFAULT ''")
            
            await conn.commit()
        except Exception as e:
            logger.warning(f"Could not ensure columns for {table_name}: {e}")
    
    async def ensure_audit_tables(self) -> None:
        """Create audit trail tables"""
        conn = await self._get_connection()
        
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_session_id TEXT,
                    sync_type TEXT,
                    table_name TEXT NOT NULL,
                    record_guid TEXT,
                    record_name TEXT,
                    action TEXT NOT NULL,
                    old_data TEXT,
                    new_data TEXT,
                    changed_fields TEXT,
                    company TEXT NOT NULL,
                    tally_alter_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'SUCCESS',
                    message TEXT
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS deleted_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    record_guid TEXT NOT NULL,
                    record_name TEXT,
                    record_data TEXT NOT NULL,
                    company TEXT NOT NULL,
                    sync_session_id TEXT,
                    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_restored INTEGER DEFAULT 0,
                    restored_at TIMESTAMP
                )
            """)
            
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(sync_session_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_table ON audit_log(table_name)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_company ON audit_log(company)")
            
            # Create sync_history table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    rows_processed INTEGER DEFAULT 0,
                    company_name TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.commit()
        except Exception as e:
            logger.error(f"Failed to create audit tables: {e}")
    
    async def ensure_company_config_table(self) -> None:
        """Ensure company_config table exists"""
        conn = await self._get_connection()
        try:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS company_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL UNIQUE,
                    company_guid TEXT DEFAULT '',
                    company_alterid INTEGER DEFAULT 0,
                    last_alter_id_master INTEGER DEFAULT 0,
                    last_alter_id_transaction INTEGER DEFAULT 0,
                    books_from TEXT DEFAULT '',
                    books_to TEXT DEFAULT '',
                    last_sync_at TEXT,
                    last_sync_type TEXT,
                    sync_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            try:
                await conn.execute("ALTER TABLE company_config ADD COLUMN books_from TEXT DEFAULT ''")
            except:
                pass
            try:
                await conn.execute("ALTER TABLE company_config ADD COLUMN books_to TEXT DEFAULT ''")
            except:
                pass
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS _diff (
                    guid TEXT PRIMARY KEY,
                    alterid TEXT DEFAULT ''
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS _delete (
                    guid TEXT PRIMARY KEY
                )
            ''')
            
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_company_config_name ON company_config(company_name)')
            await conn.commit()
        except Exception as e:
            logger.warning(f"Could not ensure company_config table: {e}")
    
    async def update_company_config(self, company_name: str, company_guid: str = "",
                                     company_alterid: int = 0, last_alter_id_master: int = 0,
                                     last_alter_id_transaction: int = 0, sync_type: str = "full",
                                     books_from: str = "", books_to: str = "", **kwargs) -> None:
        """Update or insert company config record"""
        conn = await self._get_connection()
        try:
            cursor = await conn.execute(
                "SELECT id, sync_count FROM company_config WHERE company_name = ?",
                (company_name,)
            )
            existing = await cursor.fetchone()
            
            now = datetime.now().isoformat()
            
            if existing:
                sync_count = (existing[1] or 0) + 1
                await conn.execute('''
                    UPDATE company_config SET
                        company_guid = COALESCE(NULLIF(?, ''), company_guid),
                        company_alterid = CASE WHEN ? > 0 THEN ? ELSE company_alterid END,
                        last_alter_id_master = ?,
                        last_alter_id_transaction = ?,
                        books_from = COALESCE(NULLIF(?, ''), books_from),
                        books_to = COALESCE(NULLIF(?, ''), books_to),
                        last_sync_at = ?,
                        last_sync_type = ?,
                        sync_count = ?,
                        updated_at = ?
                    WHERE company_name = ?
                ''', (company_guid, company_alterid, company_alterid, last_alter_id_master,
                      last_alter_id_transaction, books_from, books_to, now, sync_type, sync_count, now, company_name))
            else:
                await conn.execute('''
                    INSERT INTO company_config 
                    (company_name, company_guid, company_alterid, last_alter_id_master, 
                     last_alter_id_transaction, books_from, books_to, last_sync_at, last_sync_type, sync_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                ''', (company_name, company_guid, company_alterid, last_alter_id_master,
                      last_alter_id_transaction, books_from, books_to, now, sync_type, now, now))
            
            await conn.commit()
        except Exception as e:
            logger.error(f"Failed to update company config: {e}")
    
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
        conn = await self._get_connection()
        total_deleted = 0
        
        try:
            for table in ALL_TABLES:
                try:
                    cursor = await conn.execute(
                        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                        (table,)
                    )
                    row = await cursor.fetchone()
                    if not row or row[0] == 0:
                        continue
                    
                    cursor = await conn.execute(f"PRAGMA table_info({table})")
                    columns = await cursor.fetchall()
                    column_names = [col[1] for col in columns]
                    
                    if "_company" in column_names:
                        cursor = await conn.execute(
                            f"SELECT COUNT(*) FROM {table} WHERE _company = ?",
                            (company_name,)
                        )
                        count_row = await cursor.fetchone()
                        count = count_row[0] if count_row else 0
                        
                        await conn.execute(
                            f"DELETE FROM {table} WHERE _company = ?",
                            (company_name,)
                        )
                        total_deleted += count
                except Exception as e:
                    logger.warning(f"Error deleting from {table}: {e}")
            
            await conn.execute(
                "DELETE FROM company_config WHERE company_name = ?",
                (company_name,)
            )
            total_deleted += 1
            
            await conn.commit()
            logger.info(f"Deleted company '{company_name}': {total_deleted} total rows")
            return total_deleted
            
        except Exception as e:
            logger.error(f"Failed to delete company data: {e}")
            raise
    
    def _load_schema_from_file(self, incremental: bool = False) -> str:
        """Load schema from SQL file"""
        if incremental:
            schema_path = Path("database-structure-incremental.sql")
        else:
            schema_path = Path("database-structure.sql")
        
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""
    
    def _convert_sql_for_sqlite(self, sql: str) -> str:
        """Convert SQL types to SQLite compatible types"""
        import re
        sql = re.sub(r'create\s+table\s+(?!if)', 'CREATE TABLE IF NOT EXISTS ', sql, flags=re.IGNORECASE)
        sql = re.sub(r'create\s+index\s+(?!if)', 'CREATE INDEX IF NOT EXISTS ', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bnvarchar\s*\(\d+\)', 'TEXT', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bvarchar\s*\(\d+\)', 'TEXT', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\btinyint\b', 'INTEGER', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bdecimal\s*\(\d+,\s*\d+\)', 'REAL', sql, flags=re.IGNORECASE)
        sql = re.sub(r'(?<!\w)int(?!\w)', 'INTEGER', sql, flags=re.IGNORECASE)
        sql = re.sub(r'(?<=\s)date(?=\s*,|\s*\n|\s+not|\s+default|\s*\))', 'TEXT', sql, flags=re.IGNORECASE)
        return sql
    
    def _get_schema_sql(self) -> str:
        """Get default database schema SQL"""
        return '''
CREATE TABLE IF NOT EXISTS config (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mst_group (
    guid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    parent TEXT NOT NULL DEFAULT '',
    primary_group TEXT NOT NULL DEFAULT '',
    is_revenue INTEGER NOT NULL DEFAULT 0,
    is_deemedpositive INTEGER NOT NULL DEFAULT 0,
    is_subledger INTEGER NOT NULL DEFAULT 0,
    sort_position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mst_ledger (
    guid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    parent TEXT NOT NULL DEFAULT '',
    alias TEXT NOT NULL DEFAULT '',
    opening_balance REAL NOT NULL DEFAULT 0,
    description TEXT NOT NULL DEFAULT '',
    mailing_name TEXT NOT NULL DEFAULT '',
    mailing_address TEXT NOT NULL DEFAULT '',
    mailing_state TEXT NOT NULL DEFAULT '',
    mailing_country TEXT NOT NULL DEFAULT '',
    mailing_pincode TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    mobile TEXT NOT NULL DEFAULT '',
    contact TEXT NOT NULL DEFAULT '',
    pan TEXT NOT NULL DEFAULT '',
    gstin TEXT NOT NULL DEFAULT '',
    gst_registration_type TEXT NOT NULL DEFAULT '',
    is_bill_wise INTEGER NOT NULL DEFAULT 0,
    is_cost_centre INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mst_vouchertype (
    guid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    parent TEXT NOT NULL DEFAULT '',
    numbering_method TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS mst_uom (
    guid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    symbol TEXT NOT NULL DEFAULT '',
    is_simple_unit INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS mst_godown (
    guid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    parent TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mst_stock_category (
    guid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    parent TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mst_stock_group (
    guid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    parent TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mst_stock_item (
    guid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    parent TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    alias TEXT NOT NULL DEFAULT '',
    uom TEXT NOT NULL DEFAULT '',
    opening_quantity REAL NOT NULL DEFAULT 0,
    opening_rate REAL NOT NULL DEFAULT 0,
    opening_value REAL NOT NULL DEFAULT 0,
    gst_applicable TEXT NOT NULL DEFAULT '',
    hsn_code TEXT NOT NULL DEFAULT '',
    gst_rate REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mst_cost_category (
    guid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    allocate_revenue INTEGER NOT NULL DEFAULT 0,
    allocate_non_revenue INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mst_cost_centre (
    guid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    parent TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mst_attendance_type (
    guid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    parent TEXT NOT NULL DEFAULT '',
    attendance_type TEXT NOT NULL DEFAULT '',
    attendance_period TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mst_employee (
    guid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    parent TEXT NOT NULL DEFAULT '',
    id_number TEXT NOT NULL DEFAULT '',
    date_of_joining TEXT,
    date_of_release TEXT,
    designation TEXT NOT NULL DEFAULT '',
    gender TEXT NOT NULL DEFAULT '',
    date_of_birth TEXT,
    pan TEXT NOT NULL DEFAULT '',
    aadhar TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mst_payhead (
    guid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    parent TEXT NOT NULL DEFAULT '',
    pay_type TEXT NOT NULL DEFAULT '',
    income_type TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mst_gst_effective_rate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_guid TEXT NOT NULL DEFAULT '',
    applicable_from TEXT,
    hsn_code TEXT NOT NULL DEFAULT '',
    rate REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mst_opening_batch_allocation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_guid TEXT NOT NULL DEFAULT '',
    godown TEXT NOT NULL DEFAULT '',
    batch TEXT NOT NULL DEFAULT '',
    quantity REAL NOT NULL DEFAULT 0,
    rate REAL NOT NULL DEFAULT 0,
    amount REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mst_opening_bill_allocation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_guid TEXT NOT NULL DEFAULT '',
    bill_name TEXT NOT NULL DEFAULT '',
    bill_type TEXT NOT NULL DEFAULT '',
    bill_date TEXT,
    amount REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mst_stockitem_standard_cost (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_guid TEXT NOT NULL DEFAULT '',
    date TEXT,
    rate REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mst_stockitem_standard_price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_guid TEXT NOT NULL DEFAULT '',
    date TEXT,
    rate REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trn_voucher (
    guid TEXT PRIMARY KEY,
    date TEXT NOT NULL DEFAULT '',
    voucher_type TEXT NOT NULL DEFAULT '',
    voucher_number TEXT NOT NULL DEFAULT '',
    reference_number TEXT NOT NULL DEFAULT '',
    reference_date TEXT,
    narration TEXT NOT NULL DEFAULT '',
    party_name TEXT NOT NULL DEFAULT '',
    place_of_supply TEXT NOT NULL DEFAULT '',
    is_invoice INTEGER NOT NULL DEFAULT 0,
    is_accounting_voucher INTEGER NOT NULL DEFAULT 0,
    is_inventory_voucher INTEGER NOT NULL DEFAULT 0,
    is_order_voucher INTEGER NOT NULL DEFAULT 0,
    is_cancelled INTEGER NOT NULL DEFAULT 0,
    is_optional INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trn_accounting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL,
    ledger TEXT NOT NULL DEFAULT '',
    amount REAL NOT NULL DEFAULT 0,
    amount_forex REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT '',
    is_party_ledger INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trn_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL,
    stock_item TEXT NOT NULL DEFAULT '',
    quantity REAL NOT NULL DEFAULT 0,
    rate REAL NOT NULL DEFAULT 0,
    amount REAL NOT NULL DEFAULT 0,
    godown TEXT NOT NULL DEFAULT '',
    tracking_number TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS trn_cost_centre (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL,
    ledger TEXT NOT NULL DEFAULT '',
    cost_centre TEXT NOT NULL DEFAULT '',
    amount REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trn_cost_category_centre (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL,
    ledger TEXT NOT NULL DEFAULT '',
    cost_category TEXT NOT NULL DEFAULT '',
    cost_centre TEXT NOT NULL DEFAULT '',
    amount REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trn_cost_inventory_category_centre (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL,
    stock_item TEXT NOT NULL DEFAULT '',
    cost_category TEXT NOT NULL DEFAULT '',
    cost_centre TEXT NOT NULL DEFAULT '',
    amount REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trn_bill (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL,
    ledger TEXT NOT NULL DEFAULT '',
    bill_type TEXT NOT NULL DEFAULT '',
    bill_name TEXT NOT NULL DEFAULT '',
    amount REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trn_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL,
    ledger TEXT NOT NULL DEFAULT '',
    transaction_type TEXT NOT NULL DEFAULT '',
    instrument_number TEXT NOT NULL DEFAULT '',
    instrument_date TEXT,
    bank_name TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS trn_batch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL,
    stock_item TEXT NOT NULL DEFAULT '',
    batch TEXT NOT NULL DEFAULT '',
    quantity REAL NOT NULL DEFAULT 0,
    rate REAL NOT NULL DEFAULT 0,
    amount REAL NOT NULL DEFAULT 0,
    godown TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS trn_inventory_accounting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL,
    stock_item TEXT NOT NULL DEFAULT '',
    ledger TEXT NOT NULL DEFAULT '',
    amount REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trn_employee (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL,
    employee TEXT NOT NULL DEFAULT '',
    amount REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trn_payhead (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL,
    employee TEXT NOT NULL DEFAULT '',
    payhead TEXT NOT NULL DEFAULT '',
    amount REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trn_attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL,
    employee TEXT NOT NULL DEFAULT '',
    attendance_type TEXT NOT NULL DEFAULT '',
    value REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trn_closingstock_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL,
    stock_item TEXT NOT NULL DEFAULT '',
    ledger TEXT NOT NULL DEFAULT '',
    amount REAL NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_trn_voucher_date ON trn_voucher(date);
CREATE INDEX IF NOT EXISTS idx_trn_voucher_type ON trn_voucher(voucher_type);
CREATE INDEX IF NOT EXISTS idx_trn_accounting_guid ON trn_accounting(guid);
CREATE INDEX IF NOT EXISTS idx_trn_inventory_guid ON trn_inventory(guid);
CREATE INDEX IF NOT EXISTS idx_mst_ledger_parent ON mst_ledger(parent);
CREATE INDEX IF NOT EXISTS idx_mst_stock_item_parent ON mst_stock_item(parent);
'''
    
    def get_placeholder(self) -> str:
        """SQLite uses ? as placeholder"""
        return '?'
    
    def get_table_quote(self) -> str:
        """SQLite uses double quotes"""
        return '"'
