from __future__ import annotations

import argparse
import tempfile
from copy import deepcopy
from pathlib import Path

import yaml

from repair.config import load_config
from repair.pipeline import RepairPipeline
from repair.reporting import save_run_result, save_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def apply_variant(config: dict, variant: str) -> dict:
    cfg = deepcopy(config)
    if variant == "no_dsl":
        cfg["repair"]["retrieval_threshold"] = 2.0
    elif variant == "no_llm":
        cfg["llm"]["enabled_for_sra"] = False
        cfg["llm"]["enabled_for_dpa"] = False
        cfg["llm"]["enabled_for_locator"] = False
    elif variant == "no_gc":
        cfg["repair"]["stagnation_patience"] = cfg["repair"]["max_cycles"]
        cfg["repair"]["beta_side_effect_bound"] = 999
    elif variant == "no_parallel_partition":
        pass
    return cfg


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    base = deepcopy(config)
    cases = RepairPipeline(args.config).load_cases(args.dataset)
    results = []
    for variant in config["experiment"]["variants"]:
        variant_cfg = apply_variant(base, variant)
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as handle:
            yaml.safe_dump(variant_cfg, handle, sort_keys=False)
            temp_path = Path(handle.name)
        pipeline = RepairPipeline(temp_path)
        for case in cases:
            result = pipeline.run_case(
                case,
                config["experiment"]["extractor"],
                config["experiment"]["locator"],
                Path(args.output) / variant,
            )
            save_run_result(result, Path(args.output) / variant)
            results.append(result)
    save_summary(results, args.output)


if __name__ == "__main__":
    main()

