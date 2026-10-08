"""
Data migration script to copy all data from SQLite to Azure SQL Server.
Handles proper table ordering for foreign key constraints and UUID conversion.
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text, MetaData, Table, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from dotenv import load_dotenv
from utils.database import Base, engine as sqlserver_engine, SessionLocal as SQLServerSessionLocal
import uuid
from datetime import datetime

# Import your models
from database_models.resume_models import (POR)

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    def __init__(self, sqlite_path: str):
        """
        Initialize the migrator with SQLite and SQL Server connections.
        
        Args:
            sqlite_path: Path to SQLite database file
        """
        self.sqlite_path = sqlite_path
        
        # Create engines
        self.sqlite_engine = create_engine(
            f"sqlite:///{sqlite_path}",
            echo=False,
            connect_args={"check_same_thread": False}
        )
        
        self.sqlserver_engine = sqlserver_engine
        
        # Create sessions
        self.sqlite_session = sessionmaker(bind=self.sqlite_engine)()
        self.sqlserver_session = SQLServerSessionLocal()
        
        # Define migration order (respects foreign key constraints)
        # Start with just POR for testing, then add others
        self.migration_order = [
            (POR, "pors")
        ]
    
    def test_connections(self) -> bool:
        """Test both database connections."""
        try:
            # Test SQLite
            with self.sqlite_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(" SQLite connection successful")
            
            # Test SQL Server
            with self.sqlserver_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(" SQL Server connection successful")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def get_sqlite_columns(self, table_name: str) -> List[str]:
        """Get actual columns from SQLite table."""
        try:
            inspector = inspect(self.sqlite_engine)
            columns = inspector.get_columns(table_name)
            return [col['name'] for col in columns]
        except Exception as e:
            logger.warning(f"Could not get columns for {table_name}: {e}")
            return []
    
    def get_table_count(self, engine: Engine, table_name: str) -> int:
        """Get row count for a table."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return result.scalar()
        except Exception as e:
            logger.warning(f"Could not get count for {table_name}: {e}")
            return 0
    
    def clear_sqlserver_data(self):
        """Clear all data from SQL Server tables (in reverse order)."""
        logger.info("🧹 Clearing existing SQL Server data...")
        
        try:
            with self.sqlserver_engine.connect() as conn:
                # Delete in reverse order to respect foreign key constraints
                for model_class, table_name in reversed(self.migration_order):
                    try:
                        result = conn.execute(text(f"DELETE FROM {table_name}"))
                        logger.info(f"   Cleared {result.rowcount} rows from {table_name}")
                    except Exception as e:
                        logger.warning(f"   Could not clear {table_name}: {e}")
                
                conn.commit()
            
            logger.info(" Data clearing completed")
            
        except Exception as e:
            logger.error(f"❌ Error clearing SQL Server data: {e}")
            raise
    
    def convert_uuid_fields(self, data: Dict[str, Any], model_class) -> Dict[str, Any]:
        """Convert UUID string fields to proper UUID objects."""
        uuid_columns = []
        for column in model_class.__table__.columns:
            if hasattr(column.type, 'impl') and 'GUID' in str(type(column.type)):
                uuid_columns.append(column.name)
        
        # Convert string UUIDs to UUID objects
        for col in uuid_columns:
            if col in data and data[col] is not None:
                if isinstance(data[col], str):
                    try:
                        data[col] = uuid.UUID(data[col])
                    except ValueError:
                        logger.warning(f"Invalid UUID format for {col}: {data[col]}")
                        data[col] = None
        
        return data
    
    def add_missing_fields(self, data: Dict[str, Any], model_class) -> Dict[str, Any]:
        """Add missing fields with default values."""
        model_columns = {col.name for col in model_class.__table__.columns}
        
        for col_name in model_columns:
            if col_name not in data:
                # Add default values for common missing columns
                if col_name == 'created_at':
                    data[col_name] = datetime.utcnow()
                    logger.info(f"   Added default created_at: {data[col_name]}")
                elif col_name == 'updated_at':
                    data[col_name] = None
                elif col_name == 'id' and col_name not in data:
                    # Skip auto-increment IDs
                    continue
                else:
                    # Find the column in the model
                    for column in model_class.__table__.columns:
                        if column.name == col_name:
                            if column.nullable:
                                data[col_name] = None
                            elif hasattr(column, 'default') and column.default is not None:
                                if hasattr(column.default, 'arg'):
                                    if callable(column.default.arg):
                                        data[col_name] = column.default.arg()
                                    else:
                                        data[col_name] = column.default.arg
                            break
        
        return data
    
    def migrate_table(self, model_class, table_name: str) -> bool:
        """Migrate a single table from SQLite to SQL Server."""
        try:
            logger.info(f"📋 Migrating {table_name}...")
            
            # Check what columns exist in SQLite
            sqlite_columns = self.get_sqlite_columns(table_name)
            model_columns = [col.name for col in model_class.__table__.columns]
            
            logger.info(f"   SQLite columns: {sqlite_columns}")
            logger.info(f"   Model columns: {model_columns}")
            
            # Get count from SQLite
            sqlite_count = self.get_table_count(self.sqlite_engine, table_name)
            logger.info(f"   Found {sqlite_count} records in SQLite")
            
            if sqlite_count == 0:
                logger.info(f"   No data to migrate for {table_name}")
                return True
            
            # Read data using raw SQL to handle missing columns
            common_columns = [col for col in sqlite_columns if col in model_columns]
            
            if not common_columns:
                logger.warning(f"   No common columns found between SQLite and model!")
                return False
            
            logger.info(f"   Common columns: {common_columns}")
            
            # Query only existing columns
            column_list = ", ".join(common_columns)
            query = f"SELECT {column_list} FROM {table_name}"
            
            with self.sqlite_engine.connect() as conn:
                result = conn.execute(text(query))
                rows = result.fetchall()
            
            # Convert to dictionaries and handle missing fields
            records_to_insert = []
            for row in rows:
                record_dict = {}
                for i, col_name in enumerate(common_columns):
                    record_dict[col_name] = row[i]
                
                # Add missing fields with defaults
                record_dict = self.add_missing_fields(record_dict, model_class)
                
                # Convert UUID fields
                record_dict = self.convert_uuid_fields(record_dict, model_class)
                records_to_insert.append(record_dict)
            
            # Batch insert into SQL Server
            if records_to_insert:
                batch_size = 1000
                total_inserted = 0
                
                for i in range(0, len(records_to_insert), batch_size):
                    batch = records_to_insert[i:i + batch_size]
                    
                    try:
                        self.sqlserver_session.bulk_insert_mappings(model_class, batch)
                        self.sqlserver_session.commit()
                        total_inserted += len(batch)
                        
                        if len(records_to_insert) > batch_size:
                            logger.info(f"   Inserted {total_inserted}/{len(records_to_insert)} records")
                            
                    except Exception as e:
                        logger.error(f"   Batch insert failed: {e}")
                        self.sqlserver_session.rollback()
                        
                        # Try individual inserts
                        for record in batch:
                            try:
                                self.sqlserver_session.bulk_insert_mappings(model_class, [record])
                                self.sqlserver_session.commit()
                                total_inserted += 1
                            except Exception as individual_error:
                                logger.error(f"   Failed to insert record: {individual_error}")
                                logger.error(f"   Record: {record}")
                                self.sqlserver_session.rollback()
            
            # Verify migration
            sqlserver_count = self.get_table_count(self.sqlserver_engine, table_name)
            logger.info(f"    Migration completed: {sqlserver_count}/{sqlite_count} records")
            
            if sqlserver_count != sqlite_count:
                logger.warning(f"   ⚠️ Record count mismatch for {table_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error migrating {table_name}: {e}")
            self.sqlserver_session.rollback()
            return False
    
    def create_tables(self):
        """Create all tables in SQL Server."""
        logger.info("🏗️ Creating tables in SQL Server...")
        try:
            Base.metadata.create_all(bind=self.sqlserver_engine)
            logger.info(" Tables created successfully")
            
            # Show created tables
            with self.sqlserver_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT TABLE_NAME 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_TYPE = 'BASE TABLE' 
                    AND TABLE_SCHEMA = 'dbo'
                """))
                tables = [row[0] for row in result]
                logger.info(f"   Created tables: {', '.join(tables)}")
                
        except Exception as e:
            logger.error(f"❌ Error creating tables: {e}")
            raise
    
    def migrate_all(self, clear_existing: bool = True) -> bool:
        """Migrate all data from SQLite to SQL Server."""
        try:
            logger.info("🚀 Starting database migration...")
            
            # Test connections
            if not self.test_connections():
                return False
            
            # Create tables in SQL Server
            self.create_tables()
            
            # Clear existing data if requested
            if clear_existing:
                self.clear_sqlserver_data()
            
            # Migrate each table in order
            success_count = 0
            for model_class, table_name in self.migration_order:
                if self.migrate_table(model_class, table_name):
                    success_count += 1
                else:
                    logger.error(f"❌ Failed to migrate {table_name}")
            
            # Summary
            total_tables = len(self.migration_order)
            logger.info(f" Migration Summary:")
            logger.info(f"   Successfully migrated: {success_count}/{total_tables} tables")
            
            if success_count == total_tables:
                logger.info("🎉 Migration completed successfully!")
                return True
            else:
                logger.warning("⚠️ Migration completed with errors")
                return False
                
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
        
        finally:
            # Close sessions
            self.sqlite_session.close()
            self.sqlserver_session.close()
    
    def verify_migration(self):
        """Verify the migration by comparing record counts."""
        logger.info("🔍 Verifying migration...")
        
        verification_results = []
        for model_class, table_name in self.migration_order:
            sqlite_count = self.get_table_count(self.sqlite_engine, table_name)
            sqlserver_count = self.get_table_count(self.sqlserver_engine, table_name)
            
            status = "" if sqlite_count == sqlserver_count else "❌"
            verification_results.append((table_name, sqlite_count, sqlserver_count, status))
            
        # Print verification table
        logger.info("\nVerification Results:")
        logger.info("=" * 60)
        logger.info(f"{'Table':<25} {'SQLite':<10} {'SQL Server':<12} {'Status'}")
        logger.info("=" * 60)
        
        for table_name, sqlite_count, sqlserver_count, status in verification_results:
            logger.info(f"{table_name:<25} {sqlite_count:<10} {sqlserver_count:<12} {status}")
        
        logger.info("=" * 60)


def main():
    """Main migration function."""
    
    # Configuration
    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "private-data/resume_app.db")
    SQLSERVER_URL = os.getenv("DATABASE_URL")
    
    if not SQLSERVER_URL:
        logger.error("❌ DATABASE_URL environment variable not set")
        sys.exit(1)
    
    if not os.path.exists(SQLITE_DB_PATH):
        logger.error(f"❌ SQLite database not found: {SQLITE_DB_PATH}")
        sys.exit(1)
    
    logger.info(f"📁 SQLite Database: {SQLITE_DB_PATH}")
    
    # Create migrator and run migration
    migrator = DatabaseMigrator(SQLITE_DB_PATH)
    
    # Confirm before proceeding
    response = input("\nThis will clear all existing data in SQL Server. Continue? (y/N): ")
    if response.lower() != 'y':
        logger.info("Migration cancelled by user")
        sys.exit(0)
    
    # Run migration
    success = migrator.migrate_all(clear_existing=True)
    
    if success:
        # Verify migration
        migrator.verify_migration()
        logger.info("\n🎉 Migration process completed!")
    else:
        logger.error("\n❌ Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
