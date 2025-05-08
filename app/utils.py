import smtplib
import uuid
from email.mime.text import MIMEText

def generate_reset_token():
    return str(uuid.uuid4())

def send_reset_email(email, token):
    try:
        msg = MIMEText(f"Click to reset your password: http://localhost:5000/reset-password/{token}")
        msg['Subject'] = 'Password Reset Request'
        msg['From'] = 'no-reply@flaskapp.com'
        msg['To'] = email

        print(f"Sending reset email to {email} with token {token}")
        return True
    except Exception as e:
        print(f"Email sending failed: {str(e)}")
        return False