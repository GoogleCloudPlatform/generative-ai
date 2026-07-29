"""
Agent Memory Layer — Dashboard

Streamlit UI that connects to the always-on memory agent.
Visualizes memories, runs queries, and triggers operations.

Usage:
    # First start the agent:
    python agent.py

    # Then start the dashboard:
    streamlit run dashboard.py
"""

import json
import time
from pathlib import Path

import requests
import streamlit as st

AGENT_URL = "http://localhost:8888"
INBOX_DIR = Path("./inbox")

UPLOAD_EXTENSIONS = [
    "txt", "md", "json", "csv", "log", "xml", "yaml", "yml",
    "png", "jpg", "jpeg", "gif", "webp", "bmp", "svg",
    "mp3", "wav", "ogg", "flac", "m4a", "aac",
    "mp4", "webm", "mov", "avi", "mkv",
    "pdf",
]

SAMPLE_TEXTS = [
    {
        "title": "📰 AI Agents in Production",
        "text": (
            "Anthropic released a report showing that 62% of Claude usage is now "
            "code-related, with AI agents being the fastest growing category. "
            "Companies are deploying agents for customer support, code review, "
            "and data analysis. The key challenge remains reliability: agents "
            "fail silently and need human oversight loops."
        ),
    },
    {
        "title": "📧 Meeting Notes: Q1 Planning",
        "text": (
            "Discussed Q1 priorities: 1) Ship the new API by March 15, "
            "2) Hire two backend engineers, 3) Reduce inference costs by 40% "
            "by switching to smaller models for routing tasks. Sarah will lead "
            "the API project. Budget approved for $50k in cloud compute."
        ),
    },
    {
        "title": "📄 Research: Memory in LLM Systems",
        "text": (
            "Current approaches to LLM memory: 1) Vector databases with RAG: "
            "good for retrieval but no active processing. 2) Conversation "
            "summarization: loses detail over time. 3) Knowledge graphs: "
            "expensive to maintain. The gap: no system actively consolidates "
            "and connects information like human memory does."
        ),
    },
    {
        "title": "💡 Product Idea: Smart Inbox",
        "text": (
            "What if email had an AI layer that continuously reads, categorizes, "
            "and summarizes incoming mail? Not just filtering: actually understanding "
            "context across conversations. Competitors: Superhuman (fast UI, no AI "
            "summary), Shortwave (some AI, limited memory)."
        ),
    },
]


def api_get(path: str) -> dict | None:
    try:
        r = requests.get(f"{AGENT_URL}{path}", timeout=30)
        return r.json()
    except Exception as e:
        st.error(f"Agent not reachable: {e}")
        return None


def api_post(path: str, data: dict) -> dict | None:
    try:
        r = requests.post(f"{AGENT_URL}{path}", json=data, timeout=60)
        return r.json()
    except Exception as e:
        st.error(f"Agent not reachable: {e}")
        return None


def render_memory_card(m: dict):
    entities = m.get("entities", [])
    topics = m.get("topics", [])
    connections = m.get("connections", [])
    importance = m.get("importance", 0.5)

    border_color = "#4ade80" if importance >= 0.7 else "#fbbf24" if importance >= 0.4 else "#555"

    st.markdown(
        f"""<div style="border-left: 3px solid {border_color}; padding: 8px 16px;
        margin: 8px 0; background: rgba(255,255,255,0.02); border-radius: 0 8px 8px 0;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="color: #ddd;">Memory #{m['id']}</strong>
            <span style="font-size: 11px; color: #666;">{m.get('created_at', '')[:16]}
            {' | ' + m.get('source', '') if m.get('source') else ''}</span>
        </div>
        <p style="color: #bbb; margin: 8px 0; font-size: 14px;">{m['summary']}</p>
        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            {''.join(f'<span style="background: rgba(139,92,246,0.15); color: #c4b5fd; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{t}</span>' for t in topics)}
            {''.join(f'<span style="background: rgba(59,130,246,0.15); color: #93c5fd; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{e}</span>' for e in entities[:5])}
        </div>
        {'<div style="margin-top: 6px; font-size: 11px; color: #666;">🔗 ' + str(len(connections)) + ' connections</div>' if connections else ''}
        </div>""",
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(page_title="Always On Agent Memory Layer", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")

    st.markdown(
        """<style>
        .stApp { background-color: #0a0a0f; }
        .stMarkdown { color: #e8e8e8; }
        .stTextInput > div > div > input { background: #12121a; color: #e8e8e8; border-color: #222; }
        .stTextArea > div > div > textarea { background: #12121a; color: #e8e8e8; border-color: #222; }
        section[data-testid="stSidebar"] { background: #08080d; }
        .stat-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
            border-radius: 12px; padding: 16px; text-align: center; }
        .stat-number { font-size: 28px; font-weight: 700; color: #c4b5fd; }
        .stat-label { font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 0.1em; }
        </style>""",
        unsafe_allow_html=True,
    )

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Agent Status")
        stats = api_get("/status")
        if stats:
            st.markdown(f'<div class="stat-card" style="margin-bottom:8px;"><div class="stat-number" style="color:#4ade80;">●</div><div class="stat-label">Agent Online</div></div>', unsafe_allow_html=True)
            st.markdown("### 📊 Memory Stats")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f'<div class="stat-card"><div class="stat-number">{stats.get("total_memories", 0)}</div><div class="stat-label">Memories</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="stat-card"><div class="stat-number">{stats.get("unconsolidated", 0)}</div><div class="stat-label">Pending</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-card" style="margin-top:8px;"><div class="stat-number">{stats.get("consolidations", 0)}</div><div class="stat-label">Consolidations</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="stat-card" style="margin-bottom:8px;"><div class="stat-number" style="color:#ef4444;">●</div><div class="stat-label">Agent Offline</div></div>', unsafe_allow_html=True)
            st.info("Start the agent:\n```\npython agent.py\n```")

        st.markdown("---")
        st.markdown("<p style='text-align: center; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 12px;'>Powered by</p>", unsafe_allow_html=True)
        logo_col1, logo_col2 = st.columns(2)
        with logo_col1:
            st.image("docs/Gemini_logo.png", use_container_width=True)
        with logo_col2:
            st.image("docs/adk_logo.png", width=90)
        st.caption(f"Endpoint: `{AGENT_URL}`")

    # Main
    st.markdown(
        """<div style="text-align: center; padding: 20px 0 10px;">
        <span style="font-size: 48px;">🧠</span>
        <h1 style="background: linear-gradient(to right, #c4b5fd, #93c5fd);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-size: 36px; margin: 8px 0 4px;">Always On Agent Memory Layer</h1>
        <p style="color: #666; font-size: 14px; max-width: 600px; margin: 0 auto;">
            Always-on memory agent that processes, consolidates, and connects information.<br>
            Built with <strong style="color: #93c5fd;">Google ADK</strong> + <strong style="color: #c4b5fd;">Gemini 3.1 Flash-Lite</strong>.
            Runs 24/7 as a background process.
        </p>
        </div>""",
        unsafe_allow_html=True,
    )

    tab_ingest, tab_query, tab_memories = st.tabs(["📥 Ingest", "🔍 Query", "🧠 Memory Bank"])

    with tab_ingest:
        st.markdown("#### Feed information into memory")
        st.markdown("<p style='color: #666; font-size: 13px;'>Paste text or drop files in the <code>./inbox</code> folder. The <strong>IngestAgent</strong> processes everything automatically.</p>", unsafe_allow_html=True)

        input_text = st.text_area("Input", height=150, placeholder="Paste text here...", label_visibility="collapsed")

        col_ingest, col_samples = st.columns([1, 1])
        with col_ingest:
            if st.button("⚡ Process into Memory", type="primary", use_container_width=True):
                if input_text.strip():
                    with st.spinner("IngestAgent processing..."):
                        t0 = time.time()
                        result = api_post("/ingest", {"text": input_text, "source": "dashboard"})
                        elapsed = time.time() - t0
                    if result:
                        st.success(f"Processed in {elapsed:.1f}s")
                        st.markdown(result.get("response", ""))

        with col_samples:
            st.markdown("<p style='color: #555; font-size: 12px;'>Or try a sample:</p>", unsafe_allow_html=True)
            for s in SAMPLE_TEXTS:
                if st.button(s["title"], use_container_width=True):
                    with st.spinner(f"IngestAgent processing..."):
                        t0 = time.time()
                        result = api_post("/ingest", {"text": s["text"], "source": s["title"]})
                        elapsed = time.time() - t0
                    if result:
                        st.success(f"**{s['title']}** processed in {elapsed:.1f}s")
                        st.markdown(result.get("response", ""))

        st.markdown("---")
        st.markdown("#### 📎 Upload Files")
        st.markdown("<p style='color: #666; font-size: 13px;'>Upload images, audio, video, PDFs, or text files. "
                    "They'll be saved to <code>./inbox</code> and processed automatically by the agent.</p>",
                    unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "Drop files here",
            type=UPLOAD_EXTENSIONS,
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

        if uploaded_files:
            INBOX_DIR.mkdir(parents=True, exist_ok=True)
            for uf in uploaded_files:
                dest = INBOX_DIR / uf.name
                if dest.exists():
                    st.warning(f"**{uf.name}** already exists in inbox, skipping.")
                    continue
                dest.write_bytes(uf.getvalue())
                ext = Path(uf.name).suffix.lower()
                if ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
                    icon = "🖼️"
                elif ext in {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"}:
                    icon = "🎵"
                elif ext in {".mp4", ".webm", ".mov", ".avi", ".mkv"}:
                    icon = "🎬"
                elif ext == ".pdf":
                    icon = "📑"
                else:
                    icon = "📄"
                st.success(f"{icon} **{uf.name}** saved to inbox — agent will process it shortly.")

        st.markdown("---")
        st.markdown("#### 🔄 Consolidate Memories")
        st.markdown("<p style='color: #666; font-size: 13px;'>The <strong>ConsolidateAgent</strong> runs automatically every 30 minutes. Trigger it manually here.</p>", unsafe_allow_html=True)
        if st.button("🔄 Run Consolidation", use_container_width=True):
            with st.spinner("ConsolidateAgent processing..."):
                t0 = time.time()
                result = api_post("/consolidate", {})
                elapsed = time.time() - t0
            if result:
                st.success(f"Consolidated in {elapsed:.1f}s")
                st.markdown(result.get("response", ""))

    with tab_query:
        st.markdown("#### Ask your memory anything")
        st.markdown("<p style='color: #666; font-size: 13px;'>The <strong>QueryAgent</strong> searches all memories and synthesizes answers with citations.</p>", unsafe_allow_html=True)

        question = st.text_input("Question", placeholder="What do you know about AI agents?", label_visibility="collapsed")

        sample_qs = [
            "What are the main themes across everything you remember?",
            "What connections do you see between different memories?",
            "What should I focus on based on what you know?",
            "Summarize everything in 3 bullet points.",
        ]
        cols = st.columns(2)
        for i, sq in enumerate(sample_qs):
            with cols[i % 2]:
                if st.button(f"💬 {sq}", use_container_width=True):
                    question = sq

        if question:
            with st.spinner("QueryAgent searching memory..."):
                t0 = time.time()
                result = api_get(f"/query?q={question}")
                elapsed = time.time() - t0
            if result:
                st.markdown(
                    f"""<div style="background: rgba(139,92,246,0.05); border: 1px solid rgba(139,92,246,0.15);
                    border-radius: 12px; padding: 20px; margin: 16px 0;">
                    <span style="font-size: 12px; color: #a78bfa;">{elapsed:.1f}s</span>
                    <div style="color: #ddd; line-height: 1.7; margin-top: 8px;">{result.get('answer', '')}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    with tab_memories:
        st.markdown("#### Stored Memories")
        data = api_get("/memories")
        if data and data.get("memories"):
            for m in data["memories"]:
                col_card, col_del = st.columns([10, 1])
                with col_card:
                    render_memory_card(m)
                with col_del:
                    if st.button("🗑️", key=f"del_{m['id']}", help=f"Delete memory #{m['id']}"):
                        result = api_post("/delete", {"memory_id": m["id"]})
                        if result and result.get("status") == "deleted":
                            st.toast(f"Deleted memory #{m['id']}")
                            st.rerun()

            st.markdown("---")
            with st.expander("⚠️ Danger Zone"):
                st.markdown("<p style='color: #ef4444; font-size: 13px;'>This will permanently delete all memories, consolidations, processed file history, <strong>and all files in the inbox folder</strong>.</p>", unsafe_allow_html=True)
                if st.button("🗑️ Clear All Memories", type="primary", use_container_width=True):
                    result = api_post("/clear", {})
                    if result:
                        files_del = result.get("files_deleted", 0)
                        msg = f"Cleared {result.get('memories_deleted', 0)} memories"
                        if files_del:
                            msg += f" and {files_del} inbox files"
                        st.toast(msg)
                        st.rerun()
        else:
            st.info("No memories yet. Ingest some information or drop files in ./inbox")


if __name__ == "__main__":
    main()
