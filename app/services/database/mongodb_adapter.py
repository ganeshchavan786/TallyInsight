"""
MongoDB Database Adapter
========================
MongoDB implementation of the database service using motor (async MongoDB driver).

Prerequisites:
- pip install motor

Configuration (config.yaml):
    database:
      type: mongodb
      host: localhost
      port: 27017
      database: tallydb
      username: admin       # optional
      password: password    # optional
      
    # Or use connection URL:
    database:
      type: mongodb
      url: mongodb://localhost:27017/tallydb
"""

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId

from .base import BaseDatabaseService
from ...config import config
from ...utils.logger import logger
from ...utils.decorators import timed
from ...utils.constants import ALL_TABLES, MASTER_TABLES, TRANSACTION_TABLES


class MongoDBDatabaseService(BaseDatabaseService):
    """MongoDB implementation of database service"""
    
    def __init__(self):
        self._client: Optional[AsyncIOMotorClient] = None
        self._db = None
        
        db_config = config.database
        self.host = getattr(db_config, 'host', 'localhost')
        self.port = getattr(db_config, 'port', 27017)
        self.database = getattr(db_config, 'database', 'tallydb')
        self.username = getattr(db_config, 'username', None)
        self.password = getattr(db_config, 'password', None)
        self.url = getattr(db_config, 'url', None)
    
    def _get_connection_url(self) -> str:
        """Build MongoDB connection URL"""
        if self.url:
            return self.url
        
        if self.username and self.password:
            return f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        else:
            return f"mongodb://{self.host}:{self.port}/{self.database}"
    
    async def connect(self) -> None:
        """Open database connection"""
        if self._client is None:
            try:
                url = self._get_connection_url()
                self._client = AsyncIOMotorClient(url)
                self._db = self._client[self.database]
                
                # Test connection
                await self._client.admin.command('ping')
                logger.info(f"Connected to MongoDB: {self.host}/{self.database}")
            except Exception as e:
                logger.error(f"MongoDB connection failed: {e}")
                raise
    
    async def disconnect(self) -> None:
        """Close database connection"""
        if self._client:
            try:
                self._client.close()
            except:
                pass
            self._client = None
            self._db = None
            logger.info("MongoDB connection closed")
    
    async def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._client is not None
    
    async def execute(self, query: str, params: Tuple = ()) -> int:
        """Execute a query - MongoDB doesn't use SQL queries"""
        # This method is for SQL compatibility
        # For MongoDB, use collection methods directly
        logger.warning("execute() called on MongoDB - use collection methods instead")
        return 0
    
    async def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all documents - for SQL compatibility"""
        # Parse simple SELECT queries for compatibility
        # Format: SELECT * FROM collection_name WHERE field = value
        if not self._db:
            await self.connect()
        
        # Simple parser for basic queries
        query_lower = query.lower()
        if 'from' in query_lower:
            parts = query_lower.split('from')
            if len(parts) > 1:
                table_part = parts[1].strip().split()[0]
                collection = self._db[table_part]
                
                filter_dict = {}
                if 'where' in query_lower:
                    # Very basic WHERE parsing
                    where_part = query.split('WHERE')[1] if 'WHERE' in query else query.split('where')[1]
                    if '=' in where_part:
                        field, value = where_part.split('=')
                        field = field.strip().replace('?', '').replace('"', '').replace("'", '')
                        if params:
                            filter_dict[field] = params[0]
                
                cursor = collection.find(filter_dict)
                docs = await cursor.to_list(length=None)
                return [self._convert_doc(doc) for doc in docs]
        
        return []
    
    async def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch single document"""
        results = await self.fetch_all(query, params)
        return results[0] if results else None
    
    async def fetch_scalar(self, query: str, params: Tuple = ()) -> Any:
        """Fetch single value"""
        result = await self.fetch_one(query, params)
        if result:
            return list(result.values())[0]
        return None
    
    def _convert_doc(self, doc: Dict) -> Dict:
        """Convert MongoDB document to dict (handle ObjectId)"""
        if doc is None:
            return None
        result = {}
        for key, value in doc.items():
            if key == '_id':
                result['_id'] = str(value)
            else:
                result[key] = value
        return result
    
    @timed
    async def bulk_insert(self, table_name: str, rows: List[Dict[str, Any]], 
                          company_name: str = None) -> int:
        """Bulk insert documents into collection"""
        if not rows:
            return 0
        
        if not self._db:
            await self.connect()
        
        if company_name:
            for row in rows:
                row['_company'] = company_name
        
        collection = self._db[table_name]
        
        try:
            # Use upsert for documents with guid
            total_inserted = 0
            batch_size = config.sync.batch_size
            
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                
                # Check if documents have guid for upsert
                if batch and 'guid' in batch[0]:
                    from pymongo import UpdateOne
                    operations = [
                        UpdateOne(
                            {'guid': doc['guid']},
                            {'$set': doc},
                            upsert=True
                        )
                        for doc in batch
                    ]
                    result = await collection.bulk_write(operations)
                    total_inserted += result.upserted_count + result.modified_count
                else:
                    result = await collection.insert_many(batch)
                    total_inserted += len(result.inserted_ids)
            
            logger.debug(f"Inserted {total_inserted} documents into {table_name}")
            return total_inserted
        except Exception as e:
            logger.error(f"Bulk insert failed for {table_name}: {e}")
            raise
    
    async def truncate_table(self, table_name: str, company_name: str = None) -> None:
        """Delete all documents from a collection"""
        if not self._db:
            await self.connect()
        
        collection = self._db[table_name]
        
        if company_name:
            await collection.delete_many({'_company': company_name})
        else:
            await collection.delete_many({})
    
    async def truncate_all_tables(self, company_name: str = None) -> None:
        """Truncate all collections"""
        for table in ALL_TABLES:
            try:
                await self.truncate_table(table, company_name)
            except Exception as e:
                logger.warning(f"Could not truncate {table}: {e}")
    
    async def get_table_count(self, table_name: str, company_name: str = None) -> int:
        """Get document count for a collection"""
        if not self._db:
            await self.connect()
        
        try:
            collection = self._db[table_name]
            
            if company_name:
                return await collection.count_documents({'_company': company_name})
            else:
                return await collection.count_documents({})
        except:
            return 0
    
    async def get_all_table_counts(self, company_name: str = None) -> Dict[str, int]:
        """Get document counts for all collections"""
        counts = {}
        for table in ALL_TABLES:
            counts[table] = await self.get_table_count(table, company_name)
        return counts
    
    async def table_exists(self, table_name: str) -> bool:
        """Check if collection exists"""
        if not self._db:
            await self.connect()
        
        collections = await self._db.list_collection_names()
        return table_name in collections
    
    async def get_database_size(self) -> int:
        """Get database size in bytes"""
        if not self._db:
            await self.connect()
        
        try:
            stats = await self._db.command('dbStats')
            return stats.get('dataSize', 0)
        except:
            return 0
    
    async def initialize_schema(self) -> None:
        """Create indexes for collections"""
        await self.create_tables()
    
    @timed
    async def create_tables(self, incremental: bool = None) -> None:
        """Create collections and indexes"""
        if not self._db:
            await self.connect()
        
        try:
            # Create indexes for master tables
            for table in MASTER_TABLES:
                collection = self._db[table]
                await collection.create_index('guid', unique=True, sparse=True)
                await collection.create_index('_company')
                await collection.create_index('name')
            
            # Create indexes for transaction tables
            for table in TRANSACTION_TABLES:
                collection = self._db[table]
                if table == 'trn_voucher':
                    await collection.create_index('guid', unique=True, sparse=True)
                else:
                    await collection.create_index('guid')
                await collection.create_index('_company')
                await collection.create_index('date')
            
            logger.info("MongoDB indexes created successfully")
            await self.ensure_audit_tables()
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise
    
    async def ensure_audit_tables(self) -> None:
        """Create audit collection with indexes"""
        if not self._db:
            await self.connect()
        
        try:
            audit_collection = self._db['audit_log']
            await audit_collection.create_index('sync_session_id')
            await audit_collection.create_index('table_name')
            await audit_collection.create_index('company')
            await audit_collection.create_index('created_at')
        except Exception as e:
            logger.warning(f"Could not create audit indexes: {e}")
    
    async def ensure_company_config_table(self) -> None:
        """Ensure company_config collection exists with indexes"""
        if not self._db:
            await self.connect()
        
        try:
            collection = self._db['company_config']
            await collection.create_index('company_name', unique=True)
            await collection.create_index('company_guid')
            
            # Create _diff and _delete collections
            diff_collection = self._db['_diff']
            await diff_collection.create_index('guid', unique=True)
            
            delete_collection = self._db['_delete']
            await delete_collection.create_index('guid', unique=True)
        except Exception as e:
            logger.warning(f"Could not ensure company_config collection: {e}")
    
    async def ensure_alterid_column_exists(self) -> None:
        """MongoDB doesn't need schema changes - alterid field is added dynamically"""
        # MongoDB is schema-less, so alterid field will be added automatically
        # when documents are inserted/updated with this field
        logger.debug("MongoDB: alterid field will be added dynamically to documents")
    
    async def update_company_config(self, company_name: str, company_guid: str = "",
                                     company_alterid: int = 0, last_alter_id_master: int = 0,
                                     last_alter_id_transaction: int = 0, sync_type: str = "full",
                                     books_from: str = "", books_to: str = "", **kwargs) -> None:
        """Update or insert company config document"""
        if not self._db:
            await self.connect()
        
        collection = self._db['company_config']
        now = datetime.now().isoformat()
        
        existing = await collection.find_one({'company_name': company_name})
        
        if existing:
            sync_count = (existing.get('sync_count') or 0) + 1
            update_doc = {
                'last_alter_id_master': last_alter_id_master,
                'last_alter_id_transaction': last_alter_id_transaction,
                'last_sync_at': now,
                'last_sync_type': sync_type,
                'sync_count': sync_count,
                'updated_at': now
            }
            if company_guid:
                update_doc['company_guid'] = company_guid
            if company_alterid > 0:
                update_doc['company_alterid'] = company_alterid
            if books_from:
                update_doc['books_from'] = books_from
            if books_to:
                update_doc['books_to'] = books_to
            
            await collection.update_one(
                {'company_name': company_name},
                {'$set': update_doc}
            )
        else:
            await collection.insert_one({
                'company_name': company_name,
                'company_guid': company_guid,
                'company_alterid': company_alterid,
                'last_alter_id_master': last_alter_id_master,
                'last_alter_id_transaction': last_alter_id_transaction,
                'books_from': books_from,
                'books_to': books_to,
                'last_sync_at': now,
                'last_sync_type': sync_type,
                'sync_count': 1,
                'created_at': now,
                'updated_at': now
            })
    
    async def get_company_config(self, company_name: str) -> Optional[Dict[str, Any]]:
        """Get company config by name"""
        if not self._db:
            await self.connect()
        
        collection = self._db['company_config']
        doc = await collection.find_one({'company_name': company_name})
        return self._convert_doc(doc)
    
    async def get_synced_companies(self) -> List[Dict[str, Any]]:
        """Get list of synced companies"""
        if not self._db:
            await self.connect()
        
        try:
            collection = self._db['company_config']
            cursor = collection.find({}).sort('company_name', 1)
            docs = await cursor.to_list(length=None)
            return [self._convert_doc(doc) for doc in docs]
        except Exception as e:
            logger.error(f"Failed to get synced companies: {e}")
            return []
    
    async def delete_company_data(self, company_name: str) -> int:
        """Delete all data for a specific company"""
        if not self._db:
            await self.connect()
        
        total_deleted = 0
        
        for table in ALL_TABLES:
            try:
                collection = self._db[table]
                result = await collection.delete_many({'_company': company_name})
                total_deleted += result.deleted_count
            except Exception as e:
                logger.warning(f"Error deleting from {table}: {e}")
        
        # Delete from company_config
        collection = self._db['company_config']
        result = await collection.delete_one({'company_name': company_name})
        total_deleted += result.deleted_count
        
        logger.info(f"Deleted company '{company_name}': {total_deleted} total documents")
        return total_deleted
    
    def get_placeholder(self) -> str:
        """MongoDB doesn't use placeholders"""
        return ''
    
    def get_table_quote(self) -> str:
        """MongoDB doesn't need quotes for collection names"""
        return ''
