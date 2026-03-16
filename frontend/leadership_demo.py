from typing import Any


def select_leadership_demo_result(workflow: str, data: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    if workflow == "pod_builder" and data.get("pod_recommendation"):
        return "pod", data["pod_recommendation"]

    recommendations = data.get("recommendations") or []
    if recommendations:
        return "recommendation", recommendations[0]

    return "none", None
