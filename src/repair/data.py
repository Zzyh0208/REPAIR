from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .graph_io import graph_from_dict, load_graph
from .schemas import CaseData


def load_case(case_dir: str | Path) -> CaseData:
    root = Path(case_dir)
    observations = pd.read_csv(root / "observations.csv")
    with (root / "labels.json").open("r", encoding="utf-8") as handle:
        labels = json.load(handle)
    initial_dir = root / "initial_subgraphs"
    initial_subgraphs = {
        graph_path.stem: load_graph(graph_path)
        for graph_path in sorted(initial_dir.glob("*.json"))
    }
    true_graph = None
    if "true_graph" in labels and labels["true_graph"]:
        true_graph = graph_from_dict(labels["true_graph"])
    symptoms = labels.get("symptoms")
    if not symptoms and "is_symptom" in observations.columns:
        symptoms = sorted(observations.loc[observations["is_symptom"] > 0, "node_id"].unique().tolist())
    return CaseData(
        case_id=root.name,
        case_dir=root,
        physical_graph=load_graph(root / "physical_graph.json"),
        observations=observations,
        symptoms=symptoms or [],
        initial_subgraphs=initial_subgraphs,
        true_roots=labels.get("true_roots", []),
        true_graph=true_graph,
    )


def load_cases(dataset_dir: str | Path, case_ids: list[str] | None = None) -> list[CaseData]:
    root = Path(dataset_dir)
    selected = set(case_ids) if case_ids else None
    cases = []
    for case_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        if selected and case_dir.name not in selected:
            continue
        cases.append(load_case(case_dir))
    return cases

