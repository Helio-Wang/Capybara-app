from capybara.eucalypt.solution import Association, NestedSolution, SolutionGenerator, BestKSolutionGenerator
from capybara.equivalence.event_vector import SolutionGeneratorEventVectorCounter, SolutionGeneratorEventVector


class Reconciliator:
    """
    General class for updating the dynamic programming matrices
    """
    def __init__(self, host_tree, parasite_tree, leaf_map,
                 cospeciation_cost, duplication_cost, transfer_cost, loss_cost, distance_threshold):
        self.solution_generator = None
        self.pool = None
        self.host_tree = host_tree
        self.parasite_tree = parasite_tree
        self.leaf_map = leaf_map
        self.cospeciation_cost = cospeciation_cost
        self.duplication_cost = duplication_cost
        self.transfer_cost = transfer_cost
        self.loss_cost = loss_cost
        self.distance_threshold = distance_threshold

        self.main_matrix, self.subtree_matrix, self.allowed_transfers = None, None, None

    def init_matrices(self):
        self.main_matrix = [[self.solution_generator.empty_solution() for _ in range(self.host_tree.size())]
                            for _ in range(self.parasite_tree.size())]
        self.subtree_matrix = [[self.solution_generator.empty_solution() for _ in range(self.host_tree.size())]
                               for _ in range(self.parasite_tree.size())]

        self.initialize_leaf_costs()
        self.allowed_transfers = [None] * self.host_tree.size()
        self.allowed_transfers[self.host_tree.root.index] = set()

    def initialize_leaf_costs(self):
        for parasite, host in self.leaf_map.items():
            row, column = parasite.index, host.index
            self.main_matrix[row][column] = self.solution_generator.from_leaf_association(Association(parasite, host))
            self.subtree_matrix[row][column] = self.main_matrix[row][column]

            distance = 1
            ancestor = host.parent
            while ancestor:
                ancestor_index = ancestor.index
                self.subtree_matrix[row][ancestor_index] = \
                    self.solution_generator.from_leaf_association(Association(parasite, host), self.loss_cost, distance)
                ancestor = ancestor.parent
                distance += 1

    def get_allowed_transfers(self, host):
        if self.allowed_transfers[host.index] is not None:
            return self.allowed_transfers[host.index]

        result = []
        target = host.get_sibling()

        if self.distance_threshold < float('Inf'):
            distance = 2

            while distance <= self.distance_threshold:
                previous, next_ = None, None
                while target != next_:
                    if previous is None:
                        next_ = target
                        while not next_.is_leaf() and distance < self.distance_threshold:
                            next_ = next_.left_child
                            distance += 1
                    else:
                        next_ = previous.parent
                        distance -= 1
                        if previous == next_.left_child and distance <= self.distance_threshold:
                            next_ = next_.right_child
                            distance += 1
                            while not next_.is_leaf() and distance < self.distance_threshold:
                                next_ = next_.left_child
                                distance += 1
                    previous = next_
                    result.append(next_)

                if target.parent.is_root():
                    break
                target = target.parent.get_sibling()
                distance += 1
        else:
            while True:
                previous, next_ = None, None
                while target != next_:
                    if previous is None:
                        next_ = target
                        while not next_.is_leaf():
                            next_ = next_.left_child
                    else:
                        next_ = previous.parent
                        if previous == next_.left_child:
                            next_ = next_.right_child
                            while not next_.is_leaf():
                                next_ = next_.left_child
                    previous = next_
                    result.append(next_)

                if target.parent.is_root():
                    break
                target = target.parent.get_sibling()

        self.allowed_transfers[host.index] = set(result)
        return result

    def run(self):
        self.fill_matrices()
        return self.finishing_up()

    def finishing_up(self):
        parasite_root_row = self.main_matrix[self.parasite_tree.root.index]
        optimal_solutions = self.solution_generator.best_solution(parasite_root_row)
        return optimal_solutions

    def fill_matrices(self):
        for parasite in self.parasite_tree:
            if parasite.is_leaf():
                continue
            for host in self.host_tree:
                self.fill_matrices_at(parasite, host)

    def fill_matrices_at(self, parasite, host):
        association = Association(parasite, host)
        row, column = parasite.index, host.index
        if host.is_leaf():
            duplication_sol = self.duplication_leaf_solution(parasite, host, association)
            transfer_sol = self.transfer_solution(parasite, host, association)
            best_solution = self.solution_generator.best_solution([duplication_sol, transfer_sol])

            self.main_matrix[row][column] = best_solution
            self.subtree_matrix[row][column] = best_solution
        else:
            duplication_sol = self.duplication_solution(parasite, host, association)
            transfer_sol = self.transfer_solution(parasite, host, association)
            cospeciation_sol = self.cospeciation_solution(parasite, host, association)
            best_solution = self.solution_generator.best_solution([cospeciation_sol, duplication_sol, transfer_sol])

            self.main_matrix[row][column] = best_solution

            loss_solution_left, loss_solution_right = self.subtree_loss_solutions(parasite, host)
            best_subtree_solution = self.solution_generator.best_solution([best_solution,
                                                                           loss_solution_left, loss_solution_right])
            self.subtree_matrix[row][column] = best_subtree_solution

    def duplication_leaf_solution(self, parasite, host, association):
        first = self.main_matrix[parasite.left_child.index][host.index]
        second = self.main_matrix[parasite.right_child.index][host.index]
        return self.solution_generator.cartesian(self.duplication_cost, first, second, association,
                                                 NestedSolution.DUPLICATION, 0)

    def duplication_solution(self, parasite, host, association):
        first1 = self.main_matrix[parasite.left_child.index][host.index]
        first2 = self.main_matrix[parasite.left_child.index][host.index]
        first3 = self.main_matrix[parasite.left_child.index][host.index]
        first4 = self.main_matrix[parasite.right_child.index][host.index]
        first5 = self.main_matrix[parasite.right_child.index][host.index]
        first6 = self.subtree_matrix[parasite.left_child.index][host.left_child.index]
        first7 = self.subtree_matrix[parasite.left_child.index][host.right_child.index]

        second1 = self.main_matrix[parasite.right_child.index][host.index]
        second2 = self.subtree_matrix[parasite.right_child.index][host.left_child.index]
        second3 = self.subtree_matrix[parasite.right_child.index][host.right_child.index]
        second4 = self.subtree_matrix[parasite.left_child.index][host.left_child.index]
        second5 = self.subtree_matrix[parasite.left_child.index][host.right_child.index]
        second6 = self.subtree_matrix[parasite.right_child.index][host.left_child.index]
        second7 = self.subtree_matrix[parasite.right_child.index][host.right_child.index]

        solution1 = self.solution_generator.cartesian(self.duplication_cost, first1, second1, association,
                                                      NestedSolution.DUPLICATION, 0)
        solution2 = self.solution_generator.cartesian(self.duplication_cost + self.loss_cost, first2, second2,
                                                      association, NestedSolution.DUPLICATION, 1)
        solution3 = self.solution_generator.cartesian(self.duplication_cost + self.loss_cost, first3, second3,
                                                      association, NestedSolution.DUPLICATION, 1)
        solution4 = self.solution_generator.cartesian(self.duplication_cost + self.loss_cost, second4, first4,
                                                      association, NestedSolution.DUPLICATION, 1)
        solution5 = self.solution_generator.cartesian(self.duplication_cost + self.loss_cost, second5, first5,
                                                      association, NestedSolution.DUPLICATION, 1)
        solution6 = self.solution_generator.cartesian(self.duplication_cost + self.loss_cost + self.loss_cost,
                                                      first6, second6, association, NestedSolution.DUPLICATION, 2)
        solution7 = self.solution_generator.cartesian(self.duplication_cost + self.loss_cost + self.loss_cost,
                                                      first7, second7, association, NestedSolution.DUPLICATION, 2)
        return self.solution_generator.best_solution([solution1, solution2, solution3, solution4,
                                                      solution5, solution6, solution7])

    def transfer_solution(self, parasite, host, association):
        best_solution = self.solution_generator.empty_solution()
        for transfer_host in self.get_allowed_transfers(host):
            first_left = self.main_matrix[parasite.left_child.index][transfer_host.index]
            first_right = self.subtree_matrix[parasite.right_child.index][host.index]
            first = self.solution_generator.cartesian(self.transfer_cost, first_left, first_right, association,
                                                      NestedSolution.HOST_SWITCH, 0)
            second_left = self.subtree_matrix[parasite.left_child.index][host.index]
            second_right = self.main_matrix[parasite.right_child.index][transfer_host.index]
            second = self.solution_generator.cartesian(self.transfer_cost, second_left, second_right, association,
                                                       NestedSolution.HOST_SWITCH, 0)
            best_solution = self.solution_generator.best_solution([best_solution, first, second])
        return best_solution

    def cospeciation_solution(self, parasite, host, association):
        first_left = self.subtree_matrix[parasite.left_child.index][host.left_child.index]
        first_right = self.subtree_matrix[parasite.right_child.index][host.right_child.index]
        first = self.solution_generator.cartesian(self.cospeciation_cost, first_left, first_right,
                                                  association, NestedSolution.COSPECIATION, 0)
        second_left = self.subtree_matrix[parasite.left_child.index][host.right_child.index]
        second_right = self.subtree_matrix[parasite.right_child.index][host.left_child.index]
        second = self.solution_generator.cartesian(self.cospeciation_cost, second_left, second_right,
                                                   association, NestedSolution.COSPECIATION, 0)
        return self.solution_generator.best_solution([first, second])

    def subtree_loss_solutions(self, parasite, host):
        return self.solution_generator.add_loss(self.loss_cost,
                                                self.subtree_matrix[parasite.index][host.left_child.index]), \
               self.solution_generator.add_loss(self.loss_cost,
                                                self.subtree_matrix[parasite.index][host.right_child.index])


class ReconciliatorCounter(Reconciliator):
    def __init__(self, host_tree, parasite_tree, leaf_map,
                 cospeciation_cost, duplication_cost, transfer_cost, loss_cost, distance_threshold, task, cli):

        super().__init__(host_tree, parasite_tree, leaf_map,
                         cospeciation_cost, duplication_cost, transfer_cost, loss_cost, distance_threshold)
        if task == 0:
            self.solution_generator = SolutionGenerator(True)
        elif task == 1:
            if cli:
                self.solution_generator = SolutionGeneratorEventVector()
            else:
                self.solution_generator = SolutionGeneratorEventVectorCounter()
        else:
            self.solution_generator = SolutionGenerator(False)
        self.init_matrices()


class ReconciliatorEnumerator(Reconciliator):
    def __init__(self, host_tree, parasite_tree, leaf_map,
                 cospeciation_cost, duplication_cost, transfer_cost, loss_cost, distance_threshold, task, maximum, cli):
        super().__init__(host_tree, parasite_tree, leaf_map,
                         cospeciation_cost, duplication_cost, transfer_cost, loss_cost, distance_threshold)

        if task == 1:
            self.solution_generator = SolutionGeneratorEventVector()
        elif not cli and task == 0 and maximum == float('Inf'):
            self.solution_generator = SolutionGenerator(True)
        else:
            self.solution_generator = SolutionGenerator(False)
        self.init_matrices()


class ReconciliatorBestKEnumerator(Reconciliator):
    def __init__(self, host_tree, parasite_tree, leaf_map,
                 cospeciation_cost, duplication_cost, transfer_cost, loss_cost, distance_threshold, k):
        super().__init__(host_tree, parasite_tree, leaf_map,
                         cospeciation_cost, duplication_cost, transfer_cost, loss_cost, distance_threshold)

        self.solution_generator = BestKSolutionGenerator(k)
        self.init_matrices()
        self.cost_summary = {}  # the number of solutions for each cost value

    def run(self):
        self.fill_matrices()
        root = self.finishing_up()
        for solution in root.children:
            if solution.cost not in self.cost_summary:
                self.cost_summary[solution.cost] = 1
            else:
                self.cost_summary[solution.cost] += 1
        return root

