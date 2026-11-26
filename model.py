import mesa
import networkx as nx


class Person(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        self.state = "Unaware"


class NarrativeModel(mesa.Model):
    def __init__(
        self,
        num_agents=100,
        spread_prob=0.1,
        correction_prob=0.02,
        rng=42,
    ):
        super().__init__(rng=rng)

        if num_agents < 6:
            raise ValueError("Use at least 6 agents.")
        if not 0 <= spread_prob <= 1 or not 0 <= correction_prob <= 1:
            raise ValueError("Probabilities must be between 0 and 1.")

        self.spread_prob = spread_prob
        self.correction_prob = correction_prob
        self.exposure_hours = 0.0
        self.people = [Person(self) for _ in range(num_agents)]
        self.graph = nx.watts_strogatz_graph(
            num_agents, 4, 0.1, seed=self.random
        )

        for person in self.random.sample(self.people, 3):
            person.state = "Exposed"

        self.datacollector = mesa.DataCollector({
            "Unaware": lambda m: m.count("Unaware"),
            "Exposed": lambda m: m.count("Exposed"),
            "Corrected": lambda m: m.count("Corrected"),
            "Exposure-hours": "exposure_hours",
        })
        self.datacollector.collect(self)

    def count(self, state):
        return sum(person.state == state for person in self.people)

    def step(self): 
        previous = [person.state for person in self.people]
        self.exposure_hours += previous.count("Exposed") / 60

        for node, person in enumerate(self.people):
            if previous[node] == "Unaware":
                contacts = sum(
                    previous[neighbor] == "Exposed"
                    for neighbor in self.graph.neighbors(node)
                )
                probability = 1 - (1 - self.spread_prob) ** contacts

                if self.random.random() < probability:
                    person.state = "Exposed"

            elif previous[node] == "Exposed":
                if self.random.random() < self.correction_prob:
                    person.state = "Corrected"

        self.running = self.steps < 120
        self.datacollector.collect(self)


if __name__ == "__main__":
    model = NarrativeModel(spread_prob=0, correction_prob=0)

    for _ in range(60):
        model.step()

    assert model.count("Exposed") == 3
    assert abs(model.exposure_hours - 3.0) < 1e-9
    assert sum(
        model.count(state)
        for state in ("Unaware", "Exposed", "Corrected")
    ) == 100

    print("Checks passed: 3 exposed people × 1 hour = 3 person-hours.")
