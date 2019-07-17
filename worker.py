import datetime
import math
import time
import PyQt5 as qt
import PyQt5.QtWidgets as qtw
import reconciliator
import cyclicity
import enumerator
import enumerate_classes as cla


class WorkerData:
    def __init__(self, parasite_tree, host_tree, leaf_map):
        self.parasite_tree = parasite_tree
        self.host_tree = host_tree
        self.leaf_map = leaf_map
        self.multiplier = 1000

    def count_solutions(self, cost_vector, task):
        recon = reconciliator.ReconciliatorCounter(self.host_tree, self.parasite_tree, self.leaf_map,
                                                   cost_vector[0] * self.multiplier, cost_vector[1] * self.multiplier,
                                                   cost_vector[2] * self.multiplier, cost_vector[3] * self.multiplier,
                                                   float('Inf'), task)
        root = recon.run()
        opt_cost = root.cost / self.multiplier

        if task in (2, 3):
            reachable = cla.fill_reachable_matrix(self.parasite_tree, self.host_tree, root)
            root = cla.fill_class_matrix(self.parasite_tree, self.host_tree, self.leaf_map, reachable, task)
        return opt_cost, root

    def enumerate_solutions_setup(self, cost_vector, task, maximum):
        recon = reconciliator.Reconciliator(self.host_tree, self.parasite_tree, self.leaf_map,
                                            cost_vector[0] * self.multiplier, cost_vector[1] * self.multiplier,
                                            cost_vector[2] * self.multiplier, cost_vector[3] * self.multiplier,
                                            float('Inf'))
        if task == 0:
            if maximum == float('Inf'):
                recon.solution_generator = reconciliator.SolutionGeneratorCounter()
            else:
                recon.solution_generator = reconciliator.SolutionGenerator(False)
        recon.init_matrices()
        root = recon.run()
        opt_cost = root.cost / self.multiplier
        return opt_cost, root


class CountThread(qt.QtCore.QThread):
    sig = qt.QtCore.pyqtSignal(str)

    def __init__(self):
        qt.QtCore.QThread.__init__(self)
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
            self.sig.emit(f'Task {task+1}: Counting the number of strong equivalence classes...')

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
                self.sig.emit(f'Total number of solutions = {num_sol}')
            elif task == 2:
                self.sig.emit(f'Total number of event partitions = {root.num_subsolutions}')
            else:
                self.sig.emit(f'Total number of strong equivalence classes = {root.num_subsolutions}')

            self.sig.emit('------')
        self.sig.emit('Optimal cost = {}'.format(opt_cost))
        self.sig.emit('------')
        self.sig.emit(f'Job finished at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.sig.emit(f'Time elapsed: {time.time() - t0:.2f} s')
        self.sig.emit('===============')
        self.sig.emit('')


class EnumerateThread(qt.QtCore.QThread, enumerator.SolutionsEnumerator):
    sig = qt.QtCore.pyqtSignal(str)
    sig2 = qt.QtCore.pyqtSignal(int)

    def __init__(self):
        qt.QtCore.QThread.__init__(self, data=None, root=None, writer=None, maximum=None, acyclic=None)
        self.num_solutions, self.num_acyclic = 0, 0
        self.data, self.cost_vector, self.task, self.filename = None, None, None, None
        self.vector = None, None, None
        self.writer = None
        self.progress_dlg = ProgressBarDialog()
        self.sig2.connect(self.progress_dlg.progress_changed)

    def on_source(self, options):
        self.data = options[0]
        self.cost_vector = options[1:5]
        self.task = options[5]
        self.filename = options[6]
        self.maximum = options[7]
        self.acyclic = options[8]
        self.vector = options[9]
        self.num_acyclic, self.num_solutions = 0, 0
        self.writer = open(self.filename, 'w')

    def print_header(self):
        if self.task == 0:
            self.sig.emit(f'Task {self.task+1}: Enumerate {"acyclic " if self.acyclic else ""}solutions'
                          f'{" (cyclic or acyclic)" if not self.acyclic else ""}...')
        elif self.task == 1:
            self.sig.emit(f'Task {self.task+1}: Enumerate one solution per event vector...')
        elif self.task == 2:
            self.sig.emit(f'Task {self.task+1}: Enumerate one solution per event partition...')
        else:
            self.sig.emit(f'Task {self.task+1}: Enumerate one solution per strong equivalence class...')

    def write_header(self, opt_cost):
        self.writer.write('#--------------------\n')
        self.writer.write('#Host tree          = {}\n'.format(self.data.host_tree))
        self.writer.write('#Parasite tree      = {}\n'.format(self.data.parasite_tree))
        self.writer.write('#Host tree size     = {}\n'.format(self.data.host_tree.size()))
        self.writer.write('#Parasite tree size = {}\n'.format(self.data.parasite_tree.size()))
        self.writer.write('#Leaf mapping       = {{{}}}\n'.format(', '.join(map(lambda x: str(x[0]) + '=' + str(x[1]),
                                                                                self.data.leaf_map.items()))))
        self.writer.write('#--------------------\n')
        if self.task == 0:
            self.writer.write(f'#Task {self.task+1}: Enumerate {"acyclic " if self.acyclic else ""}solutions '
                              f'{"(cyclic or acyclic)" if not self.acyclic else ""}\n')
        elif self.task == 1:
            self.writer.write(f'#Task {self.task+1}: Enumerate one solution per event vector\n')
        elif self.task == 2:
            self.writer.write(f'#Task {self.task+1}: Enumerate one solution per event partition\n')
        else:
            self.writer.write(f'#Task {self.task+1}: Enumerate one solution per strong equivalence class\n')
        self.writer.write('#Co-speciation cost = {}\n'.format(self.cost_vector[0]))
        self.writer.write('#Duplication cost   = {}\n'.format(self.cost_vector[1]))
        self.writer.write('#Host-switch cost   = {}\n'.format(self.cost_vector[2]))
        self.writer.write('#Loss cost          = {}\n'.format(self.cost_vector[3]))
        self.writer.write('#Optimal cost       = {}\n'.format(opt_cost))
        self.writer.write('#--------------------\n')

    def run(self):
        self.sig.emit('===============')
        self.sig.emit(f'Job started at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        t0 = time.time()
        self.sig.emit(f'Cost vector: {tuple(self.cost_vector)}')
        self.print_header()

        if self.progress_dlg.exec() == qtw.QDialog.Rejected:
            self.sig.emit('------')
            self.sig.emit(f'Job aborted at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
            self.sig.emit(f'Time elapsed: {time.time() - t0:.2f} s')
            self.sig.emit('===============')
            self.sig.emit('')
            self.writer.close()
            return

        self.sig2.emit(1)
        opt_cost, root = self.data.enumerate_solutions_setup(self.cost_vector, self.task, self.maximum)
        self.write_header(opt_cost)
        self.sig2.emit(5)
        self.sig.emit('------')
        self.root = root
        self.loop_enumerate()

        self.writer.write('#--------------------\n')
        if self.maximum == float('Inf'):
            if self.task == 0 and self.acyclic:
                self.sig.emit(f'Number of acyclic solutions = {self.num_acyclic} out of {self.num_solutions}')
                self.writer.write(f'#Number of acyclic solutions = {self.num_acyclic} out of {self.num_solutions}\n')
            else:
                self.sig.emit(f'Number of solutions = {self.num_acyclic}')
                self.writer.write(f'#Number of solutions = {self.num_acyclic}\n')
        else:
            self.sig.emit(f'Number of output solutions = {self.num_acyclic} (maximum {self.maximum})')
            self.writer.write(f'#Number of output solutions = {self.num_acyclic} (maximum {self.maximum})\n')

        self.sig.emit('Optimal cost = {}'.format(opt_cost))
        self.sig.emit('Output written to {}'.format(self.filename))
        self.sig.emit('------')
        self.sig.emit(f'Job finished at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.sig.emit(f'Time elapsed: {time.time() - t0:.2f} s')
        self.sig.emit('===============')
        self.sig.emit('')
        self.writer.close()

    def loop_enumerate(self):
        percentage = 0
        while True:
            # reinitialize information related to the current solution
            self.current_mapping = {}
            self.current_text = []
            self.transfer_candidates = []

            # build the next solution
            self.num_solutions += 1
            current_cell = self.root
            iterator = enumerator.SolutionIterator(self.root)
            while not iterator.done():
                current_cell = self.get_next(current_cell, iterator)
            self.clean_stack()

            # is the current solution acyclic?
            is_acyclic = False
            if self.acyclic:
                transfer_edges = cyclicity.find_transfer_edges(self.data.host_tree,
                                                               self.current_mapping, self.transfer_candidates)
                if not transfer_edges:
                    is_acyclic = True
                else:
                    is_acyclic = cyclicity.is_acyclic_stolzer(self.current_mapping, transfer_edges)

            # write the solution only if it is acyclic, or if the user wants both
            if not self.acyclic or is_acyclic:
                self.num_acyclic += 1
                self.writer.write(', '.join(self.current_text))
                self.writer.write('\n')

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


class ProgressBarDialog(qtw.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Writing the output file')
        self.progress = qtw.QProgressBar(self)
        self.progress.setGeometry(0, 0, 300, 25)
        self.progress.setMaximum(100)
        vlayout = qtw.QVBoxLayout()
        vlayout.addWidget(qtw.QLabel('Please wait...'))
        vlayout.addWidget(self.progress)
        vlayout.setSpacing(0)
        vlayout.setContentsMargins(30, 30, 30, 30)
        self.setLayout(vlayout)
        self.resize(500, 150)

    def progress_changed(self, value):
        self.progress.setValue(value)
        if value == 100:
            self.accept()

