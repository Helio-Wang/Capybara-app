from capybara.eucalypt.tree import TreeNode, Tree

_OPEN_BRACKET = '('
_CLOSED_BRACKET = ')'
_CHILD_SEPARATOR = ','


def tree_from_newick(newick, label_prefix):
    key, cursor, brackets = 0, 0, 0
    tree = Tree(key)
    root = tree.root
    root.set_label(label_prefix + str(key))
    key += 1
    current_node = root

    while cursor < len(newick):
        character = newick[cursor]
        if character == _OPEN_BRACKET:
            new_node = TreeNode(key)
            new_node.set_label(label_prefix + str(key))
            current_node.add_child(new_node)
            current_node = new_node
            key += 1
            cursor += 1
            brackets += 1
        elif character == _CHILD_SEPARATOR:
            new_node = TreeNode(key)
            new_node.set_label(label_prefix + str(key))
            if current_node.parent.has_left_child() and current_node.parent.has_right_child():
                raise NexusFileParserException('A non-leaf tree node must have exactly two children.')
            current_node.parent.add_child(new_node)
            current_node = new_node
            key += 1
            cursor += 1
        elif character == _CLOSED_BRACKET:
            current_node = current_node.parent
            cursor += 1
            brackets -= 1
            if brackets < 0:
                return None
        else:
            label = [character]
            cursor += 1
            while cursor < len(newick) and newick[cursor] not in (_CHILD_SEPARATOR, _CLOSED_BRACKET):
                label.append(newick[cursor])
                cursor += 1
            label = ''.join(label).strip()
            current_node.set_label(label)

    # construct the post-order
    tree.linearize()
    return tree


class NexusFileParserException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class NexusParser:
    def __init__(self, file):
        self.reader = file
        self.host_tree = None
        self.parasite_tree = None
        self.leaf_map = {}

    @staticmethod
    def is_comment_line(line):
        return line[0] == '[' or line[0] == '#'

    def read(self):
        line = self.reader.readline()
        while line:
            # remove leading and trailing whitespaces, compress inner whitespaces
            line = ''.join(line.strip()).lower()
            # catch valid file starting line
            if 'begin parasite' in line or 'begin host' in line or 'begin symbiont' in line:
                self.parse_standard_nexus(line)
                break
            elif 'begin trees' in line:
                raise NexusFileParserException('This file format is not supported.')
            # skip invalid and empty lines
            line = self.reader.readline()
        if not self.host_tree:
            raise NexusFileParserException('Could not read host tree from Nexux file.')
        if not self.parasite_tree:
            raise NexusFileParserException('Could not read symbiont tree from Nexux file.')
        if not self.leaf_map:
            raise NexusFileParserException('Unexpected end of file while searching for DISTRIBUTION section.')

    def parse_standard_nexus(self, first_line):
        # first construct the two trees
        string_host_tree, string_parasite_tree = self.read_trees(first_line)
        if not string_host_tree:
            raise NexusFileParserException('Could not read host tree from Nexus file.')
        if not string_parasite_tree:
            raise NexusFileParserException('Could not read symbiont tree from Nexus file.')
        distribution = self.read_distribution()
        if not distribution:
            raise NexusFileParserException('Unexpected end of file while searching for DISTRIBUTION section.')

        self.host_tree = tree_from_newick(string_host_tree, '!H')
        if not self.host_tree:
            raise NexusFileParserException('\n'.join(['Malformed tree string', string_host_tree, '']))
        self.parasite_tree = tree_from_newick(string_parasite_tree, '!P')
        if not self.parasite_tree:
            raise NexusFileParserException('\n'.join(['Malformed tree string', string_parasite_tree, '']))
        if not self.host_tree.is_full():
            raise NexusFileParserException('Host tree is not full')
        if not self.parasite_tree.is_full():
            raise NexusFileParserException('Symbiont tree is not full')

        # then construct the leaf map
        leaf_label_map = {}
        distribution = distribution.replace(';', '').strip().split(',')
        for string_pair in distribution:
            parasite_label, host_label = string_pair.split(':')
            parasite_label = parasite_label.strip()
            host_label = host_label.strip()

            if parasite_label in leaf_label_map:
                if leaf_label_map[parasite_label] != host_label:
                    raise NexusFileParserException('A symbiont label cannot be associated to two different host labels.')
            leaf_label_map[parasite_label] = host_label
        return_code = self.build_leaf_map(leaf_label_map)
        if return_code == 1:
            raise NexusFileParserException('The distribution is not leaf-to-leaf.')
        elif return_code == 2:
            raise NexusFileParserException('Not every leaf node in symbiont tree is mapped.')

    def read_trees(self, first_line):
        string_host_tree, string_parasite_tree = '', ''
        if 'begin parasite' in first_line or 'begin symbiont' in first_line:
            # read parasite first
            string_parasite_tree = self.read_tree_string()
            line = self.reader.readline()
            while line:
                line = ''.join(line.strip())
                if 'begin host' in line.lower():
                    string_host_tree = self.read_tree_string()
                    break
                line = self.reader.readline()
        else:
            # read host first
            string_host_tree = self.read_tree_string()
            line = self.reader.readline()
            while line:
                line = ''.join(line.strip()).lower()
                if 'begin parasite' in line or 'begin symbiont' in line:
                    string_parasite_tree = self.read_tree_string()
                    break
                line = self.reader.readline()
        return string_host_tree, string_parasite_tree

    def read_tree_string(self):
        try:
            line = self.reader.readline()
            while line:
                line = line.rstrip()
                if not NexusParser.is_comment_line(line) and '=' in line:  # found the tree string
                    break
                line = self.reader.readline()
            if not line:
                return ''
            line = ''.join(line.strip())
            tree_string = line.split('=')[1]
            return tree_string.replace(';', '').replace(' ', '')
        except (ValueError, IndexError):
            return ''

    def read_distribution(self):
        line = self.reader.readline()
        while line:
            line = ''.join(line.strip()).lower()
            if 'range' in line:
                break
            line = self.reader.readline()
        if not line:
            return ''
        distribution = ''
        line = self.reader.readline()
        while line:
            line = ''.join(line.strip())
            if 'end;' in line.lower() or 'endblock;' in line.lower():
                break
            if NexusParser.is_comment_line(line):
                continue
            distribution += line
            line = self.reader.readline()
        if not line:
            return ''
        return distribution

    def build_leaf_map(self, leaf_label_map):
        host_label_map = {}
        for host_node in self.host_tree:
            if host_node.is_leaf():
                host_label_map[host_node.label] = host_node
        for parasite_node in self.parasite_tree:
            if parasite_node.is_leaf():
                try:
                    host_label = leaf_label_map[parasite_node.label]
                except KeyError:
                    return 2
                try:
                    self.leaf_map[parasite_node] = host_label_map[host_label]
                except KeyError:
                    return 1
        return 0


