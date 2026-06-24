# REPAIR: Defect-Aware Iterative Subgraph Refinement for Traffic Root-Cause Analysis

This repository contains the reference implementation of **REPAIR**, a plug-and-play subgraph refinement framework for traffic root-cause analysis. REPAIR takes an initial candidate subgraph, detects structural defects, applies targeted repair operators, and sends the refined graph to a downstream root-cause locator.

## Overview

The codebase includes:

- the full REPAIR pipeline with `DPA`, `SRA`, `GC`, `DSL`, and nine repair operators
- experiment runners for single-case execution, plug-and-play evaluation, ablations, and robustness tests
- built-in extractors and locators used by the main pipeline
- OpenRouter-based LLM integration

Inputs are expected to be converted into the case format described in [data/README.md](data/README.md).

## Repository Structure

```text
REPAIR/
  configs/            experiment configurations
  data/               input format documentation
  docs/               environment notes
  examples/           toy example for installation checks
  scripts/            experiment entry points
  src/repair/         main source code
  tests/              basic tests
```

## Installation

Python 3.10 or newer is recommended.

```bash
cd E:\py_project\REPAIR
python -m venv .venv
.venv\Scripts\activate
pip install -U pip
pip install -e .
```

Or:

```bash
pip install -r requirements.txt
```

## OpenRouter Configuration

Set the API key before running any LLM-enabled experiment:

```bash
set OPENROUTER_API_KEY=your_api_key
```

The default backend is configured in `configs/default.yaml`.

## Data Format

Each case directory should contain:

- `physical_graph.json`
- `observations.csv`
- `labels.json`
- `initial_subgraphs/<extractor>.json`

See [data/README.md](data/README.md) for the full schema. A minimal example is provided in `examples/toy_dataset`.

## Usage

Run a single case:

```bash
python scripts/run_repair.py ^
  --config configs/default.yaml ^
  --dataset examples/toy_dataset/cases ^
  --case-id toy-001 ^
  --extractor topocausal ^
  --locator structural ^
  --output artifacts/single_case
```

Run plug-and-play evaluation:

```bash
python scripts/run_plug_and_play.py ^
  --config configs/experiments/pluggability.yaml ^
  --dataset examples/toy_dataset/cases ^
  --output artifacts/pluggability
```

Run ablations:

```bash
python scripts/run_ablation.py ^
  --config configs/experiments/ablation.yaml ^
  --dataset examples/toy_dataset/cases ^
  --output artifacts/ablation
```

Run robustness experiments:

```bash
python scripts/run_robustness.py ^
  --config configs/experiments/robustness.yaml ^
  --dataset examples/toy_dataset/cases ^
  --output artifacts/robustness
```

Export a case study:

```bash
python scripts/export_case_study.py ^
  --config configs/default.yaml ^
  --dataset examples/toy_dataset/cases ^
  --case-id toy-001 ^
  --extractor topocausal ^
  --locator structural ^
  --output artifacts/case_study/toy-001.json
```

## Main Scripts

- `scripts/run_repair.py`: run REPAIR on one case
- `scripts/run_plug_and_play.py`: sweep extractor-locator pairs
- `scripts/run_ablation.py`: run ablation settings
- `scripts/run_robustness.py`: run perturbation-based evaluation
- `scripts/export_case_study.py`: export cycle-level traces for one case

## Citation

If you use this codebase, please cite the corresponding paper.