from datetime import date

import requests
import streamlit as st

API_BASE_URL = st.sidebar.text_input("Backend URL", "http://localhost:8000")

st.title("DynPro Brain - Phase 1 MVP Scaffold")
st.caption("Decision support for capability intelligence (human-in-the-loop).")

workflow = st.selectbox(
    "Workflow",
    [
        "expert_finder",
        "interviewer_finder",
        "client_domain_finder",
        "poc_support_finder",
        "pod_builder",
    ],
)
text_query = st.text_area("What are you trying to find?", height=100)
skills = st.text_input("Skill filters (comma-separated)")
domains = st.text_input("Domain filters (comma-separated)")
client_name = st.text_input("Client name (e.g., FinBank)")
domain_name = st.text_input("Domain name (e.g., BFSI)")
worked_with_person_name = st.text_input("Worked with person name (optional)")
prefer_people_who_worked_together = st.checkbox("Prefer people who worked together")

internal_external = st.selectbox("Internal/External", ["Any", "internal", "external"])
country = st.text_input("Country filter (exact, e.g., India)")
timezone = st.text_input("Timezone filter (exact, e.g., IST)")
practice = st.text_input("Practice filter (exact, e.g., Data & AI)")
minimum_available_percent = st.slider(
    "Minimum available percent", min_value=0, max_value=100, value=0, step=5
)
max_bill_rate = st.number_input(
    "Max bill rate (optional)",
    min_value=0.0,
    value=0.0,
    step=5.0,
    help="Use this when you want budget-aware matching without showing raw commercial detail in results.",
)
budget_band = st.selectbox("Budget band", ["Any", "economy", "standard", "premium"])

if workflow == "pod_builder":
    st.subheader("Pod Builder Inputs")
    required_skills = st.text_input("Required skills (comma-separated)")
    desired_roles = st.text_input("Desired roles (comma-separated)")
    pod_size = st.slider("Pod size", min_value=1, max_value=6, value=3, step=1)
    internal_external_preference = st.selectbox(
        "Internal/External preference",
        ["Any", "internal", "external"],
    )
    budget_ceiling = st.number_input(
        "Pod budget ceiling (estimated total)", min_value=0.0, value=0.0, step=10.0
    )
else:
    required_skills = ""
    desired_roles = ""
    pod_size = 3
    internal_external_preference = "Any"
    budget_ceiling = 0.0

interviewer_only = st.checkbox("Interviewer only")
minimum_prior_interview_count = st.number_input(
    "Minimum prior interview count", min_value=0, value=0, step=1
)
poc_support_only = st.checkbox("POC support only")
minimum_client_facing_comfort = st.selectbox(
    "Minimum client-facing comfort", ["Any", "low", "medium", "high"]
)
minimum_poc_participation_count = st.number_input(
    "Minimum POC participation count", min_value=0, value=0, step=1
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
            "worked_with_person_name": worked_with_person_name.strip() or None,
            "prefer_people_who_worked_together": prefer_people_who_worked_together,
            "minimum_available_percent": (
                minimum_available_percent if minimum_available_percent > 0 else None
            ),
            "max_bill_rate": max_bill_rate if max_bill_rate > 0 else None,
            "budget_band": None if budget_band == "Any" else budget_band,
            "interviewer_only": interviewer_only,
            "minimum_prior_interview_count": (
                minimum_prior_interview_count if minimum_prior_interview_count > 0 else None
            ),
            "poc_support_only": poc_support_only,
            "minimum_client_facing_comfort": (
                None if minimum_client_facing_comfort == "Any" else minimum_client_facing_comfort
            ),
            "minimum_poc_participation_count": (
                minimum_poc_participation_count if minimum_poc_participation_count > 0 else None
            ),
            "available_by_date": available_by_date.isoformat() if use_available_by_date else None,
            "required_skills": [s.strip() for s in required_skills.split(",") if s.strip()],
            "desired_roles": [r.strip() for r in desired_roles.split(",") if r.strip()],
            "pod_size": pod_size,
            "internal_external_preference": (
                None
                if internal_external_preference == "Any"
                else internal_external_preference
            ),
            "budget_ceiling": budget_ceiling if budget_ceiling > 0 else None,
        }
        response = requests.post(f"{API_BASE_URL}/api/v1/search", json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()

        if workflow == "pod_builder" and data.get("pod_recommendation"):
            pod = data["pod_recommendation"]
            st.subheader("Pod Recommendation")
            for person in pod["recommended_people"]:
                with st.container(border=True):
                    st.markdown(
                        f"### {person['full_name']} ({person['current_role']})"
                    )
                    st.write(f"Assigned role: **{person.get('assigned_role') or 'TBD'}**")
                    st.write(
                        f"Availability: {person['availability_percent']}% | Bill rate: {person['bill_rate_usd']}"
                    )
                    st.write(f"Matched skills: {person['matched_skills']}")
                    st.write(f"Matched roles: {person['matched_roles']}")

            st.markdown("### Coverage Summary")
            st.json(pod["coverage_summary"])

            st.markdown("### Budget Fit Summary")
            st.json(pod["budget_fit_summary"])

            st.markdown("### Gaps")
            st.write(pod["gaps"] or ["No major gaps identified in this simple pass."])

            st.markdown("### Substitutions / Backups")
            st.write(pod["substitutions_or_backups"])

            st.markdown("### Explainability")
            st.write("**Why this pod was suggested**")
            st.write(pod["why_this_pod_was_suggested"])
            st.write("**Constraints satisfied**")
            st.write(pod["constraints_satisfied"])
            st.write("**Constraints partially satisfied**")
            st.write(pod["constraints_partially_satisfied"])
            st.write("**Uncertainties**")
            st.write(pod["uncertainties"])
            st.info(f"Next action: {pod['next_action']}")
        else:
            st.subheader("Recommendations")
            for rec in data["recommendations"]:
                with st.container(border=True):
                    st.markdown(f"### {rec['full_name']} ({rec['role']})")
                    st.write(f"Confidence: **{rec['confidence_score']}**")
                    st.write(f"Confidence band: **{rec['confidence_band'].upper()}**")
                    st.write(f"Evidence count: **{rec['evidence_count']}**")
                    st.write(f"Freshness: **{rec['freshness_summary']}**")
                    if rec.get("source_mix"):
                        st.write("Source mix:")
                        st.json(rec["source_mix"])
                    st.write("**Why recommended**")
                    st.write(rec["why_recommended"])
                    st.write("**Evidence IDs**")
                    st.write(rec["evidence_ids"])
                    st.write("**Uncertainties**")
                    st.write(rec["uncertainties"])
                    st.info(f"Next action: {rec['next_action']}")

        st.subheader("System Notes")
        st.write(data["notes"])
