from __future__ import annotations

import networkx as nx

from .features import ObservationView
from .schemas import CaseData


def manifest_extractor(case: CaseData, name: str) -> nx.DiGraph:
    if name not in case.initial_subgraphs:
        raise KeyError(f"Extractor '{name}' was not found for case '{case.case_id}'.")
    return case.initial_subgraphs[name].copy()


def topocausal_extractor(case: CaseData, depth: int = 3, threshold: float = 0.18) -> nx.DiGraph:
    graph = nx.DiGraph()
    obs = ObservationView(case.observations)
    frontier = list(case.symptoms)
    for symptom in frontier:
        if symptom in case.physical_graph:
            graph.add_node(symptom, **dict(case.physical_graph.nodes[symptom]))
    for _ in range(depth):
        next_frontier: list[str] = []
        for node in frontier:
            for pred in case.physical_graph.predecessors(node):
                if obs.anomaly_score(pred) < threshold:
                    continue
                if pred not in graph:
                    graph.add_node(pred, **dict(case.physical_graph.nodes[pred]))
                    next_frontier.append(pred)
                graph.add_edge(pred, node)
        frontier = next_frontier
        if not frontier:
            break
    return graph


def granger_extractor(case: CaseData, threshold: float = 0.1) -> nx.DiGraph:
    graph = nx.DiGraph()
    obs = ObservationView(case.observations)
    for symptom in case.symptoms:
        if symptom in case.physical_graph:
            graph.add_node(symptom, **dict(case.physical_graph.nodes[symptom]))
            for pred in case.physical_graph.predecessors(symptom):
                if obs.granger_proxy(pred, symptom) > threshold:
                    graph.add_node(pred, **dict(case.physical_graph.nodes[pred]))
                    graph.add_edge(pred, symptom)
    return graph


def build_initial_graph(case: CaseData, extractor: str) -> nx.DiGraph:
    if extractor in case.initial_subgraphs:
        return manifest_extractor(case, extractor)
    if extractor == "topocausal":
        return topocausal_extractor(case)
    if extractor == "granger":
        return granger_extractor(case)
    raise KeyError(f"Unknown extractor: {extractor}")

