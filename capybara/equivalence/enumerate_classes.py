from capybara.eucalypt.util import flatten, get_associations
from capybara.eucalypt.solution import Association, NestedSolution
from capybara.equivalence.equivalence_class import NestedClass


def fill_reachable_matrix(parasite_tree, host_tree, optimal_solutions):
    """
    Index all solutions for future access
    """
    reachable = [[set() for _ in range(host_tree.size())] for _ in range(parasite_tree.size())]

    for root in flatten(optimal_solutions):
        association = root.association
        reachable[association.parasite.index][association.host.index].add(root)

    def fill(p):
        if p.is_leaf():
            return

        p1, p2 = p.left_child, p.right_child

        for h_index in range(host_tree.size()):
            for node in reachable[p.index][h_index]:
                for left_child in flatten(node.children[0]):
                    reachable[p1.index][left_child.association.host.index].add(left_child)
                for right_child in flatten(node.children[1]):
                    reachable[p2.index][right_child.association.host.index].add(right_child)
        fill(p1)
        fill(p2)

    fill(parasite_tree.root)
    return reachable


def fill_class_matrix(parasite_tree, host_tree, leaf_map, reachable_matrix, task):
    """
    Build the class enumeration graph by merging
    """
    class_matrix = [[NestedClass.empty_class() for _ in range(host_tree.size())] for _ in range(parasite_tree.size())]
    for p in parasite_tree:
        if p.is_leaf():
            class_matrix[p.index][leaf_map[p].index] = NestedClass.class_from_leaf(p, leaf_map[p])

        else:
            p1, p2 = p.left_child, p.right_child

            for h in host_tree:
                for node in reachable_matrix[p.index][h.index]:

                    left_sum = NestedClass.empty_class()
                    for left_association in get_associations(node.children[0]):
                        left_sum = NestedClass.merge(left_sum, class_matrix[p1.index][left_association.host.index])

                    right_sum = NestedClass.empty_class()
                    for right_association in get_associations(node.children[1]):
                        right_sum = NestedClass.merge(right_sum, class_matrix[p2.index][right_association.host.index])

                    # relabel the association and the event according to the equivalence relation
                    if task == 2:
                        sub_sol = get_sub_solution_event_partition(left_sum, right_sum, node, p)
                    else:  # task 3
                        sub_sol = get_sub_solution_strong(left_sum, right_sum, node, p)

                    class_matrix[p.index][h.index] = NestedClass.merge(class_matrix[p.index][h.index], sub_sol)

    root_sol = NestedClass.empty_class()
    for h in host_tree:
        root_sol = NestedClass.merge(root_sol, class_matrix[parasite_tree.root.index][h.index])
    return root_sol


def get_sub_solution_strong(left_sum, right_sum, node, parasite):
    """
    Add the signature to a new class according the strong equivalence relation
    """
    if node.event == NestedSolution.HOST_SWITCH:
        return NestedClass.cartesian(left_sum, right_sum,
                                     Association(parasite, NestedClass.SWITCH_NODE), node.event)
    return NestedClass.cartesian(left_sum, right_sum,
                                 Association(parasite, node.association.host), node.event)


def get_sub_solution_event_partition(left_sum, right_sum, node, parasite):
    """
    Add the signature to a new class according the event partition equivalence relation
    """
    return NestedClass.cartesian(left_sum, right_sum,
                                 Association(parasite, NestedClass.GENERAL_NODE), node.event)

