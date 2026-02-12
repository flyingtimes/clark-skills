#!/usr/bin/env python3
"""
Send Email Skill
Basic email sending capability via SMTP
"""

import os
import sys
import smtplib
import argparse
from email.message import EmailMessage
from pathlib import Path
from typing import Optional, Dict

try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


class SmtpEmailClient:
    """Basic email client for sending emails via SMTP"""

    # Common email server configurations
    SMTP_SERVERS = {
        'gmail.com': {
            'server': 'smtp.gmail.com',
            'port': 587,
            'starttls': True
        },
        'outlook.com': {
            'server': 'smtp.office365.com',
            'port': 587,
            'starttls': True
        },
        'hotmail.com': {
            'server': 'smtp.live.com',
            'port': 587,
            'starttls': True
        },
        'yahoo.com': {
            'server': 'smtp.mail.yahoo.com',
            'port': 587,
            'starttls': True
        },
        'icloud.com': {
            'server': 'smtp.mail.me.com',
            'port': 587,
            'starttls': True
        }
    }

    def __init__(
        self,
        email_address: str,
        auth_code: str,
        smtp_server: str,
        smtp_port: int,
        debug: bool = False
    ):
        """Initialize the SMTP email client

        Args:
            email_address: Sender email address
            auth_code: Authentication code/password
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            debug: Enable debug mode
        """
        self.email_address = email_address
        self.auth_code = auth_code
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.debug = debug

        # Validate configuration
        if not email_address:
            raise ValueError("Email address is required")
        if not auth_code:
            raise ValueError("Authentication code is required")
        if not smtp_server:
            raise ValueError("SMTP server is required")
        if not smtp_port:
            raise ValueError("SMTP port is required")

    def _generate_subject(self, text: str) -> str:
        """Generate email subject from text

        Args:
            text: Text to generate subject from

        Returns:
            Generated subject line
        """
        if len(text) <= 20:
            return text
        return text[:20] + "..."

    def _create_message(
        self,
        to_email: str,
        subject: str,
        content: str,
        content_type: str = 'text/plain'
    ) -> EmailMessage:
        """Create email message

        Args:
            to_email: Recipient email address
            subject: Email subject
            content: Email content
            content_type: Content type (text/plain or text/html)

        Returns:
            EmailMessage object
        """
        if not to_email:
            raise ValueError("Recipient email address is required")
        if not content:
            raise ValueError("Email content is required")

        message = EmailMessage()
        message['From'] = self.email_address
        message['To'] = to_email
        message['Subject'] = subject
        message.set_content(content, subtype=content_type)

        return message

    def send_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        content_type: str = 'text/plain',
        timeout: int = 30
    ) -> bool:
        """Send email via SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            content: Email content
            content_type: Content type (text/plain or text/html)
            timeout: Connection timeout in seconds

        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Generate subject if not provided
            if not subject:
                subject = self._generate_subject(content)

            # Create message
            message = self._create_message(to_email, subject, content, content_type)

            # Connect to SMTP server
            if self.debug:
                print(f"Connecting to SMTP server: {self.smtp_server}:{self.smtp_port}")

            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=timeout)

            if self.debug:
                print("Connection established")

            # Extended Hello
            server.ehlo_or_helo_if_needed()

            # Start TLS if required
            if self.smtp_port == 587:
                if self.debug:
                    print("Starting TLS")
                server.starttls()
                server.ehlo()  # Send HELO after TLS

            # Login
            if self.debug:
                print("Logging in")
            server.login(self.email_address, self.auth_code)

            # Send email
            if self.debug:
                print("Sending email")
            server.send_message(message)

            # Close connection
            server.quit()

            if self.debug:
                print("Email sent successfully")

            return True

        except smtplib.SMTPAuthenticationError as e:
            print(f"SMTP Authentication Error: {e}", file=sys.stderr)
            return False
        except smtplib.SMTPConnectError as e:
            print(f"SMTP Connection Error: {e}", file=sys.stderr)
            return False
        except smtplib.SMTPException as e:
            print(f"SMTP Error: {e}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error sending email: {e}", file=sys.stderr)
            return False


def load_env_file(env_path: Optional[str] = None) -> Dict[str, str]:
    """Load environment variables from file

    Args:
        env_path: Path to .env file

    Returns:
        Dictionary of environment variables
    """
    if env_path:
        load_dotenv(env_path)

    return {
        'EMAIL_ADDRESS': os.getenv('EMAIL_ADDRESS'),
        'AUTH_CODE': os.getenv('AUTH_CODE'),
        'SMTP_SERVER': os.getenv('SMTP_SERVER'),
        'SMTP_PORT': os.getenv('SMTP_PORT'),
    }


def main():
    """Main function for sending email"""
    parser = argparse.ArgumentParser(description='Send email via SMTP')
    parser.add_argument('email', help='Recipient email address')
    parser.add_argument('content', help='Email content')
    parser.add_argument('--subject', help='Email subject (optional)')
    parser.add_argument('--content-type', default='text/plain',
                       choices=['text/plain', 'text/html'],
                       help='Email content type (default: text/plain)')
    parser.add_argument('--env', help='Path to .env file')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    # Load environment variables
    env_vars = load_env_file(args.env)

    # Check required environment variables
    required_vars = ['EMAIL_ADDRESS', 'AUTH_CODE', 'SMTP_SERVER', 'SMTP_PORT']
    missing_vars = [var for var in required_vars if not env_vars.get(var)]

    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}", file=sys.stderr)
        print(f"Required: {', '.join(required_vars)}", file=sys.stderr)
        if HAS_DOTENV:
            print(f"Create a .env file with these variables or set them in your environment", file=sys.stderr)
        else:
            print(f"Install python-dotenv to use .env files: pip install python-dotenv", file=sys.stderr)
        sys.exit(1)

    # Convert SMTP port to integer
    try:
        smtp_port = int(env_vars['SMTP_PORT'])
    except ValueError:
        print(f"Invalid SMTP port: {env_vars['SMTP_PORT']}", file=sys.stderr)
        sys.exit(1)

    # Create email client
    try:
        client = SmtpEmailClient(
            email_address=env_vars['EMAIL_ADDRESS'],
            auth_code=env_vars['AUTH_CODE'],
            smtp_server=env_vars['SMTP_SERVER'],
            smtp_port=smtp_port,
            debug=args.debug
        )
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Send email
    success = client.send_email(
        to_email=args.email,
        subject=args.subject,
        content=args.content,
        content_type=args.content_type,
        timeout=30
    )

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()