# Data Format

The repository expects case-level inputs that are already derived from SUMO simulation outputs or from an equivalent preprocessing pipeline.

## Directory Structure

```text
cases/
  <case_id>/
    physical_graph.json
    observations.csv
    labels.json
    initial_subgraphs/
      granger.json
      topocausal.json
      ocean.json
      ...
```

## `physical_graph.json`

```json
{
  "directed": true,
  "nodes": [
    {"id": "v1", "attrs": {"road_type": "arterial"}},
    {"id": "v2", "attrs": {}}
  ],
  "edges": [
    {"source": "v1", "target": "v2", "attrs": {"length": 120.0}}
  ]
}
```

## `observations.csv`

Required columns:

- `timestamp`
- `node_id`
- `speed`
- `density`
- `flow`
- `occupancy`
- `queue_length`
- `time_mean_speed`
- `headway`
- `harmonic_speed`

Optional columns:

- `is_symptom`

## `labels.json`

```json
{
  "true_roots": ["v1"],
  "symptoms": ["v5"],
  "true_graph": {
    "directed": true,
    "nodes": [],
    "edges": []
  }
}
```

If `true_graph` is omitted, structural metrics that depend on ground-truth topology are skipped. RCA metrics still run if `true_roots` are provided.

## `initial_subgraphs/*.json`

Each extractor is stored as a graph file with the same schema as `physical_graph.json`. The filename stem is treated as the extractor name.

## Notes

- The repository does not assume a single upstream extractor implementation.
- Any external baseline can be integrated by exporting its candidate subgraph in this format.
- The toy dataset under `examples/toy_dataset` is only for installation checks and interface validation.

