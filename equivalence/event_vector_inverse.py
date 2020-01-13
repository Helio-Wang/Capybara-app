from eucalypt.solution import NestedSolution
from equivalence.event_vector import NestedSolutionEventVector
from eucalypt.enumerator import SolutionsEnumerator


class VectorEnumerator:
    """
    Given the event vector, a reconciliation can be found by backtracking (not used in the app)
    """
    def __init__(self, root, writer, config):
        self.root = root
        self.writer = writer
        self.config = config

        self.current_mapping = {}
        self.current_text = []  # text for the printing the current solution

    def visit(self, solution, target_vector):
        if solution.composition_type == NestedSolution.MULTIPLE:
            for child in solution.children:
                if target_vector in child.event_vectors:
                    self.visit(child, target_vector)
                    return
        elif solution.composition_type == NestedSolution.FINAL:
            self.current_mapping[solution.association.parasite] = solution.association.host
            self.current_text.append(str(solution.association))
        else:
            self.current_mapping[solution.association.parasite] = solution.association.host
            self.current_text.append(str(solution.association))

            for left_vector in solution.children[0].event_vectors:
                for right_vector in solution.children[1].event_vectors:
                    new_vec = left_vector.cartesian(right_vector, solution.event, solution.num_losses)
                    if new_vec == target_vector:
                        self.visit(solution.children[0], left_vector)
                        self.visit(solution.children[1], right_vector)
                        return

    def run(self):
        num_class = 0
        num_solutions = 0
        for target_vector in self.root.event_vectors:
            self.current_text = []
            self.current_mapping = {}
            num_class += 1
            num_solutions += target_vector.num_subsolutions
            print(num_class, target_vector.vector, 'of size ', target_vector.num_subsolutions)
            self.writer.write('#Class {:d} with vector {} and size {:d}\n'.format(num_class,
                                                                                  str(target_vector.vector),
                                                                                  target_vector.num_subsolutions))
            self.visit(self.root, target_vector)
            self.writer.write(', '.join(self.current_text))
            self.writer.write('\n')
        return num_class, num_solutions


class VectorEnumeratorAll:
    """
    Build a DAG containing all reconciliations with a given event vector (not used in the app)
    """
    def __init__(self, root, writer, config):
        self.root = root
        self.writer = writer
        self.config = config

    def visit(self, solution, target_vector):
        if solution.composition_type == NestedSolution.MULTIPLE:
            new_children = []
            for child in solution.children:
                if target_vector in child.event_vectors:
                    new_children.append(self.visit(child, target_vector))
            return NestedSolutionEventVector(0, None, NestedSolution.MULTIPLE, None, False,
                                             new_children, solution.event_vectors)
        elif solution.composition_type == NestedSolution.FINAL:
            return solution
        else:
            new_children = []
            for left_vector in solution.children[0].event_vectors:
                for right_vector in solution.children[1].event_vectors:
                    new_vec = left_vector.cartesian(right_vector, solution.event, solution.num_losses)
                    if new_vec == target_vector:
                        first = self.visit(solution.children[0], left_vector)
                        second = self.visit(solution.children[1], right_vector)
                        new_children.append(NestedSolutionEventVector(0, solution.association, NestedSolution.SIMPLE,
                                            solution.event, False, [first, second], solution.event_vectors))
            return NestedSolutionEventVector(0, None, NestedSolution.MULTIPLE, None, False,
                                             new_children, solution.event_vectors)

    def run(self):
        num_class = 0
        num_solutions = 0
        for target_vector in self.root.event_vectors:
            num_class += 1
            num_solutions += target_vector.num_subsolutions
            print(num_class, target_vector.vector, 'of size ', target_vector.num_subsolutions)
            self.writer.write('#Class {:d} with vector {} and size {:d}\n'.format(num_class,
                                                                                  str(target_vector.vector),
                                                                                  target_vector.num_subsolutions))
            new_root = self.visit(self.root, target_vector)
            enumerator = SolutionsEnumerator(new_root, self.writer, self.config)
            _, _ = enumerator.run()

        return num_class, num_solutions


def enumerate_solutions(root, writer, config):
    enumerator = VectorEnumeratorAll(root, writer, config)
    num_class, num_solutions = enumerator.run()
    writer.write('#--------------------\n#Total number of E-equivalence classes = {:d}\n'.format(num_class))
    print('Total number of E-equivalence class = {:d} among {:d} solutions'.format(num_class, num_solutions))

