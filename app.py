"""
AI AGENT SỔ TAY KẾ TOÁN – THUẾ – TÀI CHÍNH INSAKO
Web App (Streamlit)
"""

import hashlib
import hmac
import json
import os
import sys
import uuid
import secrets
from pathlib import Path
from datetime import datetime
from typing import Optional

# Force UTF-8 trên mọi môi trường (Linux Streamlit Cloud, Windows)
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# Đảm bảo working directory là thư mục dự án
import os
os.chdir(ROOT)

from src.services.auth_service import (
    hash_password as _auth_hash, verify_password as _auth_verify,
    get_supabase_password_hash, save_new_password,
    create_otp, verify_otp, send_otp_email, get_user_email,
    send_otp_sms, get_user_phone, _mask_phone,
)
from src.agents.tax_agent import TaxAgent
from src.services.tax_case_service import TaxCaseService
from src.tools.report_tool import ReportTool
from src.utils.helpers import format_currency, today_str
from src.services import supabase_service as supa
from src.utils.file_processor import build_message_with_file, get_file_type

# ── Cấu hình trang ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="INSAKO Tax Agent",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="auto",
)


# ── Xác thực đăng nhập ───────────────────────────────────────────────────────
def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _load_users() -> dict:
    # Ưu tiên đọc từ Streamlit Cloud secrets (khi deploy online)
    try:
        if hasattr(st, "secrets") and "users" in st.secrets:
            users = {}
            for uname, info in st.secrets["users"].items():
                users[uname] = dict(info)
            return users
    except Exception:
        pass

    auth_path = ROOT / "auth.json"
    if auth_path.exists():
        with open(auth_path, encoding="utf-8") as f:
            data = json.load(f)
        # Loại bỏ các key comment
        return {k: v for k, v in data.items() if not k.startswith("_")}
    # Mặc định nếu chưa có file auth.json
    return {
        "insako": {"name": "Kế toán INSAKO", "password_hash": _hash_password("insako2024"), "role": "admin"},
    }


def _get_token_secret() -> str:
    try:
        return st.secrets.get("TOKEN_SECRET", "insako-token-secret-2024")
    except Exception:
        return "insako-token-secret-2024"

def _make_token(username: str) -> str:
    """HMAC token tự xác thực — không cần server lưu gì."""
    import base64 as _b64
    secret = _get_token_secret()
    b64_user = _b64.urlsafe_b64encode(username.encode()).decode().rstrip("=")
    sig = hmac.new(secret.encode(), b64_user.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{b64_user}.{sig}"

def _validate_token(token: str) -> Optional[str]:
    """Trả về username nếu token HMAC hợp lệ."""
    import base64 as _b64
    if not token or "." not in token:
        return None
    try:
        b64_user, sig = token.rsplit(".", 1)
        secret = _get_token_secret()
        expected = hmac.new(secret.encode(), b64_user.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, expected):
            return None
        pad = 4 - len(b64_user) % 4
        return _b64.urlsafe_b64decode(b64_user + "=" * pad).decode()
    except Exception:
        return None

def _save_token_to_url(token: str):
    """Lưu token vào URL query param — tồn tại qua F5."""
    st.query_params["_tk"] = token

def _clear_token_from_url():
    """Xóa token khỏi URL khi logout."""
    st.query_params.pop("_tk", None)
    """, height=0, scrolling=False)

def _check_login(username: str, password: str, users: dict) -> bool:
    uname = username.strip().lower()
    user = users.get(uname)
    if not user:
        return False
    # Ưu tiên mật khẩu đã reset lưu trên Supabase
    sb_hash = get_supabase_password_hash(uname)
    if sb_hash:
        return _auth_verify(password, sb_hash)
    return hmac.compare_digest(user["password_hash"], _hash_password(password))


def _forgot_password_ui():
    """Quen mat khau: chon kenh (SMS/email) -> gui OTP -> dat mat khau moi."""
    step = st.session_state.get("fp_step", 1)

    if step == 1:
        st.markdown("**Bước 1 – Nhập tên đăng nhập**")
        fp_user = st.text_input("Username", key="fp_username", placeholder="Nhập username...")
        channel = st.radio("Nhận mã OTP qua", ["📱 SMS", "📧 Email"], key="fp_channel", horizontal=True)

        if st.button("🔑 Gửi mã OTP", key="fp_send", type="primary"):
            if not fp_user.strip():
                st.error("Vui lòng nhập username.")
                return
            uname = fp_user.strip().lower()
            users = _load_users()
            if uname not in users:
                st.error("❌ Không tìm thấy tài khoản này.")
                return

            otp = create_otp(uname)
            if not otp:
                st.error("Lỗi kết nối Supabase. Thử lại sau.")
                return

            if "SMS" in channel:
                phone = get_user_phone(uname)
                if not phone:
                    st.warning("⚠️ Tài khoản chưa có số điện thoại. Chọn Email hoặc liên hệ admin.")
                    return
                ok = send_otp_sms(phone, otp)
                masked = _mask_phone(phone)
                channel_label = f"SMS đến **{masked}**"
            else:
                email = get_user_email(uname)
                if not email:
                    st.warning("⚠️ Tài khoản chưa có email. Chọn SMS hoặc liên hệ admin.")
                    return
                ok = send_otp_email(email, uname, otp)
                parts = email.split("@")
                masked = parts[0][:3] + "***@" + parts[1] if len(parts) == 2 else email
                channel_label = f"Email đến **{masked}**"

            if ok:
                st.session_state.update({
                    "fp_step": 2,
                    "fp_user": uname,
                    "fp_channel_label": channel_label,
                })
                st.rerun()
            else:
                st.error("❌ Gửi thất bại. Kiểm tra cấu hình TWILIO/SMTP trong Streamlit Secrets.")

    elif step == 2:
        label = st.session_state.get("fp_channel_label", "")
        uname = st.session_state.get("fp_user", "")
        st.success(f"✅ Đã gửi mã OTP đến {label}.")
        st.markdown("**Bước 2 – Nhập mã OTP và mật khẩu mới**")

        otp_input = st.text_input("Mã OTP (6 số)", key="fp_otp", placeholder="Nhập mã vừa nhận...")
        new_pw1 = st.text_input("Mật khẩu mới", type="password", key="fp_pw1")
        new_pw2 = st.text_input("Xác nhận mật khẩu", type="password", key="fp_pw2")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Xác nhận", key="fp_confirm", type="primary"):
                if not otp_input.strip():
                    st.error("Vui lòng nhập mã OTP.")
                elif not new_pw1 or len(new_pw1) < 6:
                    st.error("Mật khẩu phải có ít nhất 6 ký tự.")
                elif new_pw1 != new_pw2:
                    st.error("❌ Mật khẩu xác nhận không khớp.")
                elif not verify_otp(uname, otp_input.strip()):
                    st.error("❌ Mã OTP sai hoặc hết hạn (10 phút). Thử gửi lại.")
                else:
                    if save_new_password(uname, _hash_password(new_pw1)):
                        st.success("✅ Đặt lại mật khẩu thành công! Đăng nhập lại.")
                        for k in ["fp_step", "fp_user", "fp_channel_label"]:
                            st.session_state.pop(k, None)
                        st.rerun()
                    else:
                        st.error("Lỗi lưu mật khẩu. Thử lại.")
        with col_b:
            if st.button("↩️ Gửi lại", key="fp_resend"):
                for k in ["fp_step", "fp_user", "fp_channel_label"]:
                    st.session_state.pop(k, None)
                st.rerun()


def _logo_base64() -> str:
    """Đọc logo từ assets/logo.png, trả về chuỗi base64."""
    import base64
    logo_path = ROOT / "assets" / "logo.png"
    if logo_path.exists():
        return base64.b64encode(logo_path.read_bytes()).decode()
    return ""


def _show_login():
    logo_b64 = _logo_base64()
    logo_src = f"data:image/png;base64,{logo_b64}" if logo_b64 else ""
    logo_img = (
        f'<img src="{logo_src}" style="width:48px;height:48px;object-fit:contain;">'
        if logo_src else "🏭"
    )

    st.markdown("""
    <style>
    #MainMenu,footer,header,[data-testid="stToolbar"],
    [data-testid="stDecoration"],[data-testid="stStatusWidget"] {display:none!important}

    body,[data-testid="stAppViewContainer"] {
        background: linear-gradient(150deg,#1a2e6e 0%,#3A5BF0 60%,#6b8eff 100%) !important;
    }
    [data-testid="stMain"],.main {background:transparent!important}

    .main .block-container {
        padding: 48px 0 0 0 !important;
        max-width: 100% !important;
    }

    /* Card – chỉ áp dụng trong cột login */
    .lcol .lcard {
        background:#fff;border-radius:22px;
        padding:28px 24px 22px;
        box-shadow:0 16px 48px rgba(0,0,0,0.22);
    }
    .lcol .llogo {
        width:60px;height:60px;border-radius:50%;background:#eef1ff;
        display:flex;align-items:center;justify-content:center;
        margin:0 auto 10px;overflow:hidden;
    }
    .lcol .lname {
        text-align:center;font-size:19px;font-weight:800;color:#1a2340;margin-bottom:3px;
    }
    .lcol .lsub {
        text-align:center;font-size:12px;color:#8a95b8;margin-bottom:14px;
    }
    .lcol .ldiv {
        height:2px;border-radius:2px;margin-bottom:0;
        background:linear-gradient(90deg,#3A5BF0,#C41230);
    }

    /* Form bên trong column giữa */
    .lcol [data-testid="stForm"] {
        background:#fff!important;
        border-radius:0 0 22px 22px!important;
        padding:16px 24px 20px!important;
        margin-top:0!important;
        box-shadow:0 16px 48px rgba(0,0,0,0.22)!important;
        border-top:none!important;
    }
    .lcol [data-testid="stTextInput"] {margin-bottom:8px!important}
    .lcol [data-testid="stTextInput"] label {
        font-size:12px!important;font-weight:600!important;color:#5a6680!important;
    }
    .lcol [data-testid="stTextInput"] input {
        height:42px!important;background:#f4f6ff!important;
        border:1.5px solid #dce2f5!important;border-radius:10px!important;
        font-size:14px!important;color:#1a2340!important;
        padding:0 13px!important;box-shadow:none!important;
    }
    .lcol [data-testid="stTextInput"] input:focus {
        border-color:#3A5BF0!important;background:#fff!important;
        box-shadow:0 0 0 3px rgba(58,91,240,0.1)!important;
    }
    .lcol [data-testid="stTextInput"] input::placeholder {color:#b8c2da!important}

    .lcol button[kind="primaryFormSubmit"] {
        background:linear-gradient(135deg,#3A5BF0,#6b8eff)!important;
        border:none!important;border-radius:10px!important;
        height:44px!important;font-size:15px!important;
        font-weight:700!important;color:white!important;
        box-shadow:0 4px 14px rgba(58,91,240,0.38)!important;
        margin-top:4px!important;
    }
    .lcol [data-testid="stAlert"] {
        border-radius:10px!important;font-size:13px!important;margin-top:4px!important;
    }
    .lcol [data-testid="stCaptionContainer"] p {
        color:#8a95b8!important;font-size:11px!important;
        text-align:center!important;margin-top:6px!important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 3 cột: padding kiri, card (38% width), padding kanan
    left, mid, right = st.columns([1, 1.4, 1])
    with mid:
        st.markdown(f"""
        <div class="lcol">
          <div class="lcard">
            <div class="llogo">{logo_img}</div>
            <div class="lname">INSAKO Tax Agent</div>
            <div class="lsub">Sổ tay Kế toán – Thuế – Tài chính nội bộ</div>
            <div class="ldiv"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Wrap form trong div.lcol để CSS selector hoạt động
        st.markdown('<div class="lcol">', unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Tên đăng nhập", placeholder="Nhập username...")
            password = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu...")
            submitted = st.form_submit_button("Đăng nhập", use_container_width=True, type="primary")
            if submitted:
                users = _load_users()
                if _check_login(username, password, users):
                    uname_clean = username.strip().lower()
                    token = _make_token(uname_clean)
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = uname_clean
                    st.session_state["user_name"] = users[uname_clean]["name"]
                    st.session_state["auth_token"] = token
                    _save_token_to_url(token)   # lưu vào URL — tồn tại qua F5
                    st.rerun()
                else:
                    st.error("Sai tên đăng nhập hoặc mật khẩu")
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("🔒 Hệ thống nội bộ · Liên hệ admin nếu quên mật khẩu")


# Kiểm tra xác thực — token nằm trong URL, tồn tại qua F5
_tk = st.query_params.get("_tk", "")
if not st.session_state.get("authenticated", False) and _tk:
    _uname_from_token = _validate_token(_tk)
    if _uname_from_token:
        _all_users = _load_users()
        if _uname_from_token in _all_users:
            st.session_state["authenticated"] = True
            st.session_state["username"] = _uname_from_token
            st.session_state["user_name"] = _all_users[_uname_from_token]["name"]
            st.session_state["auth_token"] = _tk
            st.rerun()

if not st.session_state.get("authenticated", False):
    _show_login()
    st.stop()

# ── CSS tùy chỉnh – màu nhận diện INSAKO ─────────────────────────────────────
_logo_b64_main = _logo_base64()
_logo_sidebar_html = (
    f'<img src="data:image/png;base64,{_logo_b64_main}" style="width:140px; margin:0 auto 0.5rem; display:block;">'
    if _logo_b64_main else
    '<div style="text-align:center;font-size:28px;margin-bottom:4px;">🏭</div>'
)

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ══════════════════════════════════════════════
   INSAKO MODERN LIGHT THEME
   Primary  : #3A5BF0  (blue)
   Accent   : #C41230  (red)
   Surface  : #ffffff  (white card)
   BG       : #f0f2fb  (light purple-grey)
══════════════════════════════════════════════ */

* {{ font-family: 'Inter', -apple-system, sans-serif !important; box-sizing: border-box; }}

/* ── Nền toàn app ── */
[data-testid="stAppViewContainer"] {{
    background: #f0f2fb !important;
    min-height: 100vh;
}}
[data-testid="stMain"] {{ background: transparent !important; }}
.main .block-container {{
    background: transparent;
    padding: 1rem 1rem 6rem !important;
    max-width: 100% !important;
}}

/* ── Chữ toàn cục ── */
p, li, span, label, div {{ color: #1a2340; }}
h1 {{ color: #1a2340 !important; font-size: 22px !important; font-weight: 800 !important; letter-spacing: -0.3px; }}
h2 {{ color: #1a2340 !important; font-size: 18px !important; font-weight: 700 !important; }}
h3 {{ color: #3A5BF0 !important; font-size: 15px !important; font-weight: 600 !important; }}
h2::after {{
    content: ""; display: block; height: 3px; width: 36px;
    background: linear-gradient(90deg,#3A5BF0,#C41230);
    border-radius: 2px; margin-top: 5px;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #1a2e6e 0%, #3A5BF0 100%) !important;
    border-right: none !important;
    box-shadow: 4px 0 20px rgba(58,91,240,0.15);
}}
[data-testid="stSidebar"] * {{ color: #ffffff !important; }}
[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.2) !important; }}
[data-testid="stSidebar"] .stRadio label {{
    font-size: 14px !important; padding: 6px 10px !important;
    border-radius: 10px; transition: background 0.2s;
}}
[data-testid="stSidebar"] .stRadio label:hover {{ background: rgba(255,255,255,0.12) !important; }}
[data-testid="stSidebar"] .stButton button {{
    background: rgba(255,255,255,0.15) !important;
    color: white !important; border: 1px solid rgba(255,255,255,0.3) !important;
    border-radius: 12px !important; font-weight: 600 !important;
    min-height: 42px !important; transition: background 0.2s !important;
}}
[data-testid="stSidebar"] .stButton button:hover {{
    background: rgba(255,255,255,0.25) !important;
}}

/* Sidebar logo strip */
.sidebar-logo-wrap {{
    background: rgba(0,0,0,0.2);
    padding: 1.2rem 0.75rem 1rem;
    margin: -1rem -1rem 0.75rem;
    border-bottom: 1px solid rgba(255,255,255,0.15);
    text-align: center;
    border-radius: 0 0 16px 16px;
}}
.sidebar-app-name {{ font-size: 13px; font-weight: 700; color: #fff !important; letter-spacing: 0.8px; margin-top: 6px; text-transform: uppercase; }}
.sidebar-app-sub  {{ font-size: 11px; color: rgba(255,255,255,0.7) !important; margin-top: 2px; }}

/* ── Nút ── */
div[data-testid="stButton"] > button,
div.stButton > button {{
    background: #ffffff !important;
    color: #3A5BF0 !important;
    border: 1.5px solid #e0e5f8 !important;
    border-radius: 12px !important;
    min-height: 44px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(58,91,240,0.08);
    transition: all 0.2s !important;
}}
div[data-testid="stButton"] > button:hover,
div.stButton > button:hover {{
    background: #f0f4ff !important;
    border-color: #3A5BF0 !important;
    box-shadow: 0 4px 14px rgba(58,91,240,0.18) !important;
    transform: translateY(-1px);
}}
div[data-testid="stButton"] > button[kind="primary"],
div.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg,#3A5BF0,#5b7fff) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 14px rgba(58,91,240,0.35) !important;
}}
div[data-testid="stButton"] > button[kind="primary"]:hover {{
    background: linear-gradient(135deg,#2d4fd6,#4a6eee) !important;
    box-shadow: 0 6px 20px rgba(58,91,240,0.45) !important;
    transform: translateY(-1px);
}}

/* ── Form submit ── */
div[data-testid="stForm"] button[kind="primaryFormSubmit"] {{
    background: linear-gradient(135deg,#3A5BF0,#5b7fff) !important;
    color: white !important; border: none !important;
    border-radius: 12px !important; font-weight: 700 !important;
    min-height: 48px !important;
    box-shadow: 0 4px 14px rgba(58,91,240,0.35) !important;
}}

/* ── Input / Textarea / Select ── */
input, textarea, select,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {{
    background: #ffffff !important;
    color: #1a2340 !important;
    border: 1.5px solid #dce2f5 !important;
    border-radius: 12px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    box-shadow: 0 1px 4px rgba(58,91,240,0.06) !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}}
input:focus, textarea:focus {{
    border-color: #3A5BF0 !important;
    box-shadow: 0 0 0 3px rgba(58,91,240,0.12) !important;
}}
input::placeholder, textarea::placeholder {{ color: #9aa5c9 !important; font-weight: 400 !important; }}
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stSelectbox"] label {{ color: #5c6b99 !important; font-size: 13px !important; font-weight: 500 !important; }}

/* ── Chat message ── */
[data-testid="stChatMessage"] {{
    background: #ffffff !important;
    border: 1px solid #e8edf8 !important;
    border-radius: 16px !important;
    margin-bottom: 0.75rem !important;
    box-shadow: 0 2px 10px rgba(58,91,240,0.07) !important;
}}
[data-testid="stChatMessageContent"] p,
[data-testid="stChatMessageContent"] li,
[data-testid="stChatMessageContent"] span,
[data-testid="stChatMessageContent"] div,
[data-testid="stChatMessageContent"] strong,
[data-testid="stChatMessageContent"] em,
[data-testid="stChatMessageContent"] td,
[data-testid="stChatMessageContent"] th {{ color: #1a2340 !important; }}
[data-testid="stChatMessageContent"] h1,
[data-testid="stChatMessageContent"] h2,
[data-testid="stChatMessageContent"] h3,
[data-testid="stChatMessageContent"] h4 {{ color: #1a2340 !important; }}
[data-testid="stChatMessageContent"] code {{
    background: #f0f4ff !important; color: #3A5BF0 !important;
    border-radius: 6px; padding: 2px 6px; font-size: 13px;
}}
[data-testid="stChatMessageContent"] hr {{ border-color: #e8edf8 !important; }}
[data-testid="stChatMessageContent"] pre {{
    overflow-x: auto !important; white-space: pre-wrap !important;
    word-break: break-word !important; max-width: 100% !important;
    background: #f7f9ff !important; border: 1px solid #dce2f5 !important;
    border-radius: 12px !important; padding: 12px 14px !important;
    font-size: 13px !important; line-height: 1.6 !important;
}}
[data-testid="stChatMessageContent"] pre code {{ color: #3A5BF0 !important; background: transparent !important; }}

/* ── Chat input box ── */
[data-testid="stBottom"] {{
    background: linear-gradient(0deg, #f0f2fb 85%, transparent) !important;
    padding: 0.5rem 1rem 0.75rem !important;
    left: 0 !important; right: 0 !important; width: 100% !important;
}}
[data-testid="stBottom"] > div {{ max-width: 100% !important; width: 100% !important; }}

/* Container tổng của chat input */
[data-testid="stChatInput"] {{
    width: 100% !important;
    max-width: 100% !important;
    position: relative !important;
    display: flex !important;
    align-items: center !important;
    background: #ffffff !important;
    border: 2px solid #dce2f5 !important;
    border-radius: 16px !important;
    box-shadow: 0 2px 12px rgba(58,91,240,0.1) !important;
    overflow: hidden !important;
    min-height: 52px !important;
}}
[data-testid="stChatInput"]:focus-within {{
    border-color: #3A5BF0 !important;
    box-shadow: 0 0 0 3px rgba(58,91,240,0.15) !important;
}}

/* Textarea bên trong – không có border riêng */
[data-testid="stChatInput"] textarea {{
    background: transparent !important;
    color: #1a2340 !important;
    border: none !important;
    border-radius: 0 !important;
    min-height: 52px !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    padding: 14px 60px 14px 18px !important;
    box-shadow: none !important;
    outline: none !important;
    resize: none !important;
    flex: 1 !important;
}}
[data-testid="stChatInput"] textarea::placeholder {{ color: #9aa5c9 !important; }}

/* Nút gửi – nằm bên phải, absolute bên trong container */
[data-testid="stChatInput"] button {{
    position: absolute !important;
    right: 8px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    background: linear-gradient(135deg,#3A5BF0,#5b7fff) !important;
    border: none !important;
    border-radius: 10px !important;
    width: 38px !important;
    height: 38px !important;
    min-width: 38px !important;
    min-height: 38px !important;
    box-shadow: 0 3px 10px rgba(58,91,240,0.35) !important;
    cursor: pointer !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    z-index: 10 !important;
}}

/* ── Card ── */
.insako-card {{
    background: #ffffff;
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    border: 1px solid #e8edf8;
    margin-bottom: 1rem;
    box-shadow: 0 4px 16px rgba(58,91,240,0.08);
    transition: box-shadow 0.2s;
}}
.insako-card:hover {{ box-shadow: 0 8px 24px rgba(58,91,240,0.14); }}
.insako-card-title {{ font-size: 15px; font-weight: 700; color: #1a2340 !important; margin-bottom: 0.5rem; }}

/* ── Metric card ── */
.metric-val {{ font-size: 28px; font-weight: 800; color: #3A5BF0 !important; }}
.metric-lbl {{ font-size: 12px; color: #7a8ab8 !important; margin-top: 2px; font-weight: 500; }}

/* ── Badge ── */
.badge-red    {{ background:#fff0f2; color:#C41230; border:1px solid #ffd6dc; border-radius:20px; padding:3px 10px; font-size:12px; font-weight:700; }}
.badge-yellow {{ background:#fffbeb; color:#b45309; border:1px solid #fde68a; border-radius:20px; padding:3px 10px; font-size:12px; font-weight:700; }}
.badge-green  {{ background:#f0fdf4; color:#16a34a; border:1px solid #bbf7d0; border-radius:20px; padding:3px 10px; font-size:12px; font-weight:700; }}
.badge-blue   {{ background:#f0f4ff; color:#3A5BF0; border:1px solid #c7d4fc; border-radius:20px; padding:3px 10px; font-size:12px; font-weight:700; }}

/* ── Chip ── */
.chip {{
    display:inline-block; background:#f0f4ff; color:#3A5BF0;
    border-radius:20px; padding:4px 12px; font-size:13px;
    margin:3px; border:1px solid #c7d4fc; font-weight:500;
}}

/* ── Divider ── */
hr {{ border-color: #e8edf8 !important; }}

/* ── Expander ── */
[data-testid="stExpander"] {{
    background: #ffffff !important;
    border: 1px solid #e8edf8 !important;
    border-radius: 14px !important;
    box-shadow: 0 2px 8px rgba(58,91,240,0.06) !important;
}}
[data-testid="stExpander"] summary {{ color: #1a2340 !important; font-weight: 600 !important; }}

/* ── Selectbox / Radio ── */
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
    background: #ffffff !important;
    border-color: #dce2f5 !important;
    color: #1a2340 !important;
    border-radius: 12px !important;
}}
.stRadio > div {{ gap: 8px; }}
.stRadio label {{ color: #1a2340 !important; font-weight: 500 !important; }}
.stCheckbox label {{ color: #1a2340 !important; font-weight: 500 !important; }}

/* ── Progress bar ── */
[data-testid="stProgress"] > div {{ background: #e8edf8 !important; border-radius: 8px !important; }}
[data-testid="stProgress"] > div > div {{ background: linear-gradient(90deg,#3A5BF0,#5b7fff) !important; border-radius: 8px !important; }}

/* ── Alert boxes ── */
[data-testid="stAlert"] {{
    background: #f7f9ff !important;
    border-color: #c7d4fc !important;
    color: #1a2340 !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(58,91,240,0.07) !important;
}}

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: #ffffff !important;
    border-radius: 14px !important;
    padding: 4px !important;
    border: 1px solid #e8edf8 !important;
    box-shadow: 0 2px 8px rgba(58,91,240,0.07) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    border-radius: 10px !important;
    font-weight: 600 !important;
    color: #7a8ab8 !important;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    background: linear-gradient(135deg,#3A5BF0,#5b7fff) !important;
    color: #ffffff !important;
}}

/* ── st.metric ── */
[data-testid="stMetric"] {{
    background: #ffffff;
    border: 1px solid #e8edf8;
    border-radius: 16px;
    padding: 16px 18px !important;
    box-shadow: 0 4px 14px rgba(58,91,240,0.08);
}}
[data-testid="stMetricValue"] {{ color: #3A5BF0 !important; font-weight: 800 !important; }}
[data-testid="stMetricLabel"] {{ color: #7a8ab8 !important; font-weight: 500 !important; }}

/* ── MOBILE RESPONSIVE ── */
@media (max-width: 768px) {{
    .main .block-container {{
        padding: 0.75rem 0.75rem 6rem !important;
    }}
    h1 {{ font-size: 20px !important; }}
    h2 {{ font-size: 16px !important; }}
    .metric-val {{ font-size: 24px !important; }}
    .insako-card {{ padding: 1rem !important; border-radius: 14px !important; }}
    input, textarea, select {{ font-size: 16px !important; }}
    [data-testid="stChatInput"] {{ border-radius: 14px !important; min-height: 50px !important; }}
    [data-testid="stChatInput"] textarea {{ font-size: 16px !important; min-height: 50px !important; }}
    [data-testid="stChatInput"] button {{ width: 36px !important; height: 36px !important; min-width: 36px !important; min-height: 36px !important; }}
    [data-testid="stSidebar"] {{ box-shadow: none !important; }}
}}

/* Login mobile */
@media (max-width: 600px) {{
    .login-wrap {{
        margin: 16px 10px 0 !important;
        padding: 1.5rem 1.2rem !important;
        border-radius: 20px !important;
    }}
    .login-wrap img {{ height: 48px !important; }}
    .login-title {{ font-size: 16px !important; }}
}}
</style>
""", unsafe_allow_html=True)


# ── Load config & services ────────────────────────────────────────────────────
@st.cache_resource
def load_services():
    cfg_path = ROOT / "config.json"
    if not cfg_path.exists():
        cfg_path = ROOT / "config.example.json"
    with open(cfg_path, encoding="utf-8") as f:
        config = json.load(f)
    # Chuyển tất cả paths thành tuyệt đối so với ROOT
    for key, rel_path in config.get("paths", {}).items():
        config["paths"][key] = str(ROOT / rel_path)
    if "system_prompt_file" in config.get("ai", {}):
        config["ai"]["system_prompt_file"] = str(ROOT / config["ai"]["system_prompt_file"])
    db_key = "tax_cases_file"
    if db_key in config.get("database", {}):
        config["database"][db_key] = str(ROOT / config["database"][db_key])
    # Khi chạy trên Streamlit Cloud: đọc API key từ secrets
    try:
        if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
            config["ai"]["api_key"] = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass

    agent = TaxAgent(config)
    case_svc = TaxCaseService(config)
    report_tool = ReportTool(config)
    return config, agent, case_svc, report_tool


config, agent, case_svc, report_tool = load_services()


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_page" not in st.session_state:
    st.session_state.active_page = "💬 Tra cứu AI"
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-logo-wrap">
        {_logo_sidebar_html}
        <div class="sidebar-app-name">INSAKO TAX AGENT</div>
        <div class="sidebar-app-sub">Kế toán · Thuế · Tài chính</div>
    </div>
    """, unsafe_allow_html=True)

    api_ok = agent._client is not None
    status = "🟢 Claude API" if api_ok else "🟡 Chế độ cục bộ"
    st.markdown(f"**Trạng thái:** {status}")
    st.markdown("---")

    is_admin = st.session_state.get("username", "") == "admin"

    pages = [
        "💬 Tra cứu AI",
        "✅ Kiểm tra hồ sơ",
        "📋 Tạo checklist",
        "📅 Kiểm tra định kỳ",
        "➕ Ghi nhận lỗi",
        "📜 Nhật ký lỗi",
        "📊 Báo cáo rủi ro",
        "🕐 Lịch sử chat",
    ]
    if is_admin:
        pages.append("⚙️ Quản lý tài khoản")

    if st.session_state.active_page not in pages:
        st.session_state.active_page = pages[0]
    page = st.radio("Chọn chức năng", pages, index=pages.index(st.session_state.active_page))
    st.session_state.active_page = page

    st.markdown("---")
    st.markdown("**Công ty:** Thế Nam / INSAKO")
    st.markdown(f"**Ngày:** {today_str()}")
    user_display = st.session_state.get("user_name", "")
    if user_display:
        st.markdown(f"**Người dùng:** {user_display}")

    if st.button("🗑️ Xóa lịch sử chat"):
        st.session_state.messages = []
        agent.clear_history()
        st.rerun()

    if st.button("🚪 Đăng xuất"):
        _clear_token_from_url()
        for k in ["authenticated", "username", "user_name", "messages", "auth_token"]:
            st.session_state.pop(k, None)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: TRA CỨU AI
# ══════════════════════════════════════════════════════════════════════════════
if page == "💬 Tra cứu AI":
    st.markdown("## 💬 Tra cứu nghiệp vụ Kế toán – Thuế")
    st.caption("Hỏi bất kỳ nghiệp vụ nào. AI trả lời theo cấu trúc: hồ sơ, rủi ro, hạch toán, checklist.")

    # Câu hỏi gợi ý nhanh – 2 cột trên mobile, 3 cột trên desktop
    st.markdown("**Gợi ý nhanh:**")
    quick_qs = [
        "Chi phí tiếp khách ký hợp đồng bán máy phun bi",
        "Thuê kỹ thuật viên tự do lắp máy, trả tiền mặt 5 triệu",
        "Nhập khẩu máy phun bi từ Trung Quốc, thuế NK và VAT",
        "Lương KPI nhân viên kinh doanh cần hồ sơ gì?",
        "Chi phí công tác phí kỹ thuật viên đi Đà Nẵng 3 ngày",
        "Hóa đơn mua phụ tùng ghi sai địa chỉ xử lý thế nào?",
    ]
    cols = st.columns(2)
    _uname = st.session_state.get("username", "")
    _sid = st.session_state.session_id

    for i, q in enumerate(quick_qs):
        with cols[i % 2]:
            if st.button(q, key=f"quick_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": q})
                supa.save_message(_uname, _sid, "user", q)
                with st.spinner("AI đang phân tích..."):
                    resp = agent.query(q, mode="general")
                st.session_state.messages.append({"role": "assistant", "content": resp})
                supa.save_message(_uname, _sid, "assistant", resp)
                st.rerun()

    st.markdown("---")

    # Hiển thị lịch sử chat
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar="📒"):
                st.markdown(msg["content"])

    # Input người dùng
    # Upload file
    with st.expander("📎 Đính kèm file (ảnh hóa đơn / PDF / Excel)", expanded=False):
        uploaded_file = st.file_uploader(
            "Chọn file",
            type=["jpg", "jpeg", "png", "webp", "pdf", "xlsx", "xls", "csv"],
            label_visibility="collapsed",
        )
        if uploaded_file:
            ftype = get_file_type(uploaded_file.name, uploaded_file.type or "")
            icons = {"image": "🖼️ Ảnh", "pdf": "📄 PDF", "excel": "📊 Excel"}
            st.caption(f"{icons.get(ftype,'📎')} **{uploaded_file.name}** — nhập câu hỏi bên dưới rồi gửi.")

    if prompt := st.chat_input("Nhập câu hỏi kế toán – thuế (VD: Chi phí vận chuyển hạt bi thép cần hồ sơ gì?)"):
        file_blocks = None
        display_note = ""
        if uploaded_file:
            file_bytes = uploaded_file.read()
            file_blocks = build_message_with_file(prompt, file_bytes, uploaded_file.name, uploaded_file.type or "")
            display_note = f"\n\n📎 *File đính kèm: {uploaded_file.name}*"

        user_display = prompt + display_note
        st.session_state.messages.append({"role": "user", "content": user_display})
        supa.save_message(_uname, _sid, "user", user_display)
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_display)

        with st.chat_message("assistant", avatar="📒"):
            with st.spinner("AI đang phân tích nghiệp vụ..."):
                response = agent.query(prompt, mode="general", file_content=file_blocks)
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        supa.save_message(_uname, _sid, "assistant", response)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: KIỂM TRA HỒ SƠ
# ══════════════════════════════════════════════════════════════════════════════
elif page == "✅ Kiểm tra hồ sơ":
    st.markdown("## ✅ Kiểm tra hồ sơ khoản chi")
    st.caption("Nhập thông tin khoản chi, AI kiểm tra hồ sơ đã đủ chưa và đánh giá rủi ro thuế.")

    col1, col2 = st.columns([3, 2])

    with col1:
        with st.form("check_form"):
            st.markdown("**Thông tin khoản chi**")
            business = st.text_input("Nghiệp vụ / Tên khoản chi", placeholder="VD: Thuê vận chuyển hạt bi thép")
            col_a, col_b = st.columns(2)
            with col_a:
                amount = st.number_input("Số tiền (VNĐ)", min_value=0, step=1000000, value=0)
            with col_b:
                payment = st.selectbox("Hình thức thanh toán", ["Chuyển khoản", "Tiền mặt", "Thẻ", "Chưa thanh toán"])

            party = st.selectbox("Đối tượng nhận tiền", ["Công ty (có MST)", "Hộ kinh doanh", "Cá nhân không HĐLĐ", "Cá nhân có HĐLĐ"])
            docs_have = st.text_area("Hồ sơ hiện có", placeholder="VD: Hóa đơn VAT, phiếu nhập kho, hợp đồng", height=80)
            docs_missing = st.text_area("Hồ sơ còn thiếu (nếu biết)", placeholder="VD: Biên bản nghiệm thu, chứng từ thanh toán", height=60)
            note = st.text_area("Ghi chú thêm", placeholder="Ngữ cảnh đặc biệt, câu hỏi cụ thể...", height=60)

            submitted = st.form_submit_button("🔍 Kiểm tra hồ sơ", use_container_width=True, type="primary")

    with col2:
        st.markdown('<div class="insako-card">', unsafe_allow_html=True)
        st.markdown("**💡 Lưu ý quan trọng**")
        st.markdown("""
- Thanh toán **tiền mặt > 20 triệu** → mất quyền khấu trừ VAT
- Cá nhân nhận tiền **> 2 triệu/lần** → khấu trừ TNCN 10%
- Hóa đơn sai thông tin người mua → không được khấu trừ VAT
- Chi phí tiếp khách không vượt **15%** tổng chi phí được trừ
        """)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="insako-card">', unsafe_allow_html=True)
        st.markdown("**📌 Ví dụ khoản chi INSAKO**")
        examples = [
            "Mua hạt bi thép 120 triệu, chuyển khoản",
            "Thuê lắp đặt máy phun bi tại KH",
            "Chi phí bảo trì định kỳ tại nhà máy",
            "Tạm ứng công tác phí kỹ thuật viên",
        ]
        for ex in examples:
            st.markdown(f"• {ex}")
        st.markdown('</div>', unsafe_allow_html=True)

    if submitted and business:
        query = f"""Kiểm tra hồ sơ khoản chi sau đây:
- Nghiệp vụ: {business}
- Số tiền: {format_currency(amount)}
- Hình thức thanh toán: {payment}
- Đối tượng nhận tiền: {party}
- Hồ sơ đã có: {docs_have or 'Chưa cung cấp'}
- Hồ sơ còn thiếu: {docs_missing or 'Chưa rõ'}
- Ghi chú: {note or 'Không có'}

Hãy kiểm tra: hồ sơ đã đủ chưa, thiếu gì, rủi ro VAT/TNDN/TNCN/BHXH, nên hạch toán ngay hay treo chờ bổ sung."""

        st.markdown("---")
        st.markdown("### Kết quả kiểm tra")
        with st.spinner("Đang kiểm tra hồ sơ..."):
            result = agent.query(query, mode="check_documents")
        st.markdown(result)

        # Cảnh báo ngưỡng tiền mặt
        if payment == "Tiền mặt" and amount > 20_000_000:
            st.error(f"⚠️ **CẢNH BÁO:** Thanh toán tiền mặt {format_currency(amount)} vượt ngưỡng 20 triệu đồng. Không được khấu trừ VAT và không được ghi nhận chi phí hợp lý TNDN!")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: TẠO CHECKLIST
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Tạo checklist":
    st.markdown("## 📋 Tạo checklist nghiệp vụ")
    st.caption("Chọn hoặc nhập nghiệp vụ để tạo checklist hồ sơ đầy đủ.")

    col1, col2 = st.columns([1, 2])

    CHECKLIST_OPTIONS = {
        "Lương cơ bản & KPI": "Lương cơ bản và KPI cho nhân viên INSAKO",
        "Mua vật tư, hàng hóa": "Mua vật tư hàng hóa trong nước (hạt bi thép, phụ tùng)",
        "Tạm ứng & Hoàn ứng": "Tạm ứng và hoàn ứng công tác phí, chi phí",
        "Nhập khẩu máy móc": "Nhập khẩu máy phun bi, phụ tùng từ nước ngoài",
        "Chi phí tiếp khách": "Chi phí tiếp khách, ăn uống đối tác, khách hàng",
        "Công tác phí": "Công tác phí kỹ thuật viên đi lắp đặt, bảo trì toàn quốc",
        "Thuê ngoài / Gia công": "Thuê ngoài nhân công lắp đặt, gia công phụ tùng",
        "Tài sản cố định": "Mua mới, thanh lý tài sản cố định",
        "Doanh thu / Xuất HĐ": "Ghi nhận doanh thu và xuất hóa đơn bán hàng, dịch vụ",
        "Chi phí bảo hành/bảo trì": "Chi phí bảo hành sau bán hàng, dịch vụ bảo trì định kỳ",
        "Chi phí hoa hồng": "Chi phí hoa hồng cho đại lý, cá nhân giới thiệu hợp đồng",
        "Nhập tên khác...": "",
    }

    with col1:
        selected = st.selectbox("Chọn nhóm nghiệp vụ", list(CHECKLIST_OPTIONS.keys()))
        custom_input = ""
        if selected == "Nhập tên khác...":
            custom_input = st.text_input("Nhập tên nghiệp vụ", placeholder="VD: Chi phí marketing online")

        generate_btn = st.button("📋 Tạo checklist", type="primary", use_container_width=True)

        st.markdown("---")
        st.markdown("**Checklist có sẵn trong KB:**")
        existing = [
            "✅ sample_checklist_luong_kpi.md",
            "✅ sample_checklist_chi_phi_mua_hang.md",
            "✅ sample_checklist_tam_ung_hoan_ung.md",
        ]
        for f in existing:
            st.caption(f)

    with col2:
        if generate_btn:
            nv = custom_input if selected == "Nhập tên khác..." else CHECKLIST_OPTIONS[selected]
            if not nv:
                st.warning("Vui lòng nhập tên nghiệp vụ.")
            else:
                with st.spinner(f"Đang tạo checklist: {selected}..."):
                    result = agent.query(f"Tạo checklist đầy đủ cho nghiệp vụ: {nv}", mode="generate_checklist")

                st.success(f"✅ Checklist: {selected}")
                st.markdown(result)

                # Nút tải về
                st.download_button(
                    label="⬇️ Tải về file .md",
                    data=result.encode("utf-8"),
                    file_name=f"checklist_{selected[:20].replace(' ', '_')}_{today_str()}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
        else:
            st.info("👈 Chọn nghiệp vụ bên trái và nhấn **Tạo checklist**")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4: KIỂM TRA ĐỊNH KỲ
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📅 Kiểm tra định kỳ":
    st.markdown("## 📅 Kiểm tra định kỳ")

    tab_month, tab_year = st.tabs(["📆 Báo cáo thuế tháng", "📊 Báo cáo tài chính năm"])

    # ── TAB 1: THÁNG ──────────────────────────────────────────────────────────
    with tab_month:
        st.caption("Checklist kiểm tra báo cáo thuế hàng tháng – đúng, đủ, kịp thời.")

        col_m1, col_m2 = st.columns([1, 3])
        with col_m1:
            now = datetime.now()
            sel_month = st.selectbox("Tháng", list(range(1, 13)), index=now.month - 2 if now.month > 1 else 0)
            sel_year = st.number_input("Năm", min_value=2020, max_value=2030, value=now.year, step=1)

        st.markdown("---")

        MONTHLY_CHECKS = {
            "🔵 VAT ĐẦU VÀO": [
                "Tổng hợp đủ hóa đơn mua vào trong tháng (hạt bi, phụ tùng, máy móc, dịch vụ)",
                "Các khoản > 20 triệu đều thanh toán chuyển khoản (không dùng tiền mặt)",
                "Hóa đơn nhập khẩu khớp với tờ khai hải quan (VAT khâu NK)",
                "Không kê khai hóa đơn sai tên/MST người mua",
                "Hóa đơn của kỳ trước (đến muộn) đã xử lý theo quy định",
            ],
            "🟢 VAT ĐẦU RA": [
                "Toàn bộ doanh thu bán máy, phụ tùng, dịch vụ đã xuất hóa đơn",
                "Hóa đơn xuất đúng tháng phát sinh doanh thu (không trễ kỳ)",
                "Thông tin hóa đơn đầu ra: tên, MST, địa chỉ KH đúng",
                "Đối chiếu tổng doanh thu trên hóa đơn = doanh thu ghi nhận sổ",
            ],
            "🟡 LƯƠNG & BHXH": [
                "Bảng lương tháng có chữ ký nhân viên đầy đủ",
                "Đã tính và khấu trừ TNCN đúng biểu lũy tiến / 10%",
                "Đã nộp BHXH, BHYT, BHTN đúng hạn (trước ngày 15–20)",
                "Hợp đồng lao động còn hiệu lực với toàn bộ nhân sự phát sinh lương",
            ],
            "🟠 CHI PHÍ KHÁC": [
                "Công tác phí kỹ thuật viên có quyết định cử đi, bảng kê chi tiết",
                "Chi tiếp khách có danh sách khách mời, hóa đơn VAT",
                "Tạm ứng chưa hoàn quá 30 ngày đã nhắc nhở hoàn ứng",
                "Không có khoản chi tiền mặt > 20 triệu chưa chuyển khoản",
            ],
            "🔴 DEADLINE & NỘP THUẾ": [
                f"Tờ khai VAT tháng {sel_month}/{sel_year} nộp trước ngày 20/{sel_month + 1 if sel_month < 12 else 1}/{sel_year if sel_month < 12 else sel_year + 1}",
                "Tờ khai TNCN (nếu phát sinh) nộp đúng hạn",
                "Số thuế VAT phải nộp đã chuyển khoản vào NSNN",
                "Lưu file tờ khai + biên lai nộp thuế vào hồ sơ tháng",
            ],
        }

        total_items = sum(len(v) for v in MONTHLY_CHECKS.values())
        checked_count = 0

        for section, items in MONTHLY_CHECKS.items():
            st.markdown(f"**{section}**")
            for i, item in enumerate(items):
                key = f"month_{sel_year}_{sel_month}_{section}_{i}"
                checked = st.checkbox(item, key=key)
                if checked:
                    checked_count += 1
            st.markdown("")

        # Progress bar
        pct = int(checked_count / total_items * 100)
        color = "🟢" if pct == 100 else ("🟡" if pct >= 60 else "🔴")
        st.markdown(f"---\n**Tiến độ: {color} {checked_count}/{total_items} mục ({pct}%)**")
        st.progress(pct / 100)

        if pct == 100:
            st.success(f"✅ Hoàn tất kiểm tra tháng {sel_month}/{sel_year}!")
        elif pct >= 60:
            st.warning(f"⚠️ Còn {total_items - checked_count} mục chưa hoàn thành.")
        else:
            st.error(f"❌ Mới hoàn thành {pct}% — cần xử lý gấp trước deadline.")

        st.markdown("---")
        st.markdown("**📎 Tải file lên để AI kiểm tra (tờ khai, bảng lương, hóa đơn...)**")
        month_files = st.file_uploader(
            "Chọn file",
            type=["jpg", "jpeg", "png", "webp", "pdf", "xlsx", "xls", "csv"],
            accept_multiple_files=True,
            key=f"upload_month_{sel_year}_{sel_month}",
            label_visibility="collapsed",
        )
        month_note = st.text_input(
            "Câu hỏi cụ thể (để trống = AI tự kiểm tra theo checklist)",
            placeholder="VD: Kiểm tra hóa đơn này có hợp lệ không?",
            key=f"note_month_{sel_year}_{sel_month}",
        )

        col_m_btn1, col_m_btn2 = st.columns(2)
        with col_m_btn1:
            if st.button("📎 Gửi file để AI kiểm tra", key="ai_month_file",
                         disabled=not month_files):
                unchecked = [item for section, items in MONTHLY_CHECKS.items()
                             for i, item in enumerate(items)
                             if not st.session_state.get(f"month_{sel_year}_{sel_month}_{section}_{i}", False)]
                checklist_context = (
                    f"Tháng {sel_month}/{sel_year} – các mục checklist CHƯA hoàn thành:\n"
                    + "\n".join(f"- {x}" for x in unchecked)
                    if unchecked else f"Tháng {sel_month}/{sel_year} – tất cả mục đã tick."
                )
                question = month_note or f"Kiểm tra file theo checklist báo cáo thuế tháng {sel_month}/{sel_year} của INSAKO. {checklist_context}"

                for uf in month_files:
                    file_bytes = uf.read()
                    file_blocks = build_message_with_file(question, file_bytes, uf.name, uf.type or "")
                    with st.spinner(f"AI đang phân tích {uf.name}..."):
                        resp = agent.query(question, file_content=file_blocks)
                    st.markdown(f"**📄 {uf.name}**")
                    st.markdown(resp)
                    st.markdown("---")

        with col_m_btn2:
            if st.button("🤖 Hỏi AI về mục chưa hoàn thành", key="ai_month"):
                unchecked = [item for section, items in MONTHLY_CHECKS.items()
                             for i, item in enumerate(items)
                             if not st.session_state.get(f"month_{sel_year}_{sel_month}_{section}_{i}", False)]
                if unchecked:
                    q = f"Tháng {sel_month}/{sel_year} còn {len(unchecked)} mục chưa hoàn thành:\n" + "\n".join(f"- {x}" for x in unchecked) + "\n\nHướng dẫn cách xử lý nhanh nhất."
                    with st.spinner("AI đang phân tích..."):
                        resp = agent.query(q)
                    st.markdown(resp)
                else:
                    st.success("Tất cả đã hoàn thành!")

    # ── TAB 2: NĂM ────────────────────────────────────────────────────────────
    with tab_year:
        st.caption("Checklist kiểm tra báo cáo tài chính cuối năm – chuẩn bị quyết toán thuế TNDN.")

        sel_year_annual = st.number_input("Năm tài chính", min_value=2020, max_value=2030,
                                          value=datetime.now().year - 1, step=1, key="annual_year")

        st.markdown("---")

        ANNUAL_CHECKS = {
            "📋 CHUẨN BỊ SỐ LIỆU": [
                "Đối chiếu tổng doanh thu năm: hóa đơn đầu ra = sổ doanh thu",
                "Đối chiếu tổng chi phí: chứng từ gốc = sổ chi phí",
                "Kiểm tra số dư công nợ phải thu (khách hàng mua máy, dịch vụ)",
                "Kiểm tra số dư công nợ phải trả (nhà cung cấp hạt bi, phụ tùng)",
                "Kiểm tra tồn kho: kiểm kê thực tế = sổ tồn kho",
                "Đối chiếu số dư tiền mặt, tiền gửi ngân hàng cuối năm",
            ],
            "💰 DOANH THU & CHI PHÍ": [
                "Doanh thu bán máy phun bi, phụ tùng ghi nhận đúng kỳ",
                "Doanh thu dịch vụ bảo trì, lắp đặt ghi nhận theo tiến độ",
                "Chi phí giá vốn hàng bán tính đúng (nhập – xuất – tồn)",
                "Chi phí lương, BHXH toàn năm khớp với bảng lương + quyết toán TNCN",
                "Chi phí công tác phí kỹ thuật viên đủ hồ sơ theo quy định",
                "Chi phí tiếp khách không vượt 15% tổng chi phí được trừ",
                "Chi phí khấu hao TSCĐ tính đúng (máy móc, phương tiện vận tải)",
                "Chi phí lãi vay (nếu có) có hợp đồng, không vượt trần lãi suất",
            ],
            "🏦 TÀI SẢN & CÔNG NỢ": [
                "Kiểm tra TSCĐ: có đủ hồ sơ mua, đang còn khấu hao, không thanh lý thiếu thủ tục",
                "Trích lập dự phòng nợ phải thu khó đòi (nếu có KH nợ quá hạn)",
                "Trích lập dự phòng giảm giá hàng tồn kho (nếu cần)",
                "Phân loại đúng nợ ngắn hạn / dài hạn",
                "Số dư tạm ứng đã được hoàn ứng hoặc hạch toán chi phí đúng",
            ],
            "📑 QUYẾT TOÁN THUẾ": [
                "Lập tờ khai quyết toán TNDN (hạn: 90 ngày sau ngày kết thúc năm tài chính)",
                "Loại trừ các chi phí không được trừ: quà tặng không có HĐ, phạt vi phạm...",
                "Kiểm tra ưu đãi thuế TNDN (nếu có: dự án đầu tư mới, địa bàn...)",
                "Quyết toán TNCN: đã cấp chứng từ khấu trừ cho nhân viên",
                "Kê khai thuế nhà thầu nước ngoài (nếu có thanh toán cho đối tác nước ngoài)",
                "Nộp báo cáo tài chính lên Cục thuế + Sở KH&ĐT đúng hạn",
            ],
            "✅ HỒ SƠ LƯU TRỮ": [
                "Đóng gói, lưu trữ chứng từ gốc theo từng tháng (tối thiểu 10 năm)",
                "File mềm tờ khai thuế tháng, quý, năm lưu đầy đủ",
                "Biên lai nộp thuế các loại lưu đầy đủ",
                "Báo cáo tài chính đã ký, đóng dấu lưu bản gốc",
            ],
        }

        total_annual = sum(len(v) for v in ANNUAL_CHECKS.values())
        checked_annual = 0

        for section, items in ANNUAL_CHECKS.items():
            st.markdown(f"**{section}**")
            for i, item in enumerate(items):
                key = f"annual_{sel_year_annual}_{section}_{i}"
                checked = st.checkbox(item, key=key)
                if checked:
                    checked_annual += 1
            st.markdown("")

        pct_a = int(checked_annual / total_annual * 100)
        color_a = "🟢" if pct_a == 100 else ("🟡" if pct_a >= 60 else "🔴")
        st.markdown(f"---\n**Tiến độ: {color_a} {checked_annual}/{total_annual} mục ({pct_a}%)**")
        st.progress(pct_a / 100)

        if pct_a == 100:
            st.success(f"✅ Hoàn tất kiểm tra báo cáo tài chính năm {sel_year_annual}!")
        elif pct_a >= 60:
            st.warning(f"⚠️ Còn {total_annual - checked_annual} mục cần xử lý trước khi quyết toán.")
        else:
            st.error(f"❌ Mới hoàn thành {pct_a}% — cần ưu tiên xử lý gấp.")

        # Upload file + AI kiểm tra
        st.markdown("---")
        st.markdown("**📎 Tải file lên để AI kiểm tra (BCTC, tờ khai quyết toán, bảng cân đối...)**")
        annual_files = st.file_uploader(
            "Chọn file",
            type=["jpg", "jpeg", "png", "webp", "pdf", "xlsx", "xls", "csv"],
            accept_multiple_files=True,
            key=f"upload_annual_{sel_year_annual}",
            label_visibility="collapsed",
        )
        annual_note = st.text_input(
            "Câu hỏi cụ thể (để trống = AI tự kiểm tra theo checklist năm)",
            placeholder="VD: Kiểm tra bảng cân đối kế toán năm có khớp không?",
            key=f"note_annual_{sel_year_annual}",
        )

        if st.button("📎 Gửi file để AI kiểm tra", key="ai_annual_file",
                     disabled=not annual_files):
            unchecked_a = [item for section, items in ANNUAL_CHECKS.items()
                           for i, item in enumerate(items)
                           if not st.session_state.get(f"annual_{sel_year_annual}_{section}_{i}", False)]
            checklist_ctx = (
                f"Năm {sel_year_annual} – các mục CHƯA hoàn thành:\n"
                + "\n".join(f"- {x}" for x in unchecked_a[:15])
                if unchecked_a else f"Năm {sel_year_annual} – tất cả mục đã tick."
            )
            question = annual_note or f"Kiểm tra file theo checklist báo cáo tài chính năm {sel_year_annual} của INSAKO. {checklist_ctx}"

            for uf in annual_files:
                file_bytes = uf.read()
                file_blocks = build_message_with_file(question, file_bytes, uf.name, uf.type or "")
                with st.spinner(f"AI đang phân tích {uf.name}..."):
                    resp = agent.query(question, file_content=file_blocks)
                st.markdown(f"**📄 {uf.name}**")
                st.markdown(resp)
                st.markdown("---")

        st.markdown("---")
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            if st.button("🤖 Hỏi AI về mục chưa xong", key="ai_annual"):
                unchecked_a = [item for section, items in ANNUAL_CHECKS.items() for i, item in enumerate(items)
                               if not st.session_state.get(f"annual_{sel_year_annual}_{section}_{i}", False)]
                if unchecked_a:
                    q = f"Quyết toán năm {sel_year_annual} còn {len(unchecked_a)} mục chưa hoàn thành:\n" + "\n".join(f"- {x}" for x in unchecked_a[:10]) + "\n\nHướng dẫn cách xử lý theo thứ tự ưu tiên."
                    with st.spinner("AI đang phân tích..."):
                        resp = agent.query(q)
                    st.markdown(resp)
                else:
                    st.success("Tất cả đã hoàn thành!")

        with col_e2:
            # Export báo cáo tiến độ
            export_lines = [f"# KIỂM TRA BÁO CÁO TÀI CHÍNH NĂM {sel_year_annual}\n"]
            for section, items in ANNUAL_CHECKS.items():
                export_lines.append(f"\n## {section}")
                for i, item in enumerate(items):
                    done = st.session_state.get(f"annual_{sel_year_annual}_{section}_{i}", False)
                    export_lines.append(f"{'☑' if done else '☐'} {item}")
            export_lines.append(f"\n---\nTiến độ: {checked_annual}/{total_annual} ({pct_a}%)")
            export_text = "\n".join(export_lines)
            st.download_button(
                "⬇️ Xuất checklist (.md)",
                data=export_text.encode("utf-8"),
                file_name=f"checklist_quyet_toan_{sel_year_annual}.md",
                mime="text/markdown",
                use_container_width=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5: GHI NHẬN LỖI
# ══════════════════════════════════════════════════════════════════════════════
elif page == "➕ Ghi nhận lỗi":
    st.markdown("## ➕ Ghi nhận lỗi quyết toán thuế")
    st.caption("Ghi lại lỗi để học hỏi và phòng ngừa tái diễn. Mỗi lỗi giúp INSAKO mạnh hơn.")

    with st.form("add_case_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Thông tin cơ bản**")
            business_type = st.text_input("Nghiệp vụ bị lỗi *", placeholder="VD: Chi phí tiếp khách")
            period = st.text_input("Kỳ phát sinh *", placeholder="VD: 2025, Q1/2025, Tháng 3/2025")
            description = st.text_area("Mô tả sai sót *", placeholder="Mô tả cụ thể: ai làm gì sai, xảy ra như thế nào...", height=100)
            dept_options = ["Kế toán", "Kinh doanh", "Kỹ thuật", "Logistics", "Nhân sự", "Ban Giám đốc"]
            departments = st.multiselect("Phòng ban liên quan", dept_options)
            root_cause = st.text_area("Nguyên nhân gốc rễ", placeholder="Tại sao sai sót xảy ra? Thiếu quy trình / Thiếu đào tạo / Lỗi nhập liệu...", height=80)

        with col2:
            st.markdown("**Đánh giá rủi ro thuế**")
            risk_opts = ["Không", "Thấp", "Trung bình", "Cao"]
            vat_risk = st.selectbox("Rủi ro VAT", risk_opts)
            tndn_risk = st.selectbox("Rủi ro TNDN", risk_opts)
            tncn_risk = st.selectbox("Rủi ro TNCN", risk_opts)
            bhxh_risk = st.selectbox("Rủi ro BHXH", risk_opts)

            st.markdown("**Thiệt hại ước tính**")
            col_x, col_y = st.columns(2)
            with col_x:
                tax_amount = st.number_input("Thuế truy thu (VNĐ)", min_value=0, step=500000)
                penalty = st.number_input("Tiền phạt (VNĐ)", min_value=0, step=100000)
            with col_y:
                late_pay = st.number_input("Chậm nộp (VNĐ)", min_value=0, step=100000)
                total = tax_amount + penalty + late_pay
                st.metric("Tổng thiệt hại", f"{total:,.0f} đ")

            st.markdown("**Xử lý**")
            handling = st.text_area("Cách xử lý hiện tại", height=60, placeholder="Đã/đang làm gì để khắc phục...")
            prevention_raw = st.text_area("Biện pháp phòng ngừa (mỗi biện pháp 1 dòng)", height=80, placeholder="1 biện pháp mỗi dòng...")
            responsible = st.text_input("Người chịu trách nhiệm", placeholder="VD: Kế toán trưởng + Trưởng phòng KD")

        submitted = st.form_submit_button("💾 Lưu lỗi", type="primary", use_container_width=True)

    if submitted:
        if not business_type or not period or not description:
            st.error("Vui lòng điền đầy đủ các trường có dấu *")
        else:
            prevention = [p.strip() for p in prevention_raw.split("\n") if p.strip()]
            case_data = {
                "business_type": business_type,
                "period": period,
                "description": description,
                "department": departments,
                "root_cause": root_cause,
                "tax_risks": {"vat": vat_risk, "tndn": tndn_risk, "tncn": tncn_risk, "bhxh": bhxh_risk},
                "tax_amount": tax_amount,
                "penalty": penalty,
                "late_payment": late_pay,
                "total_loss": total,
                "current_handling": handling,
                "prevention": prevention,
                "responsible": responsible,
                "status": "Mới phát hiện",
                "found_by": "Kế toán nội bộ",
                "source": "Tự kiểm tra",
            }
            case_id = case_svc.add_case(case_data)
            st.success(f"✅ Đã lưu lỗi thành công! Mã case: **{case_id}**")
            st.info("👉 Xem trong mục **📜 Nhật ký lỗi** để theo dõi và cập nhật trạng thái.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5: NHẬT KÝ LỖI
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📜 Nhật ký lỗi":
    st.markdown("## 📜 Nhật ký lỗi quyết toán thuế")

    cases = case_svc.list_cases()
    summary = case_svc.get_summary()

    # KPI tổng quan
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tổng số case", summary.get("total_cases", 0))
    col2.metric("Tổng thiệt hại", f"{summary.get('total_loss_estimated', 0)/1e6:.1f}M đ")
    by_status = summary.get("by_status", {})
    col3.metric("Đã xử lý", by_status.get("Đã xử lý", 0))
    col4.metric("Đang theo dõi", by_status.get("Đang theo dõi", 0) + by_status.get("Đang xử lý", 0))

    st.markdown("---")

    # Bộ lọc
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        status_filter = st.selectbox("Lọc theo trạng thái", ["Tất cả", "Mới phát hiện", "Đang xử lý", "Đang theo dõi", "Đã xử lý"])
    with col_f2:
        search = st.text_input("Tìm kiếm", placeholder="Nhập từ khóa...")

    filtered = cases
    if status_filter != "Tất cả":
        filtered = [c for c in filtered if c.get("status") == status_filter]
    if search:
        filtered = [c for c in filtered if search.lower() in json.dumps(c, ensure_ascii=False).lower()]

    st.caption(f"Hiển thị {len(filtered)}/{len(cases)} case")

    # Badge màu theo trạng thái
    STATUS_BADGE = {
        "Đã xử lý": "badge-green",
        "Đang xử lý": "badge-yellow",
        "Đang theo dõi": "badge-yellow",
        "Mới phát hiện": "badge-red",
    }
    RISK_BADGE = {"Cao": "badge-red", "Trung bình": "badge-yellow", "Thấp": "badge-green", "Không": "badge-blue"}

    for case in filtered:
        with st.expander(f"**{case.get('id')}** — {case.get('business_type')} | Kỳ: {case.get('period')} | Thiệt hại: {format_currency(case.get('total_loss', 0))}"):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"**Mô tả:** {case.get('description', '')}")
                st.markdown(f"**Nguyên nhân gốc rễ:** {case.get('root_cause', '')}")

                risks = case.get("tax_risks", {})
                risk_html = " ".join(
                    '<span class="' + RISK_BADGE.get(v, "badge-blue") + '">' + k.upper() + ': ' + v + '</span>'
                    for k, v in risks.items() if v and v != "Không"
                )
                if risk_html:
                    st.markdown(f"**Rủi ro:** {risk_html}", unsafe_allow_html=True)

                prevention = case.get("prevention", [])
                if prevention:
                    st.markdown("**Phòng ngừa:**")
                    for p in prevention:
                        st.markdown(f"  • {p}")

                handling = case.get("current_handling")
                if handling:
                    st.markdown(f"**Xử lý:** {handling}")

            with col_b:
                status = case.get("status", "")
                badge_cls = STATUS_BADGE.get(status, "badge-blue")
                st.markdown(f'<span class="{badge_cls}">{status}</span>', unsafe_allow_html=True)
                st.markdown(f"**Người chịu TN:** {case.get('responsible', '—')}")
                st.markdown(f"**Phát hiện:** {case.get('date_found', '')}")

                new_status = st.selectbox(
                    "Cập nhật trạng thái",
                    ["Mới phát hiện", "Đang xử lý", "Đang theo dõi", "Đã xử lý"],
                    index=["Mới phát hiện", "Đang xử lý", "Đang theo dõi", "Đã xử lý"].index(status) if status in ["Mới phát hiện", "Đang xử lý", "Đang theo dõi", "Đã xử lý"] else 0,
                    key=f"status_{case.get('id')}"
                )
                if st.button("💾 Lưu", key=f"save_{case.get('id')}"):
                    case_svc.update_case_status(case.get("id"), new_status)
                    st.success("Đã cập nhật!")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6: BÁO CÁO RỦI RO
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Báo cáo rủi ro":
    st.markdown("## 📊 Báo cáo rủi ro thuế")
    st.caption("Tổng hợp toàn bộ lỗi, đánh giá rủi ro và đề xuất cải thiện.")

    cases = case_svc.list_cases()
    summary = case_svc.get_summary()

    # Dashboard tổng quan
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Phân bố theo trạng thái**")
        by_status = summary.get("by_status", {})
        if by_status:
            import pandas as pd
            df_status = pd.DataFrame(list(by_status.items()), columns=["Trạng thái", "Số case"])
            st.bar_chart(df_status.set_index("Trạng thái"))

    with col2:
        st.markdown("**Phân bố theo loại rủi ro thuế**")
        by_tax = summary.get("by_tax_type", {})
        if by_tax:
            df_tax = pd.DataFrame(list(by_tax.items()), columns=["Loại thuế", "Số case"])
            st.bar_chart(df_tax.set_index("Loại thuế"))

    st.markdown("---")

    # Thống kê tài chính
    col_a, col_b, col_c = st.columns(3)
    total_tax = sum(c.get("tax_amount", 0) for c in cases)
    total_penalty = sum(c.get("penalty", 0) for c in cases)
    total_late = sum(c.get("late_payment", 0) for c in cases)
    col_a.metric("Tổng thuế truy thu", f"{total_tax/1e6:.1f}M đ")
    col_b.metric("Tổng tiền phạt", f"{total_penalty/1e6:.1f}M đ")
    col_c.metric("Tổng tiền chậm nộp", f"{total_late/1e6:.1f}M đ")

    st.markdown("---")

    # Xuất báo cáo
    st.markdown("**Xuất báo cáo đầy đủ**")
    if st.button("📊 Tạo báo cáo rủi ro", type="primary"):
        with st.spinner("Đang tạo báo cáo..."):
            content = report_tool.generate_risk_report(cases, summary)
            file_path = report_tool.save_report(content)

        st.success(f"✅ Đã tạo báo cáo: `{file_path}`")

        st.download_button(
            label="⬇️ Tải báo cáo (.md)",
            data=content.encode("utf-8"),
            file_name=f"insako_risk_report_{today_str()}.md",
            mime="text/markdown",
            use_container_width=True,
        )

        with st.expander("Xem trước báo cáo"):
            st.markdown(content)

    # Hỏi AI phân tích rủi ro
    st.markdown("---")
    st.markdown("**Hỏi AI phân tích rủi ro chuyên sâu**")
    risk_q = st.text_area("Câu hỏi phân tích", placeholder="VD: Theo các lỗi đã ghi nhận, INSAKO cần ưu tiên cải thiện quy trình nào nhất để giảm rủi ro thuế năm 2026?")
    if st.button("🤖 Phân tích AI") and risk_q:
        context = f"Dựa trên {len(cases)} case lỗi quyết toán thuế của INSAKO với tổng thiệt hại {format_currency(summary.get('total_loss_estimated', 0))}: {risk_q}"
        with st.spinner("AI đang phân tích..."):
            resp = agent.query(context)
        st.markdown(resp)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7: LỊCH SỬ CHAT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🕐 Lịch sử chat":
    st.markdown("## 🕐 Lịch sử hội thoại")
    st.caption("Xem lại các cuộc trò chuyện đã lưu trên Supabase.")

    cur_user = st.session_state.get("username", "")
    cur_is_admin = cur_user == "admin"

    # Admin xem tất cả hoặc lọc theo user; user thường chỉ thấy của mình
    filter_user = None if cur_is_admin else cur_user
    if cur_is_admin:
        col_f1, col_f2 = st.columns([2, 3])
        with col_f1:
            filter_input = st.text_input("Lọc theo username (để trống = tất cả)", placeholder="VD: ketoan")
            filter_user = filter_input.strip().lower() if filter_input.strip() else None

    sessions = supa.get_sessions(username=filter_user)

    if not sessions:
        sb_ok = supa._get_client() is not None
        if not sb_ok:
            st.warning("⚠️ Chưa kết nối Supabase. Kiểm tra SUPABASE_URL và SUPABASE_KEY trong Streamlit Secrets.")
        else:
            st.info("Chưa có lịch sử chat nào được lưu.")
    else:
        st.markdown(f"**{len(sessions)} cuộc hội thoại** được tìm thấy.")
        st.markdown("---")

        for sess in sessions:
            sid = sess["session_id"]
            started = sess["started_at"][:16].replace("T", " ") if sess.get("started_at") else "—"
            uname_label = f" | 👤 {sess['username']}" if cur_is_admin else ""
            label = f"🗓️ {started}{uname_label} | 💬 {sess['count']} tin nhắn"

            with st.expander(label):
                msgs = supa.get_session_messages(sid)
                if not msgs:
                    st.caption("Không tải được tin nhắn.")
                    continue

                # Hiển thị từng tin nhắn
                for m in msgs:
                    if m["role"] == "user":
                        with st.chat_message("user", avatar="👤"):
                            st.markdown(m["content"])
                    else:
                        with st.chat_message("assistant", avatar="📒"):
                            st.markdown(m["content"])

                # Nút export
                export_text = "\n\n".join(
                    f"[{m['role'].upper()} – {m['created_at'][:16]}]\n{m['content']}"
                    for m in msgs
                )
                st.download_button(
                    label="⬇️ Tải về .txt",
                    data=export_text.encode("utf-8"),
                    file_name=f"chat_{started.replace(' ','_').replace(':','-')}.txt",
                    mime="text/plain",
                    key=f"dl_{sid}",
                )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 8: QUẢN LÝ TÀI KHOẢN (chỉ admin)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Quản lý tài khoản":  # PAGE 8
    if not st.session_state.get("username", "") == "admin":
        st.error("⛔ Chỉ Admin mới có quyền truy cập trang này.")
        st.stop()

    st.markdown("## ⚙️ Quản lý tài khoản người dùng")
    st.caption("Thêm, sửa mật khẩu, xóa tài khoản. Thay đổi sẽ tạo ra đoạn TOML để cập nhật lên Streamlit Secrets.")

    users = _load_users()

    # ── Danh sách tài khoản ───────────────────────────────────────────────────
    st.markdown("### 👥 Danh sách tài khoản hiện tại")
    for uname, info in users.items():
        role_badge = {"admin": "🔴 Admin", "accountant": "🟡 Kế toán", "viewer": "🔵 Xem"}.get(info.get("role",""), "⚪ Khác")
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.markdown(f"**{uname}** — {info.get('name','')}")
        with col2:
            st.markdown(role_badge)
        with col3:
            st.markdown(f"`{info.get('role','')}`")

    st.markdown("---")

    # ── Tab thao tác ──────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["🔑 Đổi mật khẩu", "➕ Thêm tài khoản", "🗑️ Xóa tài khoản"])

    with tab1:
        st.markdown("#### Đổi mật khẩu người dùng")
        u_change = st.selectbox("Chọn tài khoản", list(users.keys()), key="pw_user")
        new_pw = st.text_input("Mật khẩu mới", type="password", key="pw_new")
        confirm_pw = st.text_input("Xác nhận mật khẩu", type="password", key="pw_confirm")

        if st.button("🔑 Tạo mật khẩu mới", key="btn_pw"):
            if not new_pw:
                st.error("Vui lòng nhập mật khẩu mới.")
            elif new_pw != confirm_pw:
                st.error("❌ Mật khẩu xác nhận không khớp.")
            elif len(new_pw) < 6:
                st.error("❌ Mật khẩu phải có ít nhất 6 ký tự.")
            else:
                new_hash = _hash_password(new_pw)
                updated = dict(users)
                updated[u_change]["password_hash"] = new_hash
                st.success(f"✅ Đã tạo hash mới cho **{u_change}**")
                st.markdown("**Sao chép đoạn TOML dưới đây → dán vào Streamlit Secrets:**")
                toml_lines = [f'ANTHROPIC_API_KEY = "{st.secrets.get("ANTHROPIC_API_KEY","YOUR_KEY_HERE") if hasattr(st,"secrets") else "YOUR_KEY_HERE"}"\n']
                for un, info in updated.items():
                    toml_lines.append(f'\n[users.{un}]')
                    toml_lines.append(f'name = "{info["name"]}"')
                    toml_lines.append(f'password_hash = "{info["password_hash"]}"')
                    toml_lines.append(f'role = "{info["role"]}"')
                st.code("\n".join(toml_lines), language="toml")
                st.info("📋 Vào **share.streamlit.io** → App → ⋮ → Settings → Secrets → paste đoạn trên → Save")

    with tab2:
        st.markdown("#### Thêm tài khoản mới")
        new_uname = st.text_input("Username (không dấu, không cách)", key="add_uname").strip().lower()
        new_name = st.text_input("Tên hiển thị", key="add_name")
        new_role = st.selectbox("Vai trò", ["accountant", "viewer", "admin"], key="add_role")
        add_pw = st.text_input("Mật khẩu", type="password", key="add_pw")

        if st.button("➕ Thêm tài khoản", key="btn_add"):
            if not new_uname or not new_name or not add_pw:
                st.error("Vui lòng điền đầy đủ thông tin.")
            elif new_uname in users:
                st.error(f"❌ Username **{new_uname}** đã tồn tại.")
            elif len(add_pw) < 6:
                st.error("❌ Mật khẩu phải có ít nhất 6 ký tự.")
            else:
                updated = dict(users)
                updated[new_uname] = {
                    "name": new_name,
                    "password_hash": _hash_password(add_pw),
                    "role": new_role,
                }
                st.success(f"✅ Đã thêm tài khoản **{new_uname}**")
                st.markdown("**Sao chép đoạn TOML dưới đây → dán vào Streamlit Secrets:**")
                toml_lines = [f'ANTHROPIC_API_KEY = "{st.secrets.get("ANTHROPIC_API_KEY","YOUR_KEY_HERE") if hasattr(st,"secrets") else "YOUR_KEY_HERE"}"\n']
                for un, info in updated.items():
                    toml_lines.append(f'\n[users.{un}]')
                    toml_lines.append(f'name = "{info["name"]}"')
                    toml_lines.append(f'password_hash = "{info["password_hash"]}"')
                    toml_lines.append(f'role = "{info["role"]}"')
                st.code("\n".join(toml_lines), language="toml")
                st.info("📋 Vào **share.streamlit.io** → App → ⋮ → Settings → Secrets → paste đoạn trên → Save")

    with tab3:
        st.markdown("#### Xóa tài khoản")
        deletable = [u for u in users.keys() if u != "admin"]
        if not deletable:
            st.info("Không có tài khoản nào để xóa (không thể xóa admin).")
        else:
            u_del = st.selectbox("Chọn tài khoản cần xóa", deletable, key="del_user")
            st.warning(f"⚠️ Sẽ xóa tài khoản **{u_del}** ({users[u_del].get('name','')}). Không thể hoàn tác!")
            if st.button("🗑️ Xác nhận xóa", key="btn_del", type="primary"):
                updated = {k: v for k, v in users.items() if k != u_del}
                st.success(f"✅ Đã xóa tài khoản **{u_del}**")
                st.markdown("**Sao chép đoạn TOML dưới đây → dán vào Streamlit Secrets:**")
                toml_lines = [f'ANTHROPIC_API_KEY = "{st.secrets.get("ANTHROPIC_API_KEY","YOUR_KEY_HERE") if hasattr(st,"secrets") else "YOUR_KEY_HERE"}"\n']
                for un, info in updated.items():
                    toml_lines.append(f'\n[users.{un}]')
                    toml_lines.append(f'name = "{info["name"]}"')
                    toml_lines.append(f'password_hash = "{info["password_hash"]}"')
                    toml_lines.append(f'role = "{info["role"]}"')
                st.code("\n".join(toml_lines), language="toml")
                st.info("📋 Vào **share.streamlit.io** → App → ⋮ → Settings → Secrets → paste đoạn trên → Save")
