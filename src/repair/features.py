from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class ObservationView:
    frame: pd.DataFrame
    baseline_ratio: float = 0.25

    def __post_init__(self) -> None:
        self.frame = self.frame.sort_values(["node_id", "timestamp"]).reset_index(drop=True)

    def node_frame(self, node_id: str) -> pd.DataFrame:
        return self.frame.loc[self.frame["node_id"] == node_id]

    def _split(self, node_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        node_frame = self.node_frame(node_id)
        if node_frame.empty:
            return node_frame, node_frame
        pivot = max(1, int(len(node_frame) * self.baseline_ratio))
        return node_frame.iloc[:pivot], node_frame.iloc[pivot:]

    def baseline(self, node_id: str, column: str) -> float:
        head, _ = self._split(node_id)
        if head.empty:
            return 0.0
        return float(head[column].mean())

    def incident(self, node_id: str, column: str) -> float:
        _, tail = self._split(node_id)
        if tail.empty:
            return 0.0
        return float(tail[column].mean())

    def anomaly_score(self, node_id: str) -> float:
        speed_base = self.baseline(node_id, "speed")
        speed_now = self.incident(node_id, "speed")
        density_base = self.baseline(node_id, "density")
        density_now = self.incident(node_id, "density")
        occupancy_base = self.baseline(node_id, "occupancy")
        occupancy_now = self.incident(node_id, "occupancy")
        speed_drop = max(0.0, (speed_base - speed_now) / max(abs(speed_base), 1e-6))
        density_jump = max(0.0, (density_now - density_base) / max(abs(density_base), 1.0))
        occupancy_jump = max(0.0, (occupancy_now - occupancy_base) / max(abs(occupancy_base), 1.0))
        return float(0.5 * speed_drop + 0.3 * density_jump + 0.2 * occupancy_jump)

    def onset_time(self, node_id: str, threshold: float) -> float:
        node_frame = self.node_frame(node_id)
        if node_frame.empty:
            return float("inf")
        baseline_speed = self.baseline(node_id, "speed")
        if baseline_speed == 0:
            return float("inf")
        for _, row in node_frame.iterrows():
            drop = (baseline_speed - float(row["speed"])) / max(abs(baseline_speed), 1e-6)
            if drop >= threshold:
                return float(row["timestamp"])
        return float("inf")

    def granger_proxy(self, src: str, dst: str) -> float:
        src_frame = self.node_frame(src)
        dst_frame = self.node_frame(dst)
        if src_frame.empty or dst_frame.empty:
            return 0.0
        merged = src_frame[["timestamp", "speed"]].merge(
            dst_frame[["timestamp", "speed"]],
            on="timestamp",
            suffixes=("_src", "_dst"),
        )
        if len(merged) < 3:
            return 0.0
        src_delta = np.diff(merged["speed_src"].to_numpy())
        dst_delta = np.diff(merged["speed_dst"].to_numpy())
        if src_delta.size == 0 or dst_delta.size == 0:
            return 0.0
        corr = np.corrcoef(src_delta[:-1] if len(src_delta) > 1 else src_delta, dst_delta[1:] if len(dst_delta) > 1 else dst_delta)[0, 1]
        if np.isnan(corr):
            return 0.0
        return float(corr)

    def symptom_intensity(self, nodes: list[str]) -> float:
        if not nodes:
            return 0.0
        scores = [self.anomaly_score(node) for node in nodes]
        return float(np.mean(scores)) if scores else 0.0

