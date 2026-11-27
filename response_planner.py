"""Enumerate hypothetical civilian assistance packages for the fictional square."""

import argparse
from itertools import combinations
from random import Random

import pandas as pd

from coupled_demo import COUPLING, POPULATION, make_crowd, plan_journeys
from crowd_model import TICK_SECONDS
from event_model import EVENT_SECONDS
from gdelt_scenarios import load_catalog
from model import NarrativeModel


COST = {"bulletin": 2, "rides": 3, "first_aid": 2}
BUDGET = 5


def feasible_packages(budget):
    if type(budget) is not int or budget < 0:
        raise ValueError("budget must be a non-negative integer")
    for size in range(len(COST) + 1):
        for package in combinations(COST, size):
            cost = sum(COST[action] for action in package)
            if cost <= budget:
                yield package, cost


def bulletin_exposure(seed, *, theme=None):
    model = NarrativeModel(num_agents=POPULATION, rng=seed, theme=theme)
    for second in range(0, EVENT_SECONDS, 60):
        if second == 120:
            model.correction_prob = 0.10
        model.step()
    return model.exposure_hours


def crowd_outcome(seed, journeys, ride_requests, aid_requests, offer_rides):
    bookings = []
    rides_used = 0
    for journey in journeys:
        index = journey.person_index
        if (
            offer_rides
            and index in ride_requests
            and rides_used < 6
            and journey.decision_second >= 120
        ):
            journey = journey._replace(travel_seconds=max(1, journey.travel_seconds - 20))
            rides_used += 1
        bookings.append((index, journey.arrival_tick()))

    contacts = set()
    travelling = inside = departed = 0
    peak = 0.0
    if bookings:
        crowd = make_crowd(seed, bookings)
        while crowd.running:
            crowd.step()
            seconds = crowd.steps * TICK_SECONDS
            if seconds >= 180 and (seconds - 180) % 60 == 0:
                waiting = aid_requests - contacts
                eligible = (
                    person for person in crowd.people
                    if person.cell is not None and person.narrative_index in waiting
                )
                person = min(
                    eligible, key=lambda p: (p.arrival_tick, p.narrative_index),
                    default=None,
                )
                if person is not None:
                    contacts.add(person.narrative_index)

        travelling = crowd.count("scheduled")
        inside = crowd.inside_count()
        departed = crowd.count("departed")
        peak = crowd.peak_density
        assert travelling == sum(tick > crowd.steps for _, tick in bookings)
    assert len(journeys) == travelling + inside + departed
    return {
        "still_travelling": travelling, "inside": inside, "departed": departed,
        "unfinished": travelling + inside, "peak_persons_m2": peak,
        "ride_requests": len(ride_requests), "rides_used": rides_used,
        "rides_unmet": len(ride_requests) - rides_used,
    }, len(contacts)


def compare_plans(seed=42, scenario="weak", budget=BUDGET, *, theme=None):
    provenance = {}
    if theme is not None:
        catalog = load_catalog()
        if theme not in catalog["themes"]:
            raise ValueError(f"Unknown cached GDELT theme: {theme}")
        provenance = {
            "gdelt_theme": theme,
            "theme_split": catalog["themes"][theme]["split"],
            "gdelt_batch_utc": catalog["batch_utc"],
        }

    packages = list(feasible_packages(budget))
    baseline, journeys = plan_journeys(seed, COUPLING[scenario], theme=theme)
    requests = Random(f"support:{seed}")
    ride_requests, aid_requests = set(), set()
    for journey in journeys:
        if requests.random() < 0.35:
            ride_requests.add(journey.person_index)
        if requests.random() < 0.20:
            aid_requests.add(journey.person_index)

    rows = []
    movement = {}
    corrected_hours = None
    for package, cost in packages:
        rides = "rides" in package
        if rides not in movement:
            movement[rides] = crowd_outcome(seed, journeys, ride_requests, aid_requests, rides)
        flow, possible_contacts = movement[rides]
        contacts = possible_contacts if "first_aid" in package else 0
        hours = baseline.exposure_hours
        if "bulletin" in package:
            if corrected_hours is None:
                corrected_hours = bulletin_exposure(seed, theme=theme)
            hours = corrected_hours
        rows.append({
            "seed": seed, "scenario": scenario, "budget": budget, **provenance,
            "plan": "+".join(package) or "baseline", "cost": cost,
            "planned": len(journeys), **flow, "exposure_person_hours": hours,
            "aid_requests": len(aid_requests), "aid_contacts": contacts,
            "aid_unmet": len(aid_requests) - contacts,
        })

    results = pd.DataFrame(rows)
    outcomes = results[["peak_persons_m2", "exposure_person_hours", "unfinished",
                        "rides_unmet", "aid_unmet"]]

    frontier = []
    for i, outcome in outcomes.iterrows():
        no_worse = outcomes.le(outcome).all(axis=1)
        better = outcomes.lt(outcome).any(axis=1)
        cheaper = results.cost < results.at[i, "cost"]
        frontier.append(not (no_worse & (better | cheaper)).any())
    results["on_frontier"] = frontier
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", choices=load_catalog()["themes"],
                        help="Select a cached theme for initial exposure placement.")
    args = parser.parse_args()
    result = compare_plans(theme=args.theme)
    print(result.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
