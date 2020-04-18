import os
from capybara.eucalypt import nexparser, reconciliator
from capybara.equivalence import enumerate_classes as cla, poly_enum_class as cenu


class TestWorker:
    def __init__(self, input_file, cosp_cost, dup_cost, switch_cost, loss_cost, task, enum=False):
        with open(os.path.join('datasets', input_file), 'r') as f:
            parser = nexparser.NexusParser(f)
            parser.read()
        self.host_tree = parser.host_tree
        self.parasite_tree = parser.parasite_tree
        self.leaf_map = parser.leaf_map
        self.multiplier = 1000
        cost_vector = [cosp_cost, dup_cost, switch_cost, loss_cost]
        self.task = task
        self.enum = enum
        if self.task == 1:
            self.reconciliator = reconciliator.ReconciliatorEnumerator(
                self.host_tree, self.parasite_tree, self.leaf_map,
                cost_vector[0] * self.multiplier, cost_vector[1] * self.multiplier,
                cost_vector[2] * self.multiplier, cost_vector[3] * self.multiplier, float('Inf'),
                self.task, None)
        else:
            self.reconciliator = reconciliator.ReconciliatorCounter(
                             self.host_tree, self.parasite_tree, self.leaf_map,
                             cost_vector[0] * self.multiplier, cost_vector[1] * self.multiplier,
                             cost_vector[2] * self.multiplier, cost_vector[3] * self.multiplier, float('Inf'),
                             self.task)

    def get_answer(self):
        opt = self.reconciliator.run()
        if self.task == 0:
            return opt.num_subsolutions
        elif self.task == 1:
            return len(opt.event_vectors)
        elif self.enum:
            class_enumerator = cenu.ClassEnumerator(self.parasite_tree, opt, self.task)
            num_class = 0
            for mapping, events in class_enumerator.run():
                num_class += 1
            return num_class
        else:
            reachable = cla.fill_reachable_matrix(self.parasite_tree, self.host_tree, opt)
            root = cla.fill_class_matrix(self.parasite_tree, self.host_tree, self.leaf_map, reachable, self.task)
            return root.num_subsolutions

