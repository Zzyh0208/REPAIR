from __future__ import annotations

import argparse

from repair.pipeline import RepairPipeline
from repair.reporting import save_run_result, save_summary


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
    save_run_result(result, args.output)
    save_summary([result], args.output)


if __name__ == "__main__":
    main()

