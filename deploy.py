#!/usr/bin/env python3
"""
Deployment script for AgroMap Uzbekistan

This script automates the deployment process for both staging and production environments.
It handles:
1. Environment setup
2. Database migration
3. SSL configuration
4. Domain setup
5. Backup verification
6. Monitoring setup
7. Alert configuration
8. Final testing
"""

import os
import sys
import argparse
import subprocess
import time
import logging
import json
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deploy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('deploy')

# Default configuration
DEFAULT_CONFIG = {
    'staging': {
        'host': 'staging.agromap.uz',
        'user': 'deploy',
        'port': 22,
        'app_dir': '/var/www/agromap-staging',
        'venv_dir': '/var/www/agromap-staging/venv',
        'db_name': 'agromap_staging',
        'db_user': 'agromap_admin',
        'ssl_cert': '/etc/letsencrypt/live/staging.agromap.uz/fullchain.pem',
        'ssl_key': '/etc/letsencrypt/live/staging.agromap.uz/privkey.pem',
        'monitoring_url': 'https://monitoring.agromap.uz/api/push/staging',
        'alert_webhook': 'https://alerts.agromap.uz/api/webhook/staging'
    },
    'production': {
        'host': 'agromap.uz',
        'user': 'deploy',
        'port': 22,
        'app_dir': '/var/www/agromap-production',
        'venv_dir': '/var/www/agromap-production/venv',
        'db_name': 'agromap_production',
        'db_user': 'agromap_admin',
        'ssl_cert': '/etc/letsencrypt/live/agromap.uz/fullchain.pem',
        'ssl_key': '/etc/letsencrypt/live/agromap.uz/privkey.pem',
        'monitoring_url': 'https://monitoring.agromap.uz/api/push/production',
        'alert_webhook': 'https://alerts.agromap.uz/api/webhook/production'
    }
}

def run_command(command, cwd=None, env=None):
    """Run a shell command and log the output."""
    logger.info(f"Running command: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info(f"Command output: {result.stdout}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"Error output: {e.stderr}")
        return False, e.stderr

def deploy_staging(config):
    """Deploy to staging environment."""
    logger.info("Starting staging deployment")
    
    # 1. Set up environment
    logger.info("Setting up staging environment")
    ssh_cmd = f"ssh -p {config['port']} {config['user']}@{config['host']}"
    
    # Create directory structure if it doesn't exist
    run_command(f"{ssh_cmd} 'mkdir -p {config['app_dir']}'")
    
    # 2. Deploy code
    logger.info("Deploying code to staging")
    run_command(f"rsync -avz --exclude 'venv' --exclude '*.pyc' --exclude '__pycache__' -e 'ssh -p {config['port']}' . {config['user']}@{config['host']}:{config['app_dir']}")
    
    # 3. Set up virtual environment
    logger.info("Setting up virtual environment")
    run_command(f"{ssh_cmd} 'python3 -m venv {config['venv_dir']} || true'")
    run_command(f"{ssh_cmd} '{config['venv_dir']}/bin/pip install --upgrade pip'")
    run_command(f"{ssh_cmd} '{config['venv_dir']}/bin/pip install -r {config['app_dir']}/requirements.txt'")
    
    # 4. Database migration
    logger.info("Running database migrations")
    run_command(f"{ssh_cmd} 'cd {config['app_dir']} && {config['venv_dir']}/bin/flask db upgrade'")
    
    # 5. SSL configuration
    logger.info("Checking SSL configuration")
    ssl_check = run_command(f"{ssh_cmd} 'test -f {config['ssl_cert']} && test -f {config['ssl_key']} && echo \"SSL certificates exist\"'")
    if not ssl_check[0]:
        logger.warning("SSL certificates not found, generating new ones")
        run_command(f"{ssh_cmd} 'certbot certonly --standalone -d {config['host']} --agree-tos --email admin@agromap.uz'")
    
    # 6. Configure Nginx
    logger.info("Configuring Nginx")
    nginx_config = f"""
server {{
    listen 80;
    server_name {config['host']};
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl;
    server_name {config['host']};
    
    ssl_certificate {config['ssl_cert']};
    ssl_certificate_key {config['ssl_key']};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {{
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    location /static/ {{
        alias {config['app_dir']}/app/static/;
        expires 30d;
    }}
}}
"""
    run_command(f"{ssh_cmd} 'echo \"{nginx_config}\" > /etc/nginx/sites-available/{config['host']}'")
    run_command(f"{ssh_cmd} 'ln -sf /etc/nginx/sites-available/{config['host']} /etc/nginx/sites-enabled/'")
    run_command(f"{ssh_cmd} 'nginx -t && systemctl reload nginx'")
    
    # 7. Configure Gunicorn
    logger.info("Configuring Gunicorn")
    gunicorn_service = f"""
[Unit]
Description=Gunicorn instance to serve AgroMap Staging
After=network.target

[Service]
User={config['user']}
Group=www-data
WorkingDirectory={config['app_dir']}
Environment="PATH={config['venv_dir']}/bin"
Environment="FLASK_ENV=staging"
ExecStart={config['venv_dir']}/bin/gunicorn --workers 4 --bind 127.0.0.1:8000 run:app
Restart=always

[Install]
WantedBy=multi-user.target
"""
    run_command(f"{ssh_cmd} 'echo \"{gunicorn_service}\" > /etc/systemd/system/agromap-staging.service'")
    run_command(f"{ssh_cmd} 'systemctl daemon-reload && systemctl enable agromap-staging.service && systemctl restart agromap-staging.service'")
    
    # 8. Set up monitoring
    logger.info("Setting up monitoring")
    run_command(f"{ssh_cmd} 'apt-get update && apt-get install -y prometheus-node-exporter'")
    
    # 9. Set up backup verification
    logger.info("Setting up backup verification")
    backup_script = f"""
#!/bin/bash
BACKUP_DIR={config['app_dir']}/backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U {config['db_user']} {config['db_name']} > $BACKUP_DIR/db_$TIMESTAMP.sql

# Verify backup
if [ -s $BACKUP_DIR/db_$TIMESTAMP.sql ]; then
    echo "Backup successful: $BACKUP_DIR/db_$TIMESTAMP.sql"
    # Keep only the 5 most recent backups
    ls -t $BACKUP_DIR/db_*.sql | tail -n +6 | xargs rm -f
    # Send success notification
    curl -X POST {config['alert_webhook']} -H "Content-Type: application/json" -d '{{"message": "Backup successful", "level": "info"}}'
else
    echo "Backup failed"
    # Send failure notification
    curl -X POST {config['alert_webhook']} -H "Content-Type: application/json" -d '{{"message": "Backup failed", "level": "error"}}'
fi
"""
    run_command(f"{ssh_cmd} 'echo \"{backup_script}\" > {config['app_dir']}/backup.sh && chmod +x {config['app_dir']}/backup.sh'")
    run_command(f"{ssh_cmd} '(crontab -l 2>/dev/null; echo \"0 2 * * * {config['app_dir']}/backup.sh\") | crontab -'")
    
    # 10. Final testing
    logger.info("Running final tests")
    run_command(f"{ssh_cmd} 'cd {config['app_dir']} && {config['venv_dir']}/bin/python run_tests.py'")
    
    # 11. Verify deployment
    logger.info("Verifying deployment")
    health_check = requests.get(f"https://{config['host']}/api/health")
    if health_check.status_code == 200:
        logger.info("Deployment successful!")
        # Send success notification
        requests.post(
            config['alert_webhook'],
            json={"message": "Staging deployment successful", "level": "info"}
        )
        return True
    else:
        logger.error(f"Deployment verification failed with status code {health_check.status_code}")
        # Send failure notification
        requests.post(
            config['alert_webhook'],
            json={"message": "Staging deployment failed", "level": "error"}
        )
        return False

def deploy_production(config):
    """Deploy to production environment."""
    logger.info("Starting production deployment")
    
    # Similar to staging deployment but with production-specific settings
    # The main difference is that we run more thorough testing before deployment
    
    # 1. Run comprehensive tests first
    logger.info("Running comprehensive tests before production deployment")
    success, _ = run_command("python run_tests.py")
    if not success:
        logger.error("Tests failed, aborting production deployment")
        return False
    
    # 2. Set up environment
    logger.info("Setting up production environment")
    ssh_cmd = f"ssh -p {config['port']} {config['user']}@{config['host']}"
    
    # Create directory structure if it doesn't exist
    run_command(f"{ssh_cmd} 'mkdir -p {config['app_dir']}'")
    
    # 3. Deploy code
    logger.info("Deploying code to production")
    run_command(f"rsync -avz --exclude 'venv' --exclude '*.pyc' --exclude '__pycache__' -e 'ssh -p {config['port']}' . {config['user']}@{config['host']}:{config['app_dir']}")
    
    # 4. Set up virtual environment
    logger.info("Setting up virtual environment")
    run_command(f"{ssh_cmd} 'python3 -m venv {config['venv_dir']} || true'")
    run_command(f"{ssh_cmd} '{config['venv_dir']}/bin/pip install --upgrade pip'")
    run_command(f"{ssh_cmd} '{config['venv_dir']}/bin/pip install -r {config['app_dir']}/requirements.txt'")
    
    # 5. Database migration
    logger.info("Running database migrations")
    # Backup database before migration
    run_command(f"{ssh_cmd} 'pg_dump -U {config['db_user']} {config['db_name']} > {config['app_dir']}/backups/pre_deploy_$(date +%Y%m%d_%H%M%S).sql'")
    run_command(f"{ssh_cmd} 'cd {config['app_dir']} && {config['venv_dir']}/bin/flask db upgrade'")
    
    # 6. SSL configuration
    logger.info("Checking SSL configuration")
    ssl_check = run_command(f"{ssh_cmd} 'test -f {config['ssl_cert']} && test -f {config['ssl_key']} && echo \"SSL certificates exist\"'")
    if not ssl_check[0]:
        logger.warning("SSL certificates not found, generating new ones")
        run_command(f"{ssh_cmd} 'certbot certonly --standalone -d {config['host']} --agree-tos --email admin@agromap.uz'")
    
    # 7. Configure Nginx
    logger.info("Configuring Nginx")
    nginx_config = f"""
server {{
    listen 80;
    server_name {config['host']};
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl;
    server_name {config['host']};
    
    ssl_certificate {config['ssl_cert']};
    ssl_certificate_key {config['ssl_key']};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {{
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    location /static/ {{
        alias {config['app_dir']}/app/static/;
        expires 30d;
    }}
}}
"""
    run_command(f"{ssh_cmd} 'echo \"{nginx_config}\" > /etc/nginx/sites-available/{config['host']}'")
    run_command(f"{ssh_cmd} 'ln -sf /etc/nginx/sites-available/{config['host']} /etc/nginx/sites-enabled/'")
    run_command(f"{ssh_cmd} 'nginx -t && systemctl reload nginx'")
    
    # 8. Configure Gunicorn
    logger.info("Configuring Gunicorn")
    gunicorn_service = f"""
[Unit]
Description=Gunicorn instance to serve AgroMap Production
After=network.target

[Service]
User={config['user']}
Group=www-data
WorkingDirectory={config['app_dir']}
Environment="PATH={config['venv_dir']}/bin"
Environment="FLASK_ENV=production"
ExecStart={config['venv_dir']}/bin/gunicorn --workers 8 --bind 127.0.0.1:8000 run:app
Restart=always

[Install]
WantedBy=multi-user.target
"""
    run_command(f"{ssh_cmd} 'echo \"{gunicorn_service}\" > /etc/systemd/system/agromap-production.service'")
    run_command(f"{ssh_cmd} 'systemctl daemon-reload && systemctl enable agromap-production.service && systemctl restart agromap-production.service'")
    
    # 9. Set up monitoring
    logger.info("Setting up monitoring")
    run_command(f"{ssh_cmd} 'apt-get update && apt-get install -y prometheus-node-exporter'")
    
    # 10. Set up backup verification
    logger.info("Setting up backup verification")
    backup_script = f"""
#!/bin/bash
BACKUP_DIR={config['app_dir']}/backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U {config['db_user']} {config['db_name']} > $BACKUP_DIR/db_$TIMESTAMP.sql

# Verify backup
if [ -s $BACKUP_DIR/db_$TIMESTAMP.sql ]; then
    echo "Backup successful: $BACKUP_DIR/db_$TIMESTAMP.sql"
    # Keep only the 10 most recent backups
    ls -t $BACKUP_DIR/db_*.sql | tail -n +11 | xargs rm -f
    # Send success notification
    curl -X POST {config['alert_webhook']} -H "Content-Type: application/json" -d '{{"message": "Backup successful", "level": "info"}}'
else
    echo "Backup failed"
    # Send failure notification
    curl -X POST {config['alert_webhook']} -H "Content-Type: application/json" -d '{{"message": "Backup failed", "level": "error"}}'
fi
"""
    run_command(f"{ssh_cmd} 'echo \"{backup_script}\" > {config['app_dir']}/backup.sh && chmod +x {config['app_dir']}/backup.sh'")
    run_command(f"{ssh_cmd} '(crontab -l 2>/dev/null; echo \"0 2 * * * {config['app_dir']}/backup.sh\") | crontab -'")
    
    # 11. Final testing
    logger.info("Running final tests")
    run_command(f"{ssh_cmd} 'cd {config['app_dir']} && {config['venv_dir']}/bin/python run_tests.py'")
    
    # 12. Verify deployment
    logger.info("Verifying deployment")
    health_check = requests.get(f"https://{config['host']}/api/health")
    if health_check.status_code == 200:
        logger.info("Deployment successful!")
        # Send success notification
        requests.post(
            config['alert_webhook'],
            json={"message": "Production deployment successful", "level": "info"}
        )
        return True
    else:
        logger.error(f"Deployment verification failed with status code {health_check.status_code}")
        # Send failure notification
        requests.post(
            config['alert_webhook'],
            json={"message": "Production deployment failed", "level": "error"}
        )
        return False

def main():
    """Main function to handle deployment."""
    parser = argparse.ArgumentParser(description='Deploy AgroMap Uzbekistan')
    parser.add_argument('environment', choices=['staging', 'production'], help='Deployment environment')
    parser.add_argument('--config', help='Path to configuration file')
    args = parser.parse_args()
    
    # Load configuration
    config = DEFAULT_CONFIG.copy()
    if args.config:
        try:
            with open(args.config, 'r') as f:
                custom_config = json.load(f)
                config.update(custom_config)
        except Exception as e:
            logger.error(f"Error loading configuration file: {e}")
            return 1
    
    # Deploy to the specified environment
    if args.environment == 'staging':
        success = deploy_staging(config['staging'])
    else:
        success = deploy_production(config['production'])
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())