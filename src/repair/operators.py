from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import networkx as nx

from .features import ObservationView
from .schemas import CaseData, DefectIssue, OperationDelta


@dataclass(slots=True)
class OperatorSpec:
    operator_id: str
    defect_categories: tuple[str, ...]
    beta: bool


def _copy_node_attrs(src_graph: nx.DiGraph, dst_graph: nx.DiGraph, node: str) -> None:
    dst_graph.add_node(node, **dict(src_graph.nodes[node]))


def _shortest_upstream_path(graph: nx.DiGraph, source: str, target: str, max_depth: int) -> list[str] | None:
    queue = deque([(source, [source])])
    visited = {source}
    while queue:
        node, path = queue.popleft()
        if len(path) - 1 > max_depth:
            continue
        if node == target:
            return path
        for succ in graph.successors(node):
            if succ in visited:
                continue
            visited.add(succ)
            queue.append((succ, path + [succ]))
    return None


def relax_thresh(case: CaseData, graph: nx.DiGraph, issue: DefectIssue, params: dict) -> OperationDelta:
    delta = OperationDelta()
    anchor = issue.context["anchor"]
    candidates = issue.context.get("candidate_nodes", [])
    if not candidates:
        delta.stale = True
        return delta
    obs = ObservationView(case.observations)
    candidate = max(candidates, key=obs.anomaly_score)
    if candidate in graph:
        delta.stale = True
        return delta
    _copy_node_attrs(case.physical_graph, graph, candidate)
    graph.add_edge(candidate, anchor)
    delta.added_nodes.add(candidate)
    delta.added_edges.add((candidate, anchor))
    return delta


def switch_indicator(case: CaseData, graph: nx.DiGraph, issue: DefectIssue, params: dict) -> OperationDelta:
    return relax_thresh(case, graph, issue, params)


def expand_front(case: CaseData, graph: nx.DiGraph, issue: DefectIssue, params: dict) -> OperationDelta:
    delta = OperationDelta()
    anchor = issue.context["anchor"]
    depth = int(params.get("depth", 3))
    obs = ObservationView(case.observations)
    threshold = float(params.get("threshold", 0.18))
    candidates = []
    for node in case.physical_graph.nodes:
        if node in graph:
            continue
        path = _shortest_upstream_path(case.physical_graph, node, anchor, depth)
        if path and obs.anomaly_score(node) >= threshold:
            candidates.append((node, path))
    if not candidates:
        delta.stale = True
        return delta
    candidate, path = max(candidates, key=lambda item: obs.anomaly_score(item[0]))
    for node in path:
        if node not in graph:
            _copy_node_attrs(case.physical_graph, graph, node)
            delta.added_nodes.add(node)
    for src, dst in zip(path[:-1], path[1:]):
        if not graph.has_edge(src, dst):
            graph.add_edge(src, dst)
            delta.added_edges.add((src, dst))
    return delta


def cond_granger(case: CaseData, graph: nx.DiGraph, issue: DefectIssue, params: dict) -> OperationDelta:
    delta = OperationDelta()
    if issue.edges:
        src, dst = issue.edges[0]
        obs = ObservationView(case.observations)
        forward = obs.granger_proxy(src, dst)
        backward = obs.granger_proxy(dst, src)
        if backward > forward and case.physical_graph.has_edge(dst, src):
            if graph.has_edge(src, dst):
                graph.remove_edge(src, dst)
                delta.removed_edges.add((src, dst))
            if not graph.has_edge(dst, src):
                graph.add_edge(dst, src)
                delta.added_edges.add((dst, src))
            return delta
    delta.stale = True
    return delta


def prune_edge(case: CaseData, graph: nx.DiGraph, issue: DefectIssue, params: dict) -> OperationDelta:
    delta = OperationDelta()
    if not issue.edges:
        delta.stale = True
        return delta
    src, dst = issue.edges[0]
    if not graph.has_edge(src, dst):
        delta.stale = True
        return delta
    graph.remove_edge(src, dst)
    if graph.number_of_nodes() and not nx.is_weakly_connected(graph):
        graph.add_edge(src, dst)
        delta.stale = True
        return delta
    delta.removed_edges.add((src, dst))
    return delta


def interv_chain(case: CaseData, graph: nx.DiGraph, issue: DefectIssue, params: dict) -> OperationDelta:
    delta = OperationDelta()
    if not issue.edges:
        delta.stale = True
        return delta
    src, dst = issue.edges[0]
    if not graph.has_edge(src, dst):
        delta.stale = True
        return delta
    obs = ObservationView(case.observations)
    threshold = float(params.get("threshold", 0.18))
    if obs.onset_time(src, threshold) > obs.onset_time(dst, threshold):
        graph.remove_edge(src, dst)
        graph.add_edge(dst, src)
        delta.removed_edges.add((src, dst))
        delta.added_edges.add((dst, src))
        return delta
    delta.stale = True
    return delta


def lateral_lca(case: CaseData, graph: nx.DiGraph, issue: DefectIssue, params: dict) -> OperationDelta:
    delta = OperationDelta()
    pair = issue.context.get("pair", [])
    candidates = issue.context.get("candidate_nodes", [])
    if len(pair) != 2 or not candidates:
        delta.stale = True
        return delta
    node = candidates[0]
    if node not in graph:
        _copy_node_attrs(case.physical_graph, graph, node)
        delta.added_nodes.add(node)
    for target in pair:
        if case.physical_graph.has_edge(node, target) and not graph.has_edge(node, target):
            graph.add_edge(node, target)
            delta.added_edges.add((node, target))
    return delta if delta.added_nodes or delta.added_edges else OperationDelta(stale=True)


def cycle_resolve(case: CaseData, graph: nx.DiGraph, issue: DefectIssue, params: dict) -> OperationDelta:
    delta = OperationDelta()
    cycle = issue.context.get("cycle", [])
    if len(cycle) < 2:
        delta.stale = True
        return delta
    obs = ObservationView(case.observations)
    threshold = float(params.get("threshold", 0.18))
    worst_edge = None
    worst_gap = float("-inf")
    for src, dst in zip(cycle, cycle[1:] + cycle[:1]):
        gap = obs.onset_time(src, threshold) - obs.onset_time(dst, threshold)
        if gap > worst_gap and graph.has_edge(src, dst):
            worst_gap = gap
            worst_edge = (src, dst)
    if not worst_edge:
        delta.stale = True
        return delta
    graph.remove_edge(*worst_edge)
    delta.removed_edges.add(worst_edge)
    return delta


def split_tied(case: CaseData, graph: nx.DiGraph, issue: DefectIssue, params: dict) -> OperationDelta:
    delta = OperationDelta()
    anchor = issue.context.get("anchor")
    if not anchor or anchor not in graph:
        delta.stale = True
        return delta
    preds = list(graph.predecessors(anchor))
    if len(preds) < 2:
        delta.stale = True
        return delta
    obs = ObservationView(case.observations)
    weakest = min(preds, key=lambda node: obs.granger_proxy(node, anchor))
    if graph.has_edge(weakest, anchor):
        graph.remove_edge(weakest, anchor)
        delta.removed_edges.add((weakest, anchor))
        return delta
    delta.stale = True
    return delta


OPERATOR_SPECS = {
    "A1": OperatorSpec("A1", ("G1",), False),
    "A2": OperatorSpec("A2", ("G2",), False),
    "A3": OperatorSpec("A3", ("G3",), True),
    "A4": OperatorSpec("A4", ("G4",), True),
    "A5": OperatorSpec("A5", ("G4",), False),
    "A6": OperatorSpec("A6", ("G5",), True),
    "A7": OperatorSpec("A7", ("G6",), True),
    "A8": OperatorSpec("A8", ("G7",), False),
    "A9": OperatorSpec("A9", ("G8",), False),
}


OPERATOR_IMPL = {
    "A1": relax_thresh,
    "A2": switch_indicator,
    "A3": expand_front,
    "A4": cond_granger,
    "A5": prune_edge,
    "A6": interv_chain,
    "A7": lateral_lca,
    "A8": cycle_resolve,
    "A9": split_tied,
}

