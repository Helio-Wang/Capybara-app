import os
from capybara.worker import Enumerator


def run(input_name, output_name, task, cost_vector=(-1, 1, 1, 1),
        verbose=False, maximum=float('Inf'), acyclic_only=False):
    enumerator = Enumerator(os.path.abspath(input_name), output_name, task, cost_vector,
                            verbose, maximum, acyclic_only)
    return enumerator.run()

