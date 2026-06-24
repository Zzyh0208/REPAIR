from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx

from .defects import DefectDetector
from .dsl import SkillLibrary
from .operators import OPERATOR_IMPL, OPERATOR_SPECS
from .planner import RepairPlanner
from .schemas import CaseData, CycleRecord


def _partition_issues(issues: list) -> list[list]:
    groups: list[list] = []
    for issue in issues:
        placed = False
        for group in groups:
            occupied = set()
            for other in group:
                occupied |= other.write_targets
            if not issue.write_targets.intersection(occupied):
                group.append(issue)
                placed = True
                break
        if not placed:
            groups.append([issue])
    return groups


class GlobalCoordinator:
    def __init__(
        self,
        config: dict[str, Any],
        detector: DefectDetector,
        planner: RepairPlanner,
        skill_library: SkillLibrary,
    ) -> None:
        self.config = config
        self.detector = detector
        self.planner = planner
        self.skill_library = skill_library
        self.resolved_ids: set[str] = set()
        self.fingerprints: set[str] = set()

    def run(self, case: CaseData, initial_graph: nx.DiGraph) -> tuple[nx.DiGraph, list[CycleRecord]]:
        graph = initial_graph.copy()
        max_cycles = int(self.config["repair"]["max_cycles"])
        capacity = int(self.config["repair"]["capacity"])
        patience = int(self.config["repair"]["stagnation_patience"])
        beta_bound = int(self.config["repair"]["beta_side_effect_bound"])
        traces: list[CycleRecord] = []
        stagnation = 0

        for cycle_index in range(max_cycles):
            issues = self.detector.scan(case, graph, resolved_ids=self.resolved_ids)
            if not issues:
                break
            phi_before = len(issues)
            actions: list[dict[str, Any]] = []
            accepted = 0
            groups = _partition_issues(issues)
            for group in groups:
                for issue in sorted(group, key=lambda item: item.confidence, reverse=True):
                    action = self.planner.select(issue)
                    signature = f"{issue.defect_id}:{action.operator_id}:{sorted(action.params.items())}"
                    if signature in self.fingerprints:
                        continue
                    spec = OPERATOR_SPECS[action.operator_id]
                    trial_graph = graph.copy()
                    delta = OPERATOR_IMPL[action.operator_id](case, trial_graph, issue, action.params)
                    if delta.stale:
                        self.fingerprints.add(signature)
                        continue
                    if trial_graph.number_of_nodes() > capacity:
                        self.fingerprints.add(signature)
                        continue
                    if any(node not in case.physical_graph for node in trial_graph.nodes):
                        self.fingerprints.add(signature)
                        continue
                    new_phi = self.detector.potential(case, trial_graph, resolved_ids=self.resolved_ids | {issue.defect_id})
                    if new_phi >= phi_before:
                        self.fingerprints.add(signature)
                        continue
                    if spec.beta and (phi_before - new_phi) <= 0:
                        self.fingerprints.add(signature)
                        continue
                    if spec.beta and len(delta.added_edges | delta.added_nodes) > beta_bound * 4:
                        self.fingerprints.add(signature)
                        continue
                    graph = trial_graph
                    self.resolved_ids.add(issue.defect_id)
                    self.fingerprints.add(signature)
                    accepted += 1
                    actions.append(
                        {
                            "issue_id": issue.defect_id,
                            "category": issue.category,
                            "operator_id": action.operator_id,
                            "source": action.source,
                            "params": action.params,
                        }
                    )
                    if self._necessity_score(case, graph, issue) >= float(self.config["repair"]["auto_admit_threshold"]):
                        self.skill_library.admit(issue, action)
                    phi_before = new_phi
            phi_after = self.detector.potential(case, graph, resolved_ids=self.resolved_ids)
            traces.append(
                CycleRecord(
                    cycle_index=cycle_index,
                    phi_before=len(issues),
                    phi_after=phi_after,
                    issues_seen=len(issues),
                    issues_resolved=accepted,
                    actions=actions,
                )
            )
            if phi_after >= len(issues):
                stagnation += 1
            else:
                stagnation = 0
            if stagnation >= patience:
                break
        self.skill_library.save()
        return graph, traces

    def _necessity_score(self, case: CaseData, graph: nx.DiGraph, issue) -> float:
        if not case.symptoms:
            return 0.0
        from .features import ObservationView

        obs = ObservationView(case.observations)
        base = obs.symptom_intensity(case.symptoms)
        focus_nodes = [node for node in issue.context.get("candidate_nodes", []) if node in graph]
        if not focus_nodes:
            focus_nodes = [node for node in issue.nodes if node in graph]
        bonus = sum(obs.anomaly_score(node) for node in focus_nodes)
        return float((base + bonus) * max(1, len(focus_nodes)))

