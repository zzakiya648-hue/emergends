import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()


def send_email(to: str, subject: str, body: str):
    sender = os.getenv("EMAIL_ADDRESS")
    pwd = os.getenv("EMAIL_APP_PASSWORD")
    if not sender or not pwd:
        raise RuntimeError(".env la EMAIL_ADDRESS / EMAIL_APP_PASSWORD illa")
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(sender, pwd.replace(" ", ""))
        s.send_message(msg)
