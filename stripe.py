from eheap import EHeap
from random import random


class TriData:
    def __init__(self, t):
        self.t = t
        self.used = False
        self.neighbors = t.neighbors()
        self.pos = None

    def destroy(self):
        self.neighbors = None

    def triangle(self):
        return self.t

    def num_unused_neighbors2(self, map):
        h = self.unused_neighbors2(map)
        n = len(h)
        return n

    def unused_neighbors2(self, map):
        h = {}
        for t2 in self.neighbors:
            td2 = map.lookup(t2)
            if not td2.used:
                h[t2] = td2
                for t3 in td2.neighbors:
                    td3 = map.lookup(t3)
                    if td3 != self and not td3.used:
                        h[t3] = td3
        return h


class Map:
    def __init__(self, s):
        self.ht = dict()
        for t in s.faces():
            self.ht[t] = TriData(t)

    def destroy(self):
        self.ht = None

    def lookup(self, t):
        if t in self.ht:
            return self.ht[t]
        else:
            raise KeyError(f"Key {t} not found in the map.")

 
class Surface:
    def __init__(self, faces):
        self._faces = faces
        for face in self._faces:
            if len(face.neighbors()) == 0:
                face.add_neighbors(self.neighbors(face))
    
    def faces(self):
        return self._faces

    def compute_neighbors(self):
        for t1 in self._faces:
            for t2 in self._faces:
                if t1 != t2 and self._shares_edge(t1, t2):
                    t1.add_neighbor(t2)

    def neighbors(self, t):
        neighbors = []
        for f in self._faces:
            if f != t and self._shares_edge(t, f):
                neighbors.append(f)
        return neighbors

    def _shares_edge(self, t1, t2):
        vertices1 = set(t1.vertices())
        vertices2 = set(t2.vertices())
        return len(vertices1.intersection(vertices2)) == 2

class Triangle:
    def __init__(self, v1, v2, v3, neighbors = []):
        self._vertices = (v1, v2, v3)
        self._neighbors = neighbors

    def vertices(self):
        return self._vertices

    def neighbors(self):
        return self._neighbors

    # add neighbors to the triangle
    def add_neighbors(self, neighbors):
        self._neighbors.extend(neighbors)

    def add_neighbor(self, neighbor):
        self._neighbors.append(neighbor)
    
    def __lt__(self, other):
        return (self.vertices()) < (other.vertices())

def triangle_priority(item, data):
    t = item
    map = data
    assert t is not None
    assert map is not None
    td = map.lookup(t)
    assert td is not None
    k = td.num_unused_neighbors2(map)
    return k

class Heap:
    def __init__(self, s):
        self.map = Map(s)
        self.heap = EHeap(triangle_priority, self.map)
        for t, td in self.map.ht.items():
            self.insert_entry_into_heap(t, td)

    def is_empty(self):
        return len(self.heap) == 0

    def top(self):
        return self.heap.top()

    def remove(self, t):
        td = self.map.lookup(t)
        td.used = True
        self.heap.remove(td.pos)
        h = self.tri_data_unused_neighbors2(td)
        for t2 in h:
            self.decrease_key(t2)

    def insert_entry_into_heap(self, key, value):
        t = key
        td = value

        assert not td.pos
        td.pos = self.heap.insert(t)
        assert td.pos

    def decrease_key(self, t):
        td = self.map.lookup(t)
        k = len(self.tri_data_unused_neighbors2(td))
        if k < td.pos.key:
            self.heap.remove(td.pos)
            td.pos = self.heap.insert(t)

    def tri_data_unused_neighbors2(self, td):
        h = set()
        for t2 in td.neighbors:
            td2 = self.map.lookup(t2)
            if not td2.used:
                h.add(t2)
                for t3 in td2.neighbors:
                    td3 = self.map.lookup(t3)
                    if td3 != td and not td3.used:
                        h.add(t3)
        return h

def vertices_are_unique(v1, v2, v3):
    """
    Check if three vertices are unique.

    Args:
        v1, v2, v3: Vertices to check.

    Returns:
        bool: True if all vertices are unique, False otherwise.
    """
    return v1 != v2 and v1 != v3 and v2 != v3


def vertex_is_one_of(v, v1, v2, v3):
    """
    Check if a vertex is one of the given three vertices.

    Args:
        v: Vertex to check.
        v1, v2, v3: Vertices to compare against.

    Returns:
        bool: True if v is one of v1, v2, or v3, False otherwise.
    """
    return v == v1 or v == v2 or v == v3


def num_shared_vertices(u1, u2, u3, v1, v2, v3):
    """
    Count the number of shared vertices between two sets of vertices.

    Args:
        u1, u2, u3: First set of vertices.
        v1, v2, v3: Second set of vertices.

    Returns:
        int: Number of shared vertices.
    """
    n = 0
    if vertex_is_one_of(v1, u1, u2, u3):
        n += 1
    if vertex_is_one_of(v2, u1, u2, u3):
        n += 1
    if vertex_is_one_of(v3, u1, u2, u3):
        n += 1
    return n


def vertices_match(v1, v2, v3, v4, v5, v6):
    """
    Check if two sets of vertices match, considering rotations.

    Args:
        v1, v2, v3: First set of vertices.
        v4, v5, v6: Second set of vertices.

    Returns:
        bool: True if the vertices match, False otherwise.
    """
    for _ in range(2):
        if (not v1 or v1 == v4) and (not v2 or v2 == v5) and (not v3 or v3 == v6):
            return True
        v4, v5, v6 = v5, v6, v4
    return (not v1 or v1 == v4) and (not v2 or v2 == v5) and (not v3 or v3 == v6)


def non_shared_vertex1(u1, u2, u3, v1, v2, v3):
    """
    Find a vertex from the first set that is not in the second set.

    Args:
        u1, u2, u3: First set of vertices.
        v1, v2, v3: Second set of vertices.

    Returns:
        The non-shared vertex.

    Raises:
        AssertionError: If all vertices are shared.
    """
    if not vertex_is_one_of(u1, v1, v2, v3):
        return u1
    elif not vertex_is_one_of(u2, v1, v2, v3):
        return u2
    elif not vertex_is_one_of(u3, v1, v2, v3):
        return u3
    else:
        raise AssertionError


def match_vertex(v, v1, v2, v3):
    """
    Rotate vertices until v1 matches v.

    Args:
        v: Vertex to match.
        v1, v2, v3: Vertices to rotate.
    """
    while v1 != v:
        v1, v2, v3 = v2, v3, v1


def find_min_neighbor(heap, t):
    """
    Find the neighbor with the minimum key.

    Args:
        heap: The heap to search.
        t: The current triangle.

    Returns:
        The neighbor with the minimum key.
    """
    min_neighbor = None
    min_key = float('inf')
    td = heap.map.lookup(t)
    for t2 in td.neighbors:
        td2 = heap.map.lookup(t2)
        if td2.used:
            continue
        k = td2.pos.key
        if k < min_key:
            min_key = k
            min_neighbor = t2
    return min_neighbor


def find_neighbor_forward(heap, t, v1, v2, v3, left_turn):
    """
    Find the forward neighbor in the strip.

    Args:
        heap: The heap to search.
        t: The current triangle.
        v1, v2, v3: Vertices of the current triangle.
        left_turn: Whether to take a left turn.

    Returns:
        The forward neighbor.
    """
    neighbor = None
    td = heap.map.lookup(t)
    for t2 in td.neighbors:
        td2 = heap.map.lookup(t2)
        if t2 == t or td2.used:
            continue
        v4, v5, v6 = t2.vertices()
        if left_turn:
            if not vertices_match(v1, v3, None, v4, v5, v6):
                continue
        else:
            if not vertices_match(v3, v2, None, v4, v5, v6):
                continue
        neighbor = t2
        v1, v2, v3 = v4, v5, v6
    return neighbor


def find_neighbor_backward(heap, t, v1, v2, v3, left_turn):
    """
    Find the backward neighbor in the strip.

    Args:
        heap: The heap to search.
        t: The current triangle.
        v1, v2, v3: Vertices of the current triangle.
        left_turn: Whether to take a left turn.

    Returns:
        The backward neighbor.
    """
    neighbor = None
    td = heap.map.lookup(t)
    for t2 in td.neighbors:
        td2 = heap.map.lookup(t2)
        if t2 == t or td2.used:
            continue
        v4, v5, v6 = t2.vertices()
        if left_turn:
            if not vertices_match(None, v2, v1, v4, v5, v6):
                continue
        else:
            if not vertices_match(v1, None, v2, v4, v5, v6):
                continue
        neighbor = t2
        v1, v2, v3 = v4, v5, v6
    return neighbor


def grow_strip_forward(heap, strip, t, v1, v2, v3):
    """
    Grow the strip forward.

    Args:
        heap: The heap to search.
        strip: The current strip.
        t: The current triangle.
        v1, v2, v3: Vertices of the current triangle.

    Returns:
        The grown strip.
    """
    assert (heap);
    assert (len(strip) == 2);
    assert (t);
    assert (v1 and v2 and v3);
    assert (vertices_are_unique(v1, v2, v3));

    left_turn = True
    while (t := find_neighbor_forward(heap, t, v1, v2, v3, left_turn)) is not None:
        heap.remove(t)
        strip.insert(0, t)
        left_turn = not left_turn
    return strip


def grow_strip_backward(heap, strip, t, v1, v2, v3):
    """
    Grow the strip backward.

    Args:
        heap: The heap to search.
        strip: The current strip.
        t: The current triangle.
        v1, v2, v3: Vertices of the current triangle.

    Returns:
        The grown strip.
    """

    assert (heap);
    assert (len(strip) >= 2);
    assert (t);
    assert (v1 and v2 and v3);
    assert (vertices_are_unique(v1, v2, v3));

    while (t2 := find_neighbor_backward(heap, t, v1, v2, v3, False)) is not None and (t := find_neighbor_backward(heap, t2, v1, v2, v3, True)) is not None:
        heap.remove(t2)
        heap.remove(t)
        strip.insert(0, t2)
        strip.insert(0, t)
    return strip


def find_right_turn(v1, v2, v3, v4, v5, v6):
    """
    Determine if the turn is a right turn.

    Args:
        v1, v2, v3: Vertices of the first triangle.
        v4, v5, v6: Vertices of the second triangle.

    Returns:
        bool: True if it is a right turn, False otherwise.
    """
    assert (v1 and v2 and v3);
    assert (v4 and v5 and v6);
    assert (vertices_are_unique (v1, v2, v3));
    assert (vertices_are_unique (v4, v5, v6));
    assert (num_shared_vertices (v1, v2, v3, v4, v5, v6) == 2);

    v = non_shared_vertex1(v1, v2, v3, v4, v5, v6)
    match_vertex(v, v1, v2, v3)
    match_vertex(v3, v4, v5, v6)
    if v5 == v2:
        assert (vertices_are_unique (v1, v2, v3));
        assert (vertices_are_unique (v4, v5, v6));
        assert (num_shared_vertices (v1, v2, v3,
					    v4, v5, v6) == 2);
        return True
    else:
        return False


def gts_surface_strip(s):
    """
    Generate surface strips from a given surface.

    Args:
        s: The surface to process.

    Returns:
        list: A list of strips.
    """
    strips = []
    heap = Heap(s)
    while not heap.is_empty():
        t1 = heap.top()
        heap.remove(t1)
        strip = [t1]
        t2 = find_min_neighbor(heap, t1)
        if t2:
            assert (t2 != t1);
            v1, v2, v3 = t1.vertices()
            v4, v5, v6 = t2.vertices()
            if find_right_turn(v1, v2, v3, v4, v5, v6):
                heap.remove(t2)
                strip.insert(0, t2)
                strip = grow_strip_forward(heap, strip, t2, v4, v5, v6)
                strip.reverse()
                strip = grow_strip_backward(heap, strip, t1, v1, v2, v3)
        strips.append(strip)
    return strips
