from flask import current_app, render_template
from flask_mail import Message
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(subject, sender, recipients, text_body, html_body):
    """Simple email sending function using smtplib"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    
    # Add text and HTML parts
    part1 = MIMEText(text_body, 'plain')
    part2 = MIMEText(html_body, 'html')
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        server = smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT'])
        if current_app.config['MAIL_USE_TLS']:
            server.starttls()
        if current_app.config['MAIL_USERNAME'] and current_app.config['MAIL_PASSWORD']:
            server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.sendmail(sender, recipients, msg.as_string())
        server.quit()
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {e}")

def send_password_reset_email(user):
    """Send password reset email with token"""
    token = user.generate_reset_token()  # Generate token if not exists
    send_email(
        subject='[AgroMap] Reset Your Password',
        sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@agromap.uz'),
        recipients=[user.email],
        text_body=render_template('email/reset_password.txt', user=user, token=token),
        html_body=render_template('email/reset_password.html', user=user, token=token)
    )