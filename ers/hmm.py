"""Forward filtering of historical traffic observations for each directed road."""


TRAFFIC_LEVELS = ("Low", "Medium", "High")


def predict_traffic(belief: dict[str, float], tables: dict) -> dict[str, float]:
    """Predict one HMM sequence step; this step has no chosen duration in seconds."""
    predicted = {}
    for next_level in TRAFFIC_LEVELS:
        predicted[next_level] = 0.0
        for previous_level in TRAFFIC_LEVELS:
            transition = tables["transition"][previous_level][next_level]
            predicted[next_level] += belief[previous_level] * transition
    return predicted


def forward_filter(observations: list[str], tables: dict) -> dict[str, float]:
    """Return traffic probabilities after the final observation in an ordered history.

    The supplied initial distribution is the prior for the first hidden state.
    Apply its first emission directly; transition before each later observation.
    An empty sequence returns a copy of that prior. The planning initialization
    function separately maps historical beliefs and priors to simulation time zero.
    """
    belief = dict(tables["initial"])
    for index, observation in enumerate(observations):
        if observation not in TRAFFIC_LEVELS:
            raise ValueError(f"Unknown traffic observation: {observation}")
        if index > 0:
            belief = predict_traffic(belief, tables)

        weights = {}
        for level in TRAFFIC_LEVELS:
            likelihood = tables["emission"][level][observation]
            weights[level] = belief[level] * likelihood

        normalizer = sum(weights.values())
        if normalizer <= 0:
            raise ValueError("Traffic observation has zero probability under the model.")
        belief = {}
        for level in TRAFFIC_LEVELS:
            belief[level] = weights[level] / normalizer
    return belief


def infer_historical_traffic(city_graph: dict, observations: list[dict], tables: dict) -> dict:
    """Filter each observed directed road, ordered by its observation numbers.

    Observation numbers order a historical sequence; they are not simulation
    timestamps. Only observed roads receive a belief here. No road's observations
    are copied to its reverse direction or to an unobserved road.
    """
    road_keys = set()
    for road in city_graph["roads"]:
        road_keys.add((road["from"], road["to"]))

    sequences = {}
    for observation in observations:
        road = (observation["from"], observation["to"])
        if road not in road_keys:
            raise ValueError(f"Traffic observation refers to an unknown road: {road}")
        number = int(observation["observation_nr"])
        if number < 1:
            raise ValueError("Traffic observation numbers must be positive.")
        if road not in sequences:
            sequences[road] = []
        sequences[road].append((number, observation["traffic_observation"]))

    beliefs = {}
    for road, sequence in sequences.items():
        sequence.sort()
        ordered_observations = []
        previous_number = None
        for number, level in sequence:
            if number == previous_number:
                raise ValueError(f"Duplicate traffic observation number on road {road}.")
            ordered_observations.append(level)
            previous_number = number
        beliefs[road] = forward_filter(ordered_observations, tables)
    return beliefs


def initialize_traffic_beliefs(city_graph: dict, historical_beliefs: dict, tables: dict) -> dict:
    """Initialize the approved fixed traffic model for all directed roads.

    Use the final filtered belief directly at simulation time zero. Roads without
    history use the supplied initial distribution. No additional HMM prediction
    is performed. The selected simulation policy reuses these beliefs unchanged.
    """
    beliefs = {}
    for road in city_graph["roads"]:
        key = (road["from"], road["to"])
        if key in historical_beliefs:
            belief = historical_beliefs[key]
        else:
            belief = tables["initial"]
        beliefs[key] = dict(belief)
    return beliefs
