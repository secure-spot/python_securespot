import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import markdown
import re
import dns.resolver
import random
import requests
sending_email_address = "nidaeman0002@gmail.com"
sending_email_password = "gaaq crpt itdt voiv"
uri = 'https://fastapi-emailsend-86697802587.asia-south2.run.app/send_email'
async def sending_email(subject, body, receiver_email):
    payload = {
        "subject": subject,
        "markdown_text": body,
        "receiver_email": receiver_email
    }

    try:
        result = requests.post(uri, json=payload)
        result.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
        json_result = result.json()

        # Check if the 'success' key exists in the response
        return json_result['success']

    except requests.exceptions.RequestException as e:
        return False

def send_response_email(email_subject, email_markdown_text, receiver_email):
    sender_email = sending_email_address
    # receiver_email = "fa21-bai-058@cuiatk.edu.pk"
    smtp_server = "smtp.gmail.com"
    port = 587

    # Create the multipart container
    message = MIMEMultipart("alternative")
    message["Subject"] = email_subject
    message["From"] = sender_email
    message["To"] = receiver_email

    # Create the plain text part
    part1 = MIMEText(email_markdown_text, "plain")

    # Convert markdown to HTML if possible
    if markdown:
        html_content = markdown.markdown(email_markdown_text)
    else:
        # Fallback: display as preformatted text
        html_content = f"<pre>{email_markdown_text}</pre>"

    # Wrap the HTML content in a basic HTML template with CSS styling
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

    # Attach both plain text and HTML parts
    message.attach(part1)
    message.attach(part2)

    try:
        with smtplib.SMTP(smtp_server, port, timeout=10) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, sending_email_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        return True
    except Exception as e:
        return False


def validate_email_syntax(email):
    """Check if the email has a basic valid syntax using regex."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def get_mx_records(domain):
    """Retrieve MX records for the given domain."""
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        # Sort by preference (lowest value is highest priority)
        records = sorted(answers, key=lambda r: r.preference)
        mx_records = [record.exchange.to_text().strip('.') for record in records]
        # If the only record is empty after stripping, it's invalid.
        if not any(mx_records):
            return None
        return mx_records
    except Exception as e:
        return None

def verify_email_smtp(email, from_address="nidaeman0002@gmail.com"):
    """
    Verify email existence by connecting to the domain's SMTP server
    and issuing MAIL FROM and RCPT TO commands.
    """
    # Step 1: Validate syntax
    if not validate_email_syntax(email):
        return False

    # Step 2: Get domain MX records
    domain = email.split('@')[1]
    mx_records = get_mx_records(domain)
    if not mx_records:
        return False

    # Choose the first valid MX record
    mx_record = mx_records[0]

    try:
        # Connect to the SMTP server on port 25
        server = smtplib.SMTP(timeout=10)
        server.set_debuglevel(1)  # Debug output
        server.connect(mx_record, 25)
        server.helo(server.local_hostname)
        server.mail(from_address)
        code, message = server.rcpt(email)
        server.quit()

        if code == 250:
            return True
        else:
            return False

    except Exception as e:
        return False

async def generate_otp():
    """Generate a 6-digit OTP as a string."""
    return str(random.randint(100000, 999999))