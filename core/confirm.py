"""Confirmation layer for risky actions."""


def confirm_action(risk_level: str, description: str) -> bool:
    """Request user confirmation before executing an action.

    Low-risk actions are permitted directly. Medium/high-risk actions
    require explicit confirmation (y/n).
    """
    if risk_level == "low":
        return True

    print(f"\n[DESKBRIDGE] Confirm action [{risk_level}]")
    print(f"Action: {description}")
    answer = input("Proceed? (y/n): ").strip().lower()
    return answer == "y"