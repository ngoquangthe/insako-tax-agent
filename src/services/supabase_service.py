"""Supabase service – lưu và truy xuất lịch sử chat."""

from __future__ import annotations
import os


def _get_client():
    """Tạo Supabase client từ secrets hoặc env."""
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


def save_message(username: str, session_id: str, role: str, content: str) -> bool:
    """Lưu 1 tin nhắn vào Supabase. Trả về True nếu thành công."""
    client = _get_client()
    if not client:
        return False
    try:
        client.table("chat_history").insert({
            "username": username,
            "session_id": session_id,
            "role": role,
            "content": content,
        }).execute()
        return True
    except Exception:
        return False


def get_history(username: str | None = None, limit: int = 200) -> list[dict]:
    """
    Lấy lịch sử chat từ Supabase.
    Nếu username=None (admin) → lấy tất cả user.
    """
    client = _get_client()
    if not client:
        return []
    try:
        q = client.table("chat_history").select("*").order("created_at", desc=True).limit(limit)
        if username:
            q = q.eq("username", username)
        result = q.execute()
        return result.data or []
    except Exception:
        return []


def get_sessions(username: str | None = None) -> list[dict]:
    """Lấy danh sách session (unique session_id) kèm thời gian và số tin nhắn."""
    client = _get_client()
    if not client:
        return []
    try:
        q = (
            client.table("chat_history")
            .select("session_id, username, created_at")
            .order("created_at", desc=True)
            .limit(500)
        )
        if username:
            q = q.eq("username", username)
        result = q.execute()
        rows = result.data or []

        # Gom nhóm theo session_id
        seen: dict[str, dict] = {}
        for r in rows:
            sid = r["session_id"]
            if sid not in seen:
                seen[sid] = {
                    "session_id": sid,
                    "username": r["username"],
                    "started_at": r["created_at"],
                    "count": 1,
                }
            else:
                seen[sid]["count"] += 1
        return list(seen.values())
    except Exception:
        return []


def get_session_messages(session_id: str) -> list[dict]:
    """Lấy toàn bộ tin nhắn của một session."""
    client = _get_client()
    if not client:
        return []
    try:
        result = (
            client.table("chat_history")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
        return result.data or []
    except Exception:
        return []
