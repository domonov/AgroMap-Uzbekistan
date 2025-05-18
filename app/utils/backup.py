#!/usr/bin/env python
"""
Backup System for AgroMap Uzbekistan

This script provides automated backup functionality for the AgroMap application,
including database backups and file backups.
"""

import os
import time
import shutil
import subprocess
import logging
from datetime import datetime
import tarfile
import boto3
from botocore.exceptions import ClientError
import json
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('backup')

class BackupSystem:
    """Handles database and file backups for the AgroMap application."""
    
    def __init__(self, config=None):
        """
        Initialize the backup system.
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config or {}
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Default configuration
        self.db_name = self.config.get('db_name', 'agromap')
        self.db_user = self.config.get('db_user', 'username')
        self.db_password = self.config.get('db_password', 'password')
        self.db_host = self.config.get('db_host', 'localhost')
        
        self.backup_dir = self.config.get('backup_dir', 'backups')
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_backup(self, backup_name=None, include_dirs=None):
        """Create a backup of the application."""
        try:
            if not backup_name:
                backup_name = f'backup_{self.timestamp}'

            # Default directories to backup
            if not include_dirs:
                include_dirs = [
                    'app',
                    'migrations',
                    'instance',
                    'config.py',
                    'pyproject.toml',
                    'setup.cfg'
                ]

            # Create backup archive
            backup_path = os.path.join(self.backup_dir, f'{backup_name}.tar.gz')
            
            if sys.platform == 'win32':
                # Use 7-Zip on Windows if available
                seven_zip = shutil.which('7z')
                if seven_zip:
                    subprocess.run([
                        seven_zip, 'a', '-ttar', 
                        f'{backup_path}.tar',
                        *include_dirs
                    ], check=True)
                    subprocess.run([
                        seven_zip, 'a', '-tgzip',
                        backup_path,
                        f'{backup_path}.tar'
                    ], check=True)
                    os.remove(f'{backup_path}.tar')
                else:
                    # Fallback to shutil on Windows
                    shutil.make_archive(
                        base_name=os.path.join(self.backup_dir, backup_name),
                        format='gztar',
                        root_dir='.',
                        base_dir='.'
                    )
            else:
                # Use tar on Unix systems
                with tarfile.open(backup_path, 'w:gz') as tar:
                    for item in include_dirs:
                        tar.add(item)

            logger.info(f'Created backup: {backup_path}')
            return backup_path

        except Exception as e:
            logger.error(f'Backup creation failed: {e}')
            raise

    def create_db_backup(self):
        """Create database backup."""
        try:
            backup_file = os.path.join(
                self.backup_dir,
                f'db_backup_{self.timestamp}.sql'
            )

            # Create database backup using pg_dump
            subprocess.run([
                'pg_dump',
                '-h', self.db_host,
                '-U', self.db_user,
                '-d', self.db_name,
                '-f', backup_file
            ], env={'PGPASSWORD': self.db_password}, check=True)

            logger.info(f'Created database backup: {backup_file}')
            return backup_file

        except Exception as e:
            logger.error(f'Database backup failed: {e}')
            raise

    def restore_backup(self, backup_path, restore_dir=None):
        """Restore from a backup archive."""
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f'Backup file not found: {backup_path}')

            if not restore_dir:
                restore_dir = os.path.join(
                    self.backup_dir,
                    f'restore_{self.timestamp}'
                )

            os.makedirs(restore_dir, exist_ok=True)

            if backup_path.endswith('.sql'):
                # Restore database backup
                subprocess.run([
                    'psql',
                    '-h', self.db_host,
                    '-U', self.db_user,
                    '-d', self.db_name,
                    '-f', backup_path
                ], env={'PGPASSWORD': self.db_password}, check=True)
            else:
                # Restore file backup
                if sys.platform == 'win32':
                    seven_zip = shutil.which('7z')
                    if seven_zip:
                        subprocess.run([
                            seven_zip, 'x', backup_path,
                            f'-o{restore_dir}'
                        ], check=True)
                    else:
                        shutil.unpack_archive(backup_path, restore_dir)
                else:
                    with tarfile.open(backup_path, 'r:gz') as tar:
                        tar.extractall(path=restore_dir)

            logger.info(f'Restored backup to: {restore_dir}')
            return True

        except Exception as e:
            logger.error(f'Backup restoration failed: {e}')
            raise

# Module level functions for compatibility
_backup_system = None

def init_backup_system(config=None):
    """Initialize the backup system."""
    global _backup_system
    if _backup_system is None:
        _backup_system = BackupSystem(config)
    return _backup_system

def create_backup(*args, **kwargs):
    """Create a backup using the global backup system."""
    if _backup_system is None:
        raise RuntimeError('Backup system not initialized')
    return _backup_system.create_backup(*args, **kwargs)