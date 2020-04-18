from capybara.eucalypt import reconciliator
from capybara.equivalence import enumerate_classes as cla


class DataInterface:
    """
    Interface between the input data and the reconciliators
    """
    def __init__(self, parasite_tree, host_tree, leaf_map):
        self.parasite_tree = parasite_tree
        self.host_tree = host_tree
        self.leaf_map = leaf_map
        self.multiplier = 1000
        self.threshold = float('Inf')

    def count_solutions(self, cost_vector, task, cli=False):
        recon = reconciliator.ReconciliatorCounter(self.host_tree, self.parasite_tree, self.leaf_map,
                                                   cost_vector[0] * self.multiplier, cost_vector[1] * self.multiplier,
                                                   cost_vector[2] * self.multiplier, cost_vector[3] * self.multiplier,
                                                   self.threshold, task, cli)
        root = recon.run()
        opt_cost = root.cost // self.multiplier

        if task in (2, 3):
            reachable = cla.fill_reachable_matrix(self.parasite_tree, self.host_tree, root)
            root = cla.fill_class_matrix(self.parasite_tree, self.host_tree, self.leaf_map, reachable, task)
        return opt_cost, root

    def enumerate_solutions_setup(self, cost_vector, task, maximum, cli=False):
        recon = reconciliator.ReconciliatorEnumerator(self.host_tree, self.parasite_tree, self.leaf_map,
                                                      cost_vector[0] * self.multiplier, cost_vector[1] * self.multiplier,
                                                      cost_vector[2] * self.multiplier, cost_vector[3] * self.multiplier,
                                                      self.threshold, task, maximum, cli)
        root = recon.run()
        opt_cost = root.cost // self.multiplier
        return opt_cost, root

    def enumerate_best_k(self, cost_vector, k):
        recon = reconciliator.ReconciliatorBestKEnumerator(self.host_tree, self.parasite_tree, self.leaf_map,
                                                           cost_vector[0] * self.multiplier,
                                                           cost_vector[1] * self.multiplier,
                                                           cost_vector[2] * self.multiplier,
                                                           cost_vector[3] * self.multiplier, self.threshold, k)
        root = recon.run()
        return root.cost // self.multiplier, recon.cost_summary, root

