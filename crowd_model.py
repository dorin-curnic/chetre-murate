from collections import Counter, deque
from math import ceil, floor

import geopandas as gpd
import matplotlib.pyplot as plt
import mesa
from shapely.geometry import box
from shapely.prepared import prep

from prepare_map import BASE


CELL_M = 0.5
TICK_SECONDS = 0.5
MAX_TICKS = 600
BIN_M = 5.0


def neighbors(cell):
    x, y = cell
    return (
        (x - 1, y),
        (x + 1, y),
        (x, y - 1),
        (x, y + 1),
    )


class Pedestrian(mesa.Agent):
    def __init__(self, model, cell):
        super().__init__(model)
        self.cell = cell


class CrowdModel(mesa.Model):
    def __init__(self, num_agents=100, rng=42, geometry=None):
        super().__init__(rng=rng)

        if not isinstance(num_agents, int) or num_agents < 1:
            raise ValueError(
                "num_agents must be a positive integer."
            )

        if geometry is None:
            path = (
                BASE / "data" / "processed"
                / "candidate-square.geojson"
            )
            frame = gpd.read_file(path)

            if len(frame) != 1 or frame.crs is None:
                raise ValueError(
                    "Expected one candidate polygon with a CRS."
                )

            geometry = frame.to_crs(
                "EPSG:32635"
            ).geometry.iloc[0]

        if (
            geometry.is_empty
            or not geometry.is_valid
            or geometry.geom_type != "Polygon"
        ):
            raise ValueError(
                "Expected one non-empty valid Polygon."
            )

        self.geometry = geometry
        self.cells = set()
        covered = prep(geometry)
        left, bottom, right, top = geometry.bounds

        for x in range(
            floor(left / CELL_M),
            ceil(right / CELL_M),
        ):
            for y in range(
                floor(bottom / CELL_M),
                ceil(top / CELL_M),
            ):
                cell_shape = box(
                    x * CELL_M,
                    y * CELL_M,
                    (x + 1) * CELL_M,
                    (y + 1) * CELL_M,
                )

                if covered.covers(cell_shape):
                    self.cells.add((x, y))

        if not self.cells:
            raise ValueError("No fully covered grid cells.")

        if num_agents > len(self.cells):
            raise ValueError(
                "More people than available cells."
            )

        point = geometry.representative_point()

        self.goal = min(
            sorted(self.cells),
            key=lambda c: (
                ((c[0] + 0.5) * CELL_M - point.x) ** 2
                + ((c[1] + 0.5) * CELL_M - point.y) ** 2
            ),
        )

        self.distances = {self.goal: 0}
        queue = deque([self.goal])

        while queue:
            cell = queue.popleft()

            for other in neighbors(cell):
                if (
                    other in self.cells
                    and other not in self.distances
                ):
                    self.distances[other] = (
                        self.distances[cell] + 1
                    )
                    queue.append(other)

        if len(self.distances) != len(self.cells):
            raise ValueError(
                "The grid is disconnected; review the boundary."
            )

        self.people = [
            Pedestrian(self, cell)
            for cell in self.random.sample(
                sorted(self.cells), num_agents
            )
        ]

        self.peak_density = self.local_peak_density()

        self.datacollector = mesa.DataCollector({
            "seconds": lambda m: m.steps * TICK_SECONDS,
            "people": lambda m: len(m.people),
            "mean_density_persons_m2": lambda m: (
                len(m.people)
                / (len(m.cells) * CELL_M**2)
            ),
            "local_peak_persons_m2": (
                lambda m: m.local_peak_density()
            ),
            "peak_so_far_persons_m2": "peak_density",
        })
        self.datacollector.collect(self)

    def local_peak_density(self):
        counts = Counter(
            (
                floor(
                    (person.cell[0] + 0.5)
                    * CELL_M / BIN_M
                ),
                floor(
                    (person.cell[1] + 0.5)
                    * CELL_M / BIN_M
                ),
            )
            for person in self.people
        )

        # Prototype metric: fixed 5 × 5 m bins, including boundary bins.
        return (
            max(counts.values(), default=0)
            / BIN_M**2
        )

    def step(self):
        self.random.shuffle(self.people)
        occupied = {
            person.cell for person in self.people
        }

        for person in self.people:
            current = person.cell

            options = [
                cell
                for cell in neighbors(current)
                if cell in self.cells
                and cell not in occupied
                and self.distances[cell]
                < self.distances[current]
            ]

            if options:
                destination = self.random.choice(options)
                occupied.remove(current)
                occupied.add(destination)
                person.cell = destination

        self.peak_density = max(
            self.peak_density,
            self.local_peak_density(),
        )
        self.running = self.steps < MAX_TICKS
        self.datacollector.collect(self)


def main():
    seed = 42
    model = CrowdModel(rng=seed)

    while model.running:
        model.step()

    assert len({
        p.cell for p in model.people
    }) == len(model.people)
    assert all(
        p.cell in model.cells for p in model.people
    )

    output = BASE / "results"
    output.mkdir(parents=True, exist_ok=True)

    frame = model.datacollector.get_model_vars_dataframe()
    frame["seed"] = seed
    frame["scenario"] = "unverified_pedestrian_only"
    frame.to_csv(
        output / "crowd-run.csv",
        index_label="tick",
    )

    fig, ax = plt.subplots(figsize=(7, 9))

    gpd.GeoSeries(
        [model.geometry], crs="EPSG:32635"
    ).boundary.plot(
        ax=ax, color="black",
    )

    ax.scatter(
        [
            (p.cell[0] + 0.5) * CELL_M
            for p in model.people
        ],
        [
            (p.cell[1] + 0.5) * CELL_M
            for p in model.people
        ],
        s=10,
        label="Synthetic pedestrians",
    )

    ax.scatter(
        [(model.goal[0] + 0.5) * CELL_M],
        [(model.goal[1] + 0.5) * CELL_M],
        marker="*",
        s=80,
        color="orange",
        label="Assumed target",
    )

    ax.set_aspect("equal")
    ax.ticklabel_format(
        style="plain", useOffset=False
    )
    ax.locator_params(axis="x", nbins=2)
    ax.set_xlabel("Easting (metres)")
    ax.set_ylabel("Northing (metres)")
    ax.set_title(
        "Synthetic crowd — unverified pedestrian-only scenario"
    )
    ax.legend()

    fig.text(
        0.5, 0.025,
        "Road availability and gathering target are assumptions.\n"
        "© OpenStreetMap contributors · ODbL\n"
        "https://www.openstreetmap.org/copyright",
        ha="center",
        fontsize=8,
    )

    fig.tight_layout(rect=(0, 0.10, 1, 1))
    fig.savefig(
        output / "crowd-final.png", dpi=150
    )
    plt.close(fig)

    print(
        f"Simulated seconds: "
        f"{model.steps * TICK_SECONDS:.1f}"
    )
    print(f"People: {len(model.people)}")
    print(
        f"Raster area: "
        f"{len(model.cells) * CELL_M**2:.1f} m²"
    )
    print(
        f"Peak fixed-bin density: "
        f"{model.peak_density:.3f} people/m²"
    )
    print("Saved:", output / "crowd-run.csv")
    print("Saved:", output / "crowd-final.png")


if __name__ == "__main__":
    main()
