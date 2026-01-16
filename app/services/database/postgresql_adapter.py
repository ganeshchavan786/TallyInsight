"""
PostgreSQL Database Adapter
===========================
PostgreSQL implementation of the database service using asyncpg.

Prerequisites:
- pip install asyncpg

Configuration (config.yaml):
    database:
      type: postgresql
      host: localhost
      port: 5432
      database: tallydb
      username: postgres
      password: password
"""

import asyncpg
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseDatabaseService
from ...config import config
from ...utils.logger import logger
from ...utils.decorators import timed
from ...utils.constants import ALL_TABLES, MASTER_TABLES, TRANSACTION_TABLES


class PostgreSQLDatabaseService(BaseDatabaseService):
    """PostgreSQL implementation of database service"""
    
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        
        db_config = config.database
        self.host = getattr(db_config, 'host', 'localhost')
        self.port = getattr(db_config, 'port', 5432)
        self.database = getattr(db_config, 'database', 'tallydb')
        self.username = getattr(db_config, 'username', 'postgres')
        self.password = getattr(db_config, 'password', '')
        self.url = getattr(db_config, 'url', None)
    
    async def connect(self) -> None:
        """Open database connection pool"""
        if self._pool is None:
            try:
                if self.url:
                    self._pool = await asyncpg.create_pool(self.url, min_size=2, max_size=10)
                else:
                    self._pool = await asyncpg.create_pool(
                        host=self.host,
                        port=self.port,
                        database=self.database,
                        user=self.username,
                        password=self.password,
                        min_size=2,
                        max_size=10
                    )
                logger.info(f"Connected to PostgreSQL: {self.host}/{self.database}")
            except Exception as e:
                logger.error(f"PostgreSQL connection failed: {e}")
                raise
    
    async def disconnect(self) -> None:
        """Close database connection pool"""
        if self._pool:
            try:
                await self._pool.close()
            except:
                pass
            self._pool = None
            logger.info("PostgreSQL connection closed")
    
    async def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._pool is not None
    
    async def execute(self, query: str, params: Tuple = ()) -> int:
        """Execute a query and return affected rows"""
        if not self._pool:
            await self.connect()
        
        # Convert ? placeholders to $1, $2, etc.
        query = self._convert_placeholders(query)
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(query, *params)
                # Parse "DELETE 5" or "UPDATE 3" to get count
                if result:
                    parts = result.split()
                    if len(parts) >= 2 and parts[-1].isdigit():
                        return int(parts[-1])
                return 0
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query[:200]}...")
            raise
    
    async def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows from query"""
        if not self._pool:
            await self.connect()
        
        query = self._convert_placeholders(query)
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            raise
    
    async def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch single row from query"""
        if not self._pool:
            await self.connect()
        
        query = self._convert_placeholders(query)
        
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(query, *params)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Fetch one failed: {e}")
            raise
    
    async def fetch_scalar(self, query: str, params: Tuple = ()) -> Any:
        """Fetch single value from query"""
        if not self._pool:
            await self.connect()
        
        query = self._convert_placeholders(query)
        
        try:
            async with self._pool.acquire() as conn:
                return await conn.fetchval(query, *params)
        except Exception as e:
            logger.error(f"Fetch scalar failed: {e}")
            raise
    
    def _convert_placeholders(self, query: str) -> str:
        """Convert ? placeholders to $1, $2, etc."""
        result = []
        param_num = 0
        i = 0
        while i < len(query):
            if query[i] == '?':
                param_num += 1
                result.append(f'${param_num}')
            else:
                result.append(query[i])
            i += 1
        return ''.join(result)
    
    @timed
    async def bulk_insert(self, table_name: str, rows: List[Dict[str, Any]], 
                          company_name: str = None) -> int:
        """Bulk insert rows into table"""
        if not rows:
            return 0
        
        if not self._pool:
            await self.connect()
        
        if company_name:
            for row in rows:
                row['_company'] = company_name
        
        columns = list(rows[0].keys())
        await self._ensure_columns_exist(table_name, columns)
        
        # Build INSERT with ON CONFLICT for upsert
        column_names = ', '.join([f'"{col}"' for col in columns])
        placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
        
        # Check if table has guid as primary key
        has_guid = 'guid' in columns
        if has_guid:
            query = f'''
                INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})
                ON CONFLICT (guid) DO UPDATE SET {', '.join([f'"{col}" = EXCLUDED."{col}"' for col in columns if col != 'guid'])}
            '''
        else:
            query = f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})'
        
        try:
            async with self._pool.acquire() as conn:
                total_inserted = 0
                batch_size = config.sync.batch_size
                
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    records = [tuple(row.get(col) for col in columns) for row in batch]
                    await conn.executemany(query, records)
                    total_inserted += len(batch)
                
                logger.debug(f"Inserted {total_inserted} rows into {table_name}")
                return total_inserted
        except Exception as e:
            logger.error(f"Bulk insert failed for {table_name}: {e}")
            raise
    
    async def truncate_table(self, table_name: str, company_name: str = None) -> None:
        """Delete all rows from a table"""
        if company_name:
            has_company_col = await self._has_column(table_name, '_company')
            if has_company_col:
                await self.execute(f'DELETE FROM "{table_name}" WHERE "_company" = ?', (company_name,))
            else:
                await self.execute(f'DELETE FROM "{table_name}"')
        else:
            await self.execute(f'DELETE FROM "{table_name}"')
    
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
                    f'SELECT COUNT(*) FROM "{table_name}" WHERE "_company" = ?',
                    (company_name,)
                )
            else:
                result = await self.fetch_scalar(f'SELECT COUNT(*) FROM "{table_name}"')
            
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
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            (table_name,)
        )
        return result > 0
    
    async def get_database_size(self) -> int:
        """Get database size in bytes"""
        try:
            result = await self.fetch_scalar(
                f"SELECT pg_database_size('{self.database}')"
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
            """SELECT COUNT(*) FROM information_schema.columns 
               WHERE table_name = ? AND column_name = ?""",
            (table_name, column_name)
        )
        return result > 0
    
    async def _ensure_columns_exist(self, table_name: str, columns: List[str]) -> None:
        """Auto-add missing columns to table"""
        if not self._pool:
            await self.connect()
        
        for col in columns:
            if not await self._has_column(table_name, col):
                try:
                    async with self._pool.acquire() as conn:
                        await conn.execute(
                            f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" TEXT DEFAULT \'\''
                        )
                    logger.debug(f"Added column '{col}' to table '{table_name}'")
                except Exception as e:
                    logger.warning(f"Could not add column {col}: {e}")
    
    @timed
    async def create_tables(self, incremental: bool = None) -> None:
        """Create all database tables"""
        if not self._pool:
            await self.connect()
        
        schema_sql = self._get_schema_sql()
        
        try:
            async with self._pool.acquire() as conn:
                statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
                for stmt in statements:
                    if stmt.strip():
                        try:
                            await conn.execute(stmt)
                        except Exception as e:
                            logger.debug(f"Statement skipped: {e}")
            
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
                    async with self._pool.acquire() as conn:
                        await conn.execute(
                            f'ALTER TABLE "{table}" ADD COLUMN "_company" TEXT DEFAULT \'\''
                        )
                except:
                    pass
    
    async def ensure_audit_tables(self) -> None:
        """Create audit trail tables"""
        audit_sql = """
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
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
        """
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(audit_sql)
        except Exception as e:
            logger.warning(f"Could not create audit_log: {e}")
    
    async def ensure_company_config_table(self) -> None:
        """Ensure company_config table exists"""
        sql = """
        CREATE TABLE IF NOT EXISTS company_config (
            id SERIAL PRIMARY KEY,
            company_name TEXT NOT NULL UNIQUE,
            company_guid TEXT DEFAULT '',
            company_alterid INTEGER DEFAULT 0,
            last_alter_id_master INTEGER DEFAULT 0,
            last_alter_id_transaction INTEGER DEFAULT 0,
            books_from TEXT DEFAULT '',
            books_to TEXT DEFAULT '',
            last_sync_at TIMESTAMP,
            last_sync_type TEXT,
            sync_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(sql)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS _diff (
                        guid TEXT PRIMARY KEY, 
                        alterid TEXT DEFAULT ''
                    )
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS _delete (
                        guid TEXT PRIMARY KEY
                    )
                """)
        except Exception as e:
            logger.warning(f"Could not ensure company_config table: {e}")
    
    async def ensure_alterid_column_exists(self) -> None:
        """Add alterid column to all tables for incremental sync support"""
        if not self._pool:
            await self.connect()
        
        added_count = 0
        for table in ALL_TABLES:
            try:
                async with self._pool.acquire() as conn:
                    # Check if column exists
                    result = await conn.fetchval(f"""
                        SELECT COUNT(*) FROM information_schema.columns 
                        WHERE table_name = '{table}' AND column_name = 'alterid'
                    """)
                    if result == 0:
                        await conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS alterid INTEGER DEFAULT 0")
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
        if not self._pool:
            await self.connect()
        
        existing = await self.fetch_one(
            "SELECT id, sync_count FROM company_config WHERE company_name = ?",
            (company_name,)
        )
        
        now = datetime.now().isoformat()
        
        if existing:
            sync_count = (existing.get('sync_count') or 0) + 1
            await self.execute('''
                UPDATE company_config SET
                    company_guid = CASE WHEN $1 != '' THEN $1 ELSE company_guid END,
                    company_alterid = CASE WHEN $2 > 0 THEN $2 ELSE company_alterid END,
                    last_alter_id_master = $3,
                    last_alter_id_transaction = $4,
                    books_from = CASE WHEN $5 != '' THEN $5 ELSE books_from END,
                    books_to = CASE WHEN $6 != '' THEN $6 ELSE books_to END,
                    last_sync_at = $7,
                    last_sync_type = $8,
                    sync_count = $9,
                    updated_at = $10
                WHERE company_name = $11
            '''.replace('?', ''), (company_guid, company_alterid, last_alter_id_master,
                  last_alter_id_transaction, books_from, books_to,
                  now, sync_type, sync_count, now, company_name))
        else:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO company_config 
                    (company_name, company_guid, company_alterid, last_alter_id_master, 
                     last_alter_id_transaction, books_from, books_to, last_sync_at, 
                     last_sync_type, sync_count, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 1, $10, $11)
                ''', company_name, company_guid, company_alterid, last_alter_id_master,
                      last_alter_id_transaction, books_from, books_to, now, sync_type, now, now)
    
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
        if not self._pool:
            await self.connect()
        
        total_deleted = 0
        
        for table in ALL_TABLES:
            try:
                if not await self.table_exists(table):
                    continue
                
                if await self._has_column(table, '_company'):
                    count = await self.fetch_scalar(
                        f'SELECT COUNT(*) FROM "{table}" WHERE "_company" = ?',
                        (company_name,)
                    )
                    await self.execute(
                        f'DELETE FROM "{table}" WHERE "_company" = ?',
                        (company_name,)
                    )
                    total_deleted += count or 0
            except Exception as e:
                logger.warning(f"Error deleting from {table}: {e}")
        
        await self.execute(
            "DELETE FROM company_config WHERE company_name = ?",
            (company_name,)
        )
        total_deleted += 1
        
        logger.info(f"Deleted company '{company_name}': {total_deleted} total rows")
        return total_deleted
    
    def _get_schema_sql(self) -> str:
        """Get PostgreSQL schema SQL"""
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
    opening_balance DECIMAL(18,2) NOT NULL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS mst_stock_item (
    guid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    parent TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    alias TEXT NOT NULL DEFAULT '',
    uom TEXT NOT NULL DEFAULT '',
    opening_quantity DECIMAL(18,4) NOT NULL DEFAULT 0,
    opening_rate DECIMAL(18,4) NOT NULL DEFAULT 0,
    opening_value DECIMAL(18,2) NOT NULL DEFAULT 0,
    gst_applicable TEXT NOT NULL DEFAULT '',
    hsn_code TEXT NOT NULL DEFAULT '',
    gst_rate DECIMAL(5,2) NOT NULL DEFAULT 0
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
    id SERIAL PRIMARY KEY,
    guid TEXT NOT NULL,
    ledger TEXT NOT NULL DEFAULT '',
    amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    amount_forex DECIMAL(18,2) NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT '',
    is_party_ledger INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trn_inventory (
    id SERIAL PRIMARY KEY,
    guid TEXT NOT NULL,
    stock_item TEXT NOT NULL DEFAULT '',
    quantity DECIMAL(18,4) NOT NULL DEFAULT 0,
    rate DECIMAL(18,4) NOT NULL DEFAULT 0,
    amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    godown TEXT NOT NULL DEFAULT '',
    tracking_number TEXT NOT NULL DEFAULT ''
)
'''
    
    def get_placeholder(self) -> str:
        """PostgreSQL uses $1, $2 placeholders"""
        return '$'
    
    def get_table_quote(self) -> str:
        """PostgreSQL uses double quotes"""
        return '"'
