from __future__ import annotations

import os
import httpx
import streamlit as st

API = os.getenv("DASHBOARD_API_URL", "http://localhost:8000")

st.set_page_config(page_title="Strategic Intelligence Monitor", page_icon="📡", layout="wide")
st.title("Strategic Intelligence Monitor")
st.caption("Internal strategic news intelligence for agency teams")

section = st.sidebar.radio("Section", ["Today", "Search", "Industries", "Clients", "Signals", "Trends", "Sources"])


def get(path: str, params: dict | None = None):
    with httpx.Client(timeout=30) as client:
        res = client.get(f"{API}{path}", params=params)
        res.raise_for_status()
        return res.json()


def post(path: str):
    with httpx.Client(timeout=120) as client:
        res = client.post(f"{API}{path}")
        res.raise_for_status()
        return res.json()


if st.sidebar.button("Collect now", use_container_width=True):
    with st.spinner("Collecting sources…"):
        st.sidebar.success(f"Completed: {post('/api/collect')['results']}")

if section == "Today":
    data = get("/api/articles", {"days": 2, "min_score": 2.5, "limit": 50})
    st.metric("Relevant items", data["total"])
    for a in data["items"]:
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            c1.subheader(a["title"])
            c2.metric("Score", a["strategic_relevance_score"])
            st.caption(f"{a.get('source_name') or ''} · {a.get('published_at') or ''} · {', '.join(a.get('industries') or [])}")
            st.write(a.get("summary") or "")
            if a.get("why_it_matters"):
                st.markdown(f"**Почему важно:** {a['why_it_matters']}")
            st.link_button("Open source", a["url"])

elif section == "Search":
    q = st.text_input("Search archive", placeholder="Например: банки молодежь, retail media, sponsorship automotive")
    semantic = st.toggle("Semantic search", value=False)
    if q:
        endpoint = "/api/search/semantic" if semantic else "/api/search"
        for a in get(endpoint, {"q": q, "limit": 40}):
            with st.container(border=True):
                st.subheader(a["title"])
                st.write(a.get("strategic_summary") or a.get("summary") or "")
                st.caption(f"Score {a['strategic_relevance_score']} · {a.get('source_name')}")
                st.link_button("Source", a["url"])

elif section == "Industries":
    industry = st.selectbox("Industry", ["Automotive", "Banking", "Fintech", "Retail", "E-commerce", "FMCG", "Technology", "Telecom", "Pharma", "Beauty", "Real Estate", "Travel", "Other"])
    data = get("/api/articles", {"industry": industry, "days": 90, "limit": 100})
    st.write(f"Found: {data['total']}")
    for a in data["items"]:
        st.markdown(f"**[{a['title']}]({a['url']})** — {a.get('summary') or ''}")

elif section == "Clients":
    clients = get("/api/clients")
    if clients:
        selected = st.selectbox("Client", clients, format_func=lambda x: x["name"])
        st.write("**Competitors:**", ", ".join(selected.get("competitors", [])))
        for a in get(f"/api/clients/{selected['slug']}/articles", {"limit": 100}):
            with st.container(border=True):
                st.subheader(a["title"])
                match = a.get("client_matches", {}).get(selected["slug"], {})
                st.caption(f"Client relevance {match.get('score', '—')} · Strategic {a['strategic_relevance_score']}")
                st.write(a.get("why_it_matters") or a.get("summary") or "")

elif section == "Signals":
    for s in get("/api/signals", {"days": 30}):
        with st.container(border=True):
            st.subheader(s["title"])
            st.write(s["description"])
            st.markdown(f"**Implication:** {s['strategic_implication']}")
            st.caption(f"Confidence {s['confidence']} · {s['article_count']} materials")

elif section == "Trends":
    days = st.select_slider("Period", options=[1, 7, 30, 90], value=30)
    data = get("/api/trends", {"days": days})
    st.metric("Articles", data["articles"])
    for key in ["topics", "industries", "brands"]:
        st.subheader(key.title())
        st.bar_chart({name: count for name, count in data[key]})

elif section == "Sources":
    health = get("/api/health")
    st.json(health)
    st.info("Source health details are stored in the database; admin source editor is planned for the next UI iteration.")
