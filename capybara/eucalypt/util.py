from capybara.eucalypt.solution import NestedSolution


class UF:
    """
    Weighted quick-union UF with path compression by halving
    amortized constant time for both union and find
    """
    def __init__(self, n):
        self._parent = list(range(n))
        self._size = [1] * n
        self._count = n

    def count(self):
        return self._count

    def find(self, p):
        while p != self._parent[p]:
            self._parent[p] = self._parent[self._parent[p]]
            p = self._parent[p]
        return p

    def union(self, p, q):
        root_p = self.find(p)
        root_q = self.find(q)
        if root_p == root_q:
            return
        if self._size[root_p] < self._size[root_q]:
            self._parent[root_p] = root_q
            self._size[root_q] += self._size[root_p]
        else:
            self._parent[root_q] = root_p
            self._size[root_p] += self._size[root_q]
        self._count -= 1


def tarjan_offline_lca(tree, pairs, subroutine):
    """
    Find lowest common ancestor and do some additional processing
    based on Tarjan's offline lowest common ancestor algorithm
    """
    list_tree = [u for u in tree]
    n = len(list_tree)
    uf = UF(n)
    colored = {u: False for u in tree}
    ancestor = {}

    def lca_subroutine(u):
        ancestor[u] = u
        if not u.is_leaf():
            for v in [u.left_child, u.right_child]:
                lca_subroutine(v)
                uf.union(u.index, v.index)
                ancestor[uf.find(u.index)] = u
        colored[u] = True
        if u in pairs:
            for v, e in pairs[u]:
                if colored[v]:
                    lca = ancestor[uf.find(v.index)]
                    if lca != u and lca != v:
                        subroutine(e)
    lca_subroutine(tree.root)


def tarjan_offline_lca_transfer_edges(host_tree, pairs):
    """
    Return the set of transfer edges
    """
    transfer_edges = set()

    def subroutine(edge):
        transfer_edges.add(edge)

    tarjan_offline_lca(host_tree, pairs, subroutine)
    return transfer_edges


def tarjan_offline_lca_transfer_vertices(host_tree, parasite_tree, pairs):
    """
    Return the vector representing transfer-vertices membership
    """
    transfer_vertices = [False] * parasite_tree.size()

    def subroutine(vertex):
        transfer_vertices[vertex] = True

    tarjan_offline_lca(host_tree, pairs, subroutine)
    return transfer_vertices


def tarjan_offline_lca_transfer_stairs(host_tree, pairs):
    """
    Return the set of transfer edges
    """
    stairs = {}

    def subroutine(edge):
        stairs[edge[0]] = edge[1]

    tarjan_offline_lca(host_tree, pairs, subroutine)
    return stairs


def find_lca(root, n1, n2):
    """
    Return the least common ancestor of nodes n1 and n2 in a binary tree defined by root
    """
    if root is None:
        return None
    if root == n1 or root == n2:
        return root

    left_lca = find_lca(root.left_child, n1, n2)
    right_lca = find_lca(root.right_child, n1, n2)

    if left_lca and right_lca:
        return root

    return left_lca if left_lca is not None else right_lca


def is_cyclic(graph):
    """
    Return true if the input digraph contains a cycle
    adapted from Tarjan's strongly connected component algorithm
    """
    counter = 0
    exited = {node: False for node in graph}
    index = {}

    stack = [(node, False) for node in graph]
    while stack:
        current, entered = stack.pop()
        if not entered:
            if current not in index:
                index[current] = counter
                counter += 1
                stack.append((current, True))
                stack.extend((child, False) for child in graph[current] if not exited[child])
        else:
            for child in graph[current]:
                if not exited[child]:
                    if index[child] <= index[current]:
                        return True

            exited[current] = True
    return False


def get_associations(node):
    """
    Generate the set of associations from the children of an OR node
    """
    if node.composition_type != NestedSolution.MULTIPLE:
        yield node.association
    else:
        asso_set = set(child.association for child in node.children)
        for association in asso_set:
            yield association


def full_flatten(node):
    """
    Generate all children of an OR node
    """
    if node.composition_type != NestedSolution.MULTIPLE:
        yield node
    else:
        for child in node.children:
            yield child


def flatten(node):
    """
    Generate all children of an OR node except the leaves
    """
    if node.composition_type == NestedSolution.SIMPLE:
        yield node
    else:
        for child in node.children:
            yield child

