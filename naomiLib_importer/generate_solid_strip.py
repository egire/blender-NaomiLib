import time
import unittest

from SolidGenerator import Sphere
from TriStripAlgos.GPT import GPTStrip
from TriStripAlgos.PyFFI import tristrip

class TestSurfaceStrip(unittest.TestCase):
    def setUp(self):
        # Create a simple surface with triangles forming a sphere
        sphere = Sphere(1, 1)

        sphere.write_obj("sphere.obj")

        self.triangles = sphere.triangles
        print(f"Triangle Count: {len(self.triangles)}")
                
    def test_surface_strip(self):
        return
        start_time = time.time()
        triangle_strips_gpt = GPTStrip.generate_triangle_strips(self.triangles)
        gpt_time = time.time() - start_time

        start_time = time.time()
        triangle_strips_nv = tristrip.stripify(self.triangles)
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
