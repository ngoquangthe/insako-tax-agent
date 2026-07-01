"""Xác thực nâng cao: OTP qua email, reset mật khẩu lưu Supabase."""

from __future__ import annotations
import hashlib
import hmac
import os
import random
import smtplib
import string
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


# ── Supabase helpers ──────────────────────────────────────────────────────────

def _get_client():
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
    except Exception:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception:
        return None


def _smtp_config() -> dict:
    try:
        import streamlit as st
        return {
            "host": st.secrets.get("SMTP_HOST", "smtp.gmail.com"),
            "port": int(st.secrets.get("SMTP_PORT", 587)),
            "user": st.secrets.get("SMTP_USER", ""),
            "password": st.secrets.get("SMTP_PASS", ""),
        }
    except Exception:
        return {"host": "smtp.gmail.com", "port": 587, "user": "", "password": ""}


# ── Password override (Supabase) ──────────────────────────────────────────────

def get_supabase_password_hash(username: str) -> str | None:
    """Lấy password hash từ Supabase (ưu tiên hơn secrets khi user đã reset)."""
    client = _get_client()
    if not client:
        return None
    try:
        result = (
            client.table("user_passwords")
            .select("password_hash")
            .eq("username", username)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0]["password_hash"] if rows else None
    except Exception:
        return None


def save_new_password(username: str, new_password_hash: str) -> bool:
    """Lưu mật khẩu mới vào Supabase (upsert)."""
    client = _get_client()
    if not client:
        return False
    try:
        client.table("user_passwords").upsert({
            "username": username,
            "password_hash": new_password_hash,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        return True
    except Exception:
        return False


# ── OTP ───────────────────────────────────────────────────────────────────────

def create_otp(username: str) -> str | None:
    """Tạo OTP 6 số, lưu Supabase, hết hạn sau 10 phút."""
    client = _get_client()
    if not client:
        return None
    token = generate_otp()
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    try:
        # Hủy OTP cũ chưa dùng
        client.table("otp_tokens").update({"used": True}).eq("username", username).eq("used", False).execute()
        client.table("otp_tokens").insert({
            "username": username,
            "token": token,
            "expires_at": expires,
            "used": False,
        }).execute()
        return token
    except Exception:
        return None


def verify_otp(username: str, token: str) -> bool:
    """Xác minh OTP còn hạn và chưa dùng. Đánh dấu đã dùng nếu đúng."""
    client = _get_client()
    if not client:
        return False
    try:
        now = datetime.now(timezone.utc).isoformat()
        result = (
            client.table("otp_tokens")
            .select("id")
            .eq("username", username)
            .eq("token", token)
            .eq("used", False)
            .gt("expires_at", now)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return False
        client.table("otp_tokens").update({"used": True}).eq("id", rows[0]["id"]).execute()
        return True
    except Exception:
        return False


# ── Email ─────────────────────────────────────────────────────────────────────

def send_otp_email(to_email: str, username: str, otp: str) -> bool:
    """Gửi OTP qua Gmail SMTP."""
    cfg = _smtp_config()
    if not cfg["user"] or not cfg["password"]:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "[INSAKO Tax Agent] Mã xác thực đặt lại mật khẩu"
        msg["From"] = f"INSAKO Tax Agent <{cfg['user']}>"
        msg["To"] = to_email

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px;">
          <div style="background:#1B3A7A;padding:20px;border-radius:12px 12px 0 0;text-align:center;">
            <h2 style="color:white;margin:0;font-size:20px;">INSAKO Tax Agent</h2>
            <p style="color:#a0b4d6;margin:4px 0 0;font-size:13px;">Kế toán · Thuế · Tài chính</p>
          </div>
          <div style="background:white;border:1px solid #dde3f0;padding:28px;border-radius:0 0 12px 12px;">
            <p style="color:#333;font-size:15px;">Xin chào <strong>{username}</strong>,</p>
            <p style="color:#555;font-size:14px;">
              Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn.
              Sử dụng mã OTP bên dưới để xác nhận:
            </p>
            <div style="background:#f4f6fb;border:2px dashed #1B3A7A;border-radius:12px;
                        padding:20px;text-align:center;margin:20px 0;">
              <div style="font-size:38px;font-weight:700;letter-spacing:10px;color:#C41230;">
                {otp}
              </div>
              <p style="color:#888;font-size:12px;margin:8px 0 0;">Mã có hiệu lực trong <strong>10 phút</strong></p>
            </div>
            <p style="color:#999;font-size:12px;">
              Nếu bạn không yêu cầu đặt lại mật khẩu, hãy bỏ qua email này.
              Mật khẩu hiện tại vẫn không thay đổi.
            </p>
            <hr style="border:none;border-top:1px solid #eee;margin:16px 0;">
            <p style="color:#bbb;font-size:11px;text-align:center;">
              INSAKO – Công ty CP Đầu tư và Thương mại Thế Nam
            </p>
          </div>
        </div>
        """
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["user"], to_email, msg.as_string())
        return True
    except Exception:
        return False


def get_user_email(username: str) -> str:
    """Lấy email của user từ st.secrets."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "users" in st.secrets:
            user = st.secrets["users"].get(username, {})
            return user.get("email", "")
    except Exception:
        pass
    return ""
