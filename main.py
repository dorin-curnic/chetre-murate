import solara
from mesa.visualization import Slider, SolaraViz, make_plot_component

from model import NarrativeModel


SEED = 42


def results_csv(model):
    frame = (
        model.datacollector.get_model_vars_dataframe()
        .rename_axis("minute")
        .reset_index()
    )

    frame["seed"] = SEED
    frame["population"] = len(model.people)
    frame["sharing_probability"] = model.spread_prob
    frame["correction_probability"] = model.correction_prob

    return frame.to_csv(index=False)


def show_results(model):
    return solara.Markdown(
        f"**Simulated minutes:** {model.steps} / 120\n\n"
        f"**Population:** {len(model.people)} · "
        f"**Unaware:** {model.count('Unaware')} · "
        f"**Exposed:** {model.count('Exposed')} · "
        f"**Corrected:** {model.count('Corrected')}\n\n"
        f"**Exposure-hours:** {model.exposure_hours:.3f} person-hours\n\n"
        "Exposure-hours accumulate time in the model's active Exposed state. "
        "All exposed agents share; correction is permanent. "
        "These are synthetic assumptions."
    )


def download_results(model):
    return solara.FileDownload(
        data=lambda: results_csv(model),
        filename="narrative-run.csv",
        label="Download this run as CSV",
        mime_type="text/csv",
    )


Page = SolaraViz(
    NarrativeModel(rng=SEED),
    components=[
        show_results,
        download_results,
        make_plot_component({
            "Unaware": "gray",
            "Exposed": "orange",
            "Corrected": "green",
        }),
        make_plot_component("Exposure-hours"),
    ],
    model_params={
        "rng": SEED,
        "num_agents": 100,
        "spread_prob": Slider(
            "Sharing probability per contact/minute",
            0.1, 0.0, 1.0, 0.01,
        ),
        "correction_prob": Slider(
            "Correction probability per minute",
            0.02, 0.0, 1.0, 0.01,
        ),
    },
    name="Comrat Square: synthetic information diffusion",
)
