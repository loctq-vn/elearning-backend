import argparse
import asyncio
from pathlib import Path
import sys

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.adapters.mailer import mailer
from app.core.config import settings


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test SMTP configuration and dispatch a test email.")
    parser.add_argument(
        "--to",
        dest="to_email",
        default=settings.emails_from_email or settings.smtp_user,
        help="Recipient email address (defaults to EMAILS_FROM_EMAIL or SMTP_USER)",
    )
    args = parser.parse_args()

    to_email = args.to_email
    if not to_email:
        print("ERROR: Recipient email address is required. Pass --to your-email@gmail.com or set EMAILS_FROM_EMAIL in .env")
        sys.exit(1)

    print("=== Testing SMTP Configuration ===")
    print(f"Host: {settings.smtp_host}")
    print(f"Port: {settings.smtp_port}")
    print(f"User: {settings.smtp_user}")
    print(f"From: {settings.emails_from_email or settings.smtp_user}")
    print(f"To:   {to_email}")
    print(f"Password configured: {'YES' if bool(settings.smtp_password) else 'NO'}")

    if not mailer.is_configured:
        print("WARNING: SMTP credentials not fully configured (SMTP_HOST and SMTP_USER required).")
        print("Please check your .env file.")
        sys.exit(1)

    print("\nSending test OTP email...")
    try:
        await mailer.send_otp_email(
            to_email=to_email,
            otp_code="987654",
            purpose="registration",
            expires_in_seconds=300,
        )
        print(">>> SUCCESS! Test OTP email sent successfully. Check your inbox (and spam folder)!")
    except Exception as exc:
        print(f">>> FAILED to send email: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
