from __future__ import annotations

import numpy as np
import pandas as pd

from .schemas import CaseData


def apply_perturbation(case: CaseData, spec: dict) -> CaseData:
    frame = case.observations.copy()
    if spec.get("speed_noise_std"):
        noise = np.random.normal(0.0, float(spec["speed_noise_std"]), size=len(frame))
        frame["speed"] = frame["speed"] + noise
    if spec.get("missing_rate"):
        mask = np.random.rand(len(frame)) >= float(spec["missing_rate"])
        frame = frame.loc[mask].reset_index(drop=True)
    graph = case.physical_graph.copy()
    if spec.get("edge_drop_rate"):
        edges = list(graph.edges)
        keep = np.random.rand(len(edges)) >= float(spec["edge_drop_rate"])
        for edge, keep_edge in zip(edges, keep):
            if not keep_edge and graph.has_edge(*edge):
                graph.remove_edge(*edge)
    return CaseData(
        case_id=case.case_id,
        case_dir=case.case_dir,
        physical_graph=graph,
        observations=frame,
        symptoms=list(case.symptoms),
        initial_subgraphs={name: subgraph.copy() for name, subgraph in case.initial_subgraphs.items()},
        true_roots=list(case.true_roots),
        true_graph=case.true_graph.copy() if case.true_graph is not None else None,
    )

