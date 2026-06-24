from __future__ import annotations

import argparse
import json
from pathlib import Path

from repair.pipeline import RepairPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--extractor", required=True)
    parser.add_argument("--locator", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pipeline = RepairPipeline(args.config)
    case = pipeline.load_cases(args.dataset, [args.case_id])[0]
    result = pipeline.run_case(case, args.extractor, args.locator, args.output)
    payload = {
        "case_id": result.case_id,
        "extractor": result.extractor,
        "locator": result.locator,
        "ranking_before": result.ranking_before,
        "ranking_after": result.ranking_after,
        "metrics": result.metrics,
        "cycles": [
            {
                "cycle_index": cycle.cycle_index,
                "phi_before": cycle.phi_before,
                "phi_after": cycle.phi_after,
                "issues_seen": cycle.issues_seen,
                "issues_resolved": cycle.issues_resolved,
                "actions": cycle.actions,
            }
            for cycle in result.cycle_records
        ],
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


if __name__ == "__main__":
    main()

