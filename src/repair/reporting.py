from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .graph_io import save_graph
from .schemas import RunResult


def save_run_result(result: RunResult, output_dir: str | Path) -> None:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    save_graph(result.graph_before, root / "graphs" / f"{result.case_id}_{result.extractor}_before.json")
    save_graph(result.graph_after, root / "graphs" / f"{result.case_id}_{result.extractor}_after.json")
    trace_dir = root / "cycle_traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    with (trace_dir / f"{result.case_id}_{result.extractor}_{result.locator}.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "case_id": result.case_id,
                "extractor": result.extractor,
                "locator": result.locator,
                "ranking_before": result.ranking_before,
                "ranking_after": result.ranking_after,
                "metrics": result.metrics,
                "cycles": [
                    {
                        "cycle_index": record.cycle_index,
                        "phi_before": record.phi_before,
                        "phi_after": record.phi_after,
                        "issues_seen": record.issues_seen,
                        "issues_resolved": record.issues_resolved,
                        "actions": record.actions,
                    }
                    for record in result.cycle_records
                ],
            },
            handle,
            indent=2,
        )


def save_summary(results: Iterable[RunResult], output_dir: str | Path) -> None:
    rows = []
    for result in results:
        row = {
            "case_id": result.case_id,
            "extractor": result.extractor,
            "locator": result.locator,
            **result.metrics,
        }
        rows.append(row)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(root / "per_case.csv", index=False)
    summary = frame.mean(numeric_only=True).to_dict() if not frame.empty else {}
    with (root / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

