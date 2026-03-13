from datetime import date

import requests
import streamlit as st

API_BASE_URL = st.sidebar.text_input("Backend URL", "http://localhost:8000")

st.title("DynPro Brain - Phase 1 MVP Scaffold")
st.caption("Decision support for capability intelligence (human-in-the-loop).")

workflow = st.selectbox(
    "Workflow",
    ["expert_finder", "interviewer_finder", "client_domain_finder"],
)
text_query = st.text_area("What are you trying to find?", height=100)
skills = st.text_input("Skill filters (comma-separated)")
domains = st.text_input("Domain filters (comma-separated)")
client_name = st.text_input("Client name (e.g., FinBank)")
domain_name = st.text_input("Domain name (e.g., BFSI)")

internal_external = st.selectbox("Internal/External", ["Any", "internal", "external"])
country = st.text_input("Country filter (exact, e.g., India)")
timezone = st.text_input("Timezone filter (exact, e.g., IST)")
practice = st.text_input("Practice filter (exact, e.g., Data & AI)")
minimum_available_percent = st.slider(
    "Minimum available percent", min_value=0, max_value=100, value=0, step=5
)
max_bill_rate = st.number_input(
    "Max bill rate (optional)", min_value=0.0, value=0.0, step=5.0,
    help="Use this when you want budget-aware matching without showing raw commercial detail in results."
)
budget_band = st.selectbox("Budget band", ["Any", "economy", "standard", "premium"])
interviewer_only = st.checkbox("Interviewer only")
minimum_prior_interview_count = st.number_input(
    "Minimum prior interview count", min_value=0, value=0, step=1
)
use_available_by_date = st.checkbox("Only include people available by a date")
available_by_date = st.date_input("Available by date", value=date.today(), disabled=not use_available_by_date)

if st.button("Run Search"):
    if not text_query.strip():
        st.warning("Please enter a query.")
    else:
        payload = {
            "workflow": workflow,
            "text_query": text_query,
            "skill_filters": [s.strip() for s in skills.split(",") if s.strip()],
            "domain_filters": [d.strip() for d in domains.split(",") if d.strip()],
            "internal_external": None if internal_external == "Any" else internal_external,
            "country": country.strip() or None,
            "timezone": timezone.strip() or None,
            "practice": practice.strip() or None,
            "client_name": client_name.strip() or None,
            "domain_name": domain_name.strip() or None,
            "minimum_available_percent": (
                minimum_available_percent if minimum_available_percent > 0 else None
            ),
            "max_bill_rate": max_bill_rate if max_bill_rate > 0 else None,
            "budget_band": None if budget_band == "Any" else budget_band,
            "interviewer_only": interviewer_only,
            "minimum_prior_interview_count": (
                minimum_prior_interview_count if minimum_prior_interview_count > 0 else None
            ),
            "available_by_date": available_by_date.isoformat() if use_available_by_date else None,
        }
        response = requests.post(f"{API_BASE_URL}/api/v1/search", json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()

        st.subheader("Recommendations")
        for rec in data["recommendations"]:
            with st.container(border=True):
                st.markdown(f"### {rec['full_name']} ({rec['role']})")
                st.write(f"Confidence: **{rec['confidence_score']}**")
                st.write("**Why recommended**")
                st.write(rec["why_recommended"])
                st.write("**Evidence IDs**")
                st.write(rec["evidence_ids"])
                st.write("**Uncertainties**")
                st.write(rec["uncertainties"])
                st.info(f"Next action: {rec['next_action']}")

        st.subheader("System Notes")
        st.write(data["notes"])
