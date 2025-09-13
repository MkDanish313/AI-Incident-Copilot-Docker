import streamlit as st
import requests
import json

API_URL = "http://backend:8000"

st.set_page_config(page_title="AI Incident Copilot", layout="wide", page_icon="🛡️")
st.title("🤖 AI Incident Copilot")

# ---------------------------
# Sidebar
# ---------------------------
st.sidebar.header("Settings")
agent = st.sidebar.selectbox("Select Agent", ["linux_agent", "aws_agent", "db_agent"])

# Fetch categories
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
except Exception:
    st.sidebar.warning("⚠️ Could not fetch agent connect command")

# ---------------------------
# Tabs
# ---------------------------
tab1, tab2 = st.tabs(["💬 Assistant", "📜 History"])

# ---------------------------
# TAB 1
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
                    with requests.post(
                        f"{API_URL}/incident",
                        json={"agent": agent, "category": category, "incident": incident},
                        stream=True,
                        timeout=600,
                    ) as resp:
                        if resp.status_code != 200:
                            st.error(f"Error: {resp.text}")
                        else:
                            response_box = st.empty()
                            full_text = ""

                            for chunk in resp.iter_lines():
                                if chunk:
                                    part = chunk.decode("utf-8")
                                    full_text += part
                                    response_box.text_area("Raw stream", full_text, height=200)

                            # Try parsing JSON at the end
                            try:
                                structured = json.loads(full_text)
                                st.success("✅ Structured AI Response")
                                st.subheader("🔍 Investigation Steps")
                                for step in structured.get("investigation", []):
                                    st.write(f"- {step}")

                                st.subheader("💻 Commands")
                                for cmd in structured.get("commands", []):
                                    st.code(cmd, language="bash")

                                st.subheader("🛠 Fixes")
                                for fix in structured.get("fixes", []):
                                    st.write(f"- {fix}")

                            except Exception:
                                st.warning("⚠️ Could not parse structured response, showing raw text instead.")
                                st.write(full_text)

                except Exception as e:
                    st.error(f"Request failed: {e}")

# ---------------------------
# TAB 2
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
