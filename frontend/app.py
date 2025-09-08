import os, time, requests, streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Incident Copilot", layout="wide")
st.title("🛠️ AI Incident Copilot")

# health
try:
    h = requests.get(f"{API_URL}/health", timeout=5).json()
    st.success(f"API OK • model={h.get('model')} • db={h.get('db')}")
except Exception as e:
    st.error(f"API not reachable: {e}")

# categories
cats = []
try:
    cats = requests.get(f"{API_URL}/categories", timeout=5).json()["categories"]
except Exception:
    st.warning("Could not load categories.")

col1, col2 = st.columns([1,2])
with col1:
    st.subheader("Create Incident")
    category = st.selectbox("Category", cats or ["kubernetes_crash","aws_outage","database_down","linux_high_cpu"])
    incident = st.text_area("Incident details", height=150, placeholder="Pods in CrashLoopBackOff ...")
    if st.button("Ask AI"):
        r = requests.post(f"{API_URL}/incident", json={"category": category, "incident": incident})
        if r.status_code == 200:
            st.session_state["last"] = r.json()
        else:
            st.error(r.text)

    if "last" in st.session_state:
        st.write("### AI Suggestion")
        st.code(st.session_state["last"]["response"])

with col2:
    st.subheader("Recent Incidents")
    try:
        items = requests.get(f"{API_URL}/incidents?limit=20").json()["items"]
        for it in items:
            st.markdown(f"**[{it['id']}] {it['category']}** — {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(it['ts']))}")
            st.write(it["incident"])
            st.code(it["response"])
            st.divider()
    except Exception as e:
        st.warning(f"Cannot load history: {e}")
