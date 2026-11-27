from collections import deque
from math import ceil

import matplotlib.pyplot as plt
import mesa

from crowd_model import (
    CELL_M,
    TICK_SECONDS,
    CrowdModel,
    neighbors,
)
from prepare_map import BASE


ARRIVAL_INTERVAL_SECONDS = 1
DWELL_SECONDS = 60
EVENT_SECONDS = 600
GATHER_DISTANCE_CELLS = 10


def distances_from(cells, start):
    distances = {start: 0}
    queue = deque([start])

    while queue:
        cell = queue.popleft()

        for other in neighbors(cell):
            if other in cells and other not in distances:
                distances[other] = distances[cell] + 1
                queue.append(other)

    if len(distances) != len(cells):
        raise ValueError("The cell grid is disconnected.")

    return distances


class EventCrowdModel(CrowdModel):
    def __init__(
        self,
        num_agents=100,
        rng=42,
        geometry=None,
    ):
        super().__init__(
            num_agents=num_agents,
            rng=rng,
            geometry=geometry,
        )

        self.entrance = min(
            self.cells, key=lambda c: (c[1], c[0])
        )
        self.exit = max(
            self.cells, key=lambda c: (c[1], c[0])
        )

        entry_distances = distances_from(
            self.cells, self.entrance
        )
        self.exit_distances = distances_from(
            self.cells, self.exit
        )

        self.entrance_zone = set(sorted(
            self.cells,
            key=lambda c: (
                entry_distances[c], c[1], c[0]
            ),
        )[:num_agents])

        self.gather_zone = {
            cell
            for cell, distance in self.distances.items()
            if distance <= GATHER_DISTANCE_CELLS
        }

        if num_agents > len(self.gather_zone):
            raise ValueError(
                "More people than assumed gathering-zone cells."
            )

        targets = self.random.sample(
            sorted(self.gather_zone), num_agents
        )
        self.target_distances = {
            target: distances_from(
                self.gather_zone, target
            )
            for target in targets
        }

        self.dwell_ticks = ceil(
            DWELL_SECONDS / TICK_SECONDS
        )
        self.event_ticks = ceil(
            EVENT_SECONDS / TICK_SECONDS
        )

        for index, (person, target) in enumerate(
            zip(self.people, targets)
        ):
            person.cell = None
            person.phase = "scheduled"
            person.arrival_tick = ceil(
                (index + 1)
                * ARRIVAL_INTERVAL_SECONDS
                / TICK_SECONDS
            )
            person.target = target
            person.gather_until_tick = None

        self.peak_density = 0.0

        self.datacollector = mesa.DataCollector({
            "seconds": lambda m: (
                m.steps * TICK_SECONDS
            ),
            "planned": lambda m: len(m.people),
            "scheduled": lambda m: m.count("scheduled"),
            "inside": lambda m: m.inside_count(),
            "entrance_zone": lambda m: sum(
                p.cell in m.entrance_zone
                for p in m.people
                if p.cell is not None
            ),
            "walking": lambda m: m.count("walking"),
            "gathering": lambda m: m.count("gathering"),
            "leaving": lambda m: m.count("leaving"),
            "departed": lambda m: m.count("departed"),
            "mean_density_persons_m2": lambda m: (
                m.inside_count()
                / (len(m.cells) * CELL_M**2)
            ),
            "local_peak_persons_m2": (
                lambda m: m.local_peak_density()
            ),
            "peak_so_far_persons_m2": "peak_density",
        })
        self.datacollector.collect(self)

    def count(self, phase):
        return sum(
            person.phase == phase
            for person in self.people
        )

    def inside_count(self):
        return sum(
            person.cell is not None
            for person in self.people
        )

    def step(self):
        tick = self.steps
        occupied = {
            p.cell
            for p in self.people
            if p.cell is not None
        }
        free_holding = sorted(
            self.entrance_zone - occupied
        )

        for person in self.people:
            if (
                person.phase == "scheduled"
                and person.arrival_tick <= tick
            ):
                assert free_holding, (
                    "A due arrival must have a physical holding cell."
                )
                person.cell = free_holding.pop(0)
                person.phase = "walking"
                occupied.add(person.cell)

        for person in self.people:
            if (
                person.phase == "gathering"
                and tick >= person.gather_until_tick
            ):
                person.phase = "leaving"

        moving = [
            p for p in self.people
            if p.cell is not None
        ]
        self.random.shuffle(moving)

        for person in moving:
            current = person.cell

            if person.phase == "walking":
                distances = (
                    self.target_distances[person.target]
                    if current in self.gather_zone
                    else self.distances
                )
            elif person.phase == "leaving":
                distances = self.exit_distances
            else:
                continue

            options = [
                cell
                for cell in neighbors(current)
                if cell in distances
                and cell not in occupied
                and distances[cell] < distances[current]
            ]

            if options:
                destination = self.random.choice(options)
                occupied.remove(current)
                occupied.add(destination)
                person.cell = destination

            if (
                person.phase == "walking"
                and person.cell == person.target
            ):
                person.phase = "gathering"
                person.gather_until_tick = (
                    tick + self.dwell_ticks
                )

        at_exit = [
            p for p in moving
            if p.phase == "leaving"
            and p.cell == self.exit
        ]

        if at_exit:
            at_exit[0].cell = None
            at_exit[0].phase = "departed"

        cells = [
            p.cell for p in self.people
            if p.cell is not None
        ]

        assert len(cells) == len(set(cells))
        assert (
            self.count("scheduled")
            + len(cells)
            + self.count("departed")
            == len(self.people)
        )
        assert all(
            (p.cell is None)
            == (p.phase in ("scheduled", "departed"))
            for p in self.people
        )

        self.peak_density = max(
            self.peak_density,
            self.local_peak_density(),
        )
        self.running = self.steps < self.event_ticks
        self.datacollector.collect(self)


def main():
    seed = 42
    model = EventCrowdModel(rng=seed)

    while model.running:
        model.step()

    output = BASE / "results"
    output.mkdir(parents=True, exist_ok=True)

    frame = model.datacollector.get_model_vars_dataframe()
    frame["seed"] = seed
    frame["scenario"] = "synthetic_event_unverified_gates"
    frame.to_csv(
        output / "event-run.csv",
        index_label="tick",
    )

    fig, ax = plt.subplots(figsize=(8, 4))
    frame.plot(
        x="seconds",
        y=["scheduled", "inside", "departed"],
        ax=ax,
    )
    ax.set_xlabel("Simulated seconds")
    ax.set_ylabel("People")
    ax.set_title(
        "Synthetic arrivals and departures — unverified scenario"
    )
    fig.tight_layout()
    fig.savefig(
        output / "event-flow.png", dpi=150
    )
    plt.close(fig)

    last = frame.iloc[-1]
    print(
        f"Simulated seconds: "
        f"{model.steps * TICK_SECONDS:.1f}"
    )

    for label in (
        "planned", "scheduled", "inside", "departed"
    ):
        print(f"{label}: {int(last[label])}")

    print(
        f"Peak fixed-bin density: "
        f"{model.peak_density:.3f} people/m²"
    )
    print("Saved:", output / "event-run.csv")
    print("Saved:", output / "event-flow.png")


if __name__ == "__main__":
    main()
