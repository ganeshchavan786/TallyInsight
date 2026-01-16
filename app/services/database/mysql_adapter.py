"""
MySQL Database Adapter
======================
MySQL implementation of the database service using aiomysql.

Prerequisites:
- pip install aiomysql

Configuration (config.yaml):
    database:
      type: mysql
      host: localhost
      port: 3306
      database: tallydb
      username: root
      password: password
"""

import aiomysql
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseDatabaseService
from ...config import config
from ...utils.logger import logger
from ...utils.decorators import timed
from ...utils.constants import ALL_TABLES, MASTER_TABLES, TRANSACTION_TABLES


class MySQLDatabaseService(BaseDatabaseService):
    """MySQL implementation of database service"""
    
    def __init__(self):
        self._pool: Optional[aiomysql.Pool] = None
        
        db_config = config.database
        self.host = getattr(db_config, 'host', 'localhost')
        self.port = getattr(db_config, 'port', 3306)
        self.database = getattr(db_config, 'database', 'tallydb')
        self.username = getattr(db_config, 'username', 'root')
        self.password = getattr(db_config, 'password', '')
    
    async def connect(self) -> None:
        """Open database connection pool"""
        if self._pool is None:
            try:
                self._pool = await aiomysql.create_pool(
                    host=self.host,
                    port=self.port,
                    db=self.database,
                    user=self.username,
                    password=self.password,
                    minsize=2,
                    maxsize=10,
                    charset='utf8mb4',
                    autocommit=True
                )
                logger.info(f"Connected to MySQL: {self.host}/{self.database}")
            except Exception as e:
                logger.error(f"MySQL connection failed: {e}")
                raise
    
    async def disconnect(self) -> None:
        """Close database connection pool"""
        if self._pool:
            try:
                self._pool.close()
                await self._pool.wait_closed()
            except:
                pass
            self._pool = None
            logger.info("MySQL connection closed")
    
    async def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._pool is not None
    
    async def execute(self, query: str, params: Tuple = ()) -> int:
        """Execute a query and return affected rows"""
        if not self._pool:
            await self.connect()
        
        # Convert ? to %s for MySQL
        query = query.replace('?', '%s')
        
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params)
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query[:200]}...")
            raise
    
    async def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows from query"""
        if not self._pool:
            await self.connect()
        
        query = query.replace('?', '%s')
        
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, params)
                    rows = await cursor.fetchall()
                    return list(rows)
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            raise
    
    async def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch single row from query"""
        if not self._pool:
            await self.connect()
        
        query = query.replace('?', '%s')
        
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, params)
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Fetch one failed: {e}")
            raise
    
    async def fetch_scalar(self, query: str, params: Tuple = ()) -> Any:
        """Fetch single value from query"""
        if not self._pool:
            await self.connect()
        
        query = query.replace('?', '%s')
        
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params)
                    row = await cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logger.error(f"Fetch scalar failed: {e}")
            raise
    
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
        
        column_names = ', '.join([f'`{col}`' for col in columns])
        placeholders = ', '.join(['%s' for _ in columns])
        
        # Use INSERT ... ON DUPLICATE KEY UPDATE for upsert
        has_guid = 'guid' in columns
        if has_guid:
            update_clause = ', '.join([f'`{col}` = VALUES(`{col}`)' for col in columns if col != 'guid'])
            query = f"INSERT INTO `{table_name}` ({column_names}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"
        else:
            query = f"INSERT INTO `{table_name}` ({column_names}) VALUES ({placeholders})"
        
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    total_inserted = 0
                    batch_size = config.sync.batch_size
                    
                    for i in range(0, len(rows), batch_size):
                        batch = rows[i:i + batch_size]
                        records = [tuple(row.get(col) for col in columns) for row in batch]
                        await cursor.executemany(query, records)
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
                await self.execute(f"DELETE FROM `{table_name}` WHERE `_company` = ?", (company_name,))
            else:
                await self.execute(f"DELETE FROM `{table_name}`")
        else:
            await self.execute(f"DELETE FROM `{table_name}`")
    
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
                    f"SELECT COUNT(*) FROM `{table_name}` WHERE `_company` = ?",
                    (company_name,)
                )
            else:
                result = await self.fetch_scalar(f"SELECT COUNT(*) FROM `{table_name}`")
            
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
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
            (self.database, table_name)
        )
        return result > 0
    
    async def get_database_size(self) -> int:
        """Get database size in bytes"""
        try:
            result = await self.fetch_scalar(
                """SELECT SUM(data_length + index_length) 
                   FROM information_schema.tables WHERE table_schema = ?""",
                (self.database,)
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
               WHERE table_schema = ? AND table_name = ? AND column_name = ?""",
            (self.database, table_name, column_name)
        )
        return result > 0
    
    async def _ensure_columns_exist(self, table_name: str, columns: List[str]) -> None:
        """Auto-add missing columns to table"""
        if not self._pool:
            await self.connect()
        
        for col in columns:
            if not await self._has_column(table_name, col):
                try:
                    await self.execute(
                        f"ALTER TABLE `{table_name}` ADD COLUMN `{col}` TEXT DEFAULT ''"
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
                async with conn.cursor() as cursor:
                    statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
                    for stmt in statements:
                        if stmt.strip():
                            try:
                                await cursor.execute(stmt)
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
                    await self.execute(
                        f"ALTER TABLE `{table}` ADD COLUMN `_company` VARCHAR(256) DEFAULT ''"
                    )
                except:
                    pass
    
    async def ensure_audit_tables(self) -> None:
        """Create audit trail tables"""
        audit_sql = """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sync_session_id VARCHAR(100),
            sync_type VARCHAR(50),
            table_name VARCHAR(100) NOT NULL,
            record_guid VARCHAR(100),
            record_name VARCHAR(256),
            action VARCHAR(50) NOT NULL,
            old_data TEXT,
            new_data TEXT,
            changed_fields TEXT,
            company VARCHAR(256) NOT NULL,
            tally_alter_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(50) DEFAULT 'SUCCESS',
            message TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        try:
            await self.execute(audit_sql)
        except Exception as e:
            logger.warning(f"Could not create audit_log: {e}")
    
    async def ensure_company_config_table(self) -> None:
        """Ensure company_config table exists"""
        sql = """
        CREATE TABLE IF NOT EXISTS company_config (
            id INT AUTO_INCREMENT PRIMARY KEY,
            company_name VARCHAR(256) NOT NULL UNIQUE,
            company_guid VARCHAR(100) DEFAULT '',
            company_alterid INT DEFAULT 0,
            last_alter_id_master INT DEFAULT 0,
            last_alter_id_transaction INT DEFAULT 0,
            books_from VARCHAR(20) DEFAULT '',
            books_to VARCHAR(20) DEFAULT '',
            last_sync_at DATETIME,
            last_sync_type VARCHAR(50),
            sync_count INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        try:
            await self.execute(sql)
            await self.execute("""
                CREATE TABLE IF NOT EXISTS _diff (
                    guid VARCHAR(100) PRIMARY KEY, 
                    alterid VARCHAR(50) DEFAULT ''
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            await self.execute("""
                CREATE TABLE IF NOT EXISTS _delete (
                    guid VARCHAR(100) PRIMARY KEY
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
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
                    async with conn.cursor() as cur:
                        # Check if column exists
                        await cur.execute(f"""
                            SELECT COUNT(*) FROM information_schema.columns 
                            WHERE table_schema = DATABASE() AND table_name = '{table}' AND column_name = 'alterid'
                        """)
                        result = await cur.fetchone()
                        if result[0] == 0:
                            await cur.execute(f"ALTER TABLE `{table}` ADD COLUMN alterid INT DEFAULT 0")
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
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if existing:
            sync_count = (existing.get('sync_count') or 0) + 1
            await self.execute('''
                UPDATE company_config SET
                    company_guid = IF(%s != '', %s, company_guid),
                    company_alterid = IF(%s > 0, %s, company_alterid),
                    last_alter_id_master = %s,
                    last_alter_id_transaction = %s,
                    books_from = IF(%s != '', %s, books_from),
                    books_to = IF(%s != '', %s, books_to),
                    last_sync_at = %s,
                    last_sync_type = %s,
                    sync_count = %s
                WHERE company_name = %s
            '''.replace('?', '%s'), (company_guid, company_guid, company_alterid, company_alterid,
                  last_alter_id_master, last_alter_id_transaction,
                  books_from, books_from, books_to, books_to,
                  now, sync_type, sync_count, company_name))
        else:
            await self.execute('''
                INSERT INTO company_config 
                (company_name, company_guid, company_alterid, last_alter_id_master, 
                 last_alter_id_transaction, books_from, books_to, last_sync_at, 
                 last_sync_type, sync_count, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
            '''.replace('?', '%s'), (company_name, company_guid, company_alterid, last_alter_id_master,
                  last_alter_id_transaction, books_from, books_to, now, sync_type, now))
    
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
                        f"SELECT COUNT(*) FROM `{table}` WHERE `_company` = ?",
                        (company_name,)
                    )
                    await self.execute(
                        f"DELETE FROM `{table}` WHERE `_company` = ?",
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
        """Get MySQL schema SQL"""
        return '''
CREATE TABLE IF NOT EXISTS config (
    name VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mst_group (
    guid VARCHAR(100) PRIMARY KEY,
    name VARCHAR(256) NOT NULL DEFAULT '',
    parent VARCHAR(256) NOT NULL DEFAULT '',
    primary_group VARCHAR(256) NOT NULL DEFAULT '',
    is_revenue INT NOT NULL DEFAULT 0,
    is_deemedpositive INT NOT NULL DEFAULT 0,
    is_subledger INT NOT NULL DEFAULT 0,
    sort_position INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mst_ledger (
    guid VARCHAR(100) PRIMARY KEY,
    name VARCHAR(256) NOT NULL DEFAULT '',
    parent VARCHAR(256) NOT NULL DEFAULT '',
    alias VARCHAR(256) NOT NULL DEFAULT '',
    opening_balance DECIMAL(18,2) NOT NULL DEFAULT 0,
    description TEXT NOT NULL,
    mailing_name VARCHAR(256) NOT NULL DEFAULT '',
    mailing_address TEXT NOT NULL,
    mailing_state VARCHAR(100) NOT NULL DEFAULT '',
    mailing_country VARCHAR(100) NOT NULL DEFAULT '',
    mailing_pincode VARCHAR(20) NOT NULL DEFAULT '',
    email VARCHAR(256) NOT NULL DEFAULT '',
    phone VARCHAR(50) NOT NULL DEFAULT '',
    mobile VARCHAR(50) NOT NULL DEFAULT '',
    contact VARCHAR(256) NOT NULL DEFAULT '',
    pan VARCHAR(20) NOT NULL DEFAULT '',
    gstin VARCHAR(20) NOT NULL DEFAULT '',
    gst_registration_type VARCHAR(50) NOT NULL DEFAULT '',
    is_bill_wise INT NOT NULL DEFAULT 0,
    is_cost_centre INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mst_vouchertype (
    guid VARCHAR(100) PRIMARY KEY,
    name VARCHAR(256) NOT NULL DEFAULT '',
    parent VARCHAR(256) NOT NULL DEFAULT '',
    numbering_method VARCHAR(50) NOT NULL DEFAULT '',
    is_active INT NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mst_stock_item (
    guid VARCHAR(100) PRIMARY KEY,
    name VARCHAR(256) NOT NULL DEFAULT '',
    parent VARCHAR(256) NOT NULL DEFAULT '',
    category VARCHAR(256) NOT NULL DEFAULT '',
    alias VARCHAR(256) NOT NULL DEFAULT '',
    uom VARCHAR(50) NOT NULL DEFAULT '',
    opening_quantity DECIMAL(18,4) NOT NULL DEFAULT 0,
    opening_rate DECIMAL(18,4) NOT NULL DEFAULT 0,
    opening_value DECIMAL(18,2) NOT NULL DEFAULT 0,
    gst_applicable VARCHAR(50) NOT NULL DEFAULT '',
    hsn_code VARCHAR(20) NOT NULL DEFAULT '',
    gst_rate DECIMAL(5,2) NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS trn_voucher (
    guid VARCHAR(100) PRIMARY KEY,
    date VARCHAR(20) NOT NULL DEFAULT '',
    voucher_type VARCHAR(100) NOT NULL DEFAULT '',
    voucher_number VARCHAR(100) NOT NULL DEFAULT '',
    reference_number VARCHAR(100) NOT NULL DEFAULT '',
    reference_date VARCHAR(20),
    narration TEXT NOT NULL,
    party_name VARCHAR(256) NOT NULL DEFAULT '',
    place_of_supply VARCHAR(100) NOT NULL DEFAULT '',
    is_invoice INT NOT NULL DEFAULT 0,
    is_accounting_voucher INT NOT NULL DEFAULT 0,
    is_inventory_voucher INT NOT NULL DEFAULT 0,
    is_order_voucher INT NOT NULL DEFAULT 0,
    is_cancelled INT NOT NULL DEFAULT 0,
    is_optional INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS trn_accounting (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guid VARCHAR(100) NOT NULL,
    ledger VARCHAR(256) NOT NULL DEFAULT '',
    amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    amount_forex DECIMAL(18,2) NOT NULL DEFAULT 0,
    currency VARCHAR(10) NOT NULL DEFAULT '',
    is_party_ledger INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS trn_inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guid VARCHAR(100) NOT NULL,
    stock_item VARCHAR(256) NOT NULL DEFAULT '',
    quantity DECIMAL(18,4) NOT NULL DEFAULT 0,
    rate DECIMAL(18,4) NOT NULL DEFAULT 0,
    amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    godown VARCHAR(256) NOT NULL DEFAULT '',
    tracking_number VARCHAR(100) NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''
    
    def get_placeholder(self) -> str:
        """MySQL uses %s as placeholder"""
        return '%s'
    
    def get_table_quote(self) -> str:
        """MySQL uses backticks"""
        return '`'
