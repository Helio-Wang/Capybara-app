from capybara.eucalypt.solution import Association, NestedSolution
from capybara.eucalypt.reconciliator import ReconciliatorEnumerator
from capybara.eucalypt.util import full_flatten


class EventReconciliator(ReconciliatorEnumerator):
    """
    Recover optimal solutions knowing all events or all event and non-host-switch hosts
    """
    def __init__(self, host_tree, parasite_tree, leaf_map,
                 cospeciation_cost, duplication_cost, transfer_cost, loss_cost, distance_threshold, task,
                 mapping, events):
        super().__init__(host_tree, parasite_tree, leaf_map, cospeciation_cost, duplication_cost,
                         transfer_cost, loss_cost, distance_threshold, task, 0)
        self.task = task  # 2 or 3
        self.mapping = mapping
        self.events = events

    def fill_matrices_at(self, parasite, host):
        association = Association(parasite, host)
        row, column = parasite.index, host.index
        event = self.events[parasite]

        if host.is_leaf():
            if event == NestedSolution.DUPLICATION:
                best_solution = self.duplication_leaf_solution(parasite, host, association)
            elif event == NestedSolution.HOST_SWITCH:
                best_solution = self.transfer_solution(parasite, host, association)
            else:
                best_solution = self.solution_generator.empty_solution()

            self.main_matrix[row][column] = best_solution
            self.subtree_matrix[row][column] = best_solution

        else:
            if event == NestedSolution.DUPLICATION:
                best_solution = self.duplication_solution(parasite, host, association)
            elif event == NestedSolution.HOST_SWITCH:
                best_solution = self.transfer_solution(parasite, host, association)
            else:
                best_solution = self.cospeciation_solution(parasite, host, association)

            self.main_matrix[row][column] = best_solution

            loss_solution_left, loss_solution_right = self.subtree_loss_solutions(parasite, host)
            best_subtree_solution = self.solution_generator.best_solution([best_solution,
                                                                           loss_solution_left, loss_solution_right])
            self.subtree_matrix[row][column] = best_subtree_solution

        # force the given mapping
        if self.task == 3:
            h = self.mapping[parasite]
            if h is not None:
                if host != h:
                    self.main_matrix[row][column] = self.solution_generator.empty_solution()
                children = []
                for node in full_flatten(self.subtree_matrix[row][column]):
                    if node.cost < float('Inf'):
                        if node.association.host == h:
                            children.append(node)

                if not children:
                    self.subtree_matrix[row][column] = self.solution_generator.empty_solution()
                elif len(children) == 1:
                    self.subtree_matrix[row][column] = children[0]
                else:
                    # this is the only place where a solution object is created outside of a solution generator
                    self.subtree_matrix[row][column] = NestedSolution(children[0].cost, None,
                                                                      NestedSolution.MULTIPLE, None,
                                                                      accumulate=False, children=children)

