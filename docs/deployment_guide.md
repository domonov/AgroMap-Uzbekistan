# AgroMap Deployment Guide

## Introduction

This guide provides detailed instructions for deploying the AgroMap application in various environments. Follow these steps to set up a production-ready instance of the application.

## System Requirements

### Minimum Requirements

- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB SSD
- **Operating System**: Ubuntu 20.04 LTS or newer
- **Database**: PostgreSQL 12+
- **Python**: 3.9+

### Recommended Requirements

- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 50GB+ SSD
- **Operating System**: Ubuntu 22.04 LTS
- **Database**: PostgreSQL 14+
- **Python**: 3.11+

## Deployment Options

AgroMap can be deployed using several methods:

1. **Traditional Server Deployment**: Manual setup on a Linux server
2. **Docker Deployment**: Using containerization
3. **Cloud Platform Deployment**: AWS, Azure, or Google Cloud

This guide covers all three approaches.

## Prerequisites

Before deployment, ensure you have:

- Domain name configured with DNS records
- SSL certificate (Let's Encrypt or commercial)
- Database credentials
- SMTP server for email notifications
- API keys for external services (weather, maps, etc.)
- Backup storage location

## Traditional Server Deployment

### 1. Server Preparation

Update the system and install required packages:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3-pip python3-dev build-essential libssl-dev libffi-dev python3-venv postgresql postgresql-contrib nginx git
```

### 2. Create a PostgreSQL Database

```bash
sudo -u postgres psql

postgres=# CREATE DATABASE agromap;
postgres=# CREATE USER agromapuser WITH PASSWORD 'secure_password';
postgres=# ALTER ROLE agromapuser SET client_encoding TO 'utf8';
postgres=# ALTER ROLE agromapuser SET default_transaction_isolation TO 'read committed';
postgres=# ALTER ROLE agromapuser SET timezone TO 'UTC';
postgres=# GRANT ALL PRIVILEGES ON DATABASE agromap TO agromapuser;
postgres=# \q
```

### 3. Clone the Repository

```bash
git clone https://github.com/yourusername/agromap-uzbekistan.git
cd agromap-uzbekistan
```

### 4. Set Up Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```
FLASK_APP=run.py
FLASK_ENV=production
SECRET_KEY=your_secure_secret_key
DATABASE_URL=postgresql://agromapuser:secure_password@localhost/agromap
SENTRY_DSN=your_sentry_dsn
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@example.com
MAIL_PASSWORD=your_email_password
WEATHER_API_KEY=your_weather_api_key
```

### 6. Initialize the Database

```bash
flask db upgrade
```

### 7. Configure Gunicorn

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/agromap.service
```

Add the following content:

```
[Unit]
Description=AgroMap Gunicorn Service
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/path/to/agromap-uzbekistan
Environment="PATH=/path/to/agromap-uzbekistan/venv/bin"
ExecStart=/path/to/agromap-uzbekistan/venv/bin/gunicorn --workers 4 --bind unix:agromap.sock -m 007 run:app

[Install]
WantedBy=multi-user.target
```

Start and enable the service:

```bash
sudo systemctl start agromap
sudo systemctl enable agromap
```

### 8. Configure Nginx

Create an Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/agromap
```

Add the following content:

```
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        include proxy_params;
        proxy_pass http://unix:/path/to/agromap-uzbekistan/agromap.sock;
    }

    location /static/ {
        alias /path/to/agromap-uzbekistan/app/static/;
    }
}
```

Enable the site and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/agromap /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

### 9. Set Up SSL with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 10. Set Up Scheduled Tasks

Create a cron job for regular tasks:

```bash
sudo crontab -e
```

Add the following lines:

```
# Daily database backup at 2 AM
0 2 * * * /path/to/agromap-uzbekistan/venv/bin/python /path/to/agromap-uzbekistan/app/utils/backup.py

# Refresh cache every 6 hours
0 */6 * * * /path/to/agromap-uzbekistan/venv/bin/flask cache-refresh
```

## Docker Deployment

### 1. Install Docker and Docker Compose

```bash
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt update
sudo apt install -y docker-ce docker-compose
sudo usermod -aG docker ${USER}
```

Log out and log back in for the group changes to take effect.

### 2. Create Docker Compose Configuration

Create a `docker-compose.yml` file:

```yaml
version: '3'

services:
  web:
    build: .
    restart: always
    depends_on:
      - db
      - redis
    environment:
      - FLASK_APP=run.py
      - FLASK_ENV=production
      - SECRET_KEY=your_secure_secret_key
      - DATABASE_URL=postgresql://agromapuser:secure_password@db/agromap
      - REDIS_URL=redis://redis:6379/0
      - SENTRY_DSN=your_sentry_dsn
      - MAIL_SERVER=smtp.example.com
      - MAIL_PORT=587
      - MAIL_USE_TLS=True
      - MAIL_USERNAME=your_email@example.com
      - MAIL_PASSWORD=your_email_password
      - WEATHER_API_KEY=your_weather_api_key
    volumes:
      - ./app/static:/app/app/static
      - ./instance:/app/instance
    networks:
      - agromap-network

  db:
    image: postgres:14
    restart: always
    environment:
      - POSTGRES_USER=agromapuser
      - POSTGRES_PASSWORD=secure_password
      - POSTGRES_DB=agromap
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - agromap-network

  redis:
    image: redis:6
    restart: always
    volumes:
      - redis_data:/data
    networks:
      - agromap-network

  nginx:
    image: nginx:latest
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./nginx/ssl:/etc/nginx/ssl
      - ./app/static:/app/static
    depends_on:
      - web
    networks:
      - agromap-network

networks:
  agromap-network:

volumes:
  postgres_data:
  redis_data:
```

### 3. Create a Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

COPY . .

RUN mkdir -p instance

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "run:app"]
```

### 4. Create Nginx Configuration

Create a directory for Nginx configuration:

```bash
mkdir -p nginx/conf.d
```

Create `nginx/conf.d/default.conf`:

```
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://web:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /app/static/;
    }
}
```

### 5. Start the Docker Containers

```bash
docker-compose up -d
```

### 6. Initialize the Database

```bash
docker-compose exec web flask db upgrade
```

### 7. Set Up SSL with Let's Encrypt

Install Certbot on the host machine:

```bash
sudo apt install -y certbot
```

Obtain certificates:

```bash
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
```

Copy certificates to Nginx directory:

```bash
mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/
```

Update Nginx configuration to use SSL:

```
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://web:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /app/static/;
    }
}
```

Restart Nginx container:

```bash
docker-compose restart nginx
```

## Cloud Platform Deployment

### AWS Deployment

#### 1. Set Up an EC2 Instance

1. Launch an Ubuntu 22.04 LTS EC2 instance (t3.medium or larger recommended)
2. Configure security groups to allow HTTP (80), HTTPS (443), and SSH (22)
3. Allocate and associate an Elastic IP
4. Connect to the instance via SSH

#### 2. Install Dependencies

Follow the steps in the Traditional Server Deployment section to install dependencies.

#### 3. Set Up RDS for PostgreSQL

1. Create a PostgreSQL RDS instance
2. Configure security groups to allow connections from your EC2 instance
3. Update your `.env` file with the RDS connection details

#### 4. Set Up S3 for Static Files and Backups

1. Create an S3 bucket for static files
2. Create an S3 bucket for backups
3. Configure IAM roles and policies
4. Update your application configuration to use S3

#### 5. Set Up CloudFront (Optional)

1. Create a CloudFront distribution pointing to your S3 bucket
2. Configure your application to use CloudFront URLs for static assets

#### 6. Set Up Route 53

1. Configure your domain in Route 53
2. Create A records pointing to your EC2 instance or CloudFront distribution

### Azure Deployment

#### 1. Set Up an Azure VM

1. Create an Ubuntu 22.04 LTS VM (Standard_B2s or larger recommended)
2. Configure network security groups to allow HTTP (80), HTTPS (443), and SSH (22)
3. Allocate a static IP address
4. Connect to the VM via SSH

#### 2. Install Dependencies

Follow the steps in the Traditional Server Deployment section to install dependencies.

#### 3. Set Up Azure Database for PostgreSQL

1. Create an Azure Database for PostgreSQL instance
2. Configure firewall rules to allow connections from your VM
3. Update your `.env` file with the database connection details

#### 4. Set Up Azure Blob Storage

1. Create a storage account
2. Create containers for static files and backups
3. Generate SAS tokens or use managed identities
4. Update your application configuration to use Azure Blob Storage

#### 5. Set Up Azure CDN (Optional)

1. Create an Azure CDN profile and endpoint pointing to your blob storage
2. Configure your application to use CDN URLs for static assets

#### 6. Set Up Azure DNS

1. Configure your domain in Azure DNS
2. Create A records pointing to your VM or CDN endpoint

## Post-Deployment Steps

### 1. Verify Deployment

1. Visit your domain in a web browser
2. Verify that all pages load correctly
3. Test user registration and login
4. Test core functionality

### 2. Set Up Monitoring

1. Configure Sentry for error tracking
2. Set up server monitoring (CPU, memory, disk usage)
3. Set up database monitoring
4. Configure alerts for critical issues

### 3. Set Up Backups

1. Verify that database backups are working
2. Set up file system backups
3. Test backup restoration process

### 4. Security Hardening

1. Run a security scan
2. Update firewall rules
3. Configure fail2ban to prevent brute force attacks
4. Set up regular security updates

### 5. Performance Optimization

1. Enable caching
2. Optimize database queries
3. Configure CDN for static assets
4. Set up load balancing if needed

## Troubleshooting

### Common Issues

#### Application Doesn't Start

1. Check logs: `sudo journalctl -u agromap.service`
2. Verify environment variables
3. Check database connection
4. Ensure all dependencies are installed

#### Database Connection Issues

1. Verify database credentials
2. Check network connectivity
3. Ensure database server is running
4. Check firewall rules

#### Nginx Configuration Problems

1. Check Nginx error logs: `sudo tail -f /var/log/nginx/error.log`
2. Verify Nginx configuration: `sudo nginx -t`
3. Check permissions on socket file

#### SSL Certificate Issues

1. Verify certificate paths
2. Check certificate expiration dates
3. Ensure proper certificate chain

## Maintenance Procedures

### Regular Updates

1. Update the application code:
   ```bash
   cd /path/to/agromap-uzbekistan
   git pull
   source venv/bin/activate
   pip install -r requirements.txt
   flask db upgrade
   sudo systemctl restart agromap
   ```

2. Update system packages:
   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

### Database Maintenance

1. Run regular vacuum operations:
   ```bash
   sudo -u postgres psql -d agromap -c "VACUUM ANALYZE;"
   ```

2. Monitor database size and performance:
   ```bash
   sudo -u postgres psql -d agromap -c "SELECT pg_size_pretty(pg_database_size('agromap'));"
   ```

### Backup Verification

1. Regularly test backup restoration:
   ```bash
   # Restore database backup
   pg_restore -U agromapuser -d agromap_test /path/to/backup.sql

   # Verify data integrity
   psql -U agromapuser -d agromap_test -c "SELECT COUNT(*) FROM users;"
   ```

## Scaling Considerations

### Vertical Scaling

1. Increase server resources (CPU, RAM)
2. Upgrade database instance
3. Optimize application code

### Horizontal Scaling

1. Set up multiple application servers
2. Configure load balancing
3. Implement database replication
4. Use distributed caching

## Conclusion

This deployment guide covers the essential steps for deploying the AgroMap application in various environments. For additional support or questions, contact the development team.

## Appendix

### Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| FLASK_APP | Flask application entry point | run.py |
| FLASK_ENV | Environment (production/development) | production |
| SECRET_KEY | Secret key for session security | random_string_here |
| DATABASE_URL | Database connection string | postgresql://user:pass@host/db |
| SENTRY_DSN | Sentry error tracking DSN | https://key@sentry.io/project |
| MAIL_SERVER | SMTP server for emails | smtp.gmail.com |
| MAIL_PORT | SMTP port | 587 |
| MAIL_USE_TLS | Use TLS for email | True |
| MAIL_USERNAME | Email username | your_email@example.com |
| MAIL_PASSWORD | Email password | your_password |
| WEATHER_API_KEY | API key for weather service | your_api_key |

### Useful Commands

```bash
# Check application status
sudo systemctl status agromap

# View application logs
sudo journalctl -u agromap.service

# Restart application
sudo systemctl restart agromap

# Check Nginx status
sudo systemctl status nginx

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Check database status
sudo systemctl status postgresql

# Create database backup
pg_dump -U agromapuser -d agromap > backup_$(date +%Y%m%d).sql

# Restore database backup
pg_restore -U agromapuser -d agromap backup.sql
```