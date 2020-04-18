import os
from capybara.worker import Counter


def run(input_name, task, cost_vector=(-1, 1, 1, 1), verbose=False):
    counter = Counter(os.path.abspath(input_name), task, cost_vector, verbose)
    return counter.run()

