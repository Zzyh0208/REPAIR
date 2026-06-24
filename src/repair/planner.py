from __future__ import annotations

import json

from .dsl import SkillLibrary
from .llm import OpenRouterClient
from .operators import OPERATOR_SPECS
from .prompts import sra_prompt
from .schemas import DefectIssue, RepairAction


DEFAULT_ACTIONS = {
    "G1": RepairAction("A1", {"threshold": 0.14}),
    "G2": RepairAction("A2", {"threshold": 0.1}),
    "G3": RepairAction("A3", {"depth": 3, "threshold": 0.18}),
    "G4": RepairAction("A5", {}),
    "G5": RepairAction("A6", {"threshold": 0.18}),
    "G6": RepairAction("A7", {}),
    "G7": RepairAction("A8", {"threshold": 0.18}),
    "G8": RepairAction("A9", {}),
}


class RepairPlanner:
    def __init__(
        self,
        config: dict,
        skill_library: SkillLibrary,
        llm_client: OpenRouterClient | None = None,
    ) -> None:
        self.config = config
        self.skill_library = skill_library
        self.llm_client = llm_client

    def select(self, issue: DefectIssue) -> RepairAction:
        cached = self.skill_library.retrieve(issue)
        if cached:
            return cached
        if self.llm_client and self.config["llm"]["enabled_for_sra"]:
            action = self._select_with_llm(issue)
            if action:
                return action
        default = DEFAULT_ACTIONS[issue.category]
        return RepairAction(default.operator_id, dict(default.params), "rule")

    def _select_with_llm(self, issue: DefectIssue) -> RepairAction | None:
        allowed = [spec.operator_id for spec in OPERATOR_SPECS.values() if issue.category in spec.defect_categories]
        context = json.dumps(
            {
                "issue": {
                    "category": issue.category,
                    "nodes": list(issue.nodes),
                    "edges": [list(edge) for edge in issue.edges],
                    "confidence": issue.confidence,
                    "context": issue.context,
                },
                "allowed_operators": allowed,
            },
            ensure_ascii=False,
        )
        system_prompt, user_prompt = sra_prompt(context)
        payload = self.llm_client.complete_json(system_prompt, user_prompt)
        operator_id = payload.get("operator_id")
        params = payload.get("params", {})
        if operator_id in allowed:
            return RepairAction(operator_id, params, "llm")
        return None

