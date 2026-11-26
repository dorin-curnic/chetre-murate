# Chetre Murate

An offline hackathon demo for the Comrat Square challenge. It couples a synthetic narrative-diffusion model to pedestrian arrivals and compares civilian assistance packages under a five-unit budget.

## Run the demo

From this directory, install the locked dependencies, generate the multi-seed results, and start Solara.

```fish
uv sync --locked
uv run --no-sync python -B evaluate_plans.py
uv run --no-sync solara run main.py --host 127.0.0.1 --port 8767
```

Open [the dashboard](http://127.0.0.1:8767/). Once the environment is installed, the simulations use the committed theme cache and run offline.

- **Narrative simulation** shows 120 minutes of diffusion. Change the sharing or correction slider, press Reset, then Step or Play. Download the minute-by-minute CSV before leaving this view. Opening it again starts a fresh narrative run.
- **Response planner** runs a ten-minute coupled scenario. Choose a theme, coupling strength and seed to compare packages and download their full metrics. The planner uses the diffusion model's default probabilities.
- **Multi-seed evaluation** reads the CSVs written by the evaluator in `results/`. Choose a theme and coupling strength to see mean changes relative to matched baselines across five seeds. The summary download includes the smallest and largest observed changes. The individual-runs download includes every case.

## Assumptions

The coupled planner uses a fictional 40 × 40 m square. A separate OSM prototype uses an unverified candidate boundary in Comrat. Its gates, road availability and movement rules require review before interpreting site-specific results.

GDELT tags select where initial exposure starts in a synthetic network. The committed cache records the global archive, checksum and matching-record counts. News tags provide no evidence of truth, local belief or attendance. The effects of communication, the demand for assistance and the link from exposure to attendance are hypothetical.

Peak density uses fixed 5 × 5 m bins. Exposure is person-hours in the active Exposed state. Unfinished journeys include everyone still travelling or inside at the cutoff. First-aid contacts measure access to assistance. The dashboard reports each outcome separately while the challenge scoring formula and medical requirements are open.
