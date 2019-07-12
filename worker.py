import datetime
import time
import PyQt5 as qt
import reconciliator
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


class CountThread(qt.QtCore.QThread):
    sig = qt.QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        qt.QtCore.QThread.__init__(self, parent)
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

