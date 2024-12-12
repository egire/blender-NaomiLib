
from collections import defaultdict
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