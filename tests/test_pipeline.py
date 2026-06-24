from pathlib import Path

from repair.pipeline import RepairPipeline


def test_toy_case_runs() -> None:
    root = Path(__file__).resolve().parents[1]
    pipeline = RepairPipeline(root / "configs" / "default.yaml")
    case = pipeline.load_cases(root / "examples" / "toy_dataset" / "cases", ["toy-001"])[0]
    result = pipeline.run_case(case, "topocausal", "structural", root / "artifacts" / "test")
    assert result.case_id == "toy-001"
    assert result.ranking_after

