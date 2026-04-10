from __future__ import annotations

import html
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Use the hosted embedding endpoint when credentials are configured.
# Fall back to hashing only when no embedding credentials are available.
if not (
    os.getenv("EMBEDDING_API_KEY")
    or os.getenv("LLM_API_KEY")
    or os.getenv("QWEN_API_KEY")
    or os.getenv("OPENAI_API_KEY")
):
    os.environ.setdefault("EMBEDDING_PROVIDER", "hashing")

from agent.conversation import ConversationAgent
from config import load_config
from exceptions import ConfigurationError
from logging_utils import configure_logging


TASK_BUTTONS = [
    {
        "key": "book_appointment",
        "title": "Book Appointment",
        "description": "Start the guided appointment intake flow.",
        "prompt": "I want to book an individual appointment",
    },
    {
        "key": "checklist",
        "title": "Pre-Arrival Checklist",
        "description": "Generate a checklist based on arrival stage and student type.",
        "prompt": "Give me a pre-arrival checklist",
    },
    {
        "key": "advising",
        "title": "Prepare For Advising",
        "description": "Get ready for an advising conversation step by step.",
        "prompt": "Help me prepare for an advising appointment",
    },
    {
        "key": "routing",
        "title": "Find The Right Service",
        "description": "Route a question to the most relevant CIE support page.",
        "prompt": "Who should I contact about my study permit?",
    },
    {
        "key": "uhip",
        "title": "Ask About UHIP",
        "description": "Look up coverage, onboarding, and common UHIP guidance.",
        "prompt": "What does the hub say about UHIP?",
    },
    {
        "key": "events",
        "title": "Find Events",
        "description": "Get relevant sessions and programs from CIE.",
        "prompt": "Recommend events about immigration",
    },
]


@st.cache_resource
def get_agent() -> ConversationAgent:
    try:
        configure_logging()
    except Exception as e:
        print(f"Error configuring logging: {e}")
    try:
        return ConversationAgent(load_config())
    except ConfigurationError as exc:
        st.error(
            "The hosted LLM is not configured. "
            "Set `LLM_API_KEY` in `.env` "
            "to the course-provided token before using the chat agent."
        )
        st.caption(str(exc))
        st.stop()


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;800&display=swap');
        html, body, [class*="css"] {
            font-family: "DM Sans", sans-serif;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(198, 230, 255, 0.95), transparent 34%),
                radial-gradient(circle at top right, rgba(222, 242, 255, 0.92), transparent 28%),
                linear-gradient(180deg, #eef7ff 0%, #f9fcff 100%);
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #e3f2ff 0%, #d2eaff 100%);
            border-right: 1px solid rgba(34, 104, 168, 0.12);
        }
        [data-testid="stSidebar"] * {
            color: #183554;
        }
        .sidebar-card {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(31, 113, 183, 0.10);
            border-radius: 20px;
            padding: 0.9rem 1rem;
            margin-bottom: 1rem;
            backdrop-filter: blur(8px);
        }
        .hero {
            background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(232,245,255,0.96));
            border: 1px solid rgba(45, 135, 210, 0.10);
            box-shadow: 0 24px 60px rgba(53, 114, 175, 0.08);
            border-radius: 28px;
            padding: 1.4rem 1.5rem 1.1rem 1.5rem;
            margin-bottom: 1rem;
        }
        .hero-badge {
            display: inline-block;
            background: linear-gradient(90deg, #2f7ec3, #60b4ef);
            color: white;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            padding: 0.35rem 0.65rem;
            border-radius: 999px;
            margin-bottom: 0.8rem;
        }
        .hero-title {
            font-size: 3.15rem;
            line-height: 0.98;
            font-weight: 800;
            letter-spacing: -0.04em;
            color: #192338;
            margin: 0;
        }
        .hero-subtitle {
            margin-top: 0.85rem;
            color: #56657f;
            font-size: 1.02rem;
            max-width: 54rem;
        }
        .empty-state {
            background: rgba(255,255,255,0.82);
            border: 1px dashed rgba(60, 146, 220, 0.30);
            border-radius: 24px;
            padding: 1.2rem 1.3rem;
            margin-top: 0.6rem;
        }
        .empty-title {
            color: #19314f;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }
        .empty-copy {
            color: #5f6d83;
            margin-bottom: 0.75rem;
        }
        .chips {
            display: flex;
            gap: 0.55rem;
            flex-wrap: wrap;
        }
        .chip {
            border-radius: 999px;
            padding: 0.45rem 0.75rem;
            background: #e0f0ff;
            color: #1d5e93;
            font-size: 0.9rem;
            border: 1px solid rgba(60, 146, 220, 0.16);
        }
        .task-heading {
            color: #19314f;
            font-size: 0.95rem;
            font-weight: 800;
            margin: 0.2rem 0 0.65rem 0;
        }
        .task-copy {
            color: #5f6d83;
            font-size: 0.88rem;
            line-height: 1.45;
            margin-bottom: 0.7rem;
            min-height: 2.8rem;
        }
        .task-card {
            background: rgba(255,255,255,0.82);
            border: 1px solid rgba(60, 146, 220, 0.16);
            border-radius: 22px;
            padding: 1rem 1rem 0.35rem 1rem;
            margin-bottom: 0.85rem;
            box-shadow: 0 14px 32px rgba(53, 114, 175, 0.06);
        }
        .task-title {
            color: #163554;
            font-size: 1rem;
            font-weight: 800;
            margin-bottom: 0.4rem;
        }
        .chat-avatar {
            width: 3.35rem;
            height: 3.35rem;
            border-radius: 1.05rem;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 14px 28px rgba(47, 115, 181, 0.14);
            margin-top: 0.15rem;
            border: 1px solid rgba(82, 149, 214, 0.16);
            overflow: hidden;
        }
        .chat-row {
            margin-bottom: 1.5rem;
        }
        .chat-avatar-user {
            background: linear-gradient(135deg, #d9ecff 0%, #f7fbff 100%);
        }
        .chat-avatar-assistant {
            background: linear-gradient(135deg, #2b7fd1 0%, #6db5f3 100%);
        }
        .chat-avatar svg {
            width: 100%;
            height: 100%;
            display: block;
        }
        .user-bubble {
            background: linear-gradient(135deg, rgba(255,255,255,0.94), rgba(240,247,255,0.96));
            border: 1px solid rgba(60, 146, 220, 0.16);
            border-radius: 1.4rem;
            padding: 1rem 1.1rem;
            color: #213049;
            font-size: 1.02rem;
            line-height: 1.45;
            box-shadow: 0 16px 32px rgba(53, 114, 175, 0.08);
            text-align: left;
        }
        .assistant-bubble {
            background: rgba(255,255,255,0.95);
            border: 1px solid rgba(60, 146, 220, 0.10);
            border-radius: 1.4rem;
            padding: 0.8rem 1rem 0.85rem 1rem;
            box-shadow: none;
            text-shadow: none;
            filter: none;
            backdrop-filter: none;
        }
        .rename-hint {
            font-size: 0.72rem;
            color: #7a91ab;
            margin-top: -0.05rem;
            margin-bottom: 0.35rem;
        }
        [data-testid="stSidebar"] .stTextInput input {
            border-radius: 12px;
            border: 1px solid rgba(60, 146, 220, 0.22);
            background: rgba(255,255,255,0.95);
            color: #183554;
        }
        div.stButton > button {
            border-radius: 14px;
            border: 1px solid rgba(32, 103, 165, 0.14);
        }
        .chat-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: #163554;
            margin-bottom: 0.18rem;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }
        .chat-meta {
            font-size: 0.74rem;
            color: #5d7692;
            margin-bottom: 0.22rem;
        }
        .chat-preview {
            font-size: 0.82rem;
            color: #5d7692;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            line-height: 1.35;
        }
        .chat-card {
            background: rgba(255,255,255,0.82);
            border: 1px solid rgba(32, 103, 165, 0.10);
            border-radius: 18px;
            padding: 0.85rem 0.9rem 0.75rem 0.9rem;
            margin-bottom: 0.45rem;
        }
        .chat-card-active {
            background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(226,242,255,0.96));
            border: 1px solid rgba(60, 146, 220, 0.28);
            box-shadow: 0 10px 24px rgba(60, 146, 220, 0.10);
        }
        .sidebar-heading {
            font-size: 0.82rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #6180a0;
            margin-top: 0.4rem;
            margin-bottom: 0.5rem;
        }
        [data-testid="stSidebar"] .stButton button[kind="primary"] {
            background: linear-gradient(90deg, #3187cf, #63b8f0);
            color: white;
            border: none;
        }
        [data-testid="stSidebar"] .stButton button[kind="secondary"] {
            background: rgba(255,255,255,0.82);
            color: #183554;
        }
        .sidebar-section-label {
            font-size: 0.78rem;
            font-weight: 700;
            color: #6a86a3;
            margin-top: 0.2rem;
            margin-bottom: 0.4rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def dedupe_sources(sources: list[dict], max_sources: int = 3) -> list[dict]:
    unique_sources: list[dict] = []
    seen_url_keys: set[str] = set()
    seen_fallback_keys: set[tuple[str, str]] = set()
    for source in sources:
        title = str(source.get("title", "")).strip().lower()
        section = str(source.get("section", "")).strip().rstrip(":").lower()
        raw_url = str(source.get("url", "")).strip()
        if raw_url:
            parts = urlsplit(raw_url)
            raw_url = urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))

        if raw_url:
            if raw_url in seen_url_keys:
                continue
            seen_url_keys.add(raw_url)
            compact_source = dict(source)
            compact_source["url"] = raw_url
            compact_source["_hide_section"] = True
            unique_sources.append(compact_source)
        else:
            fallback_key = (title, section)
            if fallback_key in seen_fallback_keys:
                continue
            seen_fallback_keys.add(fallback_key)
            unique_sources.append(source)

        if len(unique_sources) >= max_sources:
            break
    return unique_sources


def render_sources(sources: list[dict]) -> None:
    compact_sources = dedupe_sources(sources)
    if not compact_sources:
        return
    st.markdown("**Sources**")
    for source in compact_sources:
        title = source.get("title", "Source").strip() or "Source"
        section = source.get("section", "").strip().rstrip(":")
        label = f"[{title}]({source.get('url', '')})"
        hide_section = bool(source.get("_hide_section"))
        if not hide_section and section and section.lower() != title.lower():
            st.markdown(f"- {label} - {section}")
        else:
            st.markdown(f"- {label}")


def render_avatar(role: str) -> None:
    avatar_class = "chat-avatar-user" if role == "user" else "chat-avatar-assistant"
    if role == "user":
        avatar_markup = """
        <svg viewBox="0 0 64 64" aria-hidden="true">
          <defs>
            <linearGradient id="userBg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#e8f4ff"/>
              <stop offset="100%" stop-color="#fdfefe"/>
            </linearGradient>
            <linearGradient id="userRing" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#2c7fd2"/>
              <stop offset="100%" stop-color="#78bdf6"/>
            </linearGradient>
          </defs>
          <rect x="1.5" y="1.5" width="61" height="61" rx="19" fill="url(#userBg)"/>
          <rect x="1.5" y="1.5" width="61" height="61" rx="19" fill="none" stroke="url(#userRing)" stroke-width="1.5"/>
          <circle cx="32" cy="25" r="9" fill="#2f7ec3"/>
          <path d="M18 48c2.7-8 9.2-12 14-12s11.3 4 14 12" fill="#2f7ec3"/>
          <circle cx="32" cy="32" r="22" fill="none" stroke="#d2e9ff" stroke-width="1.6"/>
        </svg>
        """
    else:
        avatar_markup = """
        <svg viewBox="0 0 64 64" aria-hidden="true">
          <defs>
            <linearGradient id="assistantBg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#2c7fd2"/>
              <stop offset="100%" stop-color="#7ac1f7"/>
            </linearGradient>
          </defs>
          <rect x="1.5" y="1.5" width="61" height="61" rx="19" fill="url(#assistantBg)"/>
          <rect x="1.5" y="1.5" width="61" height="61" rx="19" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="1.5"/>
          <rect x="18" y="19" width="28" height="24" rx="8" fill="white" opacity="0.98"/>
          <rect x="26" y="14" width="12" height="6" rx="3" fill="white" opacity="0.92"/>
          <circle cx="27" cy="31" r="2.6" fill="#2f7ec3"/>
          <circle cx="37" cy="31" r="2.6" fill="#2f7ec3"/>
          <path d="M25.5 35.5c2.1 2.9 4.3 4.2 6.5 4.2s4.4-1.3 6.5-4.2" fill="none" stroke="#2f7ec3" stroke-width="2.4" stroke-linecap="round"/>
          <path d="M21 46l4-4h14l4 4" fill="none" stroke="white" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        """
    st.markdown(
        f'<div class="chat-avatar {avatar_class}">{avatar_markup}</div>',
        unsafe_allow_html=True,
    )


def render_user_message(content: str) -> None:
    st.markdown('<div class="chat-row">', unsafe_allow_html=True)
    spacer_col, message_col, avatar_col = st.columns([0.14, 0.70, 0.16], vertical_alignment="top")
    with message_col:
        st.markdown(f'<div class="user-bubble">{html.escape(content)}</div>', unsafe_allow_html=True)
    with avatar_col:
        render_avatar("user")
    st.markdown("</div>", unsafe_allow_html=True)


def render_assistant_message(content: str, sources: list[dict]) -> None:
    st.markdown('<div class="chat-row">', unsafe_allow_html=True)
    avatar_col, message_col, spacer_col = st.columns([0.16, 0.70, 0.14], vertical_alignment="top")
    with avatar_col:
        render_avatar("assistant")
    with message_col:
        st.markdown(content)
        render_sources(sources)
    st.markdown("</div>", unsafe_allow_html=True)


def hydrate_session_messages(agent: ConversationAgent, session_id: str) -> list[dict]:
    session = agent.memory.get_session(session_id)
    return [
        {
            "role": message.role,
            "content": message.content,
            "sources": [source.model_dump() for source in message.sources],
        }
        for message in session.history
    ]


def ensure_state(agent: ConversationAgent) -> None:
    if "chat_cache" not in st.session_state:
        st.session_state.chat_cache = {}
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None
    if "editing_session_id" not in st.session_state:
        st.session_state.editing_session_id = None
    sessions = agent.memory.list_sessions()
    if "active_session_id" not in st.session_state:
        st.session_state.active_session_id = sessions[0]["session_id"] if sessions else agent.new_session_id()
    active_session_id = st.session_state.active_session_id
    if active_session_id not in st.session_state.chat_cache:
        st.session_state.chat_cache[active_session_id] = hydrate_session_messages(agent, active_session_id)


def start_new_chat(agent: ConversationAgent) -> None:
    session_id = agent.new_session_id()
    st.session_state.active_session_id = session_id
    st.session_state.chat_cache[session_id] = []
    st.session_state.editing_session_id = None


def begin_rename_session(session_id: str, title: str) -> None:
    st.session_state.editing_session_id = session_id
    st.session_state[f"rename_input_{session_id}"] = title


def commit_rename_session(agent: ConversationAgent, session_id: str) -> None:
    title = str(st.session_state.get(f"rename_input_{session_id}", "")).strip()
    cleaned_title = " ".join(title.split()).strip()
    if hasattr(agent.memory, "rename_session"):
        agent.memory.rename_session(session_id, cleaned_title)
    else:
        session = agent.memory.get_session(session_id)
        session.title = cleaned_title[:80] if cleaned_title else None
        agent.memory.save_session(session)
    st.session_state.editing_session_id = None


def process_prompt(agent: ConversationAgent, session_id: str, prompt: str) -> None:
    st.session_state.chat_cache.setdefault(session_id, [])
    st.session_state.chat_cache[session_id].append({"role": "user", "content": prompt, "sources": []})
    render_user_message(prompt)

    st.markdown('<div class="chat-row">', unsafe_allow_html=True)
    assistant_col, message_col, _ = st.columns([0.16, 0.70, 0.14], vertical_alignment="top")
    with assistant_col:
        render_avatar("assistant")

    assistant_payload: dict[str, str | list[dict]] = {
        "role": "assistant",
        "content": "",
        "sources": [],
    }
    response = None
    try:
        with message_col:
            placeholder = st.empty()
            with placeholder.container():
                with st.spinner("Preparing a response..."):
                    _, response = agent.handle_message(prompt, session_id)
            placeholder.empty()
        if response is not None:
            assistant_payload = {
                "role": "assistant",
                "content": response.answer,
                "sources": [source.model_dump() for source in response.sources],
            }
    except Exception as exc:  # noqa: BLE001
        assistant_payload = {
            "role": "assistant",
            "content": (
                "I hit a system error while processing that request. "
                "Please check the hosted LLM configuration and try again."
            ),
            "sources": [],
        }
        st.error(str(exc))
        with message_col:
            st.markdown(str(assistant_payload["content"]))
    st.markdown("</div>", unsafe_allow_html=True)
    st.session_state.chat_cache[session_id].append(assistant_payload)
    st.rerun()


def format_timestamp(raw: str) -> str:
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%b %d, %H:%M")
    except ValueError:
        return raw


def pick_next_session(agent: ConversationAgent) -> str:
    sessions = agent.memory.list_sessions()
    if sessions:
        return str(sessions[0]["session_id"])
    return agent.new_session_id()


def render_session_card(agent: ConversationAgent, item: dict[str, str | int | bool]) -> None:
    session_id = str(item["session_id"])
    title = str(item["title"])
    preview = str(item["preview"])
    updated_at = format_timestamp(str(item["updated_at"]))
    active = session_id == st.session_state.active_session_id
    card_class = "chat-card chat-card-active" if active else "chat-card"
    is_editing = st.session_state.editing_session_id == session_id

    st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
    if is_editing:
        st.text_input(
            "Rename session",
            key=f"rename_input_{session_id}",
            label_visibility="collapsed",
            on_change=commit_rename_session,
            args=(agent, session_id),
            placeholder="Enter a conversation name",
        )
        st.markdown('<div class="rename-hint">Click outside the input or press Enter to save.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="chat-meta">{updated_at or "Saved chat"}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="chat-preview">{preview or "Open this conversation"}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Open", key=f"open_{session_id}", use_container_width=True):
        st.session_state.active_session_id = session_id
        st.session_state.chat_cache[session_id] = hydrate_session_messages(agent, session_id)
        st.session_state.editing_session_id = None
        st.rerun()

    if is_editing:
        st.button("Editing", key=f"editing_{session_id}", use_container_width=True, disabled=True)
    else:
        if st.button("Rename", key=f"rename_{session_id}", use_container_width=True):
            begin_rename_session(session_id, title)
            st.rerun()

    if st.button("Archive", key=f"archive_{session_id}", use_container_width=True):
        agent.memory.archive_session(session_id)
        st.session_state.chat_cache.pop(session_id, None)
        st.session_state.editing_session_id = None
        if st.session_state.active_session_id == session_id:
            st.session_state.active_session_id = pick_next_session(agent)
        st.rerun()

    if st.button("Delete", key=f"delete_{session_id}", use_container_width=True):
        agent.memory.delete_session(session_id)
        st.session_state.chat_cache.pop(session_id, None)
        st.session_state.editing_session_id = None
        if st.session_state.active_session_id == session_id:
            st.session_state.active_session_id = pick_next_session(agent)
        st.rerun()


def render_sidebar(agent: ConversationAgent) -> None:
    with st.sidebar:
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        st.markdown("## Conversations")
        st.caption("Start a new thread or reopen a previous one.")
        if st.button("New chat", use_container_width=True, type="primary"):
            start_new_chat(agent)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="sidebar-heading">Saved Chats</div>', unsafe_allow_html=True)
        sessions = agent.memory.list_sessions()
        if not sessions:
            st.info("No saved chats yet. Start a conversation to create one.")
        else:
            for item in sessions:
                render_session_card(agent, item)

        archived = [item for item in agent.memory.list_sessions(include_archived=True) if item["archived"]]
        if archived:
            with st.expander("Archived conversations", expanded=False):
                st.markdown(
                    '<div class="sidebar-section-label">Restore or permanently remove archived chats</div>',
                    unsafe_allow_html=True,
                )
                for item in archived:
                    session_id = str(item["session_id"])
                    title = str(item["title"])
                    preview = str(item["preview"])
                    updated_at = format_timestamp(str(item["updated_at"]))
                    st.markdown(
                        f"""
                        <div class="chat-card">
                          <div class="chat-title">{title}</div>
                          <div class="chat-meta">{updated_at or "Archived chat"}</div>
                          <div class="chat-preview">{preview or "Archived conversation"}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    restore_col, purge_col = st.columns([1.5, 1.0])
                    with restore_col:
                        if st.button("Restore", key=f"restore_{session_id}", use_container_width=True):
                            agent.memory.unarchive_session(session_id)
                            st.rerun()
                    with purge_col:
                        if st.button("Delete", key=f"purge_{session_id}", use_container_width=True):
                            agent.memory.delete_session(session_id)
                            st.session_state.chat_cache.pop(session_id, None)
                            st.rerun()


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero">
          <div class="hero-badge">University of Toronto • CIE</div>
          <h1 class="hero-title">Resource Hub Agent</h1>
          <div class="hero-subtitle">
            A conversational assistant for international student support, built on the Centre for International Experience
            Resource Hub with retrieval, action workflows, and cited answers.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    st.markdown(
        """
        <div class="empty-state">
          <div class="empty-title">Ask a question or start a task</div>
          <div class="empty-copy">
            You can ask about UHIP, finances, immigration resources, the U of T roadmap, or use actions like
            checklist generation, appointment booking intake, and advising preparation.
          </div>
          <div class="chips">
            <div class="chip">What does the hub say about UHIP?</div>
            <div class="chip">I want to book an individual appointment</div>
            <div class="chip">Give me a pre-arrival checklist</div>
            <div class="chip">Help me prepare for advising</div>
            <div class="chip">Who should I contact about my study permit?</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_task_buttons() -> None:
    st.markdown('<div class="task-heading">Start A Task</div>', unsafe_allow_html=True)
    for index in range(0, len(TASK_BUTTONS), 3):
        row = TASK_BUTTONS[index : index + 3]
        columns = st.columns(len(row))
        for column, task in zip(columns, row):
            with column:
                st.markdown(
                    f"""
                    <div class="task-card">
                      <div class="task-title">{task["title"]}</div>
                      <div class="task-copy">{task["description"]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(task["title"], key=f"task_{task['key']}", use_container_width=True):
                    st.session_state.pending_prompt = task["prompt"]
                    st.rerun()


def main() -> None:
    st.set_page_config(page_title="UofT CIE Resource Hub Agent", page_icon="🎓", layout="wide")
    agent = get_agent()
    inject_styles()
    ensure_state(agent)
    render_sidebar(agent)
    render_hero()
    render_task_buttons()

    active_session_id = st.session_state.active_session_id
    incoming_prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None
    prompt = st.chat_input("Ask about the CIE Resource Hub or request an action...")
    if prompt:
        incoming_prompt = prompt

    chat_history = st.session_state.chat_cache.get(active_session_id, [])
    if not chat_history:
        render_empty_state()

    for item in chat_history:
        if item["role"] == "user":
            render_user_message(str(item["content"]))
        else:
            render_assistant_message(str(item["content"]), item.get("sources", []))

    if incoming_prompt:
        process_prompt(agent, active_session_id, incoming_prompt)


if __name__ == "__main__":
    main()
