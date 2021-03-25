from capybara.eucalypt.solution import NestedSolution
from capybara.equivalence.event_vector import NestedSolutionEventVector
from capybara.eucalypt.enumerator import SolutionIterator, SolutionsEnumerator
from capybara.equivalence.event_reconciliator import EventReconciliator


class InverseEnumerator:
    def __init__(self, data, root):
        self.data = data
        self.root = root
        self.new_root = None

    def build_new_root(self):
        pass

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


class VectorEnumerator(InverseEnumerator):
    """
    Build a DAG containing all reconciliations with a given event vector
    """
    def __init__(self, vector, data, root):
        super().__init__(data, root)
        self.vector = vector

    def visit_vector_all(self, solution, target_vector):
        """
        Recursive function in Event Vector Enumeration loop for counting and extracting all solutions
        """
        if solution.composition_type == NestedSolution.MULTIPLE:
            new_children = []
            for child in solution.children:
                if target_vector in child.event_vectors:
                    new_children.append(self.visit_vector_all(child, target_vector))
            return NestedSolutionEventVector(0, None, NestedSolution.MULTIPLE, None, True,
                                             new_children, solution.event_vectors)
        elif solution.composition_type == NestedSolution.FINAL:
            return solution
        else:
            new_children = []
            for left_vector in solution.children[0].event_vectors:
                for right_vector in solution.children[1].event_vectors:
                    new_vec = left_vector.cartesian(right_vector, solution.event, solution.num_losses)
                    if new_vec == target_vector:
                        first = self.visit_vector_all(solution.children[0], left_vector)
                        second = self.visit_vector_all(solution.children[1], right_vector)
                        new_children.append(NestedSolutionEventVector(0, solution.association, NestedSolution.SIMPLE,
                                                                      solution.event, True, [first, second],
                                                                      solution.event_vectors))
            return NestedSolutionEventVector(0, None, NestedSolution.MULTIPLE, None, True,
                                             new_children, solution.event_vectors)

    def build_new_root(self):
        self.new_root = self.visit_vector_all(self.root, self.vector)


class EventEnumerator(InverseEnumerator):
    """
    Build a DAG containing all reconciliations in a given equivalence class
    """
    def __init__(self, mapping, events, task, data, root, cost_vector):
        super().__init__(data, root)
        self.mapping = mapping
        self.events = events
        self.task = task
        self.cost_vector = cost_vector

    def  build_new_root(self):
        reconciliator = EventReconciliator(self.data.host_tree, self.data.parasite_tree,
                                           self.data.leaf_map,
                                           self.cost_vector[0] * self.data.multiplier,
                                           self.cost_vector[1] * self.data.multiplier,
                                           self.cost_vector[2] * self.data.multiplier,
                                           self.cost_vector[3] * self.data.multiplier,
                                           float('Inf'), self.task,
                                           self.mapping, self.events, accumulate=True)
        self.new_root = reconciliator.run()
        return self.new_root.num_subsolutions

