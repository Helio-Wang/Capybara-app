import datetime
import math
import time
import PyQt5 as qt
from capybara.eucalypt.solution import NestedSolution
from capybara.eucalypt.nexparser import tree_from_newick
from capybara.eucalypt import cyclicity, enumerator
from capybara.equivalence import event_reconciliator, poly_enum_class as cenu, enumerate_classes as cla


class CountThread(qt.QtCore.QThread):
    """
    Thread starts with the Count button event, sends the number of solutions to the interface
    """
    sig = qt.QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.data, self.cost_vector, self.tasks = None, None, None

    def on_source(self, options):
        self.data = options[0]
        self.cost_vector = options[1:5]
        self.tasks = options[5:]

    def print_header(self, task):
        if task == 0:
            self.sig.emit(f'Task {task+1}: Counting the number of solutions (cyclic or acyclic)...')
        elif task == 1:
            self.sig.emit(f'Task {task+1}: Counting the number of solutions grouped by event vectors...')
        elif task == 2:
            self.sig.emit(f'Task {task+1}: Counting the number of event partitions...')
        else:
            self.sig.emit(f'Task {task+1}: Counting the number of CD-equivalence classes...')

    def run(self):
        self.sig.emit('===============')
        self.sig.emit(f'Job started at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        t0 = time.time()
        self.sig.emit(f'Cost vector: {tuple(self.cost_vector)}')
        self.sig.emit('------')
        opt_cost = 0
        for task in self.tasks:
            self.print_header(task)

            opt_cost, root = self.data.count_solutions(self.cost_vector, task)
            if task == 0:
                self.sig.emit(f'Total number of solutions = {root.num_subsolutions}')
            elif task == 1:
                num_class = 0
                num_sol = 0
                for target_vector in root.event_vectors:
                    num_class += 1
                    self.sig.emit(f"{num_class}: {target_vector.vector} of size {target_vector.num_subsolutions}")
                    num_sol += target_vector.num_subsolutions
                self.sig.emit(f'Total number of event vectors = {num_class}')
                self.sig.emit(f'Total number of solutions = {num_sol}')
            elif task == 2:
                self.sig.emit(f'Total number of event partitions = {root.num_subsolutions}')
            else:
                self.sig.emit(f'Total number of CD-equivalence classes = {root.num_subsolutions}')

            self.sig.emit('------')
        self.sig.emit('Optimal cost = {}'.format(opt_cost))
        self.sig.emit('------')
        self.sig.emit(f'Job finished at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.sig.emit(f'Time elapsed: {time.time() - t0:.2f} s')
        self.sig.emit('===============')
        self.sig.emit('')
        self.exit(0)


class EnumerateThread(qt.QtCore.QThread, enumerator.SolutionsEnumerator):
    """
    Thread starts with the Enumerate button event, writes solutions to a file, updates the progress bar
    """
    sig = qt.QtCore.pyqtSignal(str)
    sig2 = qt.QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__(data=None, root=None, writer=None, maximum=None, acyclic=None)
        self.num_solutions, self.num_acyclic = 0, 0
        self.data, self.cost_vector, self.task, self.filename = None, None, None, None
        self.maximum, self.acyclic, self.label_only = None, None, None
        self.writer = None
        self.t0 = 0

    def on_source(self, options):
        self.data = options[0]
        self.cost_vector = options[1:5]
        self.task = options[5]
        self.filename = options[6]
        self.maximum = options[7]
        self.acyclic_only = options[8]
        self.label_only = options[9]
        self.num_acyclic, self.num_solutions = 0, 0
        self.writer = open(self.filename, 'w')

    def print_header(self):
        if self.task == 0:
            self.sig.emit(f'Task {self.task+1}: Enumerate {"acyclic " if self.acyclic_only else ""}solutions'
                          f'{" (cyclic or acyclic)" if not self.acyclic_only else ""}...')
        elif self.task == 1:
            self.sig.emit(f'Task {self.task+1}: Enumerate one solution per event vector...')
        elif self.task == 2:
            self.sig.emit(f'Task {self.task+1}: Enumerate one solution per event partition...')
        else:
            self.sig.emit(f'Task {self.task+1}: Enumerate one solution per CD-equivalence class...')

    def run(self, label=''):
        self.sig.emit('===============')
        self.sig.emit(f'Job started at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.t0 = time.time()
        self.sig.emit(f'Cost vector: {tuple(self.cost_vector)}')
        self.print_header()

        self.sig2.emit(1)
        opt_cost, root = self.data.enumerate_solutions_setup(self.cost_vector, self.task, self.maximum)
        try:
            self.write_header(opt_cost, self.task, self.cost_vector)
            self.sig2.emit(5)
            self.sig.emit('------')
            self.root = root
            if self.task == 0:
                self.loop_enumerate()
            elif self.task == 1:
                self.loop_vector()
            else:
                if self.maximum == float('Inf'):
                    reachable = cla.fill_reachable_matrix(self.data.parasite_tree, self.data.host_tree, root)
                    cla_root = cla.fill_class_matrix(self.data.parasite_tree, self.data.host_tree, self.data.leaf_map,
                                                     reachable, self.task)
                    self.sig2.emit(30)
                    self.loop_classes(cla_root.num_subsolutions)
                else:
                    self.loop_classes()
            self.writer.write('#--------------------\n')
            if self.maximum == float('Inf'):
                if self.task == 0 and self.acyclic_only:
                    self.sig.emit(f'Number of acyclic solutions = {self.num_acyclic} out of {self.num_solutions}')
                    self.writer.write(f'#Number of acyclic solutions = {self.num_acyclic} out of {self.num_solutions}\n')
                else:
                    self.sig.emit(f'Number of solutions = {self.num_acyclic}')
                    self.writer.write(f'#Number of solutions = {self.num_acyclic}\n')
            else:
                self.sig.emit(f'Number of output solutions = {self.num_acyclic} (maximum {self.maximum})')
                self.writer.write(f'#Number of output solutions = {self.num_acyclic} (maximum {self.maximum})\n')
        except ValueError:  # aborted
            return
        self.sig.emit('Optimal cost = {}'.format(opt_cost))
        self.sig.emit('Output written to {}'.format(self.filename))
        self.sig.emit('------')
        self.sig.emit(f'Job finished at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.sig.emit(f'Time elapsed: {time.time() - self.t0:.2f} s')
        self.sig.emit('===============')
        self.sig.emit('')
        self.writer.close()
        self.exit(0)

    def abort(self):
        self.sig.emit('------')
        self.sig.emit(f'Job aborted at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.sig.emit(f'Time elapsed: {time.time() - self.t0:.2f} s')
        self.sig.emit('===============')
        self.sig.emit('')
        self.writer.close()
        self.exit(1)

    def loop_vector(self):
        percentage = 5
        num_class = 0
        for target_vector in self.root.event_vectors:
            self.current_text = []
            self.current_mapping = {}
            num_class += 1
            if num_class >= self.maximum:
                break
            self.visit_vector(self.root, target_vector)
            self.writer.write(', '.join(self.current_text))
            self.writer.write(f'\n[{str(target_vector.vector)}]\n')

            if self.maximum == float('Inf'):
                new_percentage = math.ceil(100 * num_class / len(self.root.event_vectors))
            else:
                new_percentage = math.ceil(100 * num_class / self.maximum)
            if new_percentage > percentage:
                percentage = new_percentage
                self.sig2.emit(int(percentage))
        self.sig2.emit(100)
        self.num_acyclic = num_class

    def loop_enumerate(self):
        percentage = 5
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

            if self.maximum == float('Inf'):
                new_percentage = math.ceil(100 * self.num_acyclic / self.root.num_subsolutions)
            else:
                new_percentage = math.ceil(100 * self.num_acyclic / self.maximum)
            if new_percentage > percentage:
                percentage = new_percentage
                self.sig2.emit(int(percentage))
        self.sig2.emit(100)

    def loop_classes(self, total_classes=0):
        percentage = 30 if self.maximum == float('Inf') else 5
        num_class = 0
        class_enumerator = cenu.ClassEnumerator(self.data.parasite_tree, self.root, self.task)
        for mapping, events in class_enumerator.run():
            num_class += 1
            if self.label_only:
                current_text = []
                for p in self.data.parasite_tree:
                    current_text.append(f'{str(p)}@{"?" if not mapping[p] else str(mapping[p])}|'
                                        f'{"CDS L"[events[p]]}')
                self.writer.write(', '.join(current_text))
                self.writer.write(f'\n[{num_class}]\n')
            else:
                recon_bis = event_reconciliator.EventReconciliator(self.data.host_tree, self.data.parasite_tree,
                                                                   self.data.leaf_map,
                                                                   self.cost_vector[0] * self.data.multiplier,
                                                                   self.cost_vector[1] * self.data.multiplier,
                                                                   self.cost_vector[2] * self.data.multiplier,
                                                                   self.cost_vector[3] * self.data.multiplier,
                                                                   float('Inf'), self.task,
                                                                   mapping, events)
                root_bis = recon_bis.run()
                recon_enumerator = enumerator.SolutionsEnumerator(self.data, root_bis, self.writer, 1, False)
                recon_enumerator.run(label=str(num_class))

            if num_class >= self.maximum:
                break
            if self.maximum == float('Inf'):
                new_percentage = math.ceil(100 * num_class / total_classes)
            else:
                new_percentage = math.ceil(100 * num_class / self.maximum)
            if new_percentage > percentage:
                percentage = new_percentage
                self.sig2.emit(int(percentage))
        self.sig2.emit(100)
        self.num_acyclic = num_class


class BestKEnumerateThread(qt.QtCore.QThread, enumerator.SolutionsEnumerator):
    """
    Enumeration thread for the best-K enumeration
    """
    sig = qt.QtCore.pyqtSignal(str)
    sig2 = qt.QtCore.pyqtSignal(int)

    def __init__(self):
        qt.QtCore.QThread.__init__(self, data=None, root=None, writer=None, maximum=None, acyclic=None)
        self.num_solutions, self.num_acyclic = 0, 0
        self.data, self.cost_vector, self.filename = None, None, None
        self.k, self.acyclic_only = None, None
        self.writer = None
        self.t0 = 0

    def on_source(self, options):
        self.data = options[0]
        self.cost_vector = options[1:5]
        self.filename = options[5]
        self.k = options[6]
        self.acyclic_only = options[7]
        self.num_acyclic, self.num_solutions = 0, 0
        self.writer = open(self.filename, 'w')

    def write_header(self, opt_cost):
        self.writer.write('#--------------------\n')
        self.writer.write('#Host tree          = {}\n'.format(self.data.host_tree))
        self.writer.write('#Symbiont tree      = {}\n'.format(self.data.parasite_tree))
        self.writer.write('#Host tree size     = {}\n'.format(self.data.host_tree.size()))
        self.writer.write('#Symbiont tree size = {}\n'.format(self.data.parasite_tree.size()))
        self.writer.write('#Leaf mapping       = {{{}}}\n'.format(', '.join(map(lambda x: str(x[0]) + '=' + str(x[1]),
                                                                                self.data.leaf_map.items()))))
        self.writer.write('#--------------------\n')
        if self.acyclic_only:
            self.writer.write('#Task: Enumerate acyclic solutions among the best K solutions\n')
        else:
            self.writer.write('#Task: Enumerate the best K solutions\n')
        self.writer.write('#Co-speciation cost = {}\n'.format(self.cost_vector[0]))
        self.writer.write('#Duplication cost   = {}\n'.format(self.cost_vector[1]))
        self.writer.write('#Host-switch cost   = {}\n'.format(self.cost_vector[2]))
        self.writer.write('#Loss cost          = {}\n'.format(self.cost_vector[3]))
        self.writer.write('#K                  = {}\n'.format(self.k))
        self.writer.write('#Optimal cost       = {}\n'.format(opt_cost))
        self.writer.write('#--------------------\n')

    def run(self, label=''):
        self.sig.emit('===============')
        self.sig.emit(f'Job started at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.t0 = time.time()
        self.sig.emit(f'Cost vector: {tuple(self.cost_vector)}')
        self.sig.emit(f'K = {self.k}')
        if self.acyclic_only:
            self.sig.emit('Enumerate acyclic solutions among the best K solutions...')
        else:
            self.sig.emit('Enumerate the best K solutions...')

        self.sig2.emit(1)
        opt_cost, cost_summary, root = self.data.enumerate_best_k(self.cost_vector, self.k)
        try:
            self.write_header(opt_cost)
            self.sig2.emit(5)
            self.sig.emit('------')
            self.root = root
            acyclic_summary = self.loop_enumerate(cost_summary)
            self.writer.write('#--------------------\n')
            self.sig.emit(f'Number of output solutions = {self.num_acyclic}{f" out of {self.num_solutions}" if self.acyclic_only else ""}')
            for cost in sorted(cost_summary.keys()):
                self.writer.write(f'#Number of solutions having cost {cost // self.data.multiplier} = {cost_summary[cost]}'
                                  f'{f" (acyclic = {acyclic_summary[cost]})" if self.acyclic_only else ""}\n')
        except ValueError:
            return
        self.sig.emit('Optimal cost = {}'.format(opt_cost))
        for cost in sorted(cost_summary.keys()):
            self.sig.emit(f'Number of solutions having cost {cost // self.data.multiplier} = {cost_summary[cost]}' 
                          f'{f" (acyclic = {acyclic_summary[cost]})" if self.acyclic_only else ""}')
        self.sig.emit('Output written to {}'.format(self.filename))
        self.sig.emit('------')
        self.sig.emit(f'Job finished at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.sig.emit(f'Time elapsed: {time.time() - self.t0:.2f} s')
        self.sig.emit('===============')
        self.sig.emit('')
        self.writer.close()
        self.exit(0)

    def abort(self):
        self.sig.emit('------')
        self.sig.emit(f'Job aborted at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.sig.emit(f'Time elapsed: {time.time() - self.t0:.2f} s')
        self.sig.emit('===============')
        self.sig.emit('')
        self.writer.close()
        self.exit(1)

    def loop_enumerate(self, cost_summary):
        percentage = 5
        acyclic_summary = {cost: 0 for cost in cost_summary}
        while True:
            self.current_mapping = {}
            self.current_text = []
            self.transfer_candidates = []

            self.num_solutions += 1
            current_cell = self.root
            iterator = enumerator.SolutionIterator(self.root, get_cost=True)
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
                acyclic_summary[iterator.final_cost] += 1
                self.num_acyclic += 1
                self.writer.write(', '.join(self.current_text))
                self.writer.write(f'\n[{self.num_acyclic}, cost = {iterator.final_cost // self.data.multiplier}]\n')

            if not self.merge_stack:
                break
            new_percentage = math.ceil(100 * self.num_acyclic / self.k)
            if new_percentage > percentage:
                percentage = new_percentage
                self.sig2.emit(int(percentage))
        self.sig2.emit(100)
        return acyclic_summary


class DotFileThread(qt.QtCore.QThread):
    """
    Thread starts with the Run button event, sends one or more trees in DOT format
    """
    sig = qt.QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.input_name = None
        self.task = None
        self.cosp_color = '"#fec771"'
        self.dup_color = '"#64e291"'
        self.switch_color = '"#64c4ed"'
        self.leaf_color = '"#fcfafa"'

    def on_source(self, options):
        self.input_name = options[0]
        self.task = options[1]

    def write_plain_tree(self, tree):
        self.sig.emit('digraph {')
        self.sig.emit('node [shape="ellipse"]')
        for node in tree:
            if node.is_root():
                continue
            self.sig.emit(f'"{node.parent.label}" -> "{node.label}"')
        self.sig.emit('};')

    def write_colored_tree(self, parasite_tree, events, hosts):
        self.sig.emit('digraph {')
        self.sig.emit('node [shape="ellipse" style=filled]')
        for p in parasite_tree:
            color = self.cosp_color if events[p.label] == 'C' else \
                    self.dup_color if events[p.label] == 'D' else \
                    self.switch_color if events[p.label] == 'S' else \
                    self.leaf_color
            tooltip = f'"{hosts[p.label]}"'
            self.sig.emit(f'"{p.label}" [fillcolor={color} tooltip={tooltip}]')
        for p in parasite_tree:
            if p.is_root():
                continue
            self.sig.emit(f'"{p.parent.label}" -> "{p.label}"')
        self.sig.emit('};')

    def run(self):
        with open(self.input_name, 'r') as f:
            if self.task == 2:
                parasite_tree = None
                try:
                    line = f.readline()
                except (UnicodeDecodeError, UnboundLocalError):
                    self.sig.emit(f'Error: The file format is not recognized '
                                  f'(Not event partitions or equivalence classes?).')
                    self.sig.emit('')
                    self.exit(0)
                    return
                while line:
                    if not parasite_tree:
                        if 'symbiont tree' in line.lower():
                            nwk = line.rstrip().split('= ')[1]
                            parasite_tree = tree_from_newick(nwk, '!P')
                    if line[0] not in ('#', '['):
                        if not parasite_tree:
                            self.sig.emit(f'Error: The symbiont tree is not found in the file.')
                            break
                        events, hosts = {}, {}
                        try:
                            for u in line.rstrip().split(', '):
                                p, v = u.split('@')
                                h, e = v.split('|')
                                events[p], hosts[p] = e, h
                        except ValueError:
                            self.sig.emit(f'Error: The file format is not recognized '
                                          f'(Not event partitions or equivalence classes?).')
                            break
                        self.write_colored_tree(parasite_tree, events, hosts)
                    try:
                        line = f.readline()
                    except (UnicodeDecodeError, UnboundLocalError):
                        self.sig.emit(f'Error: The file format is not recognized '
                                      f'(Not event partitions or equivalence classes?).')
                        self.sig.emit('')
                        self.exit(0)
                        return
            else:  # host tree or parasite tree
                tree = None
                try:
                    line = f.readline()
                except (UnicodeDecodeError, UnboundLocalError):
                    self.sig.emit(f'Error: The file format is not recognized ')
                    self.sig.emit('')
                    self.exit(0)
                    return
                while line:
                    if (self.task == 0 and 'host tree' in line.lower()) or 'symbiont tree' in line.lower():
                        nwk = line.rstrip().split('= ')[1]
                        tree = tree_from_newick(nwk, '!H' if self.task == 0 else '!P')
                        break
                    try:
                        line = f.readline()
                    except (UnicodeDecodeError, UnboundLocalError):
                        self.sig.emit(f'Error: The file format is not recognized ')
                        self.sig.emit('')
                        self.exit(0)
                        return
                if tree:
                    self.write_plain_tree(tree)
                else:
                    self.sig.emit(f'The {"host" if self.task == 0 else "symbiont"} tree is not found in the file.')
        self.sig.emit('')
        self.exit(0)

