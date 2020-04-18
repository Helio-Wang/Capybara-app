from capybara.eucalypt.util import flatten, full_flatten
from capybara.eucalypt.tree import TreeNode
from capybara.eucalypt.solution import Association, NestedSolution


class NestedClass(NestedSolution):
    GENERAL_NODE = TreeNode('GENERAL')
    SWITCH_NODE = TreeNode('SWITCH')

    def __init__(self, association, composition_type, event, children):
        super().__init__(0, association, composition_type, event, True, children)

    def __str__(self):
        return '(' + str(self.event) + '|' + str(self.association) + ')'

    @staticmethod
    def empty_class():
        return NestedClass(None, NestedSolution.FINAL, NestedSolution.LEAF, [])

    @staticmethod
    def class_from_leaf(parasite, host):
        return NestedClass(Association(parasite, host), NestedSolution.FINAL, NestedSolution.LEAF, [])

    @staticmethod
    def is_empty(solution):
        return solution.composition_type == NestedSolution.FINAL and solution.association is None

    @staticmethod
    def cartesian(first, second, association, event):
        if NestedClass.is_empty(first) or NestedClass.is_empty(second):
            return NestedClass.empty_class()
        return NestedClass(association, NestedSolution.SIMPLE, event, [first, second])

    @staticmethod
    def merge(first, second):
        if NestedClass.is_empty(second):
            return first
        if NestedClass.is_empty(first):
            return second

        children = set()
        for solution in [first, second]:
            for child in full_flatten(solution):
                child_wrapped = NestedClassWrapper(child)
                children.add(child_wrapped)

        NestedClassWrapper.reduce(children)

        for a in children:
            for b in children:
                if a < b or a == b:
                    continue
        return NestedClassWrapper.unwrap(children)


class NestedClassWrapper:
    """
    the wrapper class is used to get a custom hashing and comparison of AND gates under equivalence (SIMPLE type)
    """
    def __init__(self, solution):
        self.solution = solution
        self._hash = None
        self._left = None
        self._right = None
        self._full_left = None
        self._full_right = None

    def __eq__(self, other):
        if self.solution.composition_type == NestedSolution.MULTIPLE or other.solution.composition_type == NestedSolution.MULTIPLE:
            raise NotImplementedError
        if self.solution.association != other.solution.association or self.solution.event != other.solution.event:
            return False
        return hash(self) == hash(other)

    def __hash__(self):
        # not a perfect hash
        if self._hash is not None:
            return self._hash
        if self.solution.composition_type == NestedSolution.MULTIPLE:
            raise NotImplementedError
        h = hash(repr(self.solution.association) + repr(self.solution.event))
        if self.solution.children:
            for c in self.left():
                h ^= hash(c) >> 1
            for c in self.right():
                h ^= hash(c) << 1
        self._hash = h
        return h

    def __lt__(self, other):
        return hash(self) < hash(other)

    def left(self):
        if self._left is None:
            self._left = [NestedClassWrapper(c) for c in flatten(self.solution.children[0])]
            self._left.sort(key=lambda x: hash(x))
        return self._left

    def right(self):
        if self._right is None:
            self._right = [NestedClassWrapper(c) for c in flatten(self.solution.children[1])]
            self._right.sort(key=lambda x: hash(x))
        return self._right

    def full_left(self):
        if self._full_left is None:
            self._full_left = [NestedClassWrapper(c) for c in full_flatten(self.solution.children[0])]
            self._full_left.sort(key=lambda x: hash(x))
        return self._full_left

    def full_right(self):
        if self._full_right is None:
            self._full_right = [NestedClassWrapper(c) for c in full_flatten(self.solution.children[1])]
            self._full_right.sort(key=lambda x: hash(x))
        return self._full_right

    def full_children(self, j):
        if j == 0:
            return self.full_left()
        if j == 1:
            return self.full_right()
        raise NotImplementedError

    def less_than(self, other):
        if self.solution.composition_type == NestedSolution.MULTIPLE or other.solution.composition_type == NestedSolution.MULTIPLE:
            raise NotImplementedError
        if not self.solution.children or not other.solution.children:
            raise NotImplementedError
        if self.solution.association != other.solution.association or self.solution.event != other.solution.event:
            return False

        for j in range(2):
            this_left = self.full_children(j)
            that_left = other.full_children(j)
            inter, diff = NestedClassWrapper.inter_diff(this_left, that_left)
            if (not inter) or diff:
                return False
        return True

    def is_partner(self, other, simple=False):
        if self.solution.composition_type == NestedSolution.MULTIPLE or other.solution.composition_type == NestedSolution.MULTIPLE:
            raise NotImplementedError
        if not self.solution.children or not other.solution.children:
            raise NotImplementedError
        if self.solution.association != other.solution.association or self.solution.event != other.solution.event:
            return False, None

        this_left = self.left()
        that_left = other.left()
        this_right = self.right()
        that_right = other.right()

        if this_left == that_left:
            right_set = set(this_right)
            right_set.update(that_right)
            if simple:
                NestedClassWrapper.simple_reduce(right_set)
            else:
                NestedClassWrapper.reduce(right_set)
            right_baby = NestedClassWrapper.unwrap(right_set)
            baby = NestedClass(self.solution.association, self.solution.composition_type, self.solution.event,
                               [self.solution.children[0], right_baby])
            return True, NestedClassWrapper(baby)
        if this_right == that_right:
            left_set = set(this_left)
            left_set.update(that_left)
            if simple:
                NestedClassWrapper.simple_reduce(left_set)
            else:
                NestedClassWrapper.reduce(left_set)
            left_baby = NestedClassWrapper.unwrap(left_set)
            baby = NestedClass(self.solution.association, self.solution.composition_type, self.solution.event,
                               [left_baby, self.solution.children[1]])
            return True, NestedClassWrapper(baby)
        return False, None

    def is_friend(self, other):
        if self.solution.composition_type == NestedSolution.MULTIPLE or other.solution.composition_type == NestedSolution.MULTIPLE:
            raise NotImplementedError
        if not self.solution.children or not other.solution.children:
            raise NotImplementedError
        if self.solution.association != other.solution.association or self.solution.event != other.solution.event:
            return False, None, None, None

        this_left = self.full_left()
        that_left = other.full_left()
        this_right = self.full_right()
        that_right = other.full_right()

        left_intersect, left_diff = NestedClassWrapper.inter_diff(this_left, that_left)
        if left_intersect and not left_diff:
            right_intersect, right_diff = NestedClassWrapper.inter_diff(this_right, that_right)
            if right_intersect:
                right_baby = NestedClassWrapper.unwrap(right_diff)
                baby = NestedClass(self.solution.association, self.solution.composition_type, self.solution.event,
                                   [self.solution.children[0], right_baby])
                return True, NestedClassWrapper(baby), other, None
            return False, None, None, None

        right_intersect, right_diff = NestedClassWrapper.inter_diff(this_right, that_right)
        if right_intersect and not right_diff:
            if left_intersect:
                left_baby = NestedClassWrapper.unwrap(left_diff)
                baby = NestedClass(self.solution.association, self.solution.composition_type, self.solution.event,
                                   [left_baby, self.solution.children[1]])
                return True, NestedClassWrapper(baby), other, None
            return False, None, None, None

        left_intersect_rev, left_diff_rev = NestedClassWrapper.inter_diff(that_left, this_left)
        if left_intersect_rev and not left_diff_rev:
            right_intersect_rev, right_diff_rev = NestedClassWrapper.inter_diff(that_right, this_right)
            if right_intersect_rev:
                right_baby = NestedClassWrapper.unwrap(right_diff_rev)
                baby = NestedClass(self.solution.association, self.solution.composition_type, self.solution.event,
                                   [other.solution.children[0], right_baby])
                return True, self, NestedClassWrapper(baby), None
            return False, None, None, None

        right_intersect_rev, right_diff_rev = NestedClassWrapper.inter_diff(that_right, this_right)
        if right_intersect_rev and not right_diff_rev:
            if left_intersect_rev:
                left_baby = NestedClassWrapper.unwrap(left_diff_rev)
                baby = NestedClass(self.solution.association, self.solution.composition_type, self.solution.event,
                                   [left_baby, other.solution.children[1]])
                return True, self, NestedClassWrapper(baby), None
            return False, None, None, None

        if right_intersect and left_intersect:
            left_baby = NestedClassWrapper.unwrap(left_diff)
            first_baby = NestedClass(self.solution.association, self.solution.composition_type, self.solution.event,
                                     [left_baby, self.solution.children[1]])
            left_intersect = NestedClassWrapper.intersection(this_left, that_left)
            middle_left = NestedClassWrapper.unwrap(left_intersect)
            middle_right = NestedClassWrapper.unwrap(right_diff)
            second_baby = NestedClass(self.solution.association, self.solution.composition_type, self.solution.event,
                                      [middle_left, middle_right])
            return True, NestedClassWrapper(first_baby), NestedClassWrapper(second_baby), other
        return False, None, None, None

    @staticmethod
    def reduce(class_set):
        while True:
            to_remove = set()
            to_add = set()
            for a in class_set:
                to_break = False
                for b in class_set:
                    if a < b or a == b:
                        continue
                    is_partner, baby = a.is_partner(b)
                    if is_partner:
                        to_remove.add(a)
                        to_remove.add(b)
                        to_add.add(baby)
                        to_break = True
                        break
                    if a.less_than(b):
                        to_remove.add(a)
                    elif b.less_than(a):
                        to_remove.add(b)
                    else:
                        is_friend, first_baby, second_baby, third_baby = a.is_friend(b)
                        if is_friend:
                            to_remove.add(a)
                            to_remove.add(b)
                            to_add.add(first_baby)
                            to_add.add(second_baby)
                            if third_baby is not None:
                                to_add.add(third_baby)
                            to_break = True
                            break

                if to_break:
                    break
            for c in to_remove:
                class_set.remove(c)
            class_set.update(to_add)
            if not to_add:
                break

    @staticmethod
    def simple_reduce(class_set):
        while True:
            to_remove = set()
            to_add = set()
            for a in class_set:
                to_break = False
                for b in class_set:
                    if a < b or a == b:
                        continue
                    is_partner, baby = a.is_partner(b, simple=True)
                    if is_partner:
                        to_remove.add(a)
                        to_remove.add(b)
                        to_add.add(baby)
                        to_break = True
                        break
                if to_break:
                    break
            for c in to_remove:
                class_set.remove(c)
            class_set.update(to_add)
            if not to_add:
                break

    @staticmethod
    def inter_diff(this_set, that_set):
        inter = False
        diff_set = set()
        for this in this_set:
            current = {this}
            for that in that_set:
                intersect, diff_children = NestedClassWrapper.local_inter_diff(current, that)
                inter = inter or intersect
                current = diff_children
            diff_set.update(current)
        if diff_set:
            NestedClassWrapper.simple_reduce(diff_set)
        return inter, diff_set

    @staticmethod
    def local_inter_diff(this_set, that):
        if not this_set:
            return False, set()
        elif len(this_set) > 1:
            inter, diff_set = False, set()
            for this in this_set:
                intersect, diff = NestedClassWrapper.local_inter_diff({this}, that)
                inter = inter or intersect
                diff_set.update(diff)
            return inter, diff_set

        this = list(this_set)[0]
        if that.solution.event != this.solution.event or that.solution.association != this.solution.association:
            return False, {this}
        if not this.solution.children:
            return True, set()

        diff_set = set()
        this_left = this.full_left()
        this_right = this.full_right()
        that_left = that.full_left()
        that_right = that.full_right()

        left_inter, left_diff = NestedClassWrapper.inter_diff(this_left, that_left)
        right_inter, right_diff = NestedClassWrapper.inter_diff(this_right, that_right)
        if left_diff:
            diff_set.add(NestedClassWrapper(NestedClass(this.solution.association, NestedSolution.SIMPLE, this.solution.event,
                                                        [NestedClassWrapper.unwrap(left_diff),
                                                         this.solution.children[1]])))
        if right_diff:
            diff_set.add(NestedClassWrapper(NestedClass(this.solution.association, NestedSolution.SIMPLE, this.solution.event,
                                                        [this.solution.children[0],
                                                         NestedClassWrapper.unwrap(right_diff)])))
        return left_inter and right_inter, diff_set

    @staticmethod
    def intersection(this_set, that_set):
        inter_set = set()
        for this in this_set:
            for that in that_set:
                intersect = NestedClassWrapper.local_intersection(this, that)
                inter_set.update(intersect)
        if inter_set:
            NestedClassWrapper.simple_reduce(inter_set)
        return inter_set

    @staticmethod
    def local_intersection(this, that):
        if that.solution.event != this.solution.event or that.solution.association != this.solution.association:
            return set()
        if not this.solution.children:
            return {this}

        inter_set = set()
        this_left = this.full_left()
        this_right = this.full_right()
        that_left = that.full_left()
        that_right = that.full_right()

        left_inter = NestedClassWrapper.intersection(this_left, that_left)
        right_inter = NestedClassWrapper.intersection(this_right, that_right)
        if left_inter and right_inter:
            inter_set.add(NestedClassWrapper(NestedClass(this.solution.association, NestedSolution.SIMPLE, this.solution.event,
                                                         [NestedClassWrapper.unwrap(left_inter), NestedClassWrapper.unwrap(right_inter)])))
        return inter_set

    @staticmethod
    def unwrap(wrapped_nodes):
        nodes = [node.solution for node in wrapped_nodes]
        if len(nodes) == 1:
            return nodes[0]
        else:
            return NestedClass(None, NestedSolution.MULTIPLE, None, nodes)


