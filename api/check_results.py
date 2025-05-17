import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
import redis # For Vercel KV
from http.server import BaseHTTPRequestHandler
import json

# --- Configuration (fetch from environment variables on Vercel) ---
WEBSITE_URL = "https://cms2results.tnmgrmuexam.ac.in/#/ExamResult"
SEARCH_TERM = "Pharm D"  # Case-insensitive search

# Email Configuration (from environment variables)
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("harxharish@gmail.com")
SMTP_PASSWORD = os.environ.get("HarisHBKAAAA1903@!")
SENDER_EMAIL = os.environ.get("harxharish@gmail.com")
RECEIVER_EMAIL = os.environ.get("harish@elevasionx.com")
EMAIL_SUBJECT_PREFIX = "[Result Vanthuruchuuu!!!!]"

# Vercel KV (Redis) connection
KV_URL = os.environ.get("KV_URL")
KV_NOTIFIED_SET_KEY = "notified_exam_results_set_pharm_d"

def get_kv_connection():
    if not KV_URL:
        print("KV_URL not configured. State will not be persistent.")
        return None
    try:
        return redis.from_url(KV_URL)
    except Exception as e:
        print(f"Error connecting to Vercel KV: {e}")
        return None

def send_email_notification(subject, body):
    """Sends an email notification."""
    if not SMTP_USERNAME or not SMTP_PASSWORD or not SENDER_EMAIL or not RECEIVER_EMAIL:
        print("Email configuration incomplete. Skipping email.")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        return False

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print(f"Email sent successfully to {RECEIVER_EMAIL}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def perform_check_and_notify():
    """Fetches website content, checks for Pharm D results, and notifies."""
    print(f"Checking {WEBSITE_URL} for '{SEARCH_TERM}' results...")
    log_messages = [f"Starting check for {SEARCH_TERM} at {WEBSITE_URL}"]

    r_kv = get_kv_connection()
    notified_results_identifiers = set()
    if r_kv:
        try:
            # Retrieve all members of the set
            members = r_kv.smembers(KV_NOTIFIED_SET_KEY)
            notified_results_identifiers = {member.decode('utf-8') for member in members}
            log_messages.append(f"Loaded {len(notified_results_identifiers)} notified results from KV.")
        except Exception as e:
            log_messages.append(f"Error reading from Vercel KV: {e}. Proceeding without persisted state for this run.")
    
    try:
        response = requests.get(WEBSITE_URL, timeout=30)
        response.raise_for_status()
        html_content = response.text
    except requests.exceptions.RequestException as e:
        log_messages.append(f"Error fetching website: {e}")
        send_email_notification(f"{EMAIL_SUBJECT_PREFIX} Website Check Failed", f"Could not fetch {WEBSITE_URL}.\nError: {e}")
        return {"status": "error", "message": "Failed to fetch website", "logs": log_messages}

    soup = BeautifulSoup(html_content, 'html.parser')
    found_new_results_details = []
    results_table = soup.find('table', id='table')

    if results_table:
        table_body = results_table.find('tbody')
        if table_body:
            rows = table_body.find_all('tr')
            log_messages.append(f"Found {len(rows)} rows in the results table.")
            for row_index, row in enumerate(rows):
                cells = row.find_all('td')
                if len(cells) >= 4: # S.No, Course Name, Course Term, Published Date
                    course_name_cell = cells[1]
                    course_name = course_name_cell.get_text(strip=True)
                    
                    # Create a robust unique identifier for the result
                    # Using course name, term, and published date should be fairly unique
                    unique_identifier_parts = [
                        cells[1].get_text(strip=True), # Course Name
                        cells[2].get_text(strip=True), # Course Term
                        cells[3].get_text(strip=True)  # Published Date
                    ]
                    result_identifier = "|".join(unique_identifier_parts)

                    if SEARCH_TERM.lower() in course_name.lower():
                        if result_identifier not in notified_results_identifiers:
                            log_messages.append(f"Found new '{SEARCH_TERM}' result: {result_identifier}")
                            details = f"Course Name: {course_name}\n"
                            details += f"Course Term: {cells[2].get_text(strip=True)}\n"
                            details += f"Published Date: {cells[3].get_text(strip=True)}\n"
                            details += f"Row Index (0-based): {row_index}\n" # For easier identification if needed
                            
                            found_new_results_details.append(details)
                            if r_kv:
                                try:
                                    r_kv.sadd(KV_NOTIFIED_SET_KEY, result_identifier)
                                    log_messages.append(f"Added '{result_identifier}' to KV notified set.")
                                except Exception as e:
                                    log_messages.append(f"Error writing to Vercel KV for '{result_identifier}': {e}")
                        else:
                            log_messages.append(f"Already notified for: {result_identifier}")
            if not rows:
                log_messages.append("No rows found in the table body.")
        else:
            log_messages.append("Could not find the table body (tbody) within the results table.")
    else:
        log_messages.append("Could not find the results table (table with id='table').")

    if found_new_results_details:
        email_body = "Hey, your results are available on: @https://cms2results.tnmgrmuexam.ac.in/#/ExamResult\n\n"
        email_body += f"New '{SEARCH_TERM}' results found on {WEBSITE_URL}:\n\n"
        email_body += "\n---\n".join(found_new_results_details)
        email_body += "\n\nFull Logs:\n" + "\n".join(log_messages)
        send_email_notification(f"{EMAIL_SUBJECT_PREFIX} New '{SEARCH_TERM}' Results Published!", email_body)
        return {"status": "success", "message": "New results found and notified.", "found_count": len(found_new_results_details), "logs": log_messages}
    else:
        log_messages.append(f"No new '{SEARCH_TERM}' results found this time.")
        # Optionally send a "still running" email if desired for cron job monitoring, but can be noisy
        # send_email_notification(f"{EMAIL_SUBJECT_PREFIX} Hourly Check Complete", f"No new '{SEARCH_TERM}' results found.\n\nLogs:\n" + "\n".join(log_messages))
        return {"status": "success", "message": "No new results found.", "logs": log_messages}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        result = perform_check_and_notify()
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode('utf-8'))
        return
    
if __name__ == '__main__':
    from http.server import HTTPServer
    port = int(os.environ.get("APP_PORT", 8000))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, handler)
    print(f"Starting HTTP server on port {port}...")
    httpd.serve_forever()