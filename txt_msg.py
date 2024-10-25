import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os


load_dotenv()
# Gmail account credentials
GMAIL_USER = 'arsanyattalla26@gmail.com'
GMAIL_PASSWORD = 'omdrveqoztfxrrti'
RECIPIENT_EMAIL = 'arsanyattalla10@gmail.com'

def send_email():
    # Set up the message
    msg = MIMEMultipart()
    msg['From'] = 'Arsany Attalla'
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = 'Automated Hourly Email'
    print(GMAIL_PASSWORD)

    # Email content
    body = "Hello! This is an automated email sent every hour."
    msg.attach(MIMEText(body, 'plain'))

    # Connect to Gmail SMTP server
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, text)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        server.quit()

# Send email every hour
try:
    while True:
        send_email()
        time.sleep(30)  # Wait for 1 hour (3600 seconds)
except KeyboardInterrupt:
    print("Process interrupted.")
