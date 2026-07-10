#!/usr/bin/env python3
"""
Streamlit web interface for the AI Web Research Assistant.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st
from ai_researcher import ResearchAssistant


st.set_page_config(
    page_title="AI Web Research Assistant",
    page_icon="🔍",
    layout="centered",
)

st.title("🔍 AI Web Research Assistant")
st.markdown(
    "Ask any question. The assistant searches **Wikipedia** and the **web**, "
    "scrapes the top results, and synthesizes a cited answer."
)

# Sidebar settings
with st.sidebar:
    st.header("Settings")
    web_results = st.slider("Web sources to scrape", 1, 10, 4)
    st.markdown("---")
    st.markdown(
        "**Power user tip:** Set `OPENAI_API_KEY` in a `.env` file or environment "
        "for natural LLM-generated answers. Without it, a local extractive "
        "summary is used."
    )

query = st.text_input(
    "Your research question",
    placeholder="e.g., What is quantum computing?",
)

if st.button("Research", type="primary") and query.strip():
    progress = st.empty()

    def update(msg: str) -> None:
        progress.info(msg)

    assistant = ResearchAssistant(
        max_web_results=web_results,
        progress_callback=update,
    )

    with st.spinner("Researching..."):
        result = assistant.research(query.strip())

    progress.empty()

    st.subheader("🤖 Answer")
    st.write(result["answer"])

    if result["wikipedia_summary"]:
        with st.expander("📚 Wikipedia Summary"):
            st.write(result["wikipedia_summary"])
            if result["wikipedia_url"]:
                st.markdown(f"[Read more on Wikipedia]({result['wikipedia_url']})")

    with st.expander("🔗 Sources"):
        for i, source in enumerate(result["sources"], start=1):
            st.markdown(f"**{i}. {source['title']}**")
            st.markdown(f"URL: [{source['url']}]({source['url']})")
            st.caption(source["snippet"][:300])
            st.divider()
