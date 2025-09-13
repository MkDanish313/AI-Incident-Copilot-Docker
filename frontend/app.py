import streamlit as st
import requests

API_URL = "http://backend:8000"

st.set_page_config(page_title="AI Incident Copilot", layout="wide", page_icon="🛡️")

st.title("🤖 AI Incident Copilot")

# ---------------------------
# Sidebar (Settings + Health)
# ---------------------------
st.sidebar.header("⚙️ Settings")

agent = st.sidebar.selectbox("Select Agent", ["linux", "aws", "db"])

# Fetch categories from API (fallback to defaults)
try:
    cat_resp = requests.get(f"{API_URL}/categories", timeout=5)
    if cat_resp.status_code == 200:
        categories = cat_resp.json().get("categories", [])
    else:
        categories = ["aws_outage", "kubernetes_crash", "database_down", "network_issue", "linux_issue"]
except Exception:
    categories = ["aws_outage", "kubernetes_crash", "database_down", "network_issue", "linux_issue"]

category = st.sidebar.selectbox("Select Category", categories)

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

    incident = st.text_area("Describe the incident (paste logs, metrics, errors):", height=150)

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
                    if resp.status_code != 200:
                        st.error(f"Error: {resp.text}")
                    else:
                        data = resp.json()
                        result = data.get("response_json", {})
                        raw_text = data.get("response_text", "")
                        agent_connect = data.get("agent_connect", "")

                        st.success("✅ AI Response (Structured)")

                        # Investigation Steps
                        if result.get("investigation_steps"):
                            st.markdown("### 🔍 Investigation Steps")
                            for step in result["investigation_steps"]:
                                st.write(f"- {step}")

                        # Commands
                        if result.get("commands"):
                            st.markdown("### 💻 Suggested Commands")
                            for cmd in result["commands"]:
                                st.code(cmd, language="bash")

                        # Fixes
                        if result.get("fixes"):
                            st.markdown("### 🛠️ Recommended Fixes")
                            for fix in result["fixes"]:
                                st.write(f"- {fix}")

                        # Severity
                        st.markdown("### 🚨 Severity")
                        st.write(result.get("severity", "unknown").capitalize())

                        # Recommended Action
                        st.markdown("### 🎯 Recommended Action")
                        st.write(result.get("recommended_action", "investigate"))

                        # Notes (fallback)
                        if result.get("notes"):
                            st.markdown("### 📝 Notes")
                            st.write(result["notes"])

                        # Agent Connect
                        if agent_connect:
                            st.markdown("### 🔗 Agent Connect Command")
                            st.code(agent_connect, language="bash")

                        # Raw Text fallback
                        if not result or not any(result.values()):
                            st.warning("⚠️ Structured output missing. Showing raw model response:")
                            st.text(raw_text)

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
            incidents = resp.json().get("items", [])
            if not incidents:
                st.info("No past incidents logged yet.")
            else:
                for inc in incidents:
                    with st.expander(f"{inc['timestamp']} | {inc['category']} | {inc['agent']}"):
                        st.write(f"**Incident:** {inc['incident']}")

                        parsed = inc.get("response_json")
                        if parsed:
                            st.markdown("**Investigation Steps:**")
                            for step in parsed.get("investigation_steps", []):
                                st.write(f"- {step}")

                            st.markdown("**Commands:**")
                            for cmd in parsed.get("commands", []):
                                st.code(cmd, language="bash")

                            st.markdown("**Fixes:**")
                            for fix in parsed.get("fixes", []):
                                st.write(f"- {fix}")

                            st.write(f"**Severity:** {parsed.get('severity')}")
                            st.write(f"**Recommended Action:** {parsed.get('recommended_action')}")
                            st.write(f"**Notes:** {parsed.get('notes', '')}")

                        else:
                            st.text(inc.get("response_text", ""))
        else:
            st.error(f"Failed to fetch history: {resp.text}")
    except Exception as e:
        st.error(f"Error fetching history: {e}")
