from __future__ import annotations

from typing import Any

import networkx as nx


def _f1_score(pred: set, truth: set) -> float:
    if not pred and not truth:
        return 1.0
    if not pred or not truth:
        return 0.0
    tp = len(pred & truth)
    precision = tp / len(pred) if pred else 0.0
    recall = tp / len(truth) if truth else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _path_pairs(graph: nx.DiGraph) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for src in graph.nodes:
        for dst in nx.descendants(graph, src):
            pairs.add((src, dst))
    return pairs


def structural_metrics(graph: nx.DiGraph, true_graph: nx.DiGraph | None, true_roots: list[str]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    if true_graph is not None:
        pred_nodes = set(graph.nodes)
        pred_edges = set(graph.edges)
        true_nodes = set(true_graph.nodes)
        true_edges = set(true_graph.edges)
        metrics["node_f1"] = _f1_score(pred_nodes, true_nodes)
        metrics["edge_f1"] = _f1_score(pred_edges, true_edges)
        metrics["path_f1"] = _f1_score(_path_pairs(graph), _path_pairs(true_graph))
        metrics["shd"] = len(pred_edges ^ true_edges)
    if true_roots:
        metrics["root_coverage"] = float(any(root in graph for root in true_roots))
    return metrics


def ranking_metrics(ranking: list[str], true_roots: list[str], top_k: list[int]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    if not true_roots:
        return metrics
    truth = set(true_roots)
    for k in top_k:
        metrics[f"hit@{k}"] = float(any(node in truth for node in ranking[:k]))
    reciprocal = 0.0
    for index, node in enumerate(ranking, start=1):
        if node in truth:
            reciprocal = 1.0 / index
            break
    metrics["mrr"] = reciprocal
    return metrics


def evaluate_all(
    graph_before: nx.DiGraph,
    graph_after: nx.DiGraph,
    ranking_before: list[str],
    ranking_after: list[str],
    true_graph: nx.DiGraph | None,
    true_roots: list[str],
    top_k: list[int],
) -> dict[str, Any]:
    metrics = {}
    before_struct = structural_metrics(graph_before, true_graph, true_roots)
    after_struct = structural_metrics(graph_after, true_graph, true_roots)
    before_rank = ranking_metrics(ranking_before, true_roots, top_k)
    after_rank = ranking_metrics(ranking_after, true_roots, top_k)
    for key, value in before_struct.items():
        metrics[f"before_{key}"] = value
    for key, value in after_struct.items():
        metrics[f"after_{key}"] = value
    for key, value in before_rank.items():
        metrics[f"before_{key}"] = value
    for key, value in after_rank.items():
        metrics[f"after_{key}"] = value
    return metrics

