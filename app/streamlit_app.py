from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.conversation import ConversationAgent
from config import load_config
from logging_utils import configure_logging


@st.cache_resource
def get_agent() -> ConversationAgent:
    configure_logging()
    return ConversationAgent(load_config())


def dedupe_sources(sources: list[dict], max_sources: int = 3) -> list[dict]:
    unique_sources: list[dict] = []
    seen_urls: set[str] = set()
    for source in sources:
        url = source.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
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
        if section and section.lower() != title.lower():
            st.markdown(f"- {label} - {section}")
        else:
            st.markdown(f"- {label}")


def main() -> None:
    st.set_page_config(page_title="UofT CIE Resource Hub Agent", page_icon="🎓", layout="wide")
    st.title("UofT CIE Resource Hub Conversational Agent")
    st.caption("RAG-powered assistant for the Centre for International Experience Resource and Information Hub")

    agent = get_agent()
    if "session_id" not in st.session_state:
        st.session_state.session_id = agent.new_session_id()
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    with st.sidebar:
        st.subheader("Session")
        st.code(st.session_state.session_id)
        if st.button("Reset conversation"):
            agent.memory.reset_session(st.session_state.session_id)
            st.session_state.session_id = agent.new_session_id()
            st.session_state.chat_history = []
            st.rerun()

    for item in st.session_state.chat_history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
            render_sources(item.get("sources", []))

    prompt = st.chat_input("Ask about the CIE Resource Hub or request an action...")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        _, response = agent.handle_message(prompt, st.session_state.session_id)
        assistant_payload = {
            "role": "assistant",
            "content": response.answer,
            "sources": [source.model_dump() for source in response.sources],
        }
        st.session_state.chat_history.append(assistant_payload)

        with st.chat_message("assistant"):
            st.markdown(response.answer)
            render_sources([source.model_dump() for source in response.sources])


if __name__ == "__main__":
    main()
