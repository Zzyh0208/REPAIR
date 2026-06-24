from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd


@dataclass(slots=True)
class CaseData:
    case_id: str
    case_dir: Path
    physical_graph: nx.DiGraph
    observations: pd.DataFrame
    symptoms: list[str]
    initial_subgraphs: dict[str, nx.DiGraph]
    true_roots: list[str] = field(default_factory=list)
    true_graph: nx.DiGraph | None = None


@dataclass(slots=True)
class DefectIssue:
    defect_id: str
    category: str
    nodes: tuple[str, ...] = ()
    edges: tuple[tuple[str, str], ...] = ()
    confidence: float = 0.0
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def write_targets(self) -> set[str]:
        targets = {f"node:{node}" for node in self.nodes}
        targets.update(f"edge:{src}->{dst}" for src, dst in self.edges)
        for node in self.context.get("candidate_nodes", []):
            targets.add(f"node:{node}")
        for src, dst in self.context.get("candidate_edges", []):
            targets.add(f"edge:{src}->{dst}")
        return targets


@dataclass(slots=True)
class RepairAction:
    operator_id: str
    params: dict[str, Any] = field(default_factory=dict)
    source: str = "rule"


@dataclass(slots=True)
class OperationDelta:
    added_nodes: set[str] = field(default_factory=set)
    removed_nodes: set[str] = field(default_factory=set)
    added_edges: set[tuple[str, str]] = field(default_factory=set)
    removed_edges: set[tuple[str, str]] = field(default_factory=set)
    stale: bool = False

    def touched(self) -> set[str]:
        touched = {f"node:{node}" for node in self.added_nodes | self.removed_nodes}
        touched.update(f"edge:{src}->{dst}" for src, dst in self.added_edges | self.removed_edges)
        return touched


@dataclass(slots=True)
class CycleRecord:
    cycle_index: int
    phi_before: int
    phi_after: int
    issues_seen: int
    issues_resolved: int
    actions: list[dict[str, Any]]


@dataclass(slots=True)
class RunResult:
    case_id: str
    extractor: str
    locator: str
    graph_before: nx.DiGraph
    graph_after: nx.DiGraph
    ranking_before: list[str]
    ranking_after: list[str]
    cycle_records: list[CycleRecord]
    metrics: dict[str, Any]

