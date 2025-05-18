"""Support system utilities for AgroMap."""
import os
import json
import logging
import smtplib
import datetime
from typing import Dict, List, Optional, Any, Union
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, current_app, request, g
import jinja2

# Set up logger
logger = logging.getLogger('support')
handler = logging.FileHandler('logs/support.log')
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class SupportSystem:
    """Support system for handling user issues and requests."""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.support_email = os.environ.get('SUPPORT_EMAIL', 'support@example.com')
        self.admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.example.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_username = os.environ.get('SMTP_USERNAME', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.issues_dir = 'data/support/issues'
        self.requests_dir = 'data/support/requests'
        self.training_dir = 'data/support/training'
        
        # Create directories if they don't exist
        os.makedirs(self.issues_dir, exist_ok=True)
        os.makedirs(self.requests_dir, exist_ok=True)
        os.makedirs(self.training_dir, exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize with Flask app."""
        self.app = app
        
        # Register before_request handler to track user activity
        @app.before_request
        def track_user_activity():
            g.start_time = datetime.datetime.now()
        
        # Register after_request handler to log slow requests
        @app.after_request
        def log_slow_requests(response):
            if hasattr(g, 'start_time'):
                duration = (datetime.datetime.now() - g.start_time).total_seconds()
                if duration > 1.0:  # Log requests taking more than 1 second
                    logger.warning(f"Slow request: {request.path} - {duration:.2f}s")
            return response
        
        # Register error handler for 500 errors
        @app.errorhandler(500)
        def handle_server_error(error):
            # Log the error
            logger.error(f"Server error: {str(error)}")
            
            # Create an error report
            error_id = self.report_error(
                error_type="server_error",
                error_message=str(error),
                traceback=getattr(error, 'traceback', None),
                request_info={
                    'path': request.path,
                    'method': request.method,
                    'user_agent': request.user_agent.string,
                    'remote_addr': request.remote_addr
                }
            )
            
            # Return error page with reference ID
            return f"An error occurred. Reference ID: {error_id}", 500
    
    def submit_bug_report(self, user_id: str, title: str, description: str, 
                         severity: str = 'medium', steps_to_reproduce: str = None,
                         browser: str = None, os: str = None) -> str:
        """Submit a bug report."""
        logger.info(f"Bug report submitted by user {user_id}: {title}")
        
        # Generate a unique ID for the bug report
        bug_id = f"BUG-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create bug report data
        bug_data = {
            'id': bug_id,
            'user_id': user_id,
            'title': title,
            'description': description,
            'severity': severity,
            'steps_to_reproduce': steps_to_reproduce,
            'browser': browser,
            'os': os,
            'status': 'new',
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        # Save bug report to file
        bug_file = os.path.join(self.issues_dir, f"{bug_id}.json")
        with open(bug_file, 'w', encoding='utf-8') as f:
            json.dump(bug_data, f, indent=2)
        
        # Send notification email
        self._send_notification_email(
            subject=f"New Bug Report: {title}",
            body=f"A new bug report has been submitted:\n\n"
                 f"ID: {bug_id}\n"
                 f"User: {user_id}\n"
                 f"Title: {title}\n"
                 f"Description: {description}\n"
                 f"Severity: {severity}\n\n"
                 f"Steps to Reproduce: {steps_to_reproduce or 'Not provided'}\n"
                 f"Browser: {browser or 'Not provided'}\n"
                 f"OS: {os or 'Not provided'}"
        )
        
        return bug_id
    
    def submit_feature_request(self, user_id: str, title: str, description: str,
                              priority: str = 'medium', use_case: str = None) -> str:
        """Submit a feature request."""
        logger.info(f"Feature request submitted by user {user_id}: {title}")
        
        # Generate a unique ID for the feature request
        request_id = f"FR-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create feature request data
        request_data = {
            'id': request_id,
            'user_id': user_id,
            'title': title,
            'description': description,
            'priority': priority,
            'use_case': use_case,
            'status': 'new',
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        # Save feature request to file
        request_file = os.path.join(self.requests_dir, f"{request_id}.json")
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(request_data, f, indent=2)
        
        # Send notification email
        self._send_notification_email(
            subject=f"New Feature Request: {title}",
            body=f"A new feature request has been submitted:\n\n"
                 f"ID: {request_id}\n"
                 f"User: {user_id}\n"
                 f"Title: {title}\n"
                 f"Description: {description}\n"
                 f"Priority: {priority}\n\n"
                 f"Use Case: {use_case or 'Not provided'}"
        )
        
        return request_id
    
    def report_performance_issue(self, user_id: str, description: str, 
                               page: str = None, action: str = None,
                               browser: str = None, os: str = None) -> str:
        """Report a performance issue."""
        logger.info(f"Performance issue reported by user {user_id}: {description}")
        
        # Generate a unique ID for the performance issue
        issue_id = f"PERF-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create performance issue data
        issue_data = {
            'id': issue_id,
            'user_id': user_id,
            'description': description,
            'page': page,
            'action': action,
            'browser': browser,
            'os': os,
            'status': 'new',
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        # Save performance issue to file
        issue_file = os.path.join(self.issues_dir, f"{issue_id}.json")
        with open(issue_file, 'w', encoding='utf-8') as f:
            json.dump(issue_data, f, indent=2)
        
        # Send notification email
        self._send_notification_email(
            subject=f"New Performance Issue Report",
            body=f"A new performance issue has been reported:\n\n"
                 f"ID: {issue_id}\n"
                 f"User: {user_id}\n"
                 f"Description: {description}\n"
                 f"Page: {page or 'Not provided'}\n"
                 f"Action: {action or 'Not provided'}\n"
                 f"Browser: {browser or 'Not provided'}\n"
                 f"OS: {os or 'Not provided'}"
        )
        
        return issue_id
    
    def report_security_issue(self, user_id: str, description: str, 
                            severity: str = 'high', impact: str = None) -> str:
        """Report a security issue."""
        logger.info(f"Security issue reported by user {user_id}")
        
        # Generate a unique ID for the security issue
        issue_id = f"SEC-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create security issue data
        issue_data = {
            'id': issue_id,
            'user_id': user_id,
            'description': description,
            'severity': severity,
            'impact': impact,
            'status': 'new',
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        # Save security issue to file
        issue_file = os.path.join(self.issues_dir, f"{issue_id}.json")
        with open(issue_file, 'w', encoding='utf-8') as f:
            json.dump(issue_data, f, indent=2)
        
        # Send notification email with high priority
        self._send_notification_email(
            subject=f"URGENT: New Security Issue Report",
            body=f"A new security issue has been reported:\n\n"
                 f"ID: {issue_id}\n"
                 f"User: {user_id}\n"
                 f"Description: {description}\n"
                 f"Severity: {severity}\n"
                 f"Impact: {impact or 'Not provided'}",
            priority="high"
        )
        
        return issue_id
    
    def report_data_issue(self, user_id: str, description: str, 
                        data_type: str = None, record_id: str = None) -> str:
        """Report a data issue."""
        logger.info(f"Data issue reported by user {user_id}: {description}")
        
        # Generate a unique ID for the data issue
        issue_id = f"DATA-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create data issue data
        issue_data = {
            'id': issue_id,
            'user_id': user_id,
            'description': description,
            'data_type': data_type,
            'record_id': record_id,
            'status': 'new',
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        # Save data issue to file
        issue_file = os.path.join(self.issues_dir, f"{issue_id}.json")
        with open(issue_file, 'w', encoding='utf-8') as f:
            json.dump(issue_data, f, indent=2)
        
        # Send notification email
        self._send_notification_email(
            subject=f"New Data Issue Report",
            body=f"A new data issue has been reported:\n\n"
                 f"ID: {issue_id}\n"
                 f"User: {user_id}\n"
                 f"Description: {description}\n"
                 f"Data Type: {data_type or 'Not provided'}\n"
                 f"Record ID: {record_id or 'Not provided'}"
        )
        
        return issue_id
    
    def report_access_problem(self, user_id: str, description: str, 
                            resource: str = None, error_message: str = None) -> str:
        """Report an access problem."""
        logger.info(f"Access problem reported by user {user_id}: {description}")
        
        # Generate a unique ID for the access problem
        issue_id = f"ACCESS-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create access problem data
        issue_data = {
            'id': issue_id,
            'user_id': user_id,
            'description': description,
            'resource': resource,
            'error_message': error_message,
            'status': 'new',
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        # Save access problem to file
        issue_file = os.path.join(self.issues_dir, f"{issue_id}.json")
        with open(issue_file, 'w', encoding='utf-8') as f:
            json.dump(issue_data, f, indent=2)
        
        # Send notification email
        self._send_notification_email(
            subject=f"New Access Problem Report",
            body=f"A new access problem has been reported:\n\n"
                 f"ID: {issue_id}\n"
                 f"User: {user_id}\n"
                 f"Description: {description}\n"
                 f"Resource: {resource or 'Not provided'}\n"
                 f"Error Message: {error_message or 'Not provided'}"
        )
        
        return issue_id
    
    def request_training(self, user_id: str, topic: str, description: str,
                       preferred_date: str = None, num_participants: int = 1) -> str:
        """Request training."""
        logger.info(f"Training requested by user {user_id}: {topic}")
        
        # Generate a unique ID for the training request
        request_id = f"TRAIN-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create training request data
        request_data = {
            'id': request_id,
            'user_id': user_id,
            'topic': topic,
            'description': description,
            'preferred_date': preferred_date,
            'num_participants': num_participants,
            'status': 'new',
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        # Save training request to file
        request_file = os.path.join(self.training_dir, f"{request_id}.json")
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(request_data, f, indent=2)
        
        # Send notification email
        self._send_notification_email(
            subject=f"New Training Request: {topic}",
            body=f"A new training request has been submitted:\n\n"
                 f"ID: {request_id}\n"
                 f"User: {user_id}\n"
                 f"Topic: {topic}\n"
                 f"Description: {description}\n"
                 f"Preferred Date: {preferred_date or 'Not provided'}\n"
                 f"Number of Participants: {num_participants}"
        )
        
        return request_id
    
    def report_error(self, error_type: str, error_message: str, 
                   traceback: str = None, request_info: Dict = None) -> str:
        """Report an error (internal use)."""
        logger.error(f"Error reported: {error_type} - {error_message}")
        
        # Generate a unique ID for the error
        error_id = f"ERR-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create error data
        error_data = {
            'id': error_id,
            'type': error_type,
            'message': error_message,
            'traceback': traceback,
            'request_info': request_info,
            'status': 'new',
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        # Save error to file
        error_file = os.path.join(self.issues_dir, f"{error_id}.json")
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(error_data, f, indent=2)
        
        # Send notification email
        self._send_notification_email(
            subject=f"New Error Report: {error_type}",
            body=f"A new error has been reported:\n\n"
                 f"ID: {error_id}\n"
                 f"Type: {error_type}\n"
                 f"Message: {error_message}\n\n"
                 f"Traceback: {traceback or 'Not available'}\n\n"
                 f"Request Info: {json.dumps(request_info, indent=2) if request_info else 'Not available'}"
        )
        
        return error_id
    
    def get_issue(self, issue_id: str) -> Optional[Dict]:
        """Get an issue by ID."""
        issue_file = os.path.join(self.issues_dir, f"{issue_id}.json")
        if os.path.exists(issue_file):
            with open(issue_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_request(self, request_id: str) -> Optional[Dict]:
        """Get a request by ID."""
        request_file = os.path.join(self.requests_dir, f"{request_id}.json")
        if os.path.exists(request_file):
            with open(request_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_training_request(self, request_id: str) -> Optional[Dict]:
        """Get a training request by ID."""
        request_file = os.path.join(self.training_dir, f"{request_id}.json")
        if os.path.exists(request_file):
            with open(request_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def update_issue_status(self, issue_id: str, status: str, 
                          comment: str = None) -> bool:
        """Update the status of an issue."""
        issue = self.get_issue(issue_id)
        if not issue:
            logger.error(f"Issue not found: {issue_id}")
            return False
        
        issue['status'] = status
        issue['updated_at'] = datetime.datetime.now().isoformat()
        
        if comment:
            if 'comments' not in issue:
                issue['comments'] = []
            
            issue['comments'].append({
                'text': comment,
                'created_at': datetime.datetime.now().isoformat()
            })
        
        issue_file = os.path.join(self.issues_dir, f"{issue_id}.json")
        with open(issue_file, 'w', encoding='utf-8') as f:
            json.dump(issue, f, indent=2)
        
        logger.info(f"Updated issue {issue_id} status to {status}")
        return True
    
    def update_request_status(self, request_id: str, status: str,
                            comment: str = None) -> bool:
        """Update the status of a request."""
        if request_id.startswith('FR-'):
            request_file = os.path.join(self.requests_dir, f"{request_id}.json")
        elif request_id.startswith('TRAIN-'):
            request_file = os.path.join(self.training_dir, f"{request_id}.json")
        else:
            logger.error(f"Invalid request ID format: {request_id}")
            return False
        
        if not os.path.exists(request_file):
            logger.error(f"Request not found: {request_id}")
            return False
        
        with open(request_file, 'r', encoding='utf-8') as f:
            request_data = json.load(f)
        
        request_data['status'] = status
        request_data['updated_at'] = datetime.datetime.now().isoformat()
        
        if comment:
            if 'comments' not in request_data:
                request_data['comments'] = []
            
            request_data['comments'].append({
                'text': comment,
                'created_at': datetime.datetime.now().isoformat()
            })
        
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(request_data, f, indent=2)
        
        logger.info(f"Updated request {request_id} status to {status}")
        return True
    
    def get_all_issues(self, status: str = None) -> List[Dict]:
        """Get all issues, optionally filtered by status."""
        issues = []
        
        for filename in os.listdir(self.issues_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.issues_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    issue = json.load(f)
                
                if status is None or issue.get('status') == status:
                    issues.append(issue)
        
        return issues
    
    def get_all_requests(self, status: str = None) -> List[Dict]:
        """Get all feature requests, optionally filtered by status."""
        requests = []
        
        for filename in os.listdir(self.requests_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.requests_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    request_data = json.load(f)
                
                if status is None or request_data.get('status') == status:
                    requests.append(request_data)
        
        return requests
    
    def get_all_training_requests(self, status: str = None) -> List[Dict]:
        """Get all training requests, optionally filtered by status."""
        requests = []
        
        for filename in os.listdir(self.training_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.training_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    request_data = json.load(f)
                
                if status is None or request_data.get('status') == status:
                    requests.append(request_data)
        
        return requests
    
    def _send_notification_email(self, subject: str, body: str, 
                               recipients: List[str] = None,
                               priority: str = 'normal') -> bool:
        """Send a notification email."""
        if not recipients:
            recipients = [self.admin_email]
        
        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not configured, skipping email notification")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.support_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            if priority == 'high':
                msg['X-Priority'] = '1'
                msg['X-MSMail-Priority'] = 'High'
                msg['Importance'] = 'High'
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Sent notification email: {subject}")
            return True
        
        except Exception as e:
            logger.error(f"Error sending notification email: {str(e)}")
            return False
    
    def generate_support_report(self, start_date: str = None, 
                              end_date: str = None) -> Dict:
        """Generate a support report for a given time period."""
        if start_date:
            start = datetime.datetime.fromisoformat(start_date)
        else:
            # Default to last 30 days
            start = datetime.datetime.now() - datetime.timedelta(days=30)
        
        if end_date:
            end = datetime.datetime.fromisoformat(end_date)
        else:
            end = datetime.datetime.now()
        
        # Get all issues and requests
        all_issues = self.get_all_issues()
        all_requests = self.get_all_requests()
        all_training = self.get_all_training_requests()
        
        # Filter by date range
        issues = [i for i in all_issues if start <= datetime.datetime.fromisoformat(i['created_at']) <= end]
        requests = [r for r in all_requests if start <= datetime.datetime.fromisoformat(r['created_at']) <= end]
        training = [t for t in all_training if start <= datetime.datetime.fromisoformat(t['created_at']) <= end]
        
        # Count by type and status
        issue_counts = {
            'bug': len([i for i in issues if i['id'].startswith('BUG-')]),
            'performance': len([i for i in issues if i['id'].startswith('PERF-')]),
            'security': len([i for i in issues if i['id'].startswith('SEC-')]),
            'data': len([i for i in issues if i['id'].startswith('DATA-')]),
            'access': len([i for i in issues if i['id'].startswith('ACCESS-')]),
            'error': len([i for i in issues if i['id'].startswith('ERR-')])
        }
        
        status_counts = {
            'new': len([i for i in issues + requests + training if i['status'] == 'new']),
            'in_progress': len([i for i in issues + requests + training if i['status'] == 'in_progress']),
            'resolved': len([i for i in issues + requests + training if i['status'] == 'resolved']),
            'closed': len([i for i in issues + requests + training if i['status'] == 'closed'])
        }
        
        # Generate report
        report = {
            'period': {
                'start': start.isoformat(),
                'end': end.isoformat()
            },
            'total_issues': len(issues),
            'total_requests': len(requests),
            'total_training': len(training),
            'issue_types': issue_counts,
            'status': status_counts,
            'recent_issues': sorted(issues, key=lambda x: x['created_at'], reverse=True)[:5],
            'recent_requests': sorted(requests, key=lambda x: x['created_at'], reverse=True)[:5]
        }
        
        return report

# Initialize support system
def init_support_system(app: Optional[Flask] = None) -> SupportSystem:
    """Initialize support system."""
    support = SupportSystem(app)
    logger.info("Support system initialized")
    return support