import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_quotation_email_simulation(to_email, quote_id, status):
    """
    Versi simulasi agar tidak error di komputer lokal tanpa SMTP Server
    """
    print(f"\n[EMAIL SERVER LOG] --------------------------------")
    print(f"Sending Email To: {to_email}")
    print(f"Subject: Quotation {quote_id} - {status}")
    print(f"Body: Your quotation has been approved. Please find attached.")
    print(f"----------------------------------------------------\n")
    return True, "Email Sent (Simulation)"

# Gunakan fungsi ini jika sudah ada SMTP Server Asli
def send_quotation_email_real(to_email, quote_id, pdf_path):
    sender = "admin@komatsu.co.id"
    password = "password"
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f"Quotation {quote_id}"
        msg.attach(MIMEText("Dokumen terlampir."))
        # Setup SMTP here...
        return True, "Sent"
    except Exception as e:
        return False, str(e)