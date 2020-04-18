from capybara.eucalypt.tree import TreeNode
from capybara.eucalypt.util import full_flatten
from capybara.eucalypt.solution import NestedSolution


def get_grandchildren(node, position):
    if position == 0:
        if node.left_grandchildren is None:
            node.left_grandchildren = set(full_flatten(node.children[0]))
        return node.left_grandchildren
    else:
        if node.right_grandchildren is None:
            node.right_grandchildren = set(full_flatten(node.children[1]))
        return node.right_grandchildren


def root_update(current, base_nodes, position):
    new_nodes = set()
    for node in base_nodes:
        to_add = False
        if position == 0:
            for left_node in current.left_child.nodes:
                if left_node in get_grandchildren(node, 0):
                    to_add = True
                    break
        else:
            for right_node in current.right_child.nodes:
                if right_node in get_grandchildren(node, 1):
                    to_add = True
                    break
        if to_add:
            new_nodes.add(node)
    current.nodes = new_nodes


def signature_update_event_partition(table, node):
    signature = (node.event, node.association.host if node.event == NestedSolution.LEAF else None)
    if signature not in table:
        table[signature] = {node}
    else:
        table[signature].add(node)


def signature_update_strong_class(table, node):
    signature = (node.event, None if node.event == NestedSolution.HOST_SWITCH else node.association.host)
    if signature not in table:
        table[signature] = {node}
    else:
        table[signature].add(node)


class EnumTreeNode(TreeNode):
    def __init__(self, key, label):
        super().__init__(key)
        self.label = label
        self.signature = None
        self.nodes = set()

    def mark(self, signature, nodes):
        self.signature = signature
        self.nodes = nodes


class EnumTree:
    def __init__(self, parasite_tree):
        self.tree = {p: EnumTreeNode(p.key, p.label) for p in parasite_tree}
        for p in parasite_tree:
            if not p.is_leaf():
                self.tree[p].add_child(self.tree[p.left_child])
                self.tree[p].add_child(self.tree[p.right_child])

    def traverse(self):
        mapping, events = {}, {}
        for p, ep in self.tree.items():
            event, host = ep.signature
            mapping[p] = host
            events[p] = event
        return mapping, events


class ClassEnumerator:
    def __init__(self, parasite_tree, optimal_solutions, task):
        self.enum_tree = EnumTree(parasite_tree)
        self.root = self.enum_tree.tree[parasite_tree.root]
        self.optimal_solutions = optimal_solutions
        if task == 2:
            self.signature_update = signature_update_event_partition
        else:
            self.signature_update = signature_update_strong_class

    def run(self):
        root_nodes = {}
        for node in full_flatten(self.optimal_solutions):
            self.signature_update(root_nodes, node)

        for signature, nodes in root_nodes.items():
            self.root.mark(signature, nodes)

            for c in self.f(self.root):
                yield self.enum_tree.traverse()

    def f(self, current):
        if current.is_leaf():
            yield current
            return

        base_nodes = current.nodes.copy()

        for left_signature, left_nodes in self.f_side(current, 0):
            current.left_child.mark(left_signature, left_nodes)

            for left in self.f(current.left_child):
                root_update(current, base_nodes, 0)

                second_base_nodes = current.nodes.copy()
                for right_signature, right_nodes in self.f_side(current, 1):
                    current.right_child.mark(right_signature, right_nodes)

                    for right in self.f(current.right_child):
                        root_update(current, second_base_nodes, 1)
                        yield current

    def f_side(self, current, position):
        all_nodes = {}
        for parent_node in current.nodes:
            for node in get_grandchildren(parent_node, position):
                self.signature_update(all_nodes, node)
        return all_nodes.items()


