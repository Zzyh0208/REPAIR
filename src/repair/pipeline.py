from __future__ import annotations

from pathlib import Path

from .config import load_config
from .coordinator import GlobalCoordinator
from .data import load_cases
from .defects import DefectDetector
from .dsl import SkillLibrary
from .evaluation import evaluate_all
from .extractors import build_initial_graph
from .llm import OpenRouterClient
from .locators import rank_roots
from .planner import RepairPlanner
from .schemas import RunResult


class RepairPipeline:
    def __init__(self, config_path: str | Path) -> None:
        self.config = load_config(config_path)
        llm_cfg = self.config["llm"]
        self.llm_client = OpenRouterClient(
            model=llm_cfg["model"],
            timeout_s=int(llm_cfg["timeout_s"]),
            max_retries=int(llm_cfg["max_retries"]),
            temperature=float(llm_cfg["temperature"]),
        )

    def run_case(self, case, extractor: str, locator: str, output_dir: str | Path | None = None) -> RunResult:
        initial_graph = build_initial_graph(case, extractor)
        llm_for_locator = self.llm_client if self.config["llm"]["enabled_for_locator"] else None
        ranking_before = rank_roots(case, initial_graph, locator, llm_for_locator)
        skill_path = None
        if output_dir:
            skill_path = Path(output_dir) / "dsl" / f"{case.case_id}.json"
        detector = DefectDetector(self.config)
        skill_library = SkillLibrary(skill_path, float(self.config["repair"]["retrieval_threshold"]))
        planner = RepairPlanner(
            self.config,
            skill_library,
            self.llm_client if self.config["llm"]["enabled_for_sra"] else None,
        )
        coordinator = GlobalCoordinator(self.config, detector, planner, skill_library)
        repaired_graph, traces = coordinator.run(case, initial_graph)
        ranking_after = rank_roots(case, repaired_graph, locator, llm_for_locator)
        metrics = evaluate_all(
            initial_graph,
            repaired_graph,
            ranking_before,
            ranking_after,
            case.true_graph,
            case.true_roots,
            list(self.config["evaluation"]["top_k"]),
        )
        return RunResult(
            case_id=case.case_id,
            extractor=extractor,
            locator=locator,
            graph_before=initial_graph,
            graph_after=repaired_graph,
            ranking_before=ranking_before,
            ranking_after=ranking_after,
            cycle_records=traces,
            metrics=metrics,
        )

    def load_cases(self, dataset_dir: str | Path, case_ids: list[str] | None = None):
        return load_cases(dataset_dir, case_ids)

