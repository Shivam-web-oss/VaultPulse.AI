"""Workflow planner (doc §12).

Turns the analyzed requirement into a dynamic plan: which registered tools,
which sources, how many rounds, and how many records each round should add.
This is the "AI decides WHAT" step; the graph executes it deterministically.

Phase D: plans over-fetch raw records (validation drops any that fail
constraints such as price caps or URL scheme), and the graph loops
search → extract → validate → deduplicate until enough valid records exist
or the planned rounds are exhausted (doc §13: report PARTIAL, never fabricate).
"""

from typing import Dict, List

from app.ai.requirement_analyzer import Requirement
from app.tools import registry

# Validation attrition: real sources yield records that fail constraint
# checks, so plan raw volume above the requested count.
RAW_OVERFETCH = 2.0
MAX_PLANNED_ROUNDS = 8
MAX_TAKE_PER_ROUND = 10


def plan(requirement: Requirement) -> Dict:
    tool_calls: List[dict] = registry.select_tools(requirement.entity)
    raw_target = int(requirement.count * RAW_OVERFETCH)
    remaining = raw_target
    rounds: List[dict] = []
    round_index = 0

    # Spread the request across available sources until the raw target is covered.
    while remaining > 0 and round_index < MAX_PLANNED_ROUNDS:
        call = tool_calls[round_index % len(tool_calls)]
        source = call["source"]
        capacity = registry.source_capacity(source)
        take = min(remaining, capacity, MAX_TAKE_PER_ROUND)
        if take <= 0:
            break
        rounds.append({"round": round_index + 1, "tool": call["name"], "source": source, "offset": 0, "take": take})
        remaining -= take
        round_index += 1

    return {
        "entity": requirement.entity,
        "targetCount": requirement.count,
        "plannedCount": raw_target - remaining,
        "sufficient": remaining <= 0,
        "rounds": rounds,
        "toolCalls": tool_calls,
    }
