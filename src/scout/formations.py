"""Stable slots and topology, independent of player identity and chemistry."""
from functools import lru_cache

import numpy as np
from scipy.optimize import linear_sum_assignment

from scout.contracts import Role
from scout.squad_contracts import FormationDefinition, FormationSlot, LineupState

PRESETS = {
    "4-3-3": [["LB", "LCB", "RCB", "RB"], ["DM"], ["LCM", "RCM"], ["LW", "ST", "RW"]],
    "4-2-3-1": [["LB", "LCB", "RCB", "RB"], ["LDM", "RDM"], ["LW", "AM", "RW"], ["ST"]],
    "4-4-2": [["LB", "LCB", "RCB", "RB"], ["LM", "LCM", "RCM", "RM"], ["LST", "RST"]],
    "3-4-3": [["LCB", "CB", "RCB"], ["LWB", "LCM", "RCM", "RWB"], ["LW", "ST", "RW"]],
    "3-5-2": [["LCB", "CB", "RCB"], ["LWB", "LCM", "DM", "RCM", "RWB"], ["LST", "RST"]],
}


def slot_role(label):
    if label == "GK":
        return Role.GK
    if "CB" in label:
        return Role.CB
    if label in {"LB", "RB", "LWB", "RWB"}:
        return Role.FB
    if "DM" in label:
        return Role.DM
    if "CM" in label:
        return Role.CM
    if label == "AM":
        return Role.AM
    if label in {"LW", "RW", "LM", "RM"}:
        return Role.W
    return Role.ST


@lru_cache
def formations():
    result = []
    for name, lines in PRESETS.items():
        rows = [["GK"], *lines]
        slots = []
        for row, labels in enumerate(rows):
            for index, label in enumerate(labels):
                x = (0.5 if len(labels) == 1 else 0.18 + index * 0.64 / (len(labels) - 1))
                y = 0.86 - row * 0.70 / (len(rows) - 1)
                slots.append(FormationSlot(id=label, label=label, role=slot_role(label), row=row, x=x, y=y,
                    side="left" if x < 0.45 else "right" if x > 0.55 else "centre"))
        edges = set()
        for row in range(1, len(rows)):
            current = [item for item in slots if item.row == row]
            for a, b in zip(current, current[1:], strict=False):
                edges.add(tuple(sorted((a.id, b.id))))
            if row > 1:
                previous = [item for item in slots if item.row == row - 1]
                for source, targets in [(current, previous), (previous, current)]:
                    for a in source:
                        b = min(targets, key=lambda item: (abs(a.x - item.x), item.id))
                        edges.add(tuple(sorted((a.id, b.id))))
        defenders = sorted((item for item in slots if item.row == 1 and item.role == Role.CB),
                           key=lambda item: (abs(item.x - 0.5), item.id))[:2]
        edges.update(tuple(sorted(("GK", item.id))) for item in defenders)
        result.append(FormationDefinition(id=name, slots=slots, edges=sorted(edges)))
    return tuple(result)


def formation(identifier):
    for item in formations():
        if item.id == identifier:
            return item
    raise ValueError("Unsupported formation")


def reassign(lineup: LineupState, destination: str, players):
    old, new = formation(lineup.formation_id), formation(destination)
    previous = {item.id: item for item in old.slots}
    selected = sorted((pid, previous[sid]) for sid, pid in lineup.assignments.items() if pid)
    slots = sorted(new.slots, key=lambda item: item.id)
    costs = np.zeros((len(selected), len(slots)))
    for i, (pid, origin) in enumerate(selected):
        player = players[pid]
        for j, target in enumerate(slots):
            keeper_mismatch = (Role.GK in player.roles) != (target.role == Role.GK)
            costs[i, j] = (1e9 if keeper_mismatch else 0) + (0 if target.role in player.roles else 1e6)
            costs[i, j] += 0 if player.planning_side in {"centre", target.side} else 1e3
            costs[i, j] += ((origin.x - target.x) ** 2 + (origin.y - target.y) ** 2) * 10
            # Stable nonseparable tie-break, below meaningful coordinate differences.
            costs[i, j] += ((i + 1) * (j + 1)) * 1e-8
    assignments = {item.id: None for item in new.slots}
    if selected:
        rows, columns = linear_sum_assignment(costs)
        for i, j in zip(rows, columns, strict=True):
            assignments[slots[j].id] = selected[i][0]
    return LineupState(snapshot_id=lineup.snapshot_id, formation_id=destination, assignments=assignments,
                       bench=lineup.bench, role_multiplier=lineup.role_multiplier)
