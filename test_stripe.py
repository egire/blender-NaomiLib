import time
from random import triangular
import unittest
from stripe import Surface, Triangle, gts_surface_strip
from collections import defaultdict


import numpy as np

from tristrip import stripify

class Sphere:
    def __init__(self, radius=1.0, subdivisions=3):
        self.radius = radius
        self.vertices = []
        self.triangles = []
        self.create_icosahedron()
        for _ in range(subdivisions):
            self.subdivide()

    def create_icosahedron(self):
        # Golden ratio and basic icosahedron vertices
        phi = (1 + np.sqrt(5)) / 2
        vertices = [
            [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
            [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
            [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1],
        ]
        # Normalize vertices to lie on the sphere
        self.vertices = [self.normalize(v) for v in vertices]
        
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

    def normalize(self, vertex):
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
                self.vertices.append(self.normalize(midpoint))
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


from concurrent.futures import ThreadPoolExecutor

def generate_triangle_strips(triangles):
    def get_shared_vertices(tri1, tri2):
        return len(set(tri1).intersection(tri2))

    strips = []
    vertex_to_triangles = defaultdict(list)
    for triangle in triangles:
        for vertex in triangle:
            vertex_to_triangles[vertex].append(triangle)

    unprocessed = set(triangles)

    def process_strip():
        strip = []
        current_triangle = unprocessed.pop()
        strip.append(current_triangle)

        while True:
            next_triangle = None
            max_shared_vertices = -1
            for vertex in current_triangle:
                for triangle in vertex_to_triangles[vertex]:
                    if triangle in unprocessed:
                        shared_vertices = get_shared_vertices(current_triangle, triangle)
                        if shared_vertices > max_shared_vertices:
                            max_shared_vertices = shared_vertices
                            next_triangle = triangle

            if next_triangle:
                strip.append(next_triangle)
                unprocessed.remove(next_triangle)
                current_triangle = next_triangle
            else:
                break

        return strip

    with ThreadPoolExecutor() as executor:
        while unprocessed:
            future = executor.submit(process_strip)
            strips.append(future.result())

    # Merge strips to reduce the number of strips
    merged_strips = []
    while strips:
        strip = strips.pop(0)
        merged = False
        for i, mstrip in enumerate(merged_strips):
            if set(strip[0]).intersection(set(mstrip[-1])):
                merged_strips[i].extend(strip)
                merged = True
                break
        if not merged:
            merged_strips.append(strip)

    # Sort strips by length in descending order to optimize the triangle strips
    merged_strips.sort(key=len, reverse=True)

    # Further merge strips to increase the average strip size
    final_strips = []
    while merged_strips:
        strip = merged_strips.pop(0)
        merged = False
        for i, fstrip in enumerate(final_strips):
            if set(strip[0]).intersection(set(fstrip[-1])) or set(strip[-1]).intersection(set(fstrip[0])):
                final_strips[i].extend(strip)
                merged = True
                break
        if not merged:
            final_strips.append(strip)

    return final_strips



class TestSurfaceStrip(unittest.TestCase):
    def setUp(self):
        # Create a simple surface with triangles forming a sphere
        sphere = Sphere(1, 8)

        self.triangles = sphere.triangles
        print(f"Triangle Count: {len(self.triangles)}")
                
    def test_surface_strip(self):
        start_time = time.time()
        triangle_strips_gpt = generate_triangle_strips(self.triangles)
        gpt_time = time.time() - start_time

        start_time = time.time()
        triangle_strips_nv = stripify(self.triangles)
        nv_time = time.time() - start_time

        self.assertIsInstance(triangle_strips_gpt, list)
        self.assertGreater(len(triangle_strips_gpt), 0)

        self.assertIsInstance(triangle_strips_nv, list)
        self.assertGreater(len(triangle_strips_nv), 0)

        # self.assertEqual(len(triangle_strips_gpt), len(triangle_strips_nv))

        print("GPT: GitHub Copilot,\t\tNV: NvTriStrip (pyffi)\n"
                f"GPT (count): {len(triangle_strips_gpt)},\t\tNV (count): {len(triangle_strips_nv)}\n"
                f"GPT (N=1): {sum(1 for strip in triangle_strips_gpt if len(strip) == 1)},\t\t\tNV (N=1): {sum(1 for strip in triangle_strips_nv if len(strip) == 1)}\n"
                f"GPT (min): {min(len(strip) for strip in triangle_strips_gpt)},\t\t\tNV (min): {min(len(strip) for strip in triangle_strips_nv)}\n"
                f"GPT (max): {max(len(strip) for strip in triangle_strips_gpt)},\t\t\tNV (max): {max(len(strip) for strip in triangle_strips_nv)}\n"
                f"GPT (avg): {sum(len(strip) for strip in triangle_strips_gpt) / len(triangle_strips_gpt):.2f},\t\tNV (avg): {sum(len(strip) for strip in triangle_strips_nv) / len(triangle_strips_nv):.2f}\n"
                f"GPT (time): {gpt_time:.4f} secs,\tNV (time): {nv_time:.4f} secs")

if __name__ == '__main__':
    unittest.main()
