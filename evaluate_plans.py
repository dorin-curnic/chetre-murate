"""Paired, offline evaluation of fixed packages across the cached themes."""

from pathlib import Path

import pandas as pd

from coupled_demo import COUPLING
from gdelt_scenarios import load_catalog
from response_planner import BUDGET, compare_plans


SEEDS = (1, 7, 42, 73, 101)


def evaluate():
    cases = []
    for theme in load_catalog()["themes"]:
        for scenario in COUPLING:
            for seed in SEEDS:
                plans = compare_plans(seed, scenario, BUDGET, theme=theme)
                plans = plans.set_index("plan")
                assert plans.index.is_unique
                baseline = plans.loc["baseline"]
                assert plans["planned"].eq(baseline["planned"]).all()
                assert plans["planned"].eq(plans["unfinished"] + plans["departed"]).all()
                for metric in ("peak_persons_m2", "exposure_person_hours", "unfinished"):
                    plans[f"delta_{metric}"] = plans[metric] - baseline[metric]
                cases.append(plans.reset_index())

    runs = pd.concat(cases, ignore_index=True)
    groups = ["theme_split", "gdelt_theme", "scenario", "budget", "plan", "cost"]
    summary = runs.groupby(groups, as_index=False, sort=False).agg(
        seeds=("seed", "nunique"),
        mean_peak_persons_m2=("peak_persons_m2", "mean"),
        mean_delta_peak=("delta_peak_persons_m2", "mean"),
        min_delta_peak=("delta_peak_persons_m2", "min"),
        max_delta_peak=("delta_peak_persons_m2", "max"),
        mean_exposure_person_hours=("exposure_person_hours", "mean"),
        mean_delta_exposure=("delta_exposure_person_hours", "mean"),
        min_delta_exposure=("delta_exposure_person_hours", "min"),
        max_delta_exposure=("delta_exposure_person_hours", "max"),
        mean_delta_unfinished=("delta_unfinished", "mean"),
        mean_rides_unmet=("rides_unmet", "mean"),
        mean_aid_unmet=("aid_unmet", "mean"),
    )
    assert summary["seeds"].eq(len(SEEDS)).all()
    return runs, summary


def main():
    runs, summary = evaluate()
    output = Path(__file__).resolve().parent / "results"
    output.mkdir(exist_ok=True)
    runs.to_csv(output / "plan-evaluation-runs.csv", index=False)
    summary.to_csv(output / "plan-evaluation-summary.csv", index=False)
    print(f"Saved {len(runs)} plan rows and {len(summary)} summary rows in {output}")
    print("Held-out themes, weak coupling. Deltas are plan minus paired baseline.")
    display = summary.loc[
        summary.theme_split.eq("held_out") & summary.scenario.eq("weak"),
        ["gdelt_theme", "plan", "seeds", "mean_delta_peak", "mean_delta_exposure",
         "mean_delta_unfinished", "mean_rides_unmet", "mean_aid_unmet"],
    ]
    print(display.to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    main()
