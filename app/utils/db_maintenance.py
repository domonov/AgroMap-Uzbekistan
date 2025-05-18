"""Database maintenance utilities for AgroMap."""
import os
import time
import logging
import subprocess
import threading
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import text
from app.utils.backup import create_backup

# Set up logger
logger = logging.getLogger('db_maintenance')
handler = logging.FileHandler('logs/db_maintenance.log')
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class DatabaseMaintenance:
    """Database maintenance utilities."""
    
    def __init__(self, app=None, db=None):
        self.app = app
        self.db = db
        self.maintenance_active = False
        self.maintenance_thread = None
        self.maintenance_interval = 86400  # 24 hours in seconds
        self.vacuum_interval = 7  # days
        self.analyze_interval = 1  # days
        self.backup_interval = 1  # days
        self.last_vacuum = None
        self.last_analyze = None
        self.last_backup = None
        self.backup_dir = 'backups/database'
        
        if app is not None and db is not None:
            self.init_app(app, db)
    
    def init_app(self, app, db):
        """Initialize with Flask app and SQLAlchemy db."""
        self.app = app
        self.db = db
        
        # Create backup directory if it doesn't exist
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Register commands
        @app.cli.command("db-vacuum")
        def vacuum_command():
            """Vacuum the database."""
            result = self.vacuum_db()
            if result:
                print("Database vacuum completed successfully.")
            else:
                print("Database vacuum failed. Check logs for details.")
        
        @app.cli.command("db-analyze")
        def analyze_command():
            """Analyze the database."""
            result = self.analyze_db()
            if result:
                print("Database analyze completed successfully.")
            else:
                print("Database analyze failed. Check logs for details.")
        
        @app.cli.command("db-backup")
        def backup_command():
            """Backup the database."""
            result = self.backup_db()
            if result:
                print(f"Database backup completed successfully. Saved to {result}")
            else:
                print("Database backup failed. Check logs for details.")
        
        @app.cli.command("db-maintenance")
        def maintenance_command():
            """Run all database maintenance tasks."""
            self.run_maintenance()
            print("Database maintenance completed.")
        
        # Start maintenance thread
        self.start_maintenance_thread()
    
    def start_maintenance_thread(self):
        """Start the maintenance thread."""
        if self.maintenance_active:
            return
        
        self.maintenance_active = True
        
        def maintenance_worker():
            """Worker function for maintenance thread."""
            while self.maintenance_active:
                try:
                    with self.app.app_context():
                        self.run_maintenance()
                except Exception as e:
                    logger.error(f"Error in maintenance thread: {str(e)}")
                
                # Sleep until next maintenance interval
                time.sleep(self.maintenance_interval)
        
        # Start the thread
        self.maintenance_thread = threading.Thread(
            target=maintenance_worker,
            daemon=True
        )
        self.maintenance_thread.start()
        logger.info("Database maintenance thread started")
    
    def stop_maintenance_thread(self):
        """Stop the maintenance thread."""
        self.maintenance_active = False
        if self.maintenance_thread:
            self.maintenance_thread.join(timeout=1.0)
            logger.info("Database maintenance thread stopped")
    
    def run_maintenance(self):
        """Run all maintenance tasks as needed."""
        logger.info("Running database maintenance checks")
        
        # Check if vacuum is needed
        if not self.last_vacuum or (datetime.now() - self.last_vacuum).days >= self.vacuum_interval:
            self.vacuum_db()
        
        # Check if analyze is needed
        if not self.last_analyze or (datetime.now() - self.last_analyze).days >= self.analyze_interval:
            self.analyze_db()
        
        # Check if backup is needed
        if not self.last_backup or (datetime.now() - self.last_backup).days >= self.backup_interval:
            self.backup_db()
    
    def vacuum_db(self):
        """Vacuum the database to reclaim space and optimize performance."""
        try:
            logger.info("Starting database vacuum")
            
            # Get database URL from app config
            db_url = self.app.config.get('SQLALCHEMY_DATABASE_URI', '')
            
            if 'postgresql' in db_url:
                # For PostgreSQL, use VACUUM FULL ANALYZE
                with self.db.engine.connect() as conn:
                    conn.execute(text("VACUUM FULL ANALYZE"))
                    logger.info("PostgreSQL VACUUM FULL ANALYZE completed")
            elif 'sqlite' in db_url:
                # For SQLite, use VACUUM
                with self.db.engine.connect() as conn:
                    conn.execute(text("VACUUM"))
                    logger.info("SQLite VACUUM completed")
            else:
                logger.warning(f"Vacuum not supported for database type: {db_url}")
                return False
            
            self.last_vacuum = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Error during database vacuum: {str(e)}")
            return False
    
    def analyze_db(self):
        """Analyze the database to update statistics."""
        try:
            logger.info("Starting database analyze")
            
            # Get database URL from app config
            db_url = self.app.config.get('SQLALCHEMY_DATABASE_URI', '')
            
            if 'postgresql' in db_url:
                # For PostgreSQL, use ANALYZE
                with self.db.engine.connect() as conn:
                    conn.execute(text("ANALYZE"))
                    logger.info("PostgreSQL ANALYZE completed")
            elif 'sqlite' in db_url:
                # For SQLite, use ANALYZE
                with self.db.engine.connect() as conn:
                    conn.execute(text("ANALYZE"))
                    logger.info("SQLite ANALYZE completed")
            else:
                logger.warning(f"Analyze not supported for database type: {db_url}")
                return False
            
            self.last_analyze = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Error during database analyze: {str(e)}")
            return False
    
    def backup_db(self):
        """Backup the database."""
        try:
            logger.info("Starting database backup")
            
            # Get database URL from app config
            db_url = self.app.config.get('SQLALCHEMY_DATABASE_URI', '')
            
            # Extract database name and type from URL
            db_type = 'unknown'
            db_name = 'database'
            
            if 'postgresql' in db_url:
                db_type = 'postgresql'
                # Extract database name from URL
                db_name = db_url.split('/')[-1].split('?')[0]
            elif 'sqlite' in db_url:
                db_type = 'sqlite'
                # Extract database file path from URL
                db_name = db_url.replace('sqlite:///', '').split('?')[0]
            
            # Create timestamp for backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{db_name}_{timestamp}.backup"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            if db_type == 'postgresql':
                # Use pg_dump for PostgreSQL
                # Extract connection details from URL
                db_host = 'localhost'
                db_port = '5432'
                db_user = 'postgres'
                db_password = ''
                
                # Parse URL for connection details
                if '@' in db_url:
                    auth_part = db_url.split('@')[0].split('://')[-1]
                    if ':' in auth_part:
                        db_user, db_password = auth_part.split(':')
                
                if '@' in db_url:
                    host_part = db_url.split('@')[1].split('/')[0]
                    if ':' in host_part:
                        db_host, db_port = host_part.split(':')
                
                # Set environment variable for password
                env = os.environ.copy()
                if db_password:
                    env['PGPASSWORD'] = db_password
                
                # Run pg_dump
                cmd = [
                    'pg_dump',
                    '-h', db_host,
                    '-p', db_port,
                    '-U', db_user,
                    '-F', 'c',  # Custom format
                    '-b',  # Include large objects
                    '-v',  # Verbose
                    '-f', backup_path,
                    db_name
                ]
                
                result = subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                logger.info(f"PostgreSQL backup completed: {backup_path}")
            
            elif db_type == 'sqlite':
                # For SQLite, just copy the file
                import shutil
                shutil.copy2(db_name, backup_path)
                logger.info(f"SQLite backup completed: {backup_path}")
            
            else:
                # Use the backup utility from app.utils.backup
                backup_path = create_backup(db_url, backup_path)
                logger.info(f"Generic backup completed: {backup_path}")
            
            self.last_backup = datetime.now()
            return backup_path
        
        except Exception as e:
            logger.error(f"Error during database backup: {str(e)}")
            return False
    
    def optimize_tables(self):
        """Optimize database tables."""
        try:
            logger.info("Starting table optimization")
            
            # Get database URL from app config
            db_url = self.app.config.get('SQLALCHEMY_DATABASE_URI', '')
            
            if 'postgresql' in db_url:
                # For PostgreSQL, use REINDEX and CLUSTER
                with self.db.engine.connect() as conn:
                    # Get list of tables
                    result = conn.execute(text(
                        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                    ))
                    tables = [row[0] for row in result]
                    
                    # Reindex each table
                    for table in tables:
                        conn.execute(text(f"REINDEX TABLE {table}"))
                        logger.info(f"Reindexed table: {table}")
                    
                    logger.info("PostgreSQL table optimization completed")
            
            elif 'sqlite' in db_url:
                # For SQLite, just vacuum
                self.vacuum_db()
            
            else:
                logger.warning(f"Table optimization not supported for database type: {db_url}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error during table optimization: {str(e)}")
            return False
    
    def check_database_size(self):
        """Check the size of the database."""
        try:
            # Get database URL from app config
            db_url = self.app.config.get('SQLALCHEMY_DATABASE_URI', '')
            
            if 'postgresql' in db_url:
                # For PostgreSQL, query the database size
                with self.db.engine.connect() as conn:
                    result = conn.execute(text(
                        "SELECT pg_size_pretty(pg_database_size(current_database()))"
                    ))
                    size = result.scalar()
                    logger.info(f"PostgreSQL database size: {size}")
                    return size
            
            elif 'sqlite' in db_url:
                # For SQLite, get the file size
                db_path = db_url.replace('sqlite:///', '')
                if os.path.exists(db_path):
                    size_bytes = os.path.getsize(db_path)
                    size_mb = size_bytes / (1024 * 1024)
                    logger.info(f"SQLite database size: {size_mb:.2f} MB")
                    return f"{size_mb:.2f} MB"
                else:
                    logger.warning(f"SQLite database file not found: {db_path}")
                    return "Unknown"
            
            else:
                logger.warning(f"Size check not supported for database type: {db_url}")
                return "Unknown"
        
        except Exception as e:
            logger.error(f"Error checking database size: {str(e)}")
            return "Error"
    
    def generate_db_report(self):
        """Generate a report about the database."""
        try:
            # Get database URL from app config
            db_url = self.app.config.get('SQLALCHEMY_DATABASE_URI', '')
            db_type = 'unknown'
            
            if 'postgresql' in db_url:
                db_type = 'PostgreSQL'
            elif 'sqlite' in db_url:
                db_type = 'SQLite'
            
            # Get database size
            db_size = self.check_database_size()
            
            # Get table counts
            table_counts = {}
            with self.db.engine.connect() as conn:
                # Get list of tables
                if db_type == 'PostgreSQL':
                    result = conn.execute(text(
                        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                    ))
                    tables = [row[0] for row in result]
                elif db_type == 'SQLite':
                    result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ))
                    tables = [row[0] for row in result]
                else:
                    tables = []
                
                # Count rows in each table
                for table in tables:
                    try:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        table_counts[table] = count
                    except Exception as e:
                        logger.error(f"Error counting rows in {table}: {str(e)}")
                        table_counts[table] = "Error"
            
            # Create report
            report = {
                'database_type': db_type,
                'database_size': db_size,
                'table_count': len(table_counts),
                'tables': table_counts,
                'last_vacuum': self.last_vacuum.isoformat() if self.last_vacuum else None,
                'last_analyze': self.last_analyze.isoformat() if self.last_analyze else None,
                'last_backup': self.last_backup.isoformat() if self.last_backup else None
            }
            
            return report
        
        except Exception as e:
            logger.error(f"Error generating database report: {str(e)}")
            return {
                'error': str(e),
                'database_type': 'Unknown',
                'database_size': 'Unknown',
                'table_count': 0,
                'tables': {}
            }

# Initialize database maintenance
def init_db_maintenance(app, db):
    """Initialize database maintenance."""
    maintenance = DatabaseMaintenance(app, db)
    return maintenance