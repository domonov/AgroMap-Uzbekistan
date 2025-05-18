"""Dependency management utilities for AgroMap."""
import os
import re
import sys
import json
import logging
import subprocess
import pkg_resources
from datetime import datetime
from flask import current_app
import requests
from packaging import version

# Set up logger
logger = logging.getLogger('dependencies')
handler = logging.FileHandler('logs/dependencies.log')
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class DependencyManager:
    """Manage project dependencies."""
    
    def __init__(self, app=None):
        self.app = app
        self.requirements_file = 'requirements.txt'
        self.backup_dir = 'backups/requirements'
        self.pypi_url = "https://pypi.org/pypi/{package}/json"
        self.outdated_packages = {}
        self.last_check = None
        self.check_interval = 86400  # 24 hours in seconds
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app."""
        self.app = app
        
        # Create backup directory if it doesn't exist
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Register commands
        @app.cli.command("check-dependencies")
        def check_dependencies_command():
            """Check for outdated dependencies."""
            outdated = self.check_outdated_dependencies()
            print(f"Found {len(outdated)} outdated packages:")
            for package, versions in outdated.items():
                print(f"{package}: {versions['current']} -> {versions['latest']}")
        
        @app.cli.command("update-dependencies")
        def update_dependencies_command():
            """Update all dependencies to their latest versions."""
            result = self.update_all_dependencies()
            print(f"Updated {len(result['updated'])} packages:")
            for package in result['updated']:
                print(f"- {package}")
            
            if result['failed']:
                print(f"\nFailed to update {len(result['failed'])} packages:")
                for package in result['failed']:
                    print(f"- {package}")
    
    def check_outdated_dependencies(self, force=False):
        """Check for outdated dependencies."""
        # Skip if checked recently
        if not force and self.last_check and (datetime.now() - self.last_check).total_seconds() < self.check_interval:
            logger.info("Skipping dependency check - checked recently")
            return self.outdated_packages
        
        logger.info("Checking for outdated dependencies")
        self.last_check = datetime.now()
        self.outdated_packages = {}
        
        try:
            # Get installed packages
            installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
            
            # Check each package for updates
            for package_name, current_version in installed_packages.items():
                try:
                    latest_version = self._get_latest_version(package_name)
                    
                    if latest_version and version.parse(latest_version) > version.parse(current_version):
                        self.outdated_packages[package_name] = {
                            'current': current_version,
                            'latest': latest_version
                        }
                        logger.info(f"Outdated package: {package_name} {current_version} -> {latest_version}")
                except Exception as e:
                    logger.error(f"Error checking {package_name}: {str(e)}")
            
            return self.outdated_packages
        except Exception as e:
            logger.error(f"Error checking for outdated dependencies: {str(e)}")
            return {}
    
    def _get_latest_version(self, package_name):
        """Get the latest version of a package from PyPI."""
        try:
            response = requests.get(self.pypi_url.format(package=package_name), timeout=10)
            if response.status_code == 200:
                package_data = response.json()
                return package_data.get('info', {}).get('version', '')
            return None
        except Exception as e:
            logger.error(f"Error getting latest version for {package_name}: {str(e)}")
            return None
    
    def update_all_dependencies(self):
        """Update all dependencies to their latest versions."""
        # First check for outdated packages
        self.check_outdated_dependencies(force=True)
        
        if not self.outdated_packages:
            logger.info("No outdated packages found")
            return {'updated': [], 'failed': []}
        
        # Backup requirements file
        self._backup_requirements()
        
        updated = []
        failed = []
        
        for package_name in self.outdated_packages.keys():
            try:
                logger.info(f"Updating {package_name}")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", package_name],
                    capture_output=True,
                    text=True,
                    check=True
                )
                updated.append(package_name)
                logger.info(f"Successfully updated {package_name}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to update {package_name}: {e.stderr}")
                failed.append(package_name)
        
        # Update requirements.txt with new versions
        if updated:
            self._update_requirements_file(updated)
        
        return {
            'updated': updated,
            'failed': failed
        }
    
    def update_specific_dependency(self, package_name, version=None):
        """Update a specific dependency to the specified version or latest."""
        try:
            # Backup requirements file
            self._backup_requirements()
            
            install_target = package_name
            if version:
                install_target = f"{package_name}=={version}"
            
            logger.info(f"Updating {install_target}")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", install_target],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Update requirements.txt
            self._update_requirements_file([package_name])
            
            logger.info(f"Successfully updated {package_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update {package_name}: {str(e)}")
            return False
    
    def _backup_requirements(self):
        """Backup the requirements.txt file."""
        if not os.path.exists(self.requirements_file):
            logger.warning(f"Requirements file {self.requirements_file} not found")
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self.backup_dir, f"requirements_{timestamp}.txt")
        
        try:
            with open(self.requirements_file, 'r') as src, open(backup_file, 'w') as dst:
                dst.write(src.read())
            logger.info(f"Backed up requirements to {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup requirements: {str(e)}")
            return False
    
    def _update_requirements_file(self, updated_packages):
        """Update the requirements.txt file with new versions."""
        if not os.path.exists(self.requirements_file):
            logger.warning(f"Requirements file {self.requirements_file} not found")
            return False
        
        try:
            # Get current installed versions
            installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
            
            # Read current requirements
            with open(self.requirements_file, 'r') as f:
                requirements = f.readlines()
            
            # Update versions
            updated_requirements = []
            for line in requirements:
                line = line.strip()
                if not line or line.startswith('#'):
                    updated_requirements.append(line)
                    continue
                
                # Parse package name and version constraint
                match = re.match(r'^([a-zA-Z0-9_\-\.]+)([<>=!~].+)?$', line)
                if match:
                    package_name = match.group(1).lower()
                    
                    # Check if this package was updated
                    if package_name in [p.lower() for p in updated_packages]:
                        if package_name in installed_packages:
                            new_version = installed_packages[package_name]
                            updated_requirements.append(f"{package_name}=={new_version}")
                            logger.info(f"Updated {package_name} to {new_version} in requirements.txt")
                        else:
                            # Keep the original line if package not found
                            updated_requirements.append(line)
                    else:
                        # Keep the original line for packages not updated
                        updated_requirements.append(line)
                else:
                    # Keep lines that don't match package pattern
                    updated_requirements.append(line)
            
            # Write updated requirements
            with open(self.requirements_file, 'w') as f:
                f.write('\n'.join(updated_requirements) + '\n')
            
            logger.info(f"Updated {self.requirements_file} with new versions")
            return True
        except Exception as e:
            logger.error(f"Failed to update requirements file: {str(e)}")
            return False
    
    def generate_dependency_report(self):
        """Generate a report of all dependencies and their versions."""
        try:
            installed_packages = sorted([
                {
                    'name': pkg.key,
                    'version': pkg.version,
                    'location': pkg.location
                }
                for pkg in pkg_resources.working_set
            ], key=lambda x: x['name'])
            
            # Check for outdated packages
            outdated = self.check_outdated_dependencies()
            
            # Add outdated status to report
            for package in installed_packages:
                if package['name'] in outdated:
                    package['outdated'] = True
                    package['latest_version'] = outdated[package['name']]['latest']
                else:
                    package['outdated'] = False
            
            return {
                'total_packages': len(installed_packages),
                'outdated_packages': len(outdated),
                'packages': installed_packages
            }
        except Exception as e:
            logger.error(f"Error generating dependency report: {str(e)}")
            return {
                'error': str(e),
                'total_packages': 0,
                'outdated_packages': 0,
                'packages': []
            }

# Function to check for outdated dependencies
def check_dependencies(app=None):
    """Check for outdated dependencies."""
    manager = DependencyManager(app)
    return manager.check_outdated_dependencies()