import collections
from capybara.eucalypt import util


def find_transfer_edges(host_tree, mapping, transfer_candidates):
    """
    Find the set of transfer edges in the solution defined by the mapping
    knowing that a host-switch happens at p for p in transfer candidates
    """
    pairs = collections.defaultdict(list)
    for p in transfer_candidates:
        h = mapping[p]
        p1, p2 = p.left_child, p.right_child
        h1, h2 = mapping[p1], mapping[p2]

        if h != h1:
            pairs[h].append((h1, (p, p1)))
            pairs[h1].append((h, (p, p1)))
        if h != h2:
            pairs[h].append((h2, (p, p2)))
            pairs[h2].append((h, (p, p2)))

    return util.tarjan_offline_lca_transfer_edges(host_tree, dict(pairs))


def is_acyclic_stolzer(mapping, transfer_edges):
    """
    Return true if the Stolzer temporal constraint graph is acyclic
    """
    # initialize
    graph = {}
    for g, h in transfer_edges:
        d, r = mapping[g], mapping[h]
        graph[d] = set()
        graph[r] = set()
        graph[d.parent] = {d}
        graph[r.parent] = {r}

    # condition 1
    for node in graph:
        descendants = node.get_proper_descendants()
        for d in descendants:
            if d in graph:
                graph[node].add(d)

    for g, h in transfer_edges:
        for gp, hp in transfer_edges:
            if g == gp:  # condition 3
                d, r = mapping[g], mapping[h]
                graph[d.parent].add(r)
                graph[r.parent].add(d)

            elif g.is_ancestor_of(gp):  # condition 2
                d, r, dp, rp = mapping[g], mapping[h], mapping[gp], mapping[hp]
                graph[d.parent].add(dp)
                graph[d.parent].add(rp)
                graph[r.parent].add(dp)
                graph[r.parent].add(rp)

    return not util.is_cyclic(graph)

