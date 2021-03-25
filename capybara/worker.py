import os
import signal
import sys
import logging
import logging.handlers
import uuid
from capybara.eucalypt import nexparser, enumerator, cyclicity
from capybara.interface import DataInterface
from capybara.equivalence import poly_enum_class as cenu
from capybara.equivalence import analyze_one_equivalence as inv


logger = logging.getLogger('capybara')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
flog = logging.handlers.TimedRotatingFileHandler('capybara.log', when='d', interval=2)
flog.setFormatter(formatter)
flog.setLevel(logging.DEBUG)
slog = logging.StreamHandler()
slog.setFormatter(formatter)
slog.setLevel(logging.WARNING)
logger.addHandler(flog)
logger.addHandler(slog)
logger.setLevel(logging.DEBUG)


def signal_handler(sig, frame):
    logger.warning('Keyboard interrupt')
    logger.info('===== Job aborted! =====')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


class Worker:
    """
    Worker class for using Capybara as a package
    """
    def __init__(self, input_name, task, cost_vector, verbose):
        self.input_name = os.path.abspath(input_name)
        self.task = task
        self.data = None
        self.cost_vector = cost_vector
        self.log = logging.getLogger('capybara')
        self.id = uuid.uuid1().hex
        self.verbose_print = print if verbose else lambda x: None

    def check_options(self):
        if self.task not in (1, 2, 3, 4):
            self.log.error(f'{self.id} The task is not valid.')
            return False
        self.task -= 1
        if len(self.cost_vector) != 4:
            self.log.error(f'{self.id} The cost vector is not valid.')
            return False
        try:
            self.cost_vector = tuple(map(int, self.cost_vector))
        except (ValueError, OverflowError):
            self.log.error(f'{self.id} The cost vector is not valid.')
            return False
        self.log.info(f'{self.id} Input file: {self.input_name}')
        self.log.info(f'{self.id} Cost vector: {self.cost_vector}')
        return True

    def read_data(self):
        self.log.info(f'{self.id} Reading the input file...')
        try:
            with open(self.input_name, 'r') as file:
                parser = nexparser.NexusParser(file)
                parser.read()
                host_tree = parser.host_tree
                parasite_tree = parser.parasite_tree
                leaf_map = parser.leaf_map
        except nexparser.NexusFileParserException as e:
            self.log.error(f'{self.id} {e.message}')
            return False
        except NotImplementedError:
            self.log.error(f'{self.id} The file format is not supported.')
            return False
        except FileNotFoundError:
            self.log.error(f'{self.id} File not found.')
            return False

        self.data = DataInterface(parasite_tree, host_tree, leaf_map)
        self.log.info(f'{self.id} Successful! Computing...')
        return True

    def start(self):
        self.verbose_print(f'{self.id} Job started!')
        self.log.info(f'{self.id} ===== Job started! =====')

    def abort(self):
        print('Error! Check the file capybara.log for more details.')
        self.log.info(f'{self.id} ===== Job aborted! =====')

    def finish(self):
        self.log.info(f'{self.id} ===== Job finished successfully! =====')


class Counter(Worker):
    """
    Compute the number of solutions or classes
    """
    def __init__(self, input_name, task, cost_vector, verbose):
        super().__init__(input_name, task, cost_vector, verbose)

    def run(self):
        self.start()
        self.log.info(f'{self.id} Running Capybara Counter Task {self.task}')
        if not self.check_options() or not self.read_data():
            self.abort()
            return
        opt_cost, root = self.data.count_solutions(self.cost_vector, self.task, cli=True)
        if self.task == 1:
            answer = len(root.event_vectors)
        else:
            answer = root.num_subsolutions
        self.log.info(f'{self.id} Done! The result of Counter Task {self.task+1} is {answer}')
        self.verbose_print(f'{self.id} Job done! The answer is {answer}')
        self.finish()
        return answer


class Enumerator(Worker, enumerator.SolutionsEnumerator):
    """
    Enumerate solutions or classes to a file
    """
    def __init__(self, input_name, output_name, task, cost_vector, verbose,
                 maximum, acyclic_only):
        Worker.__init__(self, input_name, task, cost_vector, verbose)
        enumerator.SolutionsEnumerator.__init__(self, data=None, root=None,
                                                writer=None, maximum=maximum, acyclic=acyclic_only)
        self.output_name = output_name
        self.num_solutions = 0
        self.num_acyclic = 0

    def check_options(self):
        # check input and cost vector
        if not super().check_options():
            return False
        # check output
        try:
            self.writer = open(self.output_name, 'w')
        except PermissionError:
            self.log.error(f'{self.id} Permission denied.')
            return False
        self.log.info(f'{self.id} Output file: {os.path.abspath(self.output_name)}')
        # check maximum and acyclic
        if self.maximum != float('Inf'):
            try:
                self.maximum = int(self.maximum)
            except ValueError:
                self.log.error(f'{self.id} The maximum is not valid.')
                return False
            if self.maximum <= 0:
                self.log.error(f'{self.id} The maximum is not valid.')
                return False
        if self.task == 0 and self.acyclic_only not in (True, False):
            self.log.error(f'{self.id} Acyclic should be either True or False.')
            return False
        return True

    def abort(self):
        super().abort()
        self.writer.close()

    def finish(self):
        super().finish()
        self.writer.close()

    def run(self, label=''):
        self.start()
        self.log.info(f'{self.id} Running Capybara Enumerator Task {self.task}')
        if not self.check_options() or not self.read_data():
            self.abort()
            return
        opt_cost, root = self.data.enumerate_solutions_setup(self.cost_vector, self.task, self.maximum)
        try:
            self.write_header(opt_cost, self.task, self.cost_vector)
            self.root = root
            if self.task == 0:
                self.loop_enumerate()
            elif self.task == 1:
                self.loop_vector()
            else:
                self.loop_classes()
            self.writer.write('#--------------------\n')
            if self.maximum == float('Inf'):
                if self.task == 0 and self.acyclic_only:
                    self.log.info(f'{self.id} Number of acyclic solutions = {self.num_acyclic} out of {self.num_solutions}')
                    self.writer.write(f'#Number of acyclic solutions = {self.num_acyclic} out of {self.num_solutions}\n')
                else:
                    self.log.info(f'{self.id} Number of solutions = {self.num_acyclic}')
                    self.writer.write(f'#Number of solutions = {self.num_acyclic}\n')
            else:
                self.log.info(f'{self.id} Number of output solutions = {self.num_acyclic} (maximum {self.maximum})')
                self.writer.write(f'#Number of output solutions = {self.num_acyclic} (maximum {self.maximum})\n')
        except ValueError:  # aborted
            return
        self.verbose_print(f'{self.id} Job done! {self.num_acyclic} solutions written to {self.output_name}')
        self.log.info(f'{self.id} Done! {self.num_acyclic} solutions written to {self.output_name}')
        self.finish()

    def write_task_title(self, task):
        if task == 0:
            self.writer.write(f'#Task {task+1}: Enumerate {"acyclic " if self.acyclic_only else ""}solutions '
                              f'{"(cyclic or acyclic)" if not self.acyclic_only else ""}\n')
        elif task == 1:
            self.writer.write(f'#Task {task+1}: Enumerate event vectors\n')
        elif task == 2:
            self.writer.write(f'#Task {task+1}: Enumerate event partitions\n')
        else:
            self.writer.write(f'#Task {task+1}: Enumerate strong equivalence classes\n')

    def loop_vector(self):
        num_class = 0
        for target_vector in self.root.event_vectors:
            num_class += 1
            if num_class >= self.maximum:
                break
            self.writer.write(f'{str(target_vector.vector)}\n')
        self.num_acyclic = num_class

    def loop_enumerate(self):
        while True:
            self.current_mapping = {}
            self.current_text = []
            self.transfer_candidates = []

            self.num_solutions += 1
            current_cell = self.root
            iterator = enumerator.SolutionIterator(self.root)
            while not iterator.done():
                current_cell = self.get_next(current_cell, iterator)
            self.clean_stack()

            is_acyclic = False
            if self.acyclic_only:
                transfer_edges = cyclicity.find_transfer_edges(self.data.host_tree,
                                                               self.current_mapping, self.transfer_candidates)
                if not transfer_edges:
                    is_acyclic = True
                else:
                    is_acyclic = cyclicity.is_acyclic_stolzer(self.current_mapping, transfer_edges)

            if not self.acyclic_only or is_acyclic:
                self.num_acyclic += 1
                self.writer.write(', '.join(self.current_text))
                self.writer.write(f'\n[{self.num_acyclic}]\n')

            if not self.merge_stack:
                break
            if self.num_acyclic >= self.maximum:
                break

    def loop_classes(self):
        num_class = 0
        class_enumerator = cenu.ClassEnumerator(self.data.parasite_tree, self.root, self.task)
        for mapping, events in class_enumerator.run():
            num_class += 1
            current_text = []
            for p in self.data.parasite_tree:
                current_text.append(f'{str(p)}@{"?" if not mapping[p] else str(mapping[p])}|'
                                    f'{"CDS L"[events[p]]}')
            self.writer.write(', '.join(current_text))
            self.writer.write(f'\n[{num_class}]\n')

            if num_class >= self.maximum:
                break
        self.num_acyclic = num_class


class EventVectorWrapper:
    """
    A wrapper for the event vector that supports the analyses on the corresponding class
    """
    def __init__(self, vector, data, root):
        self.vector = vector
        self.enumerator = inv.VectorEnumerator(self.vector, data, root)

    def __str__(self):
        return str(self.vector)

    def get_size(self):
        return self.enumerator.get_size()

    def print_one_representative(self):
        print(self.enumerator.get_one_representative())


class EquivalenceClassWrapper:
    """
    A wrapper for the event partition or CD-equivalence class that supports the analyses
    """
    def __init__(self, mapping, events, task, data, root, cost_vector):
        self.mapping = mapping
        self.events = events
        self.data = data
        self.enumerator = inv.EventEnumerator(mapping, events, task, data, root, cost_vector)

    def __str__(self):
        text = []
        for p in self.data.parasite_tree:
            text.append(f'{str(p)}@{"?" if not self.mapping[p] else str(self.mapping[p])}|'
                        f'{"CDS L"[self.events[p]]}')
        return ', '.join(text)

    def get_size(self):
        return self.enumerator.get_size()

    def print_one_representative(self):
        print(self.enumerator.get_one_representative())


class Generator(Worker):
    """
    Generate the equivalence classes one by one
    """
    def __init__(self, input_name, task, cost_vector, verbose):
        super().__init__(input_name, task, cost_vector, verbose)

    def check_options(self):
        # check input and cost vector
        if not super().check_options():
            return False
        # disable task 0
        if self.task == 0:
            self.log.error(f'{self.id} Cannot run the generator with task 1.')
            return False
        return True

    def run(self):
        self.start()
        self.log.info(f'{self.id} Running Capybara Generator Task {self.task}')
        if not self.check_options() or not self.read_data():
            self.abort()
            return
        opt_cost, root = self.data.enumerate_solutions_setup(self.cost_vector, self.task, float('Inf'), True)
        num_classes = 0
        if self.task == 1:
            for vector in root.event_vectors:
                num_classes += 1
                yield EventVectorWrapper(vector, self.data, root)
        else:
            class_enumerator = cenu.ClassEnumerator(self.data.parasite_tree, root, self.task)
            for mapping, events in class_enumerator.run():
                num_classes += 1
                yield EquivalenceClassWrapper(mapping, events, self.task, self.data, root, self.cost_vector)
        self.log.info(f'{self.id} Done! {num_classes} solutions generated')
        self.finish()

