from mesa.visualization import Slider, SolaraViz, make_plot_component

from model import NarrativeModel


Page = SolaraViz(
    NarrativeModel(),
    components=[
        make_plot_component({
            "Unaware": "gray",
            "Exposed": "orange",
            "Corrected": "green",
        }),
        make_plot_component("Exposure-hours"),
    ],
    model_params={
        "rng": 42,
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
