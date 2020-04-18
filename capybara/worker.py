import signal
import sys
import logging
import logging.handlers
from capybara.eucalypt import nexparser, enumerator, cyclicity
from capybara.interface import DataInterface
from capybara.equivalence import poly_enum_class as cenu


logger = logging.getLogger('capybara')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
flog = logging.handlers.TimedRotatingFileHandler('capybara.log')
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
        self.input_name = input_name
        self.task = task-1
        self.data = None
        self.cost_vector = cost_vector
        self.log = logging.getLogger('capybara')
        self.verbose_print = print if verbose else lambda x: None

    def check_options(self):
        if self.task not in (0, 1, 2, 3):
            self.log.error('The task is not valid.')
            return False
        if len(self.cost_vector) != 4:
            self.log.error('The cost vector is not valid.')
            return False
        try:
            self.cost_vector = tuple(map(int, self.cost_vector))
        except (ValueError, OverflowError):
            self.log.error('The cost vector is not valid.')
            return False
        self.log.info(f'Input file: {self.input_name}')
        self.log.info(f'Cost vector: {self.cost_vector}')
        return True

    def read_data(self):
        self.log.info(f'Reading the input file...')
        try:
            with open(self.input_name, 'r') as file:
                parser = nexparser.NexusParser(file)
                parser.read()
                host_tree = parser.host_tree
                parasite_tree = parser.parasite_tree
                leaf_map = parser.leaf_map
        except nexparser.NexusFileParserException as e:
            self.log.error(e.message)
            return False
        except NotImplementedError:
            self.log.error('The file format is not supported.')
            return False
        except FileNotFoundError:
            self.log.error('File not found.')
            return False

        self.data = DataInterface(parasite_tree, host_tree, leaf_map)
        self.log.info('Successful! Computing...')
        return True

    def start(self):
        self.verbose_print("Job started!")
        self.log.info('===== Job started! =====')

    def abort(self):
        print('Error! Check the file capybara.log for more details.')
        self.log.info('===== Job aborted! =====')

    def finish(self):
        self.log.info('Computation done!')
        self.log.info('===== Job finished successfully! =====')


class Counter(Worker):
    """
    Counter simply the number of solutions or classes
    """
    def __init__(self, input_name, task, cost_vector, verbose):
        super().__init__(input_name, task, cost_vector, verbose)

    def run(self):
        self.start()
        self.log.info(f'Running Capybara Counter Task {self.task+1}')
        if not self.check_options() or not self.read_data():
            self.abort()
            return
        opt_cost, root = self.data.count_solutions(self.cost_vector, self.task, cli=True)
        if self.task == 1:
            answer = len(root.event_vectors)
        else:
            answer = root.num_subsolutions
        self.log.info(f'The result of Counter task {self.task+1} is {answer}')
        self.verbose_print(f'Job done! The answer is {answer}')
        self.finish()
        return answer


class Enumerator(Worker, enumerator.SolutionsEnumerator):
    def __init__(self, input_name, output_name, task, cost_vector, verbose,
                 maximum, acyclic_only):
        Worker.__init__(self, input_name, task, cost_vector, verbose)
        enumerator.SolutionsEnumerator.__init__(self, data=None, root=None,
                                                writer=None, maximum=maximum, acyclic=acyclic_only)
        self.output_name = output_name
        self.num_solutions = 0
        self.num_acyclic = 0

    def check_options(self):
        try:
            self.writer = open(self.output_name, 'w')
        except PermissionError:
            self.log.error('Permission denied.')
            return False
        if not super().check_options():
            return False
        if self.maximum != float('Inf'):
            try:
                self.maximum = int(self.maximum)
            except ValueError:
                self.log.error('The maximum is not valid.')
                return False
            if self.maximum <= 0:
                self.log.error('The maximum is not valid.')
                return False
        if self.task == 0 and self.acyclic_only not in (True, False):
            self.log.error('Acyclic should be either True or False.')
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
        self.log.info(f'Running Capybara Enumerator Task {self.task+1}')
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
                    self.log.info(f'Number of acyclic solutions = {self.num_acyclic} out of {self.num_solutions}')
                    self.writer.write(f'#Number of acyclic solutions = {self.num_acyclic} out of {self.num_solutions}\n')
                else:
                    self.log.info(f'Number of solutions = {self.num_acyclic}')
                    self.writer.write(f'#Number of solutions = {self.num_acyclic}\n')
            else:
                self.log.info(f'Number of output solutions = {self.num_acyclic} (maximum {self.maximum})')
                self.writer.write(f'#Number of output solutions = {self.num_acyclic} (maximum {self.maximum})\n')
        except ValueError:  # aborted
            return
        self.verbose_print(f'Job done! {self.num_acyclic} solutions written to {self.output_name}')
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

