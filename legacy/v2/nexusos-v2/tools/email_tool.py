"""
Email Tool - Send/receive emails via IMAP/SMTP
"""
import os
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from typing import Dict, List, Optional
import base64

class EmailTool:
    """Email via IMAP/SMTP"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        # SMTP settings
        self.smtp_host = self.config.get("smtp_host")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.smtp_user = self.config.get("smtp_user")
        self.smtp_password = self.config.get("smtp_password")
        # IMAP settings
        self.imap_host = self.config.get("imap_host")
        self.imap_user = self.config.get("imap_user")
        self.imap_password = self.config.get("imap_password")
    
    def _create_message(self, to: str, subject: str, body: str, html: str = None) -> MIMEMultipart:
        """Create email message"""
        msg = MIMEMultipart("alternative")
        msg["From"] = self.smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        
        # Plain text part
        msg.attach(MIMEText(body, "plain"))
        
        # HTML part (optional)
        if html:
            msg.attach(MIMEText(html, "html"))
        
        return msg
    
    def send(self, to: str, subject: str, body: str, html: str = None) -> Dict:
        """Send email"""
        if not self.smtp_host or not self.smtp_user:
            return {"success": False, "error": "SMTP not configured"}
        
        try:
            msg = self._create_message(to, subject, body, html)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return {"success": True, "to": to, "subject": subject}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_with_attachment(self, to: str, subject: str, body: str, 
                            file_path: str = None, file_data: bytes = None) -> Dict:
        """Send email with attachment"""
        if not self.smtp_host or not self.smtp_user:
            return {"success": False, "error": "SMTP not configured"}
        
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            
            # Add attachment
            if file_path:
                with open(file_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                    part["Content-Disposition"] = f'attachment; filename="{os.path.basename(file_path)}"'
                    msg.attach(part)
            elif file_data:
                part = MIMEApplication(file_data, Name="attachment")
                part["Content-Disposition"] = "attachment"
                msg.attach(part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return {"success": True, "to": to, "subject": subject}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def inbox(self, folder: str = "INBOX", limit: int = 10) -> Dict:
        """List recent emails"""
        if not self.imap_host or not self.imap_user:
            return {"success": False, "error": "IMAP not configured"}
        
        try:
            with imaplib.IMAP4_SSL(self.imap_host) as server:
                server.login(self.imap_user, self.imap_password)
                server.select(folder)
                
                # Fetch recent
                typ, data = server.search(None, "ALL")
                email_ids = data[0].split()[-limit:]
                
                emails = []
                for eid in email_ids:
                    typ, msg_data = server.fetch(eid, "(RFC822)")
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    # Parse headers
                    subject = msg.get("Subject", "")
                    from_ = msg.get("From", "")
                    date = msg.get("Date", "")
                    
                    # Get body
                    body = ""
                    if msg.is_multipart:
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()
                    
                    emails.append({
                        "id": eid.decode(),
                        "subject": subject,
                        "from": from_,
                        "date": date,
                        "body": body[:500]
                    })
                
                return {"success": True, "emails": emails}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def read(self, email_id: str, folder: str = "INBOX") -> Dict:
        """Read specific email"""
        if not self.imap_host or not self.imap_user:
            return {"success": False, "error": "IMAP not configured"}
        
        try:
            with imaplib.IMAP4_SSL(self.imap_host) as server:
                server.login(self.imap_user, self.imap_password)
                server.select(folder)
                
                typ, msg_data = server.fetch(email_id.encode(), "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Parse
                subject = msg.get("Subject", "")
                from_ = msg.get("From", "")
                date = msg.get("Date", "")
                
                # Body
                body = ""
                html = ""
                if msg.is_multipart:
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        if ctype == "text/plain":
                            body = part.get_payload(decode=True).decode()
                        elif ctype == "text/html":
                            html = part.get_payload(decode=True).decode()
                else:
                    body = msg.get_payload(decode=True).decode()
                
                return {
                    "success": True,
                    "email": {
                        "subject": subject,
                        "from": from_,
                        "date": date,
                        "body": body,
                        "html": html
                    }
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search(self, query: str, folder: str = "INBOX", limit: int = 10) -> Dict:
        """Search emails"""
        if not self.imap_host or not self.imap_user:
            return {"success": False, "error": "IMAP not configured"}
        
        try:
            with imaplib.IMAP4_SSL(self.imap_host) as server:
                server.login(self.imap_user, self.imap_password)
                server.select(folder)
                
                typ, data = server.search(None, f'SUBJECT "{query}"')
                email_ids = data[0].split()[-limit:]
                
                return {"success": True, "ids": [eid.decode() for eid in email_ids]}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton
_email_tool = None

def get_email_tool(config: Dict = None) -> EmailTool:
    global _email_tool
    if _email_tool is None:
        _email_tool = EmailTool(config)
    return _email_tool