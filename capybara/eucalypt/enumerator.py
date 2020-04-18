from capybara.eucalypt.solution import NestedSolution
from capybara.eucalypt import cyclicity


class SolutionIterator:
    def __init__(self, root, get_cost=False):
        self.stack = [root]
        self.get_cost = get_cost
        self.final_cost = None

    def done(self):
        return not self.stack

    def get_next(self):
        if self.get_cost and self.final_cost is None:
            if self.stack[-1].composition_type != NestedSolution.MULTIPLE:
                self.final_cost = self.stack[-1].cost
        self.move_to_next()
        if self.done():
            return None
        return self.stack[-1]

    def get_child(self, index):
        child = self.stack[-1].children[index]
        self.stack.append(child)
        return child

    def move_to_next(self):
        starting_cell = self.stack[-1]
        if starting_cell.composition_type != NestedSolution.FINAL:
            # just move left down
            self.stack.append(starting_cell.children[0])
            return

        # turning back up, try to find my parent
        current_cell = self.stack.pop()
        found = False
        while self.stack:
            previous_cell = self.stack[-1]
            if previous_cell.composition_type == NestedSolution.SIMPLE and current_cell == previous_cell.children[0]:
                found = True
                break
            current_cell = self.stack.pop()
        if found:  # add my sibling
            self.stack.append(self.stack[-1].children[1])


class SolutionsEnumerator:
    def __init__(self, data, root, writer, maximum, acyclic):
        self.data = data
        self.root = root
        self.merge_stack = []
        self.current_index = 0
        self.writer = writer
        self.maximum = maximum
        self.acyclic_only = acyclic

        self.current_mapping = {}
        self.current_text = []  # text for the printing the current solution
        self.transfer_candidates = []

    def write_task_title(self, task):
        if task == 0:
            self.writer.write(f'#Task {task+1}: Enumerate {"acyclic " if self.acyclic_only else ""}solutions '
                              f'{"(cyclic or acyclic)" if not self.acyclic_only else ""}\n')
        elif task == 1:
            self.writer.write(f'#Task {task+1}: Enumerate one solution per event vector\n')
        elif task == 2:
            self.writer.write(f'#Task {task+1}: Enumerate one solution per event partition\n')
        else:
            self.writer.write(f'#Task {task+1}: Enumerate one solution per strong equivalence class\n')

    def write_header(self, opt_cost, task, cost_vector):
        self.writer.write('#--------------------\n')
        self.writer.write('#Host tree          = {}\n'.format(self.data.host_tree))
        self.writer.write('#Symbiont tree      = {}\n'.format(self.data.parasite_tree))
        self.writer.write('#Host tree size     = {}\n'.format(self.data.host_tree.size()))
        self.writer.write('#Symbiont tree size = {}\n'.format(self.data.parasite_tree.size()))
        self.writer.write('#Leaf mapping       = {{{}}}\n'.format(', '.join(map(lambda x: str(x[0]) + '=' + str(x[1]),
                                                                                self.data.leaf_map.items()))))
        self.writer.write('#--------------------\n')
        self.write_task_title(task)
        self.writer.write('#Co-speciation cost = {}\n'.format(cost_vector[0]))
        self.writer.write('#Duplication cost   = {}\n'.format(cost_vector[1]))
        self.writer.write('#Host-switch cost   = {}\n'.format(cost_vector[2]))
        self.writer.write('#Loss cost          = {}\n'.format(cost_vector[3]))
        self.writer.write('#Optimal cost       = {}\n'.format(opt_cost))
        self.writer.write('#--------------------\n')

    def run(self, label=''):
        num_solutions = 0
        num_acyclic = 0

        while True:
            if num_solutions >= self.maximum:
                break
            # reinitialize information related to the current solution
            self.current_mapping = {}
            self.current_text = []
            self.transfer_candidates = []

            # build the next solution
            num_solutions += 1
            current_cell = self.root
            iterator = SolutionIterator(self.root)
            while not iterator.done():
                current_cell = self.get_next(current_cell, iterator)
            self.clean_stack()

            # is the current solution acyclic?
            is_acyclic = False
            if self.acyclic_only:
                transfer_edges = cyclicity.find_transfer_edges(self.data.host_tree,
                                                               self.current_mapping, self.transfer_candidates)
                if not transfer_edges:
                    is_acyclic = True
                else:
                    is_acyclic = cyclicity.is_acyclic_stolzer(self.current_mapping, transfer_edges)

            # write the solution only if it is acyclic, or if the user wants both
            if not self.acyclic_only or is_acyclic:
                num_acyclic += 1
                self.writer.write(', '.join(self.current_text))
                self.writer.write(f'\n[{str(num_acyclic) if not label else label}]\n')

            if not self.merge_stack:
                break
            if num_acyclic >= self.maximum:
                break
        return num_solutions, num_acyclic

    def process_event_cell(self, current_cell):
        if current_cell.event == NestedSolution.HOST_SWITCH:
            self.transfer_candidates.append(current_cell.association.parasite)
        # write the actual mapping
        self.current_text.append(str(current_cell))
        self.current_mapping[current_cell.association.parasite] = current_cell.association.host

    def get_next(self, current_cell, iterator):
        if current_cell.composition_type == NestedSolution.MULTIPLE:
            next_cell = self.next_merged_solution(current_cell, iterator)
            self.current_index += 1
        else:
            self.process_event_cell(current_cell)

            next_cell = iterator.get_next()

        return next_cell

    def clean_stack(self):
        self.current_index = 0
        stop = False
        while self.merge_stack and not stop:
            num_children, index = self.merge_stack[-1]
            if index == num_children:  # remove the sentinels
                self.merge_stack.pop()
            else:
                stop = True

    def next_merged_solution(self, current_cell, iterator):
        if self.current_index >= len(self.merge_stack):
            # create a new branch, add a new entry to the stack
            self.merge_stack.append((len(current_cell.children)-1, 0))
            return iterator.get_child(0)
        elif self.current_index == len(self.merge_stack) - 1:
            # move to a new child, update the stack
            next_child_index = self.merge_stack[self.current_index][1] + 1
            self.merge_stack[self.current_index] = (self.merge_stack[self.current_index][0], next_child_index)
            return iterator.get_child(next_child_index)
        else:
            # stay on the same child
            child_index = self.merge_stack[self.current_index][1]
            return iterator.get_child(child_index)

    def visit_vector(self, solution, target_vector):
        """
        Recursive function in Event Vector Enumeration loop for extracting one solution
        """
        if solution.composition_type == NestedSolution.MULTIPLE:
            for child in solution.children:
                if target_vector in child.event_vectors:
                    self.visit_vector(child, target_vector)
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
                        self.visit_vector(solution.children[0], left_vector)
                        self.visit_vector(solution.children[1], right_vector)
                        return

