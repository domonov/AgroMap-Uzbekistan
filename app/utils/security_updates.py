"""Security update utilities for AgroMap."""
import os
import json
import logging
import requests
import subprocess
import pkg_resources
from datetime import datetime
from flask import current_app
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Set up logger
logger = logging.getLogger('security')
handler = logging.FileHandler('logs/security.log')
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class SecurityUpdateManager:
    """Manage security updates for dependencies."""
    
    def __init__(self, app=None):
        self.app = app
        self.vulnerabilities = {}
        self.last_check = None
        self.check_interval = 86400  # 24 hours in seconds
        self.pypi_url = "https://pypi.org/pypi/{package}/json"
        self.nvd_api_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        self.nvd_api_key = os.environ.get("NVD_API_KEY", "")
        self.admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
        self.smtp_server = os.environ.get("SMTP_SERVER", "smtp.example.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_username = os.environ.get("SMTP_USERNAME", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app."""
        self.app = app
        
        # Register command to check for security updates
        @app.cli.command("check-security-updates")
        def check_security_updates_command():
            """Check for security updates in dependencies."""
            self.check_for_updates()
            print(f"Security check completed. Found {len(self.vulnerabilities)} vulnerable packages.")
            for package, vulns in self.vulnerabilities.items():
                print(f"{package}: {len(vulns)} vulnerabilities")
    
    def check_for_updates(self, force=False):
        """Check for security updates in dependencies."""
        # Skip if checked recently
        if not force and self.last_check and (datetime.now() - self.last_check).total_seconds() < self.check_interval:
            logger.info("Skipping security check - checked recently")
            return self.vulnerabilities
        
        logger.info("Checking for security updates")
        self.last_check = datetime.now()
        self.vulnerabilities = {}
        
        try:
            # Get installed packages
            installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
            
            # Check each package for vulnerabilities
            for package_name, version in installed_packages.items():
                try:
                    vulns = self._check_package_vulnerabilities(package_name, version)
                    if vulns:
                        self.vulnerabilities[package_name] = vulns
                        logger.warning(f"Security vulnerabilities found in {package_name} {version}: {len(vulns)} issues")
                except Exception as e:
                    logger.error(f"Error checking {package_name}: {str(e)}")
            
            # If vulnerabilities found, notify admin
            if self.vulnerabilities:
                self._notify_admin()
                
            return self.vulnerabilities
        except Exception as e:
            logger.error(f"Error checking for security updates: {str(e)}")
            return {}
    
    def _check_package_vulnerabilities(self, package_name, current_version):
        """Check a specific package for known vulnerabilities."""
        vulnerabilities = []
        
        # Check PyPI for newer versions
        try:
            response = requests.get(self.pypi_url.format(package=package_name), timeout=10)
            if response.status_code == 200:
                package_data = response.json()
                latest_version = package_data.get('info', {}).get('version', '')
                
                if latest_version and latest_version != current_version:
                    # Check release info for security notes
                    release_info = package_data.get('releases', {}).get(latest_version, [])
                    for release in release_info:
                        if 'security' in release.get('comment_text', '').lower():
                            vulnerabilities.append({
                                'type': 'security_release',
                                'current_version': current_version,
                                'latest_version': latest_version,
                                'description': release.get('comment_text', 'Security update available')
                            })
        except Exception as e:
            logger.error(f"Error checking PyPI for {package_name}: {str(e)}")
        
        # Check NVD database if API key is available
        if self.nvd_api_key:
            try:
                headers = {
                    'apiKey': self.nvd_api_key
                }
                params = {
                    'keywordSearch': package_name,
                    'keywordExactMatch': True
                }
                response = requests.get(self.nvd_api_url, headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    nvd_data = response.json()
                    for vuln in nvd_data.get('vulnerabilities', []):
                        cve = vuln.get('cve', {})
                        cve_id = cve.get('id', '')
                        description = cve.get('descriptions', [{}])[0].get('value', '')
                        
                        # Check if this vulnerability affects our version
                        for node in cve.get('configurations', []):
                            for match in node.get('nodes', []):
                                for cpe_match in match.get('cpeMatch', []):
                                    if package_name.lower() in cpe_match.get('criteria', '').lower():
                                        vulnerabilities.append({
                                            'type': 'cve',
                                            'id': cve_id,
                                            'description': description,
                                            'url': f"https://nvd.nist.gov/vuln/detail/{cve_id}"
                                        })
            except Exception as e:
                logger.error(f"Error checking NVD for {package_name}: {str(e)}")
        
        # Check safety-db as a fallback
        try:
            result = subprocess.run(
                ["pip-audit", package_name],
                capture_output=True,
                text=True,
                check=False
            )
            
            if "No known vulnerabilities found" not in result.stdout:
                for line in result.stdout.splitlines():
                    if package_name in line and "vulnerability" in line:
                        vulnerabilities.append({
                            'type': 'pip_audit',
                            'description': line.strip()
                        })
        except Exception as e:
            logger.error(f"Error running pip-audit for {package_name}: {str(e)}")
        
        return vulnerabilities
    
    def _notify_admin(self):
        """Notify administrator about security vulnerabilities."""
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = self.admin_email
            msg['Subject'] = f"[SECURITY] Vulnerabilities found in {len(self.vulnerabilities)} packages"
            
            # Build email body
            body = "The following security vulnerabilities were found in your dependencies:\n\n"
            
            for package, vulns in self.vulnerabilities.items():
                body += f"Package: {package}\n"
                for i, vuln in enumerate(vulns, 1):
                    body += f"  {i}. Type: {vuln.get('type')}\n"
                    if 'id' in vuln:
                        body += f"     ID: {vuln.get('id')}\n"
                    if 'current_version' in vuln:
                        body += f"     Current Version: {vuln.get('current_version')}\n"
                    if 'latest_version' in vuln:
                        body += f"     Latest Version: {vuln.get('latest_version')}\n"
                    body += f"     Description: {vuln.get('description')}\n"
                    if 'url' in vuln:
                        body += f"     URL: {vuln.get('url')}\n"
                    body += "\n"
                
                body += "\n"
            
            body += "Please update these packages as soon as possible to address these security issues."
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email if SMTP credentials are configured
            if self.smtp_username and self.smtp_password:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
                    logger.info(f"Security notification email sent to {self.admin_email}")
            else:
                logger.warning("SMTP credentials not configured, skipping email notification")
                
            # Log the vulnerabilities
            logger.warning(f"Security vulnerabilities found: {json.dumps(self.vulnerabilities)}")
            
        except Exception as e:
            logger.error(f"Error sending security notification: {str(e)}")
    
    def update_vulnerable_packages(self, packages=None):
        """Update vulnerable packages."""
        if not packages:
            packages = list(self.vulnerabilities.keys())
        
        updated = []
        failed = []
        
        for package in packages:
            try:
                logger.info(f"Updating {package}")
                result = subprocess.run(
                    ["pip", "install", "--upgrade", package],
                    capture_output=True,
                    text=True,
                    check=True
                )
                updated.append(package)
                logger.info(f"Successfully updated {package}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to update {package}: {e.stderr}")
                failed.append(package)
        
        return {
            'updated': updated,
            'failed': failed
        }

# Function to check for security updates
def check_security_updates(app=None):
    """Check for security updates in dependencies."""
    manager = SecurityUpdateManager(app)
    return manager.check_for_updates()