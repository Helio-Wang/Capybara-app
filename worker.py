import datetime
import PyQt5 as qt
import reconciliator


class WorkerData:
    def __init__(self, parasite_tree, host_tree, leaf_map):
        self.parasite_tree = parasite_tree
        self.host_tree = host_tree
        self.leaf_map = leaf_map
        self.multiplier = 1000

    def count_solutions(self, cost_vector, task):
        recon = reconciliator.ReconciliatorCount(self.host_tree, self.parasite_tree, self.leaf_map,
                                                 cost_vector[0] * self.multiplier, cost_vector[1] * self.multiplier,
                                                 cost_vector[2] * self.multiplier, cost_vector[3] * self.multiplier,
                                                 float('Inf'), task)
        root = recon.run()
        return root.cost / self.multiplier, root


class CountThread(qt.QtCore.QThread):
    sig1 = qt.QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        qt.QtCore.QThread.__init__(self, parent)
        self.data, self.cost_vector, self.tasks = None, None, None

    def on_source(self, options):
        self.data = options[0]
        self.cost_vector = options[1:5]
        self.tasks = options[5:]

    def run(self):
        self.sig1.emit('===============')
        self.sig1.emit(f'<b>New job started at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</b>')
        self.sig1.emit(f'Cost vector: {tuple(self.cost_vector)}')
        self.sig1.emit('------')
        for task in self.tasks:
            if task == 0:
                self.sig1.emit(f'Task {task+1}: Counting the number of solutions (cyclic or acyclic)...')
            elif task == 1:
                self.sig1.emit(f'Task {task+1}: Counting the number of solutions grouped by event vectors...')

            opt_cost, root = self.data.count_solutions(self.cost_vector, task)
            if task == 0:
                self.sig1.emit(f'Total number of solutions = {root.num_subsolutions}')
            elif task == 1:
                num_class = 0
                num_sol = 0
                for target_vector in root.event_vectors:
                    num_class += 1
                    self.sig1.emit(f"{num_class}: {target_vector.vector} of size {target_vector.num_subsolutions}")
                    num_sol += target_vector.num_subsolutions
                self.sig1.emit(f'Total number of solutions = {num_sol}')

            self.sig1.emit('Optimal cost = {}'.format(opt_cost))
            self.sig1.emit('------')
        self.sig1.emit('===============')
        self.sig1.emit('')

