from __future__ import annotations

import argparse

from repair.config import load_config
from repair.pipeline import RepairPipeline
from repair.perturbation import apply_perturbation
from repair.reporting import save_run_result, save_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    pipeline = RepairPipeline(args.config)
    cases = pipeline.load_cases(args.dataset)
    results = []
    for spec in config["experiment"]["perturbations"]:
        for case in cases:
            perturbed = apply_perturbation(case, spec)
            result = pipeline.run_case(
                perturbed,
                config["experiment"]["extractor"],
                config["experiment"]["locator"],
                f"{args.output}/{spec['name']}",
            )
            save_run_result(result, f"{args.output}/{spec['name']}")
            results.append(result)
    save_summary(results, args.output)


if __name__ == "__main__":
    main()

