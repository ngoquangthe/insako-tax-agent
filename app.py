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
from pathlib import Path
from datetime import datetime

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
    initial_sidebar_state="expanded",
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


def _check_login(username: str, password: str, users: dict) -> bool:
    user = users.get(username.strip().lower())
    if not user:
        return False
    return hmac.compare_digest(user["password_hash"], _hash_password(password))


def _show_login():
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background: #1a1a2e; }
    .login-box {
        max-width: 420px; margin: 80px auto 0;
        background: white; border-radius: 16px;
        padding: 2.5rem 2rem; box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .login-logo { text-align:center; font-size:48px; margin-bottom:0.5rem; }
    .login-title { text-align:center; font-size:22px; font-weight:700; color:#1a1a2e; margin-bottom:0.25rem; }
    .login-sub { text-align:center; font-size:13px; color:#666; margin-bottom:1.5rem; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-logo">📒</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">INSAKO Tax Agent</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Sổ tay Kế toán – Thuế – Tài chính nội bộ</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Tên đăng nhập", placeholder="Nhập username...")
            password = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu...")
            submitted = st.form_submit_button("🔐 Đăng nhập", use_container_width=True)

            if submitted:
                users = _load_users()
                if _check_login(username, password, users):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username.strip().lower()
                    st.session_state["user_name"] = users[username.strip().lower()]["name"]
                    st.rerun()
                else:
                    st.error("❌ Sai tên đăng nhập hoặc mật khẩu")

        st.caption("Liên hệ quản trị viên nếu quên mật khẩu.")


# Kiểm tra xác thực
if not st.session_state.get("authenticated", False):
    _show_login()
    st.stop()

# ── CSS tùy chỉnh ────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Font và màu nền */
[data-testid="stAppViewContainer"] { background: #f8f9fa; }
[data-testid="stSidebar"] { background: #1a1a2e; }
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
[data-testid="stSidebar"] .stRadio label { color: #e0e0e0 !important; font-size: 15px; }
[data-testid="stSidebar"] hr { border-color: #333 !important; }

/* Card */
.insako-card {
    background: white;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    border: 1px solid #e8eaf0;
    margin-bottom: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.insako-card-title {
    font-size: 15px;
    font-weight: 600;
    color: #1a1a2e;
    margin-bottom: 0.5rem;
}

/* Chat bubble */
.chat-user {
    background: #1a1a2e;
    color: white;
    border-radius: 16px 16px 4px 16px;
    padding: 0.8rem 1.2rem;
    margin: 0.5rem 0 0.5rem 20%;
    font-size: 14px;
    line-height: 1.6;
}
.chat-ai {
    background: white;
    color: #1a1a2e;
    border-radius: 16px 16px 16px 4px;
    padding: 0.8rem 1.2rem;
    margin: 0.5rem 20% 0.5rem 0;
    font-size: 14px;
    line-height: 1.6;
    border: 1px solid #e8eaf0;
}

/* Metric card */
.metric-row {
    display: flex;
    gap: 12px;
    margin-bottom: 1rem;
}
.metric-card {
    flex: 1;
    background: white;
    border-radius: 10px;
    padding: 1rem;
    border: 1px solid #e8eaf0;
    text-align: center;
}
.metric-val { font-size: 28px; font-weight: 700; color: #1a1a2e; }
.metric-lbl { font-size: 12px; color: #666; margin-top: 2px; }

/* Badge */
.badge-red { background:#fee2e2; color:#991b1b; border-radius:20px; padding:3px 10px; font-size:12px; font-weight:600; }
.badge-yellow { background:#fef9c3; color:#854d0e; border-radius:20px; padding:3px 10px; font-size:12px; font-weight:600; }
.badge-green { background:#dcfce7; color:#166534; border-radius:20px; padding:3px 10px; font-size:12px; font-weight:600; }
.badge-blue { background:#dbeafe; color:#1e40af; border-radius:20px; padding:3px 10px; font-size:12px; font-weight:600; }

/* Quick chip */
.chip {
    display: inline-block;
    background: #f1f5f9;
    color: #334155;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 13px;
    margin: 3px;
    cursor: pointer;
    border: 1px solid #e2e8f0;
}
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
    st.markdown("### 📒 INSAKO Tax Agent")
    st.markdown("*Kế toán – Thuế – Tài chính*")
    st.markdown("---")

    api_ok = agent._client is not None
    status = "🟢 Claude API" if api_ok else "🟡 Chế độ cục bộ"
    st.markdown(f"**Trạng thái:** {status}")
    st.markdown("---")

    is_admin = st.session_state.get("username", "") == "admin"

    pages = [
        "💬 Tra cứu AI",
        "✅ Kiểm tra hồ sơ",
        "📋 Tạo checklist",
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
        for k in ["authenticated", "username", "user_name", "messages"]:
            st.session_state.pop(k, None)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: TRA CỨU AI
# ══════════════════════════════════════════════════════════════════════════════
if page == "💬 Tra cứu AI":
    st.markdown("## 💬 Tra cứu nghiệp vụ Kế toán – Thuế")
    st.caption("Hỏi bất kỳ nghiệp vụ nào. AI trả lời theo cấu trúc: hồ sơ, rủi ro, hạch toán, checklist.")

    # Câu hỏi gợi ý nhanh
    st.markdown("**Gợi ý nhanh:**")
    cols = st.columns(3)
    quick_qs = [
        "Chi phí tiếp khách ký hợp đồng bán máy phun bi",
        "Thuê kỹ thuật viên tự do lắp máy, trả tiền mặt 5 triệu",
        "Nhập khẩu máy phun bi từ Trung Quốc, thuế NK và VAT",
        "Lương KPI nhân viên kinh doanh cần hồ sơ gì?",
        "Chi phí công tác phí kỹ thuật viên đi Đà Nẵng 3 ngày",
        "Hóa đơn mua phụ tùng ghi sai địa chỉ xử lý thế nào?",
    ]
    _uname = st.session_state.get("username", "")
    _sid = st.session_state.session_id

    for i, q in enumerate(quick_qs):
        with cols[i % 3]:
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
# PAGE 4: GHI NHẬN LỖI
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
