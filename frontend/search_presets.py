SCENARIO_PRESETS = {
    "Expert Finder": {
        "workflow": "expert_finder",
        "prompt": "Show me internal people in India who worked on Snowflake and Salesforce.",
        "default_payload": {
            "skill_filters": ["Snowflake", "Salesforce"],
            "country": "India",
            "internal_external": "internal",
        },
    },
    "Interviewer Finder": {
        "workflow": "interviewer_finder",
        "prompt": "Who can interview a Workato delivery lead with client-facing experience?",
        "default_payload": {
            "skill_filters": ["Workato"],
            "interviewer_only": True,
            "minimum_prior_interview_count": 2,
            "minimum_client_facing_comfort": "medium",
        },
    },
    "Client/Domain Finder": {
        "workflow": "client_domain_finder",
        "prompt": "Who has worked at HealthSure before?",
        "default_payload": {
            "client_name": "HealthSure",
            "domain_filters": ["Healthcare"],
            "minimum_available_percent": 20,
        },
    },
    "Pod Builder": {
        "workflow": "pod_builder",
        "prompt": "Build me a 4-person pod for a 6-week integration POC under this budget.",
        "default_payload": {
            "required_skills": ["Workato", "Integration Architecture", "Client Communication"],
            "desired_roles": ["Delivery Lead", "Integration Engineer", "Solution Architect"],
            "pod_size": 4,
        },
    },
    "POC Support Finder": {
        "workflow": "poc_support_finder",
        "prompt": "Who can support a client-facing healthcare AI POC?",
        "default_payload": {
            "poc_support_only": True,
            "domain_filters": ["Healthcare"],
            "minimum_client_facing_comfort": "medium",
            "minimum_poc_participation_count": 1,
        },
    },
}

SCENARIO_ORDER = [
    "Expert Finder",
    "Interviewer Finder",
    "Client/Domain Finder",
    "Pod Builder",
    "POC Support Finder",
]
