"""Offline sensitivity experiment on a fictional 40 m square."""

from math import ceil
from random import Random
from typing import NamedTuple

import pandas as pd
from shapely.geometry import box

from crowd_model import CELL_M, TICK_SECONDS
from event_model import EVENT_SECONDS, EventCrowdModel
from model import NarrativeModel


POPULATION = 100
COUPLING = {"zero": 0.0, "weak": 0.15, "strong": 0.45}


class Journey(NamedTuple):
    person_index: int
    decision_second: int
    travel_seconds: int

    def arrival_tick(self):
        return ceil((self.decision_second + self.travel_seconds) / TICK_SECONDS)


def plan_journeys(seed, uplift):
    """Record each intended journey before any assistance is offered."""
    narrative = NarrativeModel(num_agents=POPULATION, rng=seed)
    decisions = Random(f"attendance:{seed}")
    decision_seconds = range(0, EVENT_SECONDS, 60)
    by_minute = [[] for _ in decision_seconds]
    for index in range(POPULATION):
        by_minute[decisions.randrange(len(by_minute))].append(index)

    journeys = []
    for second, cohort in zip(decision_seconds, by_minute, strict=True):
        for index in cohort:
            exposed = narrative.people[index].state == "Exposed"
            belief_draw = decisions.random()
            attendance_draw = decisions.random()
            travel_seconds = decisions.randint(1, 90)
            believes = exposed and belief_draw < 0.5
            probability = 0.25 + (uplift if believes else 0.0)
            if attendance_draw < probability:
                journeys.append(Journey(index, second, travel_seconds))
        narrative.step()

    return narrative, journeys


def attendance_plan(seed, uplift):
    narrative, journeys = plan_journeys(seed, uplift)
    return narrative, [(j.person_index, j.arrival_tick()) for j in journeys]


def make_crowd(seed, bookings):
    crowd = EventCrowdModel(
        num_agents=len(bookings), rng=seed, geometry=box(0, 0, 40, 40)
    )
    # The same 5 m by 5 m holding area is available in every scenario.
    crowd.entrance_zone = {
        (x, y) for x, y in crowd.cells
        if x * CELL_M < 5 and y * CELL_M < 5
    }
    assert len(crowd.entrance_zone) >= POPULATION
    for person, (index, arrival_tick) in zip(crowd.people, bookings, strict=True):
        person.narrative_index = index
        person.arrival_tick = arrival_tick
    return crowd


def run_scenario(seed, scenario):
    narrative, bookings = attendance_plan(seed, COUPLING[scenario])
    planned = len(bookings)
    scheduled, inside, departed, peak = 0, 0, 0, 0.0
    if bookings:
        crowd = make_crowd(seed, bookings)
        while crowd.running:
            crowd.step()

        scheduled = crowd.count("scheduled")
        inside = crowd.inside_count()
        departed = crowd.count("departed")
        peak = crowd.peak_density
        assert scheduled == sum(tick > crowd.steps for _, tick in bookings)

    assert planned == scheduled + inside + departed
    return {
        "scenario": scenario,
        "seed": seed,
        "population": POPULATION,
        "did_not_attend": POPULATION - planned,
        "planned": planned,
        "still_travelling": scheduled,
        "inside": inside,
        "departed": departed,
        "peak_persons_m2": peak,
        "exposure_person_hours": narrative.exposure_hours,
    }


if __name__ == "__main__":
    results = pd.DataFrame(run_scenario(42, scenario) for scenario in COUPLING)
    print(results.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
