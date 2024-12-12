import numpy as np

class Sphere:
    def __init__(self, radius=1.0, subdivisions=3):
        self.radius = radius
        self.vertices = []  # List of (x, y, z)
        self.normals = []   # List of (nx, ny, nz)
        self.uvs = []       # List of (u, v)
        self.triangles = [] # List of (v1, v2, v3)
        self.create_icosahedron()
        for _ in range(subdivisions):
            self.subdivide()

    def write_obj(self, filename):
        """
        Writes the sphere to an .obj file, including normals and UVs.

        :param filename: The name of the file to write to.
        """
        with open(filename, 'w') as f:
            # Write vertices, normals, and UVs
            for vertex in self.vertices:
                f.write(f"v {vertex[0]} {vertex[1]} {vertex[2]}\n")
            for uv in self.uvs:
                f.write(f"vt {uv[0]} {uv[1]}\n")
            for normal in self.normals:
                f.write(f"vn {normal[0]} {normal[1]} {normal[2]}\n")

            # Write faces (including vertex/UV/normal indices)
            for triangle in self.triangles:
                f.write(f"f {triangle[0] + 1}/{triangle[0] + 1}/{triangle[0] + 1} "
                        f"{triangle[1] + 1}/{triangle[1] + 1}/{triangle[1] + 1} "
                        f"{triangle[2] + 1}/{triangle[2] + 1}/{triangle[2] + 1}\n")

    def create_icosahedron(self):
        # Golden ratio and basic icosahedron vertices
        phi = (1 + np.sqrt(5)) / 2
        vertices = [
            [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
            [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
            [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1],
        ]
        # Normalize vertices to lie on the sphere
        for v in vertices:
            self.add_vertex(self.normalize(v))

        # Define triangles (by vertex indices)
        self.triangles = [
            (0, 11, 5), (0, 5, 1), (0, 1, 7),
            (0, 7, 10), (0, 10, 11),
            (1, 5, 9), (5, 11, 4), (11, 10, 2),
            (10, 7, 6), (7, 1, 8), (3, 9, 4),
            (3, 4, 2), (3, 2, 6), (3, 6, 8),
            (3, 8, 9), (4, 9, 5), (2, 4, 11),
            (6, 2, 10), (8, 6, 7), (9, 8, 1)
        ]

    def add_vertex(self, vertex):
        """
        Adds a vertex, its normal, and UV coordinates.
        """
        self.vertices.append(vertex)
        self.normals.append(self.normalize(vertex))  # Normal is the same as the normalized position
        self.uvs.append(self.compute_uv(vertex))     # Compute UV coordinates

    def compute_uv(self, vertex):
        """
        Computes the UV coordinates for a given vertex.
        """
        x, y, z = vertex
        u = 0.5 + np.arctan2(z, x) / (2 * np.pi)
        v = 0.5 - np.arcsin(y) / np.pi
        return (u, v)

    def normalize(self, vertex):
        """
        Normalizes a vertex to lie on the sphere.
        """
        length = np.linalg.norm(vertex)
        return [v / length * self.radius for v in vertex]

    def subdivide(self):
        edge_midpoint_cache = {}
        new_triangles = []

        def midpoint(v1, v2):
            key = tuple(sorted((v1, v2)))
            if key not in edge_midpoint_cache:
                midpoint = [
                    (self.vertices[v1][i] + self.vertices[v2][i]) / 2
                    for i in range(3)
                ]
                edge_midpoint_cache[key] = len(self.vertices)
                self.add_vertex(self.normalize(midpoint))  # Add vertex with UVs and normals
            return edge_midpoint_cache[key]

        for v1, v2, v3 in self.triangles:
            a = midpoint(v1, v2)
            b = midpoint(v2, v3)
            c = midpoint(v3, v1)
            new_triangles.extend([
                (v1, a, c),
                (v2, b, a),
                (v3, c, b),
                (a, b, c)
            ])

        self.triangles = new_triangles
