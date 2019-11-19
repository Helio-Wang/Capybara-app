import heapq


class Association:
    def __init__(self, parasite, host):
        self.parasite = parasite
        self.host = host

    def __repr__(self):
        return self.parasite.label + '@' + self.host.label

    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(other, Association):
            return self.parasite.label == other.parasite.label and self.host.label == other.host.label
        return False

    def __hash__(self):
        """Overrides the default implementation"""
        return hash(self.parasite.label + self.host.label)


class NestedSolution:
    SIMPLE, MULTIPLE, FINAL = 0, 1, 2
    COSPECIATION, DUPLICATION, HOST_SWITCH, LEAF = 0, 1, 2, 4

    def __init__(self, cost, association, composition_type, event, accumulate, children, num_subsolutions=1):
        self.cost = cost
        self.association = association
        self.composition_type = composition_type
        self.event = event
        self.accumulate = accumulate

        self.left_grandchildren = None
        self.right_grandchildren = None

        self.children = children

        self.num_subsolutions = num_subsolutions
        if accumulate and num_subsolutions == 1:  # recompute
            if self.composition_type == NestedSolution.SIMPLE:
                self.num_subsolutions = self.children[0].num_subsolutions * self.children[1].num_subsolutions
            elif self.composition_type == NestedSolution.MULTIPLE:
                self.num_subsolutions = sum(child.num_subsolutions for child in self.children)

    def __str__(self):
        if self.association is None:  # multiple
            if not self.children:  # empty solution
                return 'Empty'
            return str(self.children[0])
        return str(self.association)


class SolutionGenerator:
    EMPTY = NestedSolution(float('Inf'), None, NestedSolution.FINAL,
                           NestedSolution.LEAF, True, [])

    def __init__(self, accumulate):
        self.accumulate = accumulate

    def empty_solution(self):
        return SolutionGenerator.EMPTY

    def from_leaf_association(self, association, loss_cost=0, distance=0):
        return NestedSolution(loss_cost * distance, association,
                              NestedSolution.FINAL,
                              NestedSolution.LEAF, self.accumulate, [])

    def cartesian(self, new_cost, first, second, association, event, num_losses):
        if first.cost == float('Inf') or second.cost == float('Inf'):
            return self.empty_solution()
        cost = new_cost + first.cost + second.cost
        return NestedSolution(cost, association, NestedSolution.SIMPLE, event, self.accumulate, [first, second])

    def add_loss(self, loss_cost, solution):
        # something which was REALLY REALLY BADLY WRITTEN in the original code
        return NestedSolution(solution.cost + loss_cost, solution.association,
                              solution.composition_type, solution.event, self.accumulate,
                              solution.children, solution.num_subsolutions)

    def best_solution(self, solutions):
        """select the solutions with minimum cost"""
        best = solutions[0]
        for solution in solutions[1:]:
            if best.cost > solution.cost:
                best = solution
            elif best.cost == solution.cost:
                best = self.merge(best, solution)
        return best

    def merge(self, first, second):
        if first.cost == float('Inf'):
            return self.empty_solution()
        children = []
        for solution in [first, second]:
            if solution.composition_type == NestedSolution.MULTIPLE:
                children.extend(solution.children)
            else:
                children.append(solution)
        return NestedSolution(first.cost, None, NestedSolution.MULTIPLE, None, self.accumulate, children)


class BestKSolutionGenerator(SolutionGenerator):
    def __init__(self, k):
        super().__init__(False)
        self.k = k

    def cartesian(self, new_cost, first, second, association, event, num_losses):
        if first.cost == float('Inf') or second.cost == float('Inf'):
            return self.empty_solution()

        if first.composition_type != NestedSolution.MULTIPLE and second.composition_type != NestedSolution.MULTIPLE:
            cost = new_cost + first.cost + second.cost
            return NestedSolution(cost, association, NestedSolution.SIMPLE, event,
                                  self.accumulate, [first, second])

        children = []
        if first.composition_type == NestedSolution.MULTIPLE and second.composition_type == NestedSolution.MULTIPLE:
            pq = [(first.children[0].cost + second.children[j].cost, 0, j) for j in range(len(second.children))]
            heapq.heapify(pq)

            while len(pq) > 0:
                v, i, j = heapq.heappop(pq)
                children.append(self.cartesian(new_cost, first.children[i], second.children[j],
                                               association, event, num_losses))
                if len(children) == self.k:
                    break
                if i < len(first.children)-1:
                    i += 1
                    heapq.heappush(pq, (first.children[i].cost + second.children[j].cost, i, j))

        elif first.composition_type == NestedSolution.MULTIPLE:
            for first_child in first.children:
                children.append(self.cartesian(new_cost, first_child, second, association, event, num_losses))
        else:
            for second_child in second.children:
                children.append(self.cartesian(new_cost, first, second_child, association, event, num_losses))

        if self.k == 1:
            return children[0]
        return NestedSolution(children[0].cost, None, NestedSolution.MULTIPLE, None, self.accumulate, children)

    def best_solution(self, solutions):
        """select the best k solutions"""
        best = solutions[0]
        for solution in solutions[1:]:
            best = self.k_merge(best, solution)
        return best

    def k_merge(self, first, second):
        if first.cost == float('Inf') and second.cost == float('Inf'):
            return self.empty_solution()
        elif first.cost == float('Inf'):
            return second
        elif second.cost == float('Inf'):
            return first

        if first.composition_type != NestedSolution.MULTIPLE and second.composition_type != NestedSolution.MULTIPLE:
            if self.k == 1:
                if first.cost < second.cost:
                    return first
                else:
                    return second
            return NestedSolution(first.cost, None, NestedSolution.MULTIPLE, None, self.accumulate,
                                  [first, second] if first.cost < second.cost else [second, first])

        first_candidates, second_candidates = [first], [second]
        if first.composition_type == NestedSolution.MULTIPLE:
            first_candidates = first.children
        if second.composition_type == NestedSolution.MULTIPLE:
            second_candidates = second.children

        if self.k == 1:
            if first_candidates[0].cost < second_candidates[0].cost:
                return first_candidates[0]
            else:
                return second_candidates[0]

        # merge two arrays of solutions with sorted costs
        children = []
        i, j = 0, 0
        while len(children) < self.k and i < len(first_candidates) and j < len(second_candidates):
            first_child, second_child = first_candidates[i], second_candidates[j]
            if first_child.cost < second_child.cost:
                children.append(first_child)
                i += 1
            elif first_child.cost > second_child.cost:
                children.append(second_child)
                j += 1
            else:
                children.append(first_child)
                i += 1
                if len(children) < self.k:
                    children.append(second_child)
                    j += 1
        while i < len(first_candidates) and len(children) < self.k:
            children.append(first_candidates[i])
            i += 1
        while j < len(second_candidates) and len(children) < self.k:
            children.append(second_candidates[j])
            j += 1

        return NestedSolution(children[0].cost, None, NestedSolution.MULTIPLE, None, self.accumulate, children)

    def add_loss(self, loss_cost, solution):
        if solution.composition_type == NestedSolution.MULTIPLE:
            new_children = []
            for child in solution.children:
                new_children.append(NestedSolution(child.cost + loss_cost, child.association,
                                                   child.composition_type, child.event, self.accumulate,
                                                   child.children))
            return NestedSolution(new_children[0].cost, None, NestedSolution.MULTIPLE,
                                  None, self.accumulate, new_children)
        else:
            return NestedSolution(solution.cost + loss_cost, solution.association,
                                  solution.composition_type, solution.event, self.accumulate,
                                  solution.children)



