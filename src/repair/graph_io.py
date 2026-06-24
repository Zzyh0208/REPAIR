from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx


def graph_from_dict(payload: dict[str, Any]) -> nx.DiGraph:
    graph = nx.DiGraph()
    for node in payload.get("nodes", []):
        graph.add_node(node["id"], **node.get("attrs", {}))
    for edge in payload.get("edges", []):
        graph.add_edge(edge["source"], edge["target"], **edge.get("attrs", {}))
    return graph


def graph_to_dict(graph: nx.DiGraph) -> dict[str, Any]:
    return {
        "directed": True,
        "nodes": [{"id": node, "attrs": dict(graph.nodes[node])} for node in graph.nodes],
        "edges": [
            {"source": src, "target": dst, "attrs": dict(graph.edges[src, dst])}
            for src, dst in graph.edges
        ],
    }


def load_graph(path: str | Path) -> nx.DiGraph:
    with Path(path).open("r", encoding="utf-8") as handle:
        return graph_from_dict(json.load(handle))


def save_graph(graph: nx.DiGraph, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(graph_to_dict(graph), handle, indent=2)

