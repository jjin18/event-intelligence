"""Simple file IO helpers for Eventful."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .event_state import PERSON_CSV_COLUMNS, empty_person, save_event_state


def read_event_brief(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text().strip()


def load_people_csv(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    with p.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person = empty_person()
            for k, v in row.items():
                if k in person:
                    person[k] = v
                else:
                    # keep unknown columns as notes
                    person.setdefault("extra", {})[k] = v
            out.append(person)
    return out


def write_event_state(path: str | Path, state: dict[str, Any]) -> None:
    save_event_state(path, state)


def write_ranked_people_csv(path: str | Path, people: list[dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PERSON_CSV_COLUMNS)
        writer.writeheader()
        for person in people:
            row = {col: _csv_value(person.get(col, "")) for col in PERSON_CSV_COLUMNS}
            writer.writerow(row)


def _csv_value(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)
