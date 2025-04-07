import os
import smtplib
import re
import dns.resolver
import random
import markdown
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# ---------- Configuration ----------
SENDING_EMAIL_ADDRESS = "nidaeman0002@gmail.com"
SENDING_EMAIL_PASSWORD = "gaaq crpt itdt voiv"  # Use environment variables in production

# ---------- Helper Functions ----------

def validate_email_syntax(email: str) -> bool:
    """Check if the email has a basic valid syntax using regex."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def get_mx_records(domain: str):
    """Retrieve MX records for the given domain."""
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        records = sorted(answers, key=lambda r: r.preference)
        mx_records = [record.exchange.to_text().strip('.') for record in records]
        if not any(mx_records):
            return None
        return mx_records
    except Exception as e:
        print("Error retrieving MX records:", e)
        return None

def verify_email_smtp(email: str, from_address: str = SENDING_EMAIL_ADDRESS) -> bool:
    """
    Verify email existence by connecting to the domain's SMTP server
    and issuing MAIL FROM and RCPT TO commands.
    """
    if not validate_email_syntax(email):
        return False

    domain = email.split('@')[1]
    mx_records = get_mx_records(domain)
    if not mx_records:
        return False

    mx_record = mx_records[0]
    try:
        server = smtplib.SMTP(timeout=10)
        server.set_debuglevel(1)  # Enable debug output (optional)
        server.connect(mx_record, 25)
        server.helo(server.local_hostname)
        server.mail(from_address)
        code, message = server.rcpt(email)
        server.quit()
        return code == 250
    except Exception as e:
        print("SMTP verification error:", e)
        return False

def send_response_email(email_subject: str, email_markdown_text: str, receiver_email: str) -> bool:
    """Send an email with both plain text and HTML versions using Gmail's SMTP."""
    sender_email = SENDING_EMAIL_ADDRESS
    smtp_server = "smtp.gmail.com"
    port = 587

    # Create the multipart container.
    message = MIMEMultipart("alternative")
    message["Subject"] = email_subject
    message["From"] = sender_email
    message["To"] = receiver_email

    # Create plain text and HTML parts.
    part1 = MIMEText(email_markdown_text, "plain")
    html_content = markdown.markdown(email_markdown_text)
    html_template = f"""\
<html>
  <head>
    <style>
      body {{
        font-family: Arial, sans-serif;
        line-height: 1.6;
        margin: 20px;
      }}
      h1, h2, h3 {{
        color: #333;
      }}
      pre {{
        background: #f4f4f4;
        padding: 10px;
        border: 1px solid #ddd;
      }}
    </style>
  </head>
  <body>
    {html_content}
  </body>
</html>
"""
    part2 = MIMEText(html_template, "html")
    message.attach(part1)
    message.attach(part2)

    try:
        with smtplib.SMTP(smtp_server, port, timeout=10) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, SENDING_EMAIL_PASSWORD)
            server.sendmail(sender_email, receiver_email, message.as_string())
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False


# ---------- Pydantic Models ----------

class EmailValidationRequest(BaseModel):
    email: str

class EmailValidationResponse(BaseModel):
    is_valid_syntax: bool
    smtp_valid: bool

class EmailSendRequest(BaseModel):
    subject: str
    markdown_text: str
    receiver_email: str

class EmailSendResponse(BaseModel):
    success: bool

# ---------- FastAPI Endpoints ----------

@app.post("/validate_email", response_model=EmailValidationResponse)
async def validate_email_endpoint(request: EmailValidationRequest):
    syntax_ok = validate_email_syntax(request.email)
    smtp_ok = verify_email_smtp(request.email) if syntax_ok else False
    return EmailValidationResponse(is_valid_syntax=syntax_ok, smtp_valid=smtp_ok)

@app.post("/send_email", response_model=EmailSendResponse)
async def send_email_endpoint(request: EmailSendRequest):
    result = send_response_email(request.subject, request.markdown_text, request.receiver_email)
    return EmailSendResponse(success=result)
