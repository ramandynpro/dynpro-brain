from datetime import date

import requests
import streamlit as st

API_BASE_URL = st.sidebar.text_input("Backend URL", "http://localhost:8000")

DEMO_SCENARIOS = [
    {
        "label": "Expert Finder",
        "workflow": "expert_finder",
        "demo_note": "Shows how leaders can quickly find a credible specialist for a time-sensitive client ask.",
        "payload": {
            "text_query": "Need a principal data engineering expert for a BFSI cloud migration kickoff in the next 2 weeks.",
            "skill_filters": ["Data Engineering", "Cloud"],
            "domain_filters": ["BFSI"],
            "country": "India",
            "timezone": "IST",
            "minimum_available_percent": 30,
            "budget_band": "standard",
        },
    },
    {
        "label": "Interviewer Finder",
        "workflow": "interviewer_finder",
        "demo_note": "Shows interviewer readiness with evidence-based confidence for a hiring sprint.",
        "payload": {
            "text_query": "Find interviewers for senior MLOps candidates with financial services delivery context.",
            "skill_filters": ["MLOps", "Python"],
            "domain_filters": ["Financial Services"],
            "interviewer_only": True,
            "minimum_prior_interview_count": 2,
            "minimum_available_percent": 20,
        },
    },
    {
        "label": "Client/Domain Finder",
        "workflow": "client_domain_finder",
        "demo_note": "Shows where existing client and domain memory can reduce ramp-up risk.",
        "payload": {
            "text_query": "Who has recent healthcare analytics experience for a payer transformation proposal?",
            "domain_filters": ["Healthcare"],
            "client_name": "HealthSure",
            "minimum_available_percent": 20,
            "budget_band": "premium",
        },
    },
    {
        "label": "POC Support Finder",
        "workflow": "poc_support_finder",
        "demo_note": "Shows who can support a client-facing POC with practical confidence and availability checks.",
        "payload": {
            "text_query": "Need client-facing POC support for an AI claims triage prototype.",
            "skill_filters": ["Generative AI", "Solution Architecture"],
            "poc_support_only": True,
            "minimum_client_facing_comfort": "medium",
            "minimum_poc_participation_count": 1,
            "minimum_available_percent": 25,
        },
    },
    {
        "label": "Pod Builder",
        "workflow": "pod_builder",
        "demo_note": "Shows how a small pod can be proposed with coverage, constraints, and next-step review guidance.",
        "payload": {
            "text_query": "Build a 3-person pod for a retail demand forecasting accelerator delivery.",
            "required_skills": ["Data Engineering", "Machine Learning", "Stakeholder Management"],
            "desired_roles": ["Tech Lead", "Data Scientist", "Delivery Manager"],
            "pod_size": 3,
            "country": "India",
            "timezone": "IST",
            "minimum_available_percent": 20,
            "internal_external_preference": "internal",
            "budget_ceiling": 420.0,
        },
    },
]

if "last_request_id" not in st.session_state:
    st.session_state["last_request_id"] = None


def run_search(payload: dict) -> dict:
    response = requests.post(f"{API_BASE_URL}/api/v1/search", json=payload, timeout=20)
    response.raise_for_status()
    data = response.json()
    st.session_state["last_request_id"] = data.get("request_id")
    return data


def render_data_source_note(data: dict) -> None:
    data_sources = data.get("data_sources") or ["sample"]
    assignment_data_sources = data.get("assignment_data_sources") or ["sample"]
    skill_evidence_data_sources = data.get("skill_evidence_data_sources") or ["sample"]
    commercial_data_sources = data.get("commercial_data_sources") or ["sample"]
    people_label = " + ".join(data_sources)
    assignment_label = " + ".join(assignment_data_sources)
    skill_evidence_label = " + ".join(skill_evidence_data_sources)
    commercial_label = " + ".join(commercial_data_sources)
    st.caption(f"People data source: {people_label}")
    st.caption(f"Assignment/project data source: {assignment_label}")
    st.caption(f"Skill evidence data source: {skill_evidence_label}")
    st.caption(f"Commercial-profile data source: {commercial_label}")

def render_leadership_demo_result(scenario: dict, payload: dict, data: dict) -> None:
    st.markdown("### Request summary")
    st.write(payload["text_query"])

    if scenario["workflow"] == "pod_builder" and data.get("pod_recommendation"):
        pod = data["pod_recommendation"]
        st.markdown("### Top recommendation or pod")
        st.write(
            ", ".join(person["full_name"] for person in pod.get("recommended_people", []))
            or "No pod recommendation returned."
        )

        st.markdown("### Why it was recommended")
        st.write(pod.get("why_this_pod_was_suggested", []))

        st.markdown("### Confidence/freshness summary")
        st.write("Pod-level confidence is inferred from role/skill coverage and supporting person evidence.")
        st.json(pod.get("coverage_summary", {}))

        st.markdown("### Constraints applied")
        st.write(pod.get("constraints_satisfied", []))
        if pod.get("constraints_partially_satisfied"):
            st.write("Partially satisfied:")
            st.write(pod["constraints_partially_satisfied"])

        st.markdown("### Next action")
        st.info(pod.get("next_action", "Review with a delivery lead."))
    else:
        rec = data.get("recommendations", [{}])[0]
        st.markdown("### Top recommendation or pod")
        st.write(f"{rec.get('full_name', 'No result')} ({rec.get('role', 'n/a')})")

        st.markdown("### Why it was recommended")
        st.write(rec.get("why_recommended", []))

        st.markdown("### Confidence/freshness summary")
        st.write(
            f"Confidence: {rec.get('confidence_band', 'n/a').upper()} "
            f"({rec.get('confidence_score', 'n/a')}) | Freshness: {rec.get('freshness_summary', 'n/a')}"
        )

        st.markdown("### Constraints applied")
        query = data.get("query", {})
        applied_constraints = {
            "skill_filters": query.get("skill_filters"),
            "domain_filters": query.get("domain_filters"),
            "country": query.get("country"),
            "timezone": query.get("timezone"),
            "minimum_available_percent": query.get("minimum_available_percent"),
            "budget_band": query.get("budget_band"),
        }
        st.json({k: v for k, v in applied_constraints.items() if v})

        st.markdown("### Next action")
        st.info(rec.get("next_action", "Review candidate fit with a delivery lead."))

    st.markdown("### What this demonstrates")
    st.caption(scenario["demo_note"])


def render_pilot_kpi(limit: int = 20) -> None:
    kpi_response = requests.get(f"{API_BASE_URL}/api/v1/pilot/kpi-summary", params={"limit": limit}, timeout=20)
    kpi_response.raise_for_status()
    kpi = kpi_response.json()

    kpi_col_1, kpi_col_2, kpi_col_3, kpi_col_4 = st.columns(4)
    kpi_col_1.metric("Total requests", kpi.get("total_requests", 0))
    kpi_col_2.metric("Average trust rating", kpi.get("average_trust_rating") or "n/a")
    useful_yes_rate = kpi.get("useful_yes_rate")
    useful_yes_percent = f"{round(useful_yes_rate * 100, 1)}%" if useful_yes_rate is not None else "n/a"
    kpi_col_3.metric("Useful yes rate", useful_yes_percent)
    kpi_col_4.metric("Recent missed-person/gap count", kpi.get("recent_missed_person_or_gap_count", 0))

    kpi_col_5, kpi_col_6 = st.columns(2)
    kpi_col_5.metric("Pod builder request count", kpi.get("pod_builder_request_count", 0))
    kpi_col_6.metric("Interviewer finder request count", kpi.get("interviewer_finder_request_count", 0))

    return kpi

st.title("DynPro Brain - Phase 1 MVP Scaffold")
st.caption("Decision support for capability intelligence (human-in-the-loop).")

view_mode = st.radio("View", ["Search", "Leadership Demo"], horizontal=True)

if view_mode == "Leadership Demo":
    st.subheader("Leadership Demo")
    st.caption("Run one-click, explainable Phase 1 scenarios mapped to core workflows.")
    scenario_labels = [scenario["label"] for scenario in DEMO_SCENARIOS]
    selected_label = st.selectbox("Choose a demo scenario", scenario_labels)
    selected_scenario = next(s for s in DEMO_SCENARIOS if s["label"] == selected_label)

    st.markdown(f"**Workflow:** `{selected_scenario['workflow']}`")
    st.write(selected_scenario["payload"]["text_query"])

    if st.button("Run Demo Scenario", type="primary"):
        payload = {
            "workflow": selected_scenario["workflow"],
            "text_query": selected_scenario["payload"]["text_query"],
            "skill_filters": selected_scenario["payload"].get("skill_filters", []),
            "domain_filters": selected_scenario["payload"].get("domain_filters", []),
            "internal_external": selected_scenario["payload"].get("internal_external"),
            "country": selected_scenario["payload"].get("country"),
            "timezone": selected_scenario["payload"].get("timezone"),
            "practice": selected_scenario["payload"].get("practice"),
            "client_name": selected_scenario["payload"].get("client_name"),
            "domain_name": selected_scenario["payload"].get("domain_name"),
            "worked_with_person_name": selected_scenario["payload"].get("worked_with_person_name"),
            "prefer_people_who_worked_together": selected_scenario["payload"].get(
                "prefer_people_who_worked_together", False
            ),
            "minimum_available_percent": selected_scenario["payload"].get("minimum_available_percent"),
            "max_bill_rate": selected_scenario["payload"].get("max_bill_rate"),
            "budget_band": selected_scenario["payload"].get("budget_band"),
            "interviewer_only": selected_scenario["payload"].get("interviewer_only", False),
            "minimum_prior_interview_count": selected_scenario["payload"].get("minimum_prior_interview_count"),
            "poc_support_only": selected_scenario["payload"].get("poc_support_only", False),
            "minimum_client_facing_comfort": selected_scenario["payload"].get("minimum_client_facing_comfort"),
            "minimum_poc_participation_count": selected_scenario["payload"].get(
                "minimum_poc_participation_count"
            ),
            "available_by_date": selected_scenario["payload"].get("available_by_date"),
            "required_skills": selected_scenario["payload"].get("required_skills", []),
            "desired_roles": selected_scenario["payload"].get("desired_roles", []),
            "pod_size": selected_scenario["payload"].get("pod_size", 3),
            "internal_external_preference": selected_scenario["payload"].get("internal_external_preference"),
            "budget_ceiling": selected_scenario["payload"].get("budget_ceiling"),
        }
        data = run_search(payload)
        render_data_source_note(data)
        render_leadership_demo_result(selected_scenario, payload, data)

    st.divider()
    st.subheader("Current Pilot KPIs")
    st.caption("Quick KPI snapshot for leadership check-ins.")
    if st.button("Refresh KPI Snapshot"):
        st.session_state["refresh_pilot_kpi_demo"] = True
    if st.session_state.get("refresh_pilot_kpi_demo", True):
        render_pilot_kpi(limit=20)

    st.stop()

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
        data = run_search(payload)

        render_data_source_note(data)

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


if st.session_state.get("last_request_id"):
    st.subheader("Pilot Feedback")
    st.caption(f"Latest request ID: {st.session_state['last_request_id']}")

    with st.form("pilot_feedback_form"):
        useful_yes_no = st.radio("Was this useful?", options=["Yes", "No"], horizontal=True)
        trust_rating = st.slider("Trust rating", min_value=1, max_value=5, value=3, step=1)
        notes = st.text_area("Notes", height=80)
        missed_person_or_gap = st.text_input("Missed person or gap")
        submit_feedback = st.form_submit_button("Submit feedback")

    if submit_feedback:
        feedback_payload = {
            "request_id": st.session_state["last_request_id"],
            "useful_yes_no": useful_yes_no == "Yes",
            "trust_rating": trust_rating,
            "notes": notes.strip() or None,
            "missed_person_or_gap": missed_person_or_gap.strip() or None,
        }
        feedback_response = requests.post(
            f"{API_BASE_URL}/api/v1/pilot/feedback", json=feedback_payload, timeout=20
        )
        feedback_response.raise_for_status()
        st.success("Thanks — pilot feedback captured.")


st.divider()
st.subheader("Pilot Admin View (Phase 1)")
st.caption("Simple pilot KPI readout from local request + feedback logs.")

if st.button("Refresh Pilot KPI Summary"):
    st.session_state["refresh_pilot_kpi"] = True

if st.session_state.get("refresh_pilot_kpi", True):
    kpi = render_pilot_kpi(limit=20)

    st.markdown("#### Requests by workflow")
    st.json(kpi.get("requests_by_workflow", {}))

    if kpi.get("duration_summary"):
        st.markdown("#### Duration summary")
        st.json(kpi["duration_summary"])

    st.markdown("#### Recent requests")
    st.dataframe(kpi.get("recent_requests", []), use_container_width=True)

    st.markdown("#### Recent feedback")
    st.dataframe(kpi.get("recent_feedback", []), use_container_width=True)
