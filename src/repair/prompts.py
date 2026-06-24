from __future__ import annotations


def dpa_prompt(issue_context: str) -> tuple[str, str]:
    system = (
        "You inspect traffic propagation subgraphs for structural defects. "
        "Return strict JSON with a list named issues. Each issue must contain "
        "category, confidence, nodes, edges, and context."
    )
    user = issue_context
    return system, user


def sra_prompt(action_context: str) -> tuple[str, str]:
    system = (
        "You choose one repair operator for a typed traffic graph defect. "
        "Return strict JSON with keys operator_id and params."
    )
    user = action_context
    return system, user


def locator_prompt(locator_context: str) -> tuple[str, str]:
    system = (
        "You rank candidate traffic root causes from strongest to weakest evidence. "
        "Return strict JSON with a list named ranking."
    )
    user = locator_context
    return system, user

