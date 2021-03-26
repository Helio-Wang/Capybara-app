from capybara.eucalypt.solution import NestedSolution
from capybara.equivalence.event_vector import NestedSolutionEventVector
from capybara.eucalypt.enumerator import SolutionIterator, SolutionsEnumerator
from capybara.equivalence.event_reconciliator import EventReconciliator



class VectorEnumerator(SolutionsEnumerator):
    """
    Build a DAG containing only ONE reconciliations with a given event vector
    """
    def __init__(self, vector, root):
        super().__init__(data=None, root=None, writer=None, maximum=None, acyclic=None)
        self.vector = vector
        self.root = root
        
    def get_one_representative(self):
        self.visit_vector(self.root, self.vector)
        return ', '.join(self.current_text)


class EventEnumerator:
    """
    Build a DAG containing all reconciliations in a given equivalence class
    """
    def __init__(self, mapping, events, task, data, root, cost_vector):
        self.data = data
        self.root = root
        self.mapping = mapping
        self.events = events
        self.task = task
        self.cost_vector = cost_vector
        self.new_root = None

    def build_new_root(self):
        reconciliator = EventReconciliator(self.data.host_tree, self.data.parasite_tree,
                                           self.data.leaf_map,
                                           self.cost_vector[0] * self.data.multiplier,
                                           self.cost_vector[1] * self.data.multiplier,
                                           self.cost_vector[2] * self.data.multiplier,
                                           self.cost_vector[3] * self.data.multiplier,
                                           float('Inf'), self.task,
                                           self.mapping, self.events, accumulate=True)
        self.new_root = reconciliator.run()

    def get_size(self):
        if self.new_root:
            return self.new_root.num_subsolutions
        self.build_new_root()
        return self.new_root.num_subsolutions

    def get_one_representative(self):
        if not self.new_root:
            _ = self.get_size()
        enumerator = SolutionsEnumerator(self.data, self.new_root, None, 1, False)
        iterator = SolutionIterator(self.root)
        current_cell = self.new_root
        while not iterator.done():
            current_cell = enumerator.get_next(current_cell, iterator)
        return ', '.join(enumerator.current_text)


