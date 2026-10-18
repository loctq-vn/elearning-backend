"""Email provider adapter boundary using SMTP."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)


class MailerAdapter:
    """SMTP-based email provider adapter."""

    def __init__(self, app_settings: Settings | None = None) -> None:
        self.settings = app_settings or settings

    @property
    def is_configured(self) -> bool:
        """Check if SMTP credentials are set."""
        return bool(self.settings.smtp_host and self.settings.smtp_user)

    def _build_mime_message(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        sender = self.settings.emails_from_email or self.settings.smtp_user
        msg["From"] = f"{self.settings.app_name} <{sender}>"
        msg["To"] = to_email

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        return msg

    def _send_sync(self, to_email: str, subject: str, html_content: str, text_content: str) -> None:
        """Synchronous SMTP sending logic, executed in worker thread."""
        host = self.settings.smtp_host
        port = self.settings.smtp_port
        user = self.settings.smtp_user
        password = self.settings.smtp_password

        msg = self._build_mime_message(to_email, subject, html_content, text_content)

        logger.info("Connecting to SMTP %s:%s for %s", host, port, to_email)
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20) as server:
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        logger.info("Email sent successfully to %s: %s", to_email, subject)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        """Send an email asynchronously."""
        plain_text = text_content or html_content

        if not self.is_configured:
            logger.warning(
                "[DEV_MAILER] SMTP not configured. Simulated sending to %s. Subject: %s\nContent:\n%s",
                to_email,
                subject,
                plain_text,
            )
            return True

        try:
            await asyncio.to_thread(self._send_sync, to_email, subject, html_content, plain_text)
            return True
        except Exception:
            logger.exception("Failed to send email to %s via SMTP %s", to_email, self.settings.smtp_host)
            raise

    async def send_otp_email(
        self,
        to_email: str,
        otp_code: str,
        purpose: str,
        expires_in_seconds: int = 300,
    ) -> bool:
        """Send OTP verification email for registration or password reset."""
        minutes = expires_in_seconds // 60

        if purpose == "registration":
            subject = f"[{self.settings.app_name}] Mã xác thực đăng ký tài khoản"
            action_desc = "đăng ký tài khoản mới trên nền tảng"
        elif purpose == "password_reset":
            subject = f"[{self.settings.app_name}] Mã xác thực đặt lại mật khẩu"
            action_desc = "yêu cầu đặt lại mật khẩu của bạn"
        else:
            subject = f"[{self.settings.app_name}] Mã xác thực tài khoản"
            action_desc = "xác thực thông tin tài khoản"

        text_content = (
            f"Chào bạn,\n\n"
            f"Bạn vừa thực hiện {action_desc}.\n"
            f"Mã xác thực OTP của bạn là: {otp_code}\n\n"
            f"Mã này có hiệu lực trong vòng {minutes} phút. Tuyệt đối không chia sẻ mã này cho bất kỳ ai.\n"
            f"Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email.\n\n"
            f"Trân trọng,\n"
            f"Đội ngũ {self.settings.app_name}"
        )

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 24px; color: #333; }}
  .card {{ max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 32px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); }}
  .header {{ text-align: center; margin-bottom: 24px; }}
  .brand {{ font-size: 22px; font-weight: 700; color: #1e3a8a; }}
  .title {{ font-size: 18px; font-weight: 600; color: #1f2937; margin-top: 12px; }}
  .otp-box {{ background: #eff6ff; border: 2px dashed #3b82f6; border-radius: 8px; padding: 18px; text-align: center; margin: 24px 0; }}
  .otp-code {{ font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #1d4ed8; font-family: monospace; }}
  .expiry {{ font-size: 13px; color: #6b7280; margin-top: 8px; }}
  .warning {{ font-size: 13px; color: #b45309; background: #fef3c7; padding: 10px 14px; border-radius: 6px; margin: 20px 0; }}
  .footer {{ font-size: 12px; color: #9ca3af; text-align: center; margin-top: 24px; border-top: 1px solid #e5e7eb; padding-top: 16px; }}
</style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="brand">{self.settings.app_name}</div>
      <div class="title">Xác thực mã OTP</div>
    </div>
    <p>Xin chào,</p>
    <p>Bạn vừa thực hiện <strong>{action_desc}</strong>. Sử dụng mã OTP bên dưới để hoàn tất:</p>
    <div class="otp-box">
      <div class="otp-code">{otp_code}</div>
      <div class="expiry">Mã xác thực có hiệu lực trong vòng <strong>{minutes} phút</strong></div>
    </div>
    <div class="warning">
      ⚠️ <strong>Cảnh báo bảo mật:</strong> Tuyệt đối không chia sẻ mã này với bất kỳ ai, kể cả nhân viên hỗ trợ.
    </div>
    <p>Nếu bạn không thực hiện yêu cầu này, hãy bỏ qua email này hoặc liên hệ hỗ trợ nếu nghi ngờ bị xâm phạm.</p>
    <div class="footer">
      Đây là email tự động, vui lòng không trả lời trực tiếp email này.<br>
      © {self.settings.app_name} — Nền tảng học trực tuyến thông minh.
    </div>
  </div>
</body>
</html>"""

        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )


mailer = MailerAdapter()
