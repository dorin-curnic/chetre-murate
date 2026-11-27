from pathlib import Path

import pandas as pd
import solara

from coupled_demo import COUPLING
from evaluate_plans import SEEDS
from gdelt_scenarios import load_catalog
from response_planner import BUDGET, compare_plans


RESULTS = Path(__file__).resolve().parent / "results"


def csv_download(frame, filename, label):
    solara.FileDownload(
        data=frame.to_csv(index=False), filename=filename, label=label,
        mime_type="text/csv",
    )


@solara.component
def PlannerPage():
    catalog = solara.use_memo(load_catalog, [])
    theme, set_theme = solara.use_state("PUBLIC_TRANSPORT")
    scenario, set_scenario = solara.use_state("weak")
    seed, set_seed = solara.use_state(42)
    plans = solara.use_memo(
        lambda: compare_plans(seed, scenario, BUDGET, theme=theme),
        [seed, scenario, theme],
    )

    with solara.Column():
        solara.Markdown("## Response planner")
        solara.Text(
            "Compare public bulletins, voluntary rides and first-aid check-ins on "
            "a fictional 40 × 40 m square. Each package uses the same intended attendees."
        )
        with solara.ColumnsResponsive(12, small=4):
            solara.Select("GDELT theme", values=list(catalog["themes"]), value=theme, on_value=set_theme)
            solara.Select("Attendance coupling", values=list(COUPLING), value=scenario, on_value=set_scenario)
            solara.Select("Simulation seed", values=list(SEEDS), value=seed, on_value=set_seed)
        split = catalog["themes"][theme]["split"].replace("_", " ")
        solara.Text(
            f"Budget {BUDGET} units · {plans.planned.iloc[0]} planned attendees · "
            f"10 simulated minutes · {split} theme"
        )
        solara.DataFrame(plans[[
            "plan", "cost", "peak_persons_m2", "exposure_person_hours",
            "unfinished", "rides_unmet", "aid_unmet",
        ]].rename(columns={
            "plan": "Package", "cost": "Cost", "peak_persons_m2": "Peak (people/m²)",
            "exposure_person_hours": "Exposure (person-hours)", "unfinished": "Unfinished",
            "rides_unmet": "Unmet rides", "aid_unmet": "Unmet aid",
        }).round(3))
        csv_download(plans, f"plans-{theme}-{scenario}-{seed}.csv", "Download all package metrics")
        solara.Text(
            "Unfinished counts people still travelling or inside at 600 seconds. "
            "The theme selects the three initially exposed synthetic people. "
            "Costs, attendance and response effects are hypothetical."
        )


@solara.component
def EvaluationPage():
    theme, set_theme = solara.use_state("WATER_SECURITY")
    scenario, set_scenario = solara.use_state("weak")
    with solara.Column():
        solara.Markdown("## Multi-seed evaluation")
        try:
            summary = pd.read_csv(RESULTS / "plan-evaluation-summary.csv")
        except FileNotFoundError:
            solara.Info("Run uv run --no-sync python -B evaluate_plans.py, then refresh this page.")
            return

        with solara.ColumnsResponsive(12, small=6):
            solara.Select("GDELT theme", values=summary.gdelt_theme.unique().tolist(), value=theme, on_value=set_theme)
            solara.Select("Attendance coupling", values=summary.scenario.unique().tolist(), value=scenario, on_value=set_scenario)
        selected = summary.loc[summary.gdelt_theme.eq(theme) & summary.scenario.eq(scenario)]
        if selected.empty:
            solara.Info("There are no saved results for this selection.")
            return

        first = selected.iloc[0]
        split = first.theme_split.replace("_", " ")
        solara.Text(
            f"{split.capitalize()} theme · {first.seeds} seeds · budget {first.budget} units. "
            "Each change is the package result minus its matching baseline, averaged across seeds."
        )
        solara.DataFrame(selected[[
            "plan", "mean_delta_peak", "mean_delta_exposure", "mean_delta_unfinished",
            "mean_rides_unmet", "mean_aid_unmet",
        ]].rename(columns={
            "plan": "Package", "mean_delta_peak": "Δ peak (people/m²)",
            "mean_delta_exposure": "Δ exposure (person-hours)",
            "mean_delta_unfinished": "Δ unfinished", "mean_rides_unmet": "Mean unmet rides",
            "mean_aid_unmet": "Mean unmet aid",
        }).round(3).reset_index(drop=True))
        csv_download(selected, f"evaluation-{theme}-{scenario}.csv", "Download this summary")
        runs = RESULTS / "plan-evaluation-runs.csv"
        if runs.is_file():
            solara.FileDownload(
                data=runs.read_bytes, filename=runs.name, label="Download individual runs for all cases",
                mime_type="text/csv",
            )
