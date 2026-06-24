from __future__ import annotations

import json

import networkx as nx

from .features import ObservationView
from .llm import OpenRouterClient
from .prompts import locator_prompt
from .schemas import CaseData


def _candidate_roots(graph: nx.DiGraph) -> list[str]:
    roots = [node for node in graph.nodes if graph.in_degree(node) == 0]
    return roots or list(graph.nodes)


def pagerank_locator(case: CaseData, graph: nx.DiGraph) -> list[str]:
    scores = nx.pagerank(graph.reverse(copy=True)) if graph.number_of_nodes() else {}
    return [node for node, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)]


def earliest_onset_locator(case: CaseData, graph: nx.DiGraph) -> list[str]:
    obs = ObservationView(case.observations)
    threshold = 0.18
    candidates = _candidate_roots(graph)
    return sorted(candidates, key=lambda node: (obs.onset_time(node, threshold), -obs.anomaly_score(node)))


def granger_score_locator(case: CaseData, graph: nx.DiGraph) -> list[str]:
    obs = ObservationView(case.observations)
    candidates = _candidate_roots(graph)
    scores = []
    for node in candidates:
        score = 0.0
        for symptom in case.symptoms:
            score += max(0.0, obs.granger_proxy(node, symptom))
        scores.append((node, score))
    return [node for node, _ in sorted(scores, key=lambda item: item[1], reverse=True)]


def structural_locator(case: CaseData, graph: nx.DiGraph) -> list[str]:
    obs = ObservationView(case.observations)
    threshold = 0.18
    candidates = _candidate_roots(graph)
    scored = []
    for node in candidates:
        reach = len(nx.descendants(graph, node)) if node in graph else 0
        score = 0.6 * (1.0 / max(obs.onset_time(node, threshold), 1.0)) + 0.4 * reach
        scored.append((node, score))
    return [node for node, _ in sorted(scored, key=lambda item: item[1], reverse=True)]


def llm_judge_locator(case: CaseData, graph: nx.DiGraph, llm_client: OpenRouterClient) -> list[str]:
    obs = ObservationView(case.observations)
    candidates = _candidate_roots(graph)
    payload = {
        "candidates": [
            {
                "node": node,
                "anomaly_score": obs.anomaly_score(node),
                "onset_time": obs.onset_time(node, 0.18),
                "reachable_nodes": len(nx.descendants(graph, node)) if node in graph else 0,
            }
            for node in candidates
        ],
        "symptoms": case.symptoms,
    }
    system_prompt, user_prompt = locator_prompt(json.dumps(payload))
    response = llm_client.complete_json(system_prompt, user_prompt)
    ranking = response.get("ranking", [])
    if not ranking:
        return structural_locator(case, graph)
    seen = set()
    ordered = []
    for node in ranking:
        if node in candidates and node not in seen:
            seen.add(node)
            ordered.append(node)
    for node in candidates:
        if node not in seen:
            ordered.append(node)
    return ordered


def rank_roots(
    case: CaseData,
    graph: nx.DiGraph,
    locator: str,
    llm_client: OpenRouterClient | None = None,
) -> list[str]:
    if locator == "pagerank":
        return pagerank_locator(case, graph)
    if locator == "earliest_onset":
        return earliest_onset_locator(case, graph)
    if locator == "granger_score":
        return granger_score_locator(case, graph)
    if locator == "structural":
        return structural_locator(case, graph)
    if locator == "llm_judge":
        if not llm_client:
            raise RuntimeError("LLM client is required for llm_judge.")
        return llm_judge_locator(case, graph, llm_client)
    raise KeyError(f"Unknown locator: {locator}")

