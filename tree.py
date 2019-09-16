class TreeNode:
    """
    Node in a rooted ordered full binary tree
    """
    def __init__(self, key):
        self.parent = None
        self.left_child = None
        self.right_child = None
        self.key = key
        self.label = str(key)
        self.index = -1
        self.internal_index = -1

    def __repr__(self):
        return self.label

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.label == other.label
        return False

    def __hash__(self):
        return hash(repr(self))

    def add_child(self, child):
        if not self.has_left_child():
            self.left_child = child
        else:
            self.right_child = child

        child.parent = self

    def has_left_child(self):
        return self.left_child is not None

    def has_right_child(self):
        return self.right_child is not None

    def is_root(self):
        return self.parent is None

    def is_leaf(self):
        return self.left_child is None and self.right_child is None

    def get_sibling(self):
        if self.is_root():
            return None
        if self == self.parent.left_child:
            return self.parent.right_child
        return self.parent.left_child

    def set_label(self, label):
        self.label = label

    def is_ancestor_of(self, node):
        """Am I an ancestor of (or equal to) that node?"""
        current_node = node
        while current_node is not None:
            if current_node.label == self.label:
                return True
            current_node = current_node.parent
        return False

    def get_proper_descendants(self):
        """get all nodes in the subtree NOT INCLUDING MYSELF
        used for the construction of Stolzer temporal constraint graph"""
        if self.is_leaf():
            return []
        return [self.left_child, self.right_child] +\
                self.left_child.get_proper_descendants() + self.right_child.get_proper_descendants()

    def get_proper_ancestors(self):
        """get all ancestors NOT INCLUDING MYSELF
        used for the construction of Stolzer temporal constraint graph"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors


class Tree:
    """
    Rooted ordered full binary tree
    """
    def __init__(self, key):
        self.nodes = []
        self.root = TreeNode(key)

    def __iter__(self):
        for u in self.nodes:
            yield u

    def __repr__(self):
        return self.post_order_string(self.root)

    @staticmethod
    def from_newick_string(newick):
        # No longer supported
        raise NotImplementedError

    def size(self):
        if not self.nodes:
            self.linearize()
        return len(self.nodes)

    def get_root(self):
        return self.root

    def linearize_(self, node):
        if node.is_leaf():
            self.nodes.append(node)
        else:
            if node.has_left_child():
                self.linearize_(node.left_child)
            if node.has_right_child():
                self.linearize_(node.right_child)
            self.nodes.append(node)

    def linearize(self):
        self.linearize_(self.root)
        j = 0
        for index, node in enumerate(self):
            if not node.is_leaf():
                node.internal_index = j
                j += 1
            node.index = index

    def post_order_string(self, node):
        if node.is_leaf():
            return repr(node)
        left_string, right_string = '', ''
        if node.has_left_child():
            left_string = self.post_order_string(node.left_child)
        if node.has_right_child():
            right_string = self.post_order_string(node.right_child)
        return '(' + ','.join([left_string, right_string]) + ')' + repr(node)

    def is_full(self):
        # for the problem we assume that all trees are full (all internal nodes have out-degree 2)
        for node in self:
            if not node.is_leaf():
                if not node.has_left_child() or not node.has_right_child():
                    return False
        return True

