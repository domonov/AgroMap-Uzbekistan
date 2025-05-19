# AgroMap Maintenance Documentation

## Introduction

This document provides comprehensive guidance for maintaining the AgroMap application. It covers routine maintenance tasks, troubleshooting procedures, performance optimization, and best practices for ensuring the system remains secure, stable, and efficient.

## Routine Maintenance Tasks

### Daily Tasks

#### 1. Monitor System Health

- Check server resource usage (CPU, memory, disk space)
- Review application logs for errors
- Verify database connectivity
- Ensure all services are running

```bash
# Check disk space
df -h

# Check memory usage
free -m

# Check CPU usage
top -n 1

# Check application logs
tail -n 100 /path/to/agromap/logs/agromap.log

# Check service status
sudo systemctl status agromap
sudo systemctl status nginx
sudo systemctl status postgresql
```

#### 2. Review Error Reports

- Check Sentry dashboard for new errors
- Review application logs for warnings and errors
- Address critical issues immediately

#### 3. Verify Backup Completion

- Confirm that daily backups completed successfully
- Check backup logs for errors
- Verify backup file integrity

```bash
# Check backup logs
tail -n 50 /path/to/agromap/logs/backup.log

# List recent backups
ls -lah /path/to/backups/
```

### Weekly Tasks

#### 1. Database Maintenance

- Run database vacuum and analyze operations
- Check for slow queries
- Optimize indexes if needed

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Run vacuum analyze
VACUUM ANALYZE;

# Check for slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

# Exit PostgreSQL
\q
```

#### 2. Security Checks

- Review authentication logs for suspicious activity
- Check for failed login attempts
- Verify firewall rules
- Scan for vulnerabilities

```bash
# Check authentication logs
grep "Failed password" /var/log/auth.log

# Check firewall status
sudo ufw status

# Run security scan (if installed)
sudo lynis audit system
```

#### 3. Update Dependencies

- Check for security updates
- Apply critical patches
- Update Python dependencies if needed

```bash
# Update system packages
sudo apt update
sudo apt list --upgradable
sudo apt upgrade -y

# Update Python dependencies
cd /path/to/agromap
source venv/bin/activate
pip list --outdated
pip install --upgrade <package-name>  # For specific packages with security updates
```

### Monthly Tasks

#### 1. Full System Backup

- Perform a complete system backup
- Back up application code, configuration, and data
- Store backups offsite

```bash
# Run full backup script
/path/to/agromap/scripts/full_backup.sh
```

#### 2. Performance Review

- Analyze application performance metrics
- Review database query performance
- Identify optimization opportunities
- Check cache hit rates

#### 3. Storage Cleanup

- Remove old log files
- Clean up temporary files
- Archive old data if necessary
- Check for large files consuming disk space

```bash
# Find large files
sudo find / -type f -size +100M -exec ls -lh {} \;

# Clean up old logs
sudo find /var/log -name "*.gz" -mtime +30 -delete

# Clean up application logs
find /path/to/agromap/logs -name "*.log.*" -mtime +30 -delete
```

#### 4. SSL Certificate Check

- Verify SSL certificate expiration dates
- Renew certificates if needed (typically done automatically with Let's Encrypt)

```bash
# Check SSL certificate expiration
openssl x509 -enddate -noout -in /etc/letsencrypt/live/yourdomain.com/cert.pem
```

### Quarterly Tasks

#### 1. Comprehensive Security Audit

- Conduct a thorough security assessment
- Review user access and permissions
- Check for unused accounts
- Update security policies

#### 2. Database Optimization

- Review and optimize database schema
- Check for unused indexes
- Analyze query patterns
- Consider partitioning large tables

```bash
# Connect to PostgreSQL
sudo -u postgres psql -d agromap

# Find unused indexes
SELECT s.schemaname,
       s.relname AS tablename,
       s.indexrelname AS indexname,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size,
       s.idx_scan AS index_scans
FROM pg_catalog.pg_stat_user_indexes s
JOIN pg_catalog.pg_index i ON s.indexrelid = i.indexrelid
WHERE s.idx_scan = 0      -- has never been scanned
  AND 0 <>ALL (i.indkey)  -- no index column is an expression
  AND i.indisunique IS FALSE; -- is not a UNIQUE index
```

#### 3. Test Disaster Recovery

- Simulate failure scenarios
- Test backup restoration
- Verify high availability configurations
- Document recovery procedures

#### 4. Update Documentation

- Review and update maintenance documentation
- Update runbooks with new procedures
- Document system changes

## Monitoring

### Key Metrics to Monitor

#### System Metrics

- CPU usage (should be below 70% on average)
- Memory usage (should be below 80% of total RAM)
- Disk space (maintain at least 20% free space)
- Network traffic
- I/O operations

#### Application Metrics

- Request response time (should be under 500ms for most endpoints)
- Error rate (should be below 1% of total requests)
- Active users
- Session duration
- API usage

#### Database Metrics

- Query performance
- Connection count
- Cache hit ratio (aim for >90%)
- Index usage
- Table size growth

### Monitoring Tools

1. **System Monitoring**
   - Prometheus + Grafana
   - Nagios
   - Zabbix

2. **Application Monitoring**
   - Sentry (for error tracking)
   - New Relic
   - Datadog

3. **Database Monitoring**
   - pgAdmin
   - pg_stat_statements
   - pgBadger

### Setting Up Alerts

Configure alerts for the following conditions:

- CPU usage exceeds 80% for more than 5 minutes
- Memory usage exceeds 90%
- Disk space falls below 10% free
- Application error rate exceeds 5%
- Database connection count approaches maximum
- Backup failure
- SSL certificate approaching expiration (30 days warning)

## Troubleshooting

### Common Issues and Solutions

#### Application Not Starting

**Symptoms:**
- Service fails to start
- 502 Bad Gateway error in browser

**Troubleshooting Steps:**
1. Check application logs:
   ```bash
   sudo journalctl -u agromap.service -n 100
   ```

2. Verify environment variables:
   ```bash
   cat /path/to/agromap/.env
   ```

3. Check for port conflicts:
   ```bash
   sudo netstat -tulpn | grep 5000
   ```

4. Verify Python dependencies:
   ```bash
   cd /path/to/agromap
   source venv/bin/activate
   pip list
   ```

**Solutions:**
- Fix configuration errors in .env file
- Restart the service: `sudo systemctl restart agromap`
- Reinstall dependencies: `pip install -r requirements.txt`
- Check for file permission issues

#### Database Connection Issues

**Symptoms:**
- "Could not connect to database" errors
- Slow application performance
- Timeout errors

**Troubleshooting Steps:**
1. Check database service status:
   ```bash
   sudo systemctl status postgresql
   ```

2. Verify database connection settings:
   ```bash
   cat /path/to/agromap/.env | grep DATABASE_URL
   ```

3. Test direct database connection:
   ```bash
   psql -U agromapuser -h localhost -d agromap
   ```

4. Check database logs:
   ```bash
   sudo tail -n 100 /var/log/postgresql/postgresql-14-main.log
   ```

**Solutions:**
- Restart PostgreSQL: `sudo systemctl restart postgresql`
- Check firewall rules for database port
- Verify database credentials
- Increase connection timeout settings

#### High CPU or Memory Usage

**Symptoms:**
- Slow application performance
- Server unresponsive
- Out of memory errors

**Troubleshooting Steps:**
1. Identify resource-intensive processes:
   ```bash
   top -c
   ```

2. Check for memory leaks:
   ```bash
   ps aux --sort=-%mem | head -10
   ```

3. Analyze application logs for long-running operations

**Solutions:**
- Restart the application
- Optimize database queries
- Increase server resources
- Implement caching for expensive operations
- Configure resource limits

#### Slow API Responses

**Symptoms:**
- API requests take longer than 1 second
- Timeout errors
- User complaints about performance

**Troubleshooting Steps:**
1. Check application logs for slow queries
2. Monitor database performance
3. Test API endpoints directly:
   ```bash
   curl -v -H "Authorization: Bearer YOUR_TOKEN" https://api.yourdomain.com/endpoint
   ```

**Solutions:**
- Optimize database queries
- Add indexes to frequently queried fields
- Implement caching
- Consider horizontal scaling

## Performance Optimization

### Database Optimization

#### Query Optimization

1. Identify slow queries:
   ```sql
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY total_time DESC
   LIMIT 20;
   ```

2. Add appropriate indexes:
   ```sql
   CREATE INDEX idx_field_name ON table_name(column_name);
   ```

3. Optimize JOIN operations:
   - Ensure proper indexes on JOIN columns
   - Consider denormalizing frequently joined data

4. Use connection pooling:
   - Configure appropriate pool size in app/__init__.py
   - Monitor connection usage

#### Database Maintenance

1. Regular VACUUM and ANALYZE:
   ```sql
   VACUUM ANALYZE;
   ```

2. Update statistics:
   ```sql
   ANALYZE table_name;
   ```

3. Reindex when necessary:
   ```sql
   REINDEX TABLE table_name;
   ```

### Application Optimization

#### Caching Strategies

1. Implement Redis caching for:
   - API responses
   - Database query results
   - Session data
   - Rendered templates

2. Configure cache timeouts appropriately:
   - Short-lived for frequently changing data (1-5 minutes)
   - Longer for static data (1 hour to 1 day)

3. Use cache warming for common queries

#### Code Optimization

1. Profile application code:
   ```python
   from werkzeug.middleware.profiler import ProfilerMiddleware
   app.wsgi_app = ProfilerMiddleware(app.wsgi_app, profile_dir='./profiles')
   ```

2. Optimize expensive operations:
   - Use async processing for long-running tasks
   - Implement pagination for large data sets
   - Use efficient algorithms

3. Minimize database queries:
   - Use eager loading with SQLAlchemy
   - Batch operations when possible

### Server Optimization

1. Configure Gunicorn workers:
   - Rule of thumb: (2 × CPU cores) + 1
   - Example for 4 cores: 9 workers

2. Optimize Nginx:
   - Enable gzip compression
   - Configure worker connections
   - Set up proper buffer sizes

3. Implement CDN for static assets:
   - Configure CloudFront or similar CDN
   - Set appropriate cache headers

## Backup and Recovery

### Backup Strategy

#### Database Backups

1. Daily full backups:
   ```bash
   pg_dump -U agromapuser -d agromap -F c -f /path/to/backups/agromap_$(date +%Y%m%d).dump
   ```

2. Hourly incremental backups (WAL archiving):
   - Configure PostgreSQL for WAL archiving
   - Set up continuous archiving

3. Backup verification:
   ```bash
   pg_restore -l /path/to/backups/agromap_20230101.dump
   ```

#### File Backups

1. Back up application code:
   ```bash
   tar -czf /path/to/backups/agromap_code_$(date +%Y%m%d).tar.gz /path/to/agromap
   ```

2. Back up user uploads and static files:
   ```bash
   tar -czf /path/to/backups/agromap_uploads_$(date +%Y%m%d).tar.gz /path/to/agromap/app/static/uploads
   ```

3. Back up configuration files:
   ```bash
   tar -czf /path/to/backups/agromap_config_$(date +%Y%m%d).tar.gz /path/to/agromap/.env /etc/nginx/sites-available/agromap /etc/systemd/system/agromap.service
   ```

### Backup Retention

- Keep daily backups for 30 days
- Keep weekly backups for 3 months
- Keep monthly backups for 1 year
- Store offsite backups in secure location

### Recovery Procedures

#### Database Recovery

1. Stop the application:
   ```bash
   sudo systemctl stop agromap
   ```

2. Restore the database:
   ```bash
   pg_restore -U agromapuser -d agromap -c /path/to/backups/agromap_20230101.dump
   ```

3. Start the application:
   ```bash
   sudo systemctl start agromap
   ```

#### Full System Recovery

1. Set up a new server with the same specifications
2. Install required software packages
3. Restore application code from backup
4. Restore configuration files
5. Restore database
6. Restore user uploads and static files
7. Update DNS records if necessary
8. Test the application thoroughly

## Security Maintenance

### Regular Security Tasks

#### User Access Management

1. Review user accounts quarterly:
   ```sql
   SELECT id, email, role, last_login, created_at FROM users ORDER BY last_login DESC;
   ```

2. Remove inactive accounts:
   ```sql
   DELETE FROM users WHERE last_login < NOW() - INTERVAL '1 year';
   ```

3. Audit admin privileges:
   ```sql
   SELECT id, email FROM users WHERE role = 'admin';
   ```

#### Security Updates

1. Keep system packages updated:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. Update Python dependencies:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

3. Apply security patches promptly

#### Security Scanning

1. Run regular vulnerability scans:
   ```bash
   # Using OWASP ZAP (if installed)
   zap-cli quick-scan --self-contained --start-options "-config api.disablekey=true" https://yourdomain.com
   ```

2. Check for common vulnerabilities:
   - SQL injection
   - Cross-site scripting (XSS)
   - Cross-site request forgery (CSRF)
   - Authentication bypasses

### Security Incident Response

1. Isolate affected systems
2. Assess the scope of the breach
3. Contain the incident
4. Eradicate the threat
5. Recover systems
6. Document the incident
7. Implement preventive measures

## System Upgrades

### Minor Version Updates

1. Create a backup before upgrading
2. Update the code:
   ```bash
   cd /path/to/agromap
   git pull origin main
   ```

3. Update dependencies:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. Run database migrations:
   ```bash
   flask db upgrade
   ```

5. Restart the application:
   ```bash
   sudo systemctl restart agromap
   ```

6. Test the application

### Major Version Updates

1. Create a full backup
2. Set up a staging environment
3. Deploy the new version to staging
4. Test thoroughly
5. Plan for downtime
6. Communicate with users
7. Perform the upgrade during low-traffic periods
8. Have a rollback plan ready

## Documentation Maintenance

### Keeping Documentation Updated

1. Review documentation quarterly
2. Update after significant changes
3. Document new features and procedures
4. Maintain a changelog

### Documentation Best Practices

1. Use clear, concise language
2. Include examples and code snippets
3. Add troubleshooting sections
4. Keep configuration examples up to date
5. Document dependencies and versions

## Appendix

### Maintenance Checklist

#### Daily Checklist
- [ ] Check system health
- [ ] Review error reports
- [ ] Verify backup completion
- [ ] Monitor disk space
- [ ] Check application logs

#### Weekly Checklist
- [ ] Run database maintenance
- [ ] Check for security updates
- [ ] Review authentication logs
- [ ] Update dependencies if needed
- [ ] Check SSL certificate status

#### Monthly Checklist
- [ ] Perform full system backup
- [ ] Clean up storage
- [ ] Review performance metrics
- [ ] Optimize database if needed
- [ ] Update documentation

#### Quarterly Checklist
- [ ] Conduct security audit
- [ ] Test disaster recovery
- [ ] Review user accounts
- [ ] Optimize application code
- [ ] Update maintenance procedures

### Useful Scripts

#### Backup Script

```bash
#!/bin/bash
# backup.sh - Database and file backup script

# Configuration
BACKUP_DIR="/path/to/backups"
APP_DIR="/path/to/agromap"
DB_NAME="agromap"
DB_USER="agromapuser"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Database backup
echo "Starting database backup..."
pg_dump -U $DB_USER -d $DB_NAME -F c -f $BACKUP_DIR/db_${DB_NAME}_${TIMESTAMP}.dump
if [ $? -eq 0 ]; then
    echo "Database backup completed successfully."
else
    echo "Database backup failed!"
    exit 1
fi

# File backup
echo "Starting file backup..."
tar -czf $BACKUP_DIR/files_${TIMESTAMP}.tar.gz $APP_DIR/app/static/uploads $APP_DIR/instance
if [ $? -eq 0 ]; then
    echo "File backup completed successfully."
else
    echo "File backup failed!"
    exit 1
fi

# Clean up old backups (keep last 30 days)
find $BACKUP_DIR -name "db_*.dump" -mtime +30 -delete
find $BACKUP_DIR -name "files_*.tar.gz" -mtime +30 -delete

echo "Backup process completed at $(date)."
```

#### Log Rotation Script

```bash
#!/bin/bash
# log_rotate.sh - Rotate and compress application logs

# Configuration
LOG_DIR="/path/to/agromap/logs"
MAX_LOGS=10
TIMESTAMP=$(date +%Y%m%d)

# Rotate application log
if [ -f "$LOG_DIR/agromap.log" ]; then
    echo "Rotating application log..."
    mv $LOG_DIR/agromap.log $LOG_DIR/agromap.log.$TIMESTAMP
    touch $LOG_DIR/agromap.log
    gzip $LOG_DIR/agromap.log.$TIMESTAMP
fi

# Keep only MAX_LOGS number of log files
ls -t $LOG_DIR/agromap.log.*.gz | tail -n +$((MAX_LOGS+1)) | xargs -r rm

echo "Log rotation completed at $(date)."
```

#### Health Check Script

```bash
#!/bin/bash
# health_check.sh - System health monitoring script

# Configuration
APP_URL="https://yourdomain.com"
DISK_THRESHOLD=90
MEMORY_THRESHOLD=90
EMAIL="admin@example.com"

# Check disk space
DISK_USAGE=$(df -h / | grep / | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt $DISK_THRESHOLD ]; then
    echo "WARNING: Disk usage is at $DISK_USAGE%" | mail -s "Disk Space Alert" $EMAIL
fi

# Check memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{print $3/$2 * 100.0}' | cut -d. -f1)
if [ $MEMORY_USAGE -gt $MEMORY_THRESHOLD ]; then
    echo "WARNING: Memory usage is at $MEMORY_USAGE%" | mail -s "Memory Usage Alert" $EMAIL
fi

# Check if application is responding
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $APP_URL)
if [ $HTTP_STATUS -ne 200 ]; then
    echo "WARNING: Application returned HTTP status $HTTP_STATUS" | mail -s "Application Alert" $EMAIL
fi

# Check database connection
sudo -u postgres psql -d agromap -c "SELECT 1" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "WARNING: Cannot connect to database" | mail -s "Database Alert" $EMAIL
fi

echo "Health check completed at $(date)."
```

### Contact Information

- **Technical Support**: support@agromap-uzbekistan.org
- **Emergency Contact**: +998 71 123 4567
- **Development Team**: dev@agromap-uzbekistan.org
- **System Administrator**: sysadmin@agromap-uzbekistan.org