SCENARIO_PRESETS = {
    "Expert Finder": {
        "workflow": "expert_finder",
        "prompt": "Show me internal people in India who worked on Snowflake and Salesforce.",
    },
    "Interviewer Finder": {
        "workflow": "interviewer_finder",
        "prompt": "Who can interview a Workato delivery lead with client-facing experience?",
    },
    "Client/Domain Finder": {
        "workflow": "client_domain_finder",
        "prompt": "Who has worked at this client before?",
    },
    "Pod Builder": {
        "workflow": "pod_builder",
        "prompt": "Build me a 4-person pod for a 6-week integration POC under this budget.",
    },
    "POC Support Finder": {
        "workflow": "poc_support_finder",
        "prompt": "Who is a strong adjacent fit if we cannot find an exact match?",
    },
}

SCENARIO_ORDER = [
    "Expert Finder",
    "Interviewer Finder",
    "Client/Domain Finder",
    "Pod Builder",
    "POC Support Finder",
]
