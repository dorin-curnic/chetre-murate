# Chetre Murate

Comrat Square hackathon workspace for a coupled information-diffusion and pedestrian-safety simulation.

## First run

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run these commands from the repository directory in fish or another shell:

```sh
uv sync --locked
uv run solara run main.py --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765 in your browser. Press Step or Play to advance the model. Stop the server with Ctrl+C. If that port is occupied, use `--port 8766`.

`main.py` exposes the installed Mesa Virus on a Network example as Solara's `Page`. The example provides the first working network simulation, controls, and charts. Its original disease-state labels remain visible.

This starter does not yet implement GDELT ingestion, the OSM square, pedestrian movement, a response planner, or the hackathon metrics. It is not a validated model of real-world unrest or attendance.

## Next steps

1. Define the evaluation inputs, budget, and exact metric definitions.
2. Build an anonymous information model with explicit exposure, belief, and sharing states.
3. Verify and cache the square's OSM geometry, including entrance queues.
4. Add hypothetical attendance coupling and test zero, weak, and strong effects.
5. Compare civilian-safety responses across held-out scenarios and random seeds.

Keep credentials and raw restricted datasets out of Git. Model public factual communications, voluntary transport support, and medical assistance; do not model force against civilians.

## Dependencies

Python 3.12 is selected in `.python-version`. Dependencies and their exact resolved versions are recorded in `pyproject.toml` and `uv.lock`. The starter reuses the example included with the locked Mesa version.

The example implementation belongs to the [Mesa project](https://github.com/mesa/mesa), distributed under Apache-2.0; this repository imports it from the installed dependency.
