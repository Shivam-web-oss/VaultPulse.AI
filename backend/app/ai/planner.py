"""Workflow planner (doc §12).

Turns the analyzed requirement into a dynamic plan: which registered tools,
which sources, how many rounds, and how many records each round should add.
This is the "AI decides WHAT" step; the graph executes it deterministically.
"""

from typing import Dict, List

from app.ai.requirement_analyzer import Requirement
from app.tools import registry


def plan(requirement: Requirement) -> Dict:
    tool_calls: List[dict] = registry.select_tools(requirement.entity)
    remaining = requirement.count
    rounds: List[dict] = []
    round_index = 0

    # Spread the request across available sources until the target is covered.
    while remaining > 0 and round_index < 6:
        call = tool_calls[round_index % len(tool_calls)]
        source = call["source"]
        capacity = registry.source_capacity(source)
        take = min(remaining, capacity, 25)
        if take <= 0:
            break
        rounds.append({"round": round_index + 1, "tool": call["name"], "source": source, "offset": 0, "take": take})
        remaining -= take
        round_index += 1

    return {
        "entity": requirement.entity,
        "targetCount": requirement.count,
        "plannedCount": requirement.count - remaining,
        "sufficient": remaining <= 0,
        "rounds": rounds,
        "toolCalls": tool_calls,
    }
