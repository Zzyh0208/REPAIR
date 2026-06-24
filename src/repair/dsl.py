from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .schemas import DefectIssue, RepairAction


@dataclass(slots=True)
class Skill:
    category: str
    fingerprint: list[float]
    operator_id: str
    params: dict[str, Any]


def issue_fingerprint(issue: DefectIssue) -> np.ndarray:
    base = {
        "G1": 0,
        "G2": 1,
        "G3": 2,
        "G4": 3,
        "G5": 4,
        "G6": 5,
        "G7": 6,
        "G8": 7,
    }
    vec = np.zeros(12, dtype=float)
    vec[base.get(issue.category, 0)] = 1.0
    vec[8] = issue.confidence
    vec[9] = len(issue.nodes)
    vec[10] = len(issue.edges)
    vec[11] = float(issue.context.get("anomaly_score", 0.0))
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


class SkillLibrary:
    def __init__(self, path: str | Path | None, threshold: float) -> None:
        self.path = Path(path) if path else None
        self.threshold = threshold
        self.skills: list[Skill] = []
        if self.path and self.path.exists():
            self._load()

    def _load(self) -> None:
        with self.path.open("r", encoding="utf-8") as handle:
            rows = json.load(handle)
        self.skills = [Skill(**row) for row in rows]

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump([asdict(skill) for skill in self.skills], handle, indent=2)

    def retrieve(self, issue: DefectIssue) -> RepairAction | None:
        if not self.skills:
            return None
        target = issue_fingerprint(issue)
        best_score = -1.0
        best_skill = None
        for skill in self.skills:
            vector = np.asarray(skill.fingerprint, dtype=float)
            denom = np.linalg.norm(vector) * np.linalg.norm(target)
            score = float(np.dot(vector, target) / denom) if denom else 0.0
            if score > best_score:
                best_score = score
                best_skill = skill
        if best_skill and best_score >= self.threshold:
            return RepairAction(
                operator_id=best_skill.operator_id,
                params=best_skill.params,
                source="dsl",
            )
        return None

    def admit(self, issue: DefectIssue, action: RepairAction) -> None:
        self.skills.append(
            Skill(
                category=issue.category,
                fingerprint=issue_fingerprint(issue).tolist(),
                operator_id=action.operator_id,
                params=action.params,
            )
        )

