from __future__ import annotations

import networkx as nx

from .features import ObservationView
from .schemas import CaseData, DefectIssue


class DefectDetector:
    def __init__(self, config: dict) -> None:
        self.config = config

    def scan(
        self,
        case: CaseData,
        graph: nx.DiGraph,
        resolved_ids: set[str] | None = None,
    ) -> list[DefectIssue]:
        resolved_ids = resolved_ids or set()
        obs = ObservationView(case.observations)
        threshold = float(self.config["repair"]["anomaly_threshold"])
        onset_gap = float(self.config["repair"]["onset_gap"])
        issues: list[DefectIssue] = []

        for node in list(graph.nodes):
            preds = list(case.physical_graph.predecessors(node))
            missing_preds = [pred for pred in preds if pred not in graph]
            strong_missing = [pred for pred in missing_preds if obs.anomaly_score(pred) >= threshold]
            if len(strong_missing) == 1:
                pred = strong_missing[0]
                issue = DefectIssue(
                    defect_id=f"G1:{pred}:{node}",
                    category="G1",
                    nodes=(node,),
                    confidence=min(0.99, obs.anomaly_score(pred)),
                    context={"anchor": node, "candidate_nodes": [pred], "anomaly_score": obs.anomaly_score(pred)},
                )
                if issue.defect_id not in resolved_ids:
                    issues.append(issue)
            if len(strong_missing) > 1:
                issue = DefectIssue(
                    defect_id=f"G3:{node}:{','.join(sorted(strong_missing))}",
                    category="G3",
                    nodes=(node,),
                    confidence=min(0.99, max(obs.anomaly_score(pred) for pred in strong_missing)),
                    context={"anchor": node, "candidate_nodes": strong_missing, "anomaly_score": max(obs.anomaly_score(pred) for pred in strong_missing)},
                )
                if issue.defect_id not in resolved_ids:
                    issues.append(issue)
            moderate_missing = [
                pred for pred in missing_preds
                if threshold * 0.55 <= obs.anomaly_score(pred) < threshold
            ]
            if moderate_missing:
                pred = max(moderate_missing, key=obs.anomaly_score)
                issue = DefectIssue(
                    defect_id=f"G2:{pred}:{node}",
                    category="G2",
                    nodes=(node,),
                    confidence=min(0.95, obs.anomaly_score(pred) + 0.1),
                    context={"anchor": node, "candidate_nodes": [pred], "anomaly_score": obs.anomaly_score(pred)},
                )
                if issue.defect_id not in resolved_ids:
                    issues.append(issue)

        for src, dst in list(graph.edges):
            support = obs.granger_proxy(src, dst)
            if support < 0.05:
                issue = DefectIssue(
                    defect_id=f"G4:{src}:{dst}",
                    category="G4",
                    edges=((src, dst),),
                    confidence=min(0.99, 0.5 - support),
                    context={"candidate_edges": [(src, dst)], "support": support},
                )
                if issue.defect_id not in resolved_ids:
                    issues.append(issue)
            if obs.onset_time(src, threshold) > obs.onset_time(dst, threshold) + onset_gap:
                issue = DefectIssue(
                    defect_id=f"G5:{src}:{dst}",
                    category="G5",
                    edges=((src, dst),),
                    confidence=0.8,
                    context={"path_edges": [(src, dst)]},
                )
                if issue.defect_id not in resolved_ids:
                    issues.append(issue)

        for left in graph.nodes:
            for right in graph.nodes:
                if left >= right:
                    continue
                common = set(case.physical_graph.predecessors(left)).intersection(case.physical_graph.predecessors(right))
                hidden = [node for node in common if node not in graph and obs.anomaly_score(node) >= threshold]
                if hidden:
                    candidate = max(hidden, key=obs.anomaly_score)
                    issue = DefectIssue(
                        defect_id=f"G6:{candidate}:{left}:{right}",
                        category="G6",
                        nodes=(left, right),
                        confidence=min(0.95, obs.anomaly_score(candidate)),
                        context={"candidate_nodes": [candidate], "pair": [left, right], "anomaly_score": obs.anomaly_score(candidate)},
                    )
                    if issue.defect_id not in resolved_ids:
                        issues.append(issue)

        for cycle in nx.simple_cycles(graph):
            if len(cycle) >= 2:
                cycle_edges = tuple((cycle[i], cycle[(i + 1) % len(cycle)]) for i in range(len(cycle)))
                issue = DefectIssue(
                    defect_id=f"G7:{'|'.join(cycle)}",
                    category="G7",
                    nodes=tuple(cycle),
                    edges=cycle_edges,
                    confidence=0.75,
                    context={"cycle": cycle},
                )
                if issue.defect_id not in resolved_ids:
                    issues.append(issue)
                break

        symptom_set = set(case.symptoms)
        for node in graph.nodes:
            if node not in symptom_set:
                continue
            preds = list(graph.predecessors(node))
            early_preds = [pred for pred in preds if obs.onset_time(pred, threshold) < float("inf")]
            if len(early_preds) >= 2:
                issue = DefectIssue(
                    defect_id=f"G8:{node}:{','.join(sorted(early_preds))}",
                    category="G8",
                    nodes=(node,),
                    confidence=0.7,
                    context={"anchor": node, "candidate_nodes": early_preds},
                )
                if issue.defect_id not in resolved_ids:
                    issues.append(issue)

        return sorted(issues, key=lambda issue: issue.confidence, reverse=True)

    def potential(self, case: CaseData, graph: nx.DiGraph, resolved_ids: set[str] | None = None) -> int:
        return len(self.scan(case, graph, resolved_ids=resolved_ids))

