import asyncio
import logging
import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

class DatabaseSafety:
    """Production-ready database safety layer."""
    
    def __init__(self, database_url: str, logger: logging.Logger):
        self.database_url = database_url
        self.logger = logger
        self.pool = None
        self.connection_timeout = 30
        self.query_timeout = 60
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        
    async def initialize(self):
        """Initialize database connection pool with safety features."""
        try:
            self.pool = await asyncio.wait_for(
                asyncpg.create_pool(
                    self.database_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=self.query_timeout,
                    server_settings={
                        'application_name': 'autofarming_bot',
                        'statement_timeout': str(self.query_timeout * 1000),  # milliseconds
                        'idle_in_transaction_session_timeout': '300000'  # 5 minutes
                    }
                ),
                timeout=self.connection_timeout
            )
            self.logger.info("Database connection pool initialized successfully")
            
            # Test connection
            await self._test_connection()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def _test_connection(self):
        """Test database connection."""
        async with self.get_connection() as conn:
            await conn.execute("SELECT 1")
        self.logger.info("Database connection test successful")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection with timeout and retry logic."""
        conn = None
        for attempt in range(self.max_retries):
            try:
                conn = await asyncio.wait_for(
                    self.pool.acquire(),
                    timeout=self.connection_timeout
                )
                yield conn
                break
                
            except asyncio.TimeoutError:
                self.logger.warning(f"Database connection timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    raise Exception("Database connection timeout after all retries")
                await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                self.logger.error(f"Database connection error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay)
                
            finally:
                if conn:
                    try:
                        await self.pool.release(conn)
                    except Exception as e:
                        self.logger.error(f"Error releasing database connection: {e}")
    
    async def execute_query(self, query: str, *args, timeout: Optional[int] = None) -> Any:
        """Execute a database query with safety features."""
        timeout = timeout or self.query_timeout
        
        for attempt in range(self.max_retries):
            try:
                async with self.get_connection() as conn:
                    result = await asyncio.wait_for(
                        conn.execute(query, *args),
                        timeout=timeout
                    )
                    return result
                    
            except asyncio.TimeoutError:
                self.logger.warning(f"Query timeout (attempt {attempt + 1}/{self.max_retries}): {query[:50]}...")
                if attempt == self.max_retries - 1:
                    raise Exception(f"Query timeout after {self.max_retries} attempts")
                await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                self.logger.error(f"Query error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay)
    
    async def fetch_one(self, query: str, *args, timeout: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Fetch a single row with safety features."""
        timeout = timeout or self.query_timeout
        
        for attempt in range(self.max_retries):
            try:
                async with self.get_connection() as conn:
                    row = await asyncio.wait_for(
                        conn.fetchrow(query, *args),
                        timeout=timeout
                    )
                    return dict(row) if row else None
                    
            except asyncio.TimeoutError:
                self.logger.warning(f"Fetch timeout (attempt {attempt + 1}/{self.max_retries}): {query[:50]}...")
                if attempt == self.max_retries - 1:
                    raise Exception(f"Fetch timeout after {self.max_retries} attempts")
                await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                self.logger.error(f"Fetch error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay)
    
    async def fetch_all(self, query: str, *args, timeout: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch all rows with safety features."""
        timeout = timeout or self.query_timeout
        
        for attempt in range(self.max_retries):
            try:
                async with self.get_connection() as conn:
                    rows = await asyncio.wait_for(
                        conn.fetch(query, *args),
                        timeout=timeout
                    )
                    return [dict(row) for row in rows]
                    
            except asyncio.TimeoutError:
                self.logger.warning(f"Fetch all timeout (attempt {attempt + 1}/{self.max_retries}): {query[:50]}...")
                if attempt == self.max_retries - 1:
                    raise Exception(f"Fetch all timeout after {self.max_retries} attempts")
                await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                self.logger.error(f"Fetch all error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay)
    
    async def transaction(self):
        """Get a database transaction with safety features."""
        return DatabaseTransaction(self)
    
    async def close(self):
        """Close database connection pool safely."""
        if self.pool:
            try:
                await asyncio.wait_for(self.pool.close(), timeout=10)
                self.logger.info("Database connection pool closed successfully")
            except asyncio.TimeoutError:
                self.logger.warning("Database close timed out, forcing close...")
                self.pool.terminate()
            except Exception as e:
                self.logger.error(f"Error closing database pool: {e}")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get database pool statistics."""
        if not self.pool:
            return {'status': 'not_initialized'}
        
        try:
            return {
                'status': 'active',
                'min_size': self.pool.get_min_size(),
                'max_size': self.pool.get_max_size(),
                'size': self.pool.get_size(),
                'free_size': self.pool.get_free_size()
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

class DatabaseTransaction:
    """Safe database transaction wrapper."""
    
    def __init__(self, db_safety: DatabaseSafety):
        self.db_safety = db_safety
        self.conn = None
        self.transaction = None
    
    async def __aenter__(self):
        """Start transaction."""
        self.conn = await self.db_safety.pool.acquire()
        self.transaction = self.conn.transaction()
        await self.transaction.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End transaction."""
        try:
            if exc_type is None:
                await self.transaction.commit()
            else:
                await self.transaction.rollback()
        finally:
            if self.conn:
                await self.db_safety.pool.release(self.conn)
    
    async def execute(self, query: str, *args):
        """Execute query in transaction."""
        return await self.conn.execute(query, *args)
    
    async def fetch_one(self, query: str, *args):
        """Fetch one row in transaction."""
        row = await self.conn.fetchrow(query, *args)
        return dict(row) if row else None
    
    async def fetch_all(self, query: str, *args):
        """Fetch all rows in transaction."""
        rows = await self.conn.fetch(query, *args)
        return [dict(row) for row in rows]

# Global database safety instance
db_safety = None

def initialize_database_safety(database_url: str, logger: logging.Logger):
    """Initialize the database safety layer."""
    global db_safety
    db_safety = DatabaseSafety(database_url, logger)
    return db_safety 