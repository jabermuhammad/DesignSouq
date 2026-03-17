import os
import smtplib
import ssl
from email.message import EmailMessage

from app import config


def _smtp_config() -> dict:
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from_email": os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USERNAME", "")),
        "from_name": os.getenv("SMTP_FROM_NAME", "DesignSouq"),
        "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"},
    }


def _build_message(to_email: str, subject: str, html_body: str) -> EmailMessage:
    cfg = _smtp_config()
    from_header = f"{cfg['from_name']} <{cfg['from_email']}>".strip()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_header
    msg["To"] = to_email
    msg.set_content("Please view this email in an HTML-capable client.")
    msg.add_alternative(html_body, subtype="html")
    return msg


def _send_email(to_email: str, subject: str, html_body: str) -> None:
    cfg = _smtp_config()
    if not cfg["username"] or not cfg["password"] or not cfg["from_email"]:
        raise RuntimeError("SMTP credentials are not configured.")

    message = _build_message(to_email, subject, html_body)
    context = ssl.create_default_context()

    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as server:
        if cfg["use_tls"]:
            server.starttls(context=context)
        server.login(cfg["username"], cfg["password"])
        server.send_message(message)


def send_reset_email(email: str, reset_link: str) -> None:
    subject = "Reset your DesignSouq password"
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background:#f6f3ee; padding:24px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;border:1px solid #e6ddd1;">
          <tr>
            <td style="padding:24px 28px;">
              <h2 style="margin:0 0 12px;color:#1b2a3a;">Reset your password</h2>
              <p style="margin:0 0 16px;color:#425466;line-height:1.6;">
                We received a request to reset your DesignSouq password. Click the button below to set a new password.
              </p>
              <p style="margin:0 0 18px;">
                <a href="{reset_link}" style="display:inline-block;padding:10px 18px;background:#c24a22;color:#fff;text-decoration:none;border-radius:999px;font-weight:700;">
                  Reset Password
                </a>
              </p>
              <p style="margin:0;color:#7a8796;font-size:12px;">
                This link expires in 30 minutes. If you did not request a reset, you can ignore this email.
              </p>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    _send_email(email, subject, html_body)


def send_verification_email(email: str, verify_link: str) -> None:
    subject = "Verify your DesignSouq account"
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background:#f6f3ee; padding:24px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;border:1px solid #e6ddd1;">
          <tr>
            <td style="padding:24px 28px;">
              <h2 style="margin:0 0 12px;color:#1b2a3a;">Verify your email</h2>
              <p style="margin:0 0 16px;color:#425466;line-height:1.6;">
                Thanks for joining DesignSouq. Click below to verify your email address.
              </p>
              <p style="margin:0 0 18px;">
                <a href="{verify_link}" style="display:inline-block;padding:10px 18px;background:#c24a22;color:#fff;text-decoration:none;border-radius:999px;font-weight:700;">
                  Verify Email
                </a>
              </p>
              <p style="margin:0;color:#7a8796;font-size:12px;">
                If you did not create this account, you can safely ignore this email.
              </p>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    _send_email(email, subject, html_body)
