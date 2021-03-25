from capybara.eucalypt.solution import NestedSolution, SolutionGenerator


class EventVector:
    """
    A tuple of four integers which can also count the number of subsolutions
    """
    def __init__(self, vector, num_subsolutions=1):
        self.vector = vector
        self.num_subsolutions = num_subsolutions

    def __eq__(self, other):
        return self.vector == other.vector

    def __hash__(self):
        return hash(tuple(self.vector))

    def __repr__(self):
        return str(self.vector)

    def cartesian(self, second, event, num_losses, accumulate=False):
        new_vector = self.vector[:]
        for i in range(4):
            new_vector[i] += second.vector[i]
        if event == NestedSolution.COSPECIATION:
            new_vector[0] += 1
        elif event == NestedSolution.DUPLICATION:
            new_vector[1] += 1
        else:
            new_vector[2] += 1
        new_vector[3] += num_losses
        if accumulate:
            return EventVector(new_vector, self.num_subsolutions * second.num_subsolutions)
        else:
            return EventVector(new_vector)

    def add_loss(self):
        new_vector = self.vector[:]
        new_vector[3] += 1
        return EventVector(new_vector, self.num_subsolutions)


class NestedSolutionEventVector(NestedSolution):
    """
    NestedSolution that also remembers a set of event vectors
    """
    def __init__(self, cost, association, composition_type, event, accumulate, children,
                 event_vectors, num_losses=0):
        super().__init__(cost, association, composition_type, event, accumulate, children)
        self.event_vectors = event_vectors
        self.num_losses = num_losses


class SolutionGeneratorEventVector(SolutionGenerator):
    def __init__(self):
        super().__init__(False)

    @staticmethod
    def cartesian_event_vector(first, second, event, num_losses):
        new_vectors = set()
        for first_vector in first:
            for second_vector in second:
                new_vector = first_vector.cartesian(second_vector, event, num_losses)
                new_vectors.add(new_vector)
        return new_vectors

    def empty_solution(self):
        return NestedSolutionEventVector(float('Inf'), None, NestedSolution.FINAL,
                                         NestedSolution.LEAF, self.accumulate, [], {EventVector([0, 0, 0, 0])}, 0)

    def from_leaf_association(self, association, loss_cost=0, distance=0):
        return NestedSolutionEventVector(loss_cost * distance, association,
                                         NestedSolution.FINAL, NestedSolution.LEAF, self.accumulate, [],
                                         {EventVector([0, 0, 0, distance])}, distance)

    def cartesian(self, new_cost, first, second, association, event, num_losses):
        cost = new_cost + first.cost + second.cost
        new_vectors = SolutionGeneratorEventVector.cartesian_event_vector(first.event_vectors,
                                                                          second.event_vectors, event, num_losses)
        return NestedSolutionEventVector(cost, association, NestedSolution.SIMPLE, event,
                                         self.accumulate, [first, second], new_vectors, num_losses)

    def add_loss(self, loss_cost, solution):
        new_event_vectors = set()
        for event_vector in solution.event_vectors:
            new_event_vectors.add(event_vector.add_loss())

        if solution.composition_type == NestedSolution.MULTIPLE:
            new_children = []
            for child in solution.children:
                new_child_event_vectors = set()
                for child_event_vector in child.event_vectors:
                    new_child_event_vectors.add(child_event_vector.add_loss())
                new_child = NestedSolutionEventVector(solution.cost + loss_cost, child.association,
                                                      child.composition_type, child.event, self.accumulate,
                                                      child.children, new_child_event_vectors, child.num_losses+1)
                new_children.append(new_child)
            return NestedSolutionEventVector(solution.cost + loss_cost, solution.association,
                                             solution.composition_type, solution.event, self.accumulate,
                                             new_children, new_event_vectors)
        else:
            return NestedSolutionEventVector(solution.cost + loss_cost, solution.association,
                                             solution.composition_type, solution.event, self.accumulate,
                                             solution.children, new_event_vectors, solution.num_losses+1)

    def merge(self, first, second):
        if first.cost == float('Inf'):
            return self.empty_solution()
        children = []
        for solution in [first, second]:
            if solution.composition_type == NestedSolution.MULTIPLE:
                children.extend(solution.children)
            else:
                children.append(solution)

        new_event_vectors = {EventVector(v.vector, v.num_subsolutions) for v in first.event_vectors}
        new_event_vectors.update(second.event_vectors)
        return NestedSolutionEventVector(first.cost, None, NestedSolution.MULTIPLE, None, self.accumulate, children,
                                         new_event_vectors)


class SolutionGeneratorEventVectorCounter(SolutionGeneratorEventVector):
    def __init__(self):
        super().__init__()

    @staticmethod
    def cartesian_event_vector(first, second, event, num_losses):
        new_vectors = set()
        count = {}
        for first_vector in first:
            for second_vector in second:
                new_vector = first_vector.cartesian(second_vector, event, num_losses, True)

                if new_vector not in count:
                    count[new_vector] = new_vector.num_subsolutions
                else:
                    count[new_vector] += new_vector.num_subsolutions
                new_vectors.add(new_vector)
        for vec in new_vectors:
            vec.num_subsolutions = count[vec]
        return new_vectors

    def cartesian(self, new_cost, first, second, association, event, num_losses):
        cost = new_cost + first.cost + second.cost
        new_vectors = SolutionGeneratorEventVectorCounter.cartesian_event_vector(first.event_vectors,
                                                                          second.event_vectors, event, num_losses)
        return NestedSolutionEventVector(cost, association, NestedSolution.SIMPLE, event,
                                         self.accumulate, [first, second], new_vectors, num_losses)

    def merge(self, first, second):
        if first.cost == float('Inf'):
            return self.empty_solution()
        children = []
        for solution in [first, second]:
            if solution.composition_type == NestedSolution.MULTIPLE:
                children.extend(solution.children)
            else:
                children.append(solution)

        new_event_vectors = {EventVector(v.vector, v.num_subsolutions) for v in first.event_vectors}
        count = {vec: vec.num_subsolutions for vec in new_event_vectors}
        for vec in second.event_vectors:
            if vec not in count:
                count[vec] = vec.num_subsolutions
            else:
                count[vec] += vec.num_subsolutions
        new_event_vectors.update(second.event_vectors)
        for vec in new_event_vectors:
            vec.num_subsolutions = count[vec]

        return NestedSolutionEventVector(first.cost, None, NestedSolution.MULTIPLE, None, self.accumulate, children,
                                         new_event_vectors)

