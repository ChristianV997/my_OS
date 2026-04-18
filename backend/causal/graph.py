class CausalGraph:

    def __init__(self):
        self.edges = {}

    def add_edge(self, parent, child, weight):
        self.edges[(parent, child)] = weight

    def children(self, node):
        return [c for (p, c) in self.edges if p == node]

    def parents(self, node):
        return [p for (p, c) in self.edges if c == node]

    def get_weight(self, parent, child, default=0.0):
        return self.edges.get((parent, child), default)
