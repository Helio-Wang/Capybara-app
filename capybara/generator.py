from capybara.worker import Generator


def run(input_name, task, cost_vector=(-1, 1, 1, 1), verbose=False):
    generator = Generator(input_name, task, cost_vector, verbose)
    return generator.run()
