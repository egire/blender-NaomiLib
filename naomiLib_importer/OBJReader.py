import string
import struct
from NLPolyFormat import NLPolyFormat, Model, Polygon
from TriStripAlgos.PyFFI import tristrip

class OBJReader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.objects = ['']
        self.vertices = dict({'': []})
        self.normals = dict({'': []})
        self.uvs = dict({'': []})
        self.faces = dict({'': []})
        self.strips = dict({'': []})
        self.tritoface = dict({'': dict()})

    def _generate_tristrips(self):
        for obj in self.objects:
            faces = self.faces[obj]
            tris = [(face[0][0], face[1][0], face[2][0]) for face in faces]
            self.strips[obj] = tristrip.stripify(tris, False)

    def _init_object(self, object_name):
        self.vertices[object_name] = []
        self.normals[object_name] = []
        self.uvs[object_name] = []
        self.faces[object_name] = []
        self.strips[object_name] = []
        self.tritoface[object_name] = dict()
        self.objects.append(object_name)

    def read(self):
        try:
            with open(self.file_path, 'r') as file:
                for line in file:
                    cur_object = self.objects[-1]
                    if line.startswith('o '):
                        if(self.objects[0] == ''):
                            self.objects = []
                        object_name = self._parse_object(line)
                        self._init_object(object_name)

                    elif line.startswith('v '):
                        self.vertices[cur_object].append(self._parse_vertex(line))
                    elif line.startswith('vn '):
                        self.normals[cur_object].append(self._parse_normal(line))
                    elif line.startswith('vt '):
                        self.uvs[cur_object].append(self._parse_uv(line))
                    elif line.startswith('f '):
                        self.faces[cur_object].append(self._parse_face(line))
                    elif line.startswith('s '):
                        continue
                    elif line.startswith('# '):
                        continue
                    else:
                        print(line)
        except FileNotFoundError:
            print('File not found')
            return False
        
        self._generate_tristrips()

        return True

    def _parse_object(self, line):
        parts = line.strip().split()
        return str(parts[1])

    def _parse_vertex(self, line):
        parts = line.strip().split()
        return (float(parts[1]), float(parts[2]), float(parts[3]))

    def _parse_face(self, line):
        cur_object = self.objects[-1]
        parts = line.strip().split()
        vtns = []
        for part in parts[1:]:
            vtn = part.split('/')
            v = int(vtn[0]) - 1
            t = int(vtn[1]) - 1 if len(vtn) > 1 and vtn[1] else None
            n = int(vtn[2]) - 1 if len(vtn) > 2 and vtn[2] else None
            vtns.append((v, t, n))
        triangle = (vtns[0][0], vtns[1][0], vtns[2][0])
        self.tritoface[cur_object][triangle] = len(self.tritoface[cur_object])
        return vtns

    def _parse_normal(self, line):
        parts = line.strip().split()
        return (float(parts[1]), float(parts[2]), float(parts[3]))

    def _parse_uv(self, line):
        parts = line.strip().split()
        return (float(parts[1]), float(parts[2]))

    def _convert_to_nlpolyformat(self):
        nl_polyformat = NLPolyFormat()
        for obj in self.objects:
            model = Model(None, None, None, None, (0, 0, 0), 1.0, -1, 5, 1.0, (0xFF, 0xFF, 0xFF, 0xFF), (0xFF, 0xFF, 0xFF, 0xFF))
            polygon = Polygon(0, 1, 1, 1, 1, 0, 0, 1)
            verts = []
            for strip in self.strips[obj]:
                for j in range(len(strip)):
                    if j >= (len(strip)-3):
                        triangle = (strip[-3], strip[-2], strip[-1])
                    else:
                        triangle = (strip[j], strip[j+1], strip[j+2])
                    
                    # check if triangle has any repeated vertices. it's a degenerate triangle, it needs added.
                    if triangle[0] == triangle[1] or triangle[0] == triangle[2] or triangle[1] == triangle[2]:
                        face_id = None
                        i = 0
                        while face_id == None:
                            next_tri = (strip[j+i+1], strip[j+i+2], strip[j+i+3])
                            face_id = self.lookup_triface(obj, next_tri)
                            i += 1
                        self.tritoface[obj][triangle] = face_id

                    # Ensure face is counter-clockwise winding
                    # if self.is_clockwise(self.vertices[obj][face[0][0]], self.vertices[obj][face[1][0]], self.vertices[obj][face[2][0]]):
                    #     face = (face[0], face[2], face[1])

                    face_id = self.lookup_triface(obj, triangle)
                    face = self.faces[obj][face_id]

                    for fv in face:
                        if strip[j] == fv[0]:
                            v, t, n = fv
                            vertex = self.vertices[obj][v]
                            normal = self.normals[obj][n] if n is not None else (0, 0, 0)
                            uv = self.uvs[obj][t] if t is not None else (0, 0)
                            verts.append((vertex[0], vertex[1], vertex[2], normal[0], normal[1], normal[2], uv[0], uv[1]))


                    # for v, t, n in face:
                    #     vertex = self.vertices[obj][v]
                    #     normal = self.normals[obj][n] if n is not None else (0, 0, 0)
                    #     uv = self.uvs[obj][t] if t is not None else (0, 0)
                    #     verts.append((vertex[0], vertex[1], vertex[2], normal[0], normal[1], normal[2], uv[0], uv[1]))
            
            polygon.set_vertices(verts)
            model.add_polygon(polygon)

            nl_polyformat.add_model(model)
        return nl_polyformat

    def lookup_triface(self, obj, triangle):
        k = None
        if triangle in self.tritoface[obj]:
            k = triangle
        elif (triangle[1], triangle[2], triangle[0]) in self.tritoface[obj]:
            k = (triangle[1], triangle[2], triangle[0]) 
        elif (triangle[2], triangle[0], triangle[1]) in self.tritoface[obj]:
            k = (triangle[2], triangle[0], triangle[1])
        elif (triangle[0], triangle[2], triangle[1]) in self.tritoface[obj]:
            k = (triangle[0], triangle[2], triangle[1]) 
        elif (triangle[2], triangle[1], triangle[0]) in self.tritoface[obj]:
            k = (triangle[2], triangle[1], triangle[0])
        elif (triangle[1], triangle[0], triangle[2]) in self.tritoface[obj]:
            k = (triangle[1], triangle[0], triangle[2])
        else:
            return None

        face_id = self.tritoface[obj][k]
        return face_id                 

    def is_clockwise(self, v0, v1, v2):
        # Calculate vectors
        vec1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        vec2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])

        # Calculate cross product
        cross_product = (
            vec1[1] * vec2[2] - vec1[2] * vec2[1],
            vec1[2] * vec2[0] - vec1[0] * vec2[2],
            vec1[0] * vec2[1] - vec1[1] * vec2[0]
        )

        # Calculate dot product with the normal vector
        dot_product = cross_product[2]  # Assuming the normal vector is (0, 0, 1)

        return dot_product < 0

if __name__ == '__main__':
    obj_reader = OBJReader('BAS00_03.obj')
    obj_reader.read()

    nl_poly_format = obj_reader._convert_to_nlpolyformat()

    with open('BAS00_03.bin', 'wb') as file:
        file.write(nl_poly_format.pack())

    print(f'Conversion of object complete')
