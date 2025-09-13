import streamlit as st
import requests

API_URL = "http://backend:8000"

st.set_page_config(page_title="AI Incident Copilot", layout="wide", page_icon="🛡️")
st.title("🤖 AI Incident Copilot")

# ---------------------------
# Sidebar (Settings + Health)
# ---------------------------
st.sidebar.header("Settings")

# Agent selection
agent = st.sidebar.selectbox("Select Agent", ["linux_agent", "aws_agent", "db_agent"])

# Fetch categories dynamically
try:
    cat_resp = requests.get(f"{API_URL}/categories", timeout=5)
    if cat_resp.status_code == 200:
        categories = cat_resp.json().get("categories", [])
    else:
        categories = []
except Exception:
    categories = []

category = st.sidebar.selectbox("Select Category", categories or ["default"])

# Agent connect command
try:
    cmd_resp = requests.get(f"{API_URL}/agent/{agent}/connect", timeout=5)
    if cmd_resp.status_code == 200:
        st.sidebar.code(cmd_resp.json()["command"], language="bash")
    else:
        st.sidebar.warning("No connect command available")
except Exception:
    st.sidebar.warning("⚠️ Could not fetch agent connect command")

# Health check
st.sidebar.subheader("⚡ System Health")
try:
    health = requests.get(f"{API_URL}/health", timeout=5).json()
    st.sidebar.success(f"Model: {health.get('model', 'unknown')}")
    st.sidebar.info(f"DB: {health.get('db', 'ok')}")
except Exception:
    st.sidebar.error("❌ Backend not reachable")

# ---------------------------
# Tabs
# ---------------------------
tab1, tab2 = st.tabs(["💬 Assistant", "📜 History"])

# ---------------------------
# TAB 1: INCIDENT ASSISTANT
# ---------------------------
with tab1:
    st.subheader("💬 Ask the AI Copilot")
    incident = st.text_area("Describe the incident:", height=120)

    if st.button("Get AI Response"):
        if not incident.strip():
            st.warning("⚠️ Please enter an incident description.")
        else:
            with st.spinner("AI is analyzing..."):
                try:
                    resp = requests.post(
                        f"{API_URL}/incident",
                        json={"agent": agent, "category": category, "incident": incident},
                        timeout=300,
                    )
                    if resp.status_code == 200:
                        st.success("AI Response:")
                        st.markdown(resp.json()["response"])
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Request failed: {e}")

# ---------------------------
# TAB 2: HISTORY VIEWER
# ---------------------------
with tab2:
    st.subheader("📜 Incident History (last 20)")

    try:
        resp = requests.get(f"{API_URL}/incidents?limit=20", timeout=10)
        if resp.status_code == 200:
            incidents = resp.json()
            if not incidents:
                st.info("No past incidents logged yet.")
            else:
                for inc in incidents:
                    with st.expander(f"{inc['timestamp']} | {inc['category']} | {inc['agent']}"):
                        st.write(f"**Incident:** {inc['incident']}")
                        st.write(f"**Response:** {inc['response']}")
        else:
            st.error(f"Failed to fetch history: {resp.text}")
    except Exception as e:
        st.error(f"Error fetching history: {e}")
