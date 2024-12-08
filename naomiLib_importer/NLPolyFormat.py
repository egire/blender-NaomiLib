﻿import struct

class NLPolyFormat:
    def __init__(self, super_index_format = 1,
        global_flag = 1,
        center_point = (0.0, 0.0, 0.0),
        radius = 0.0):

        self.super_index_format = super_index_format
        self.global_flag = global_flag
        self.center_point = center_point
        self.radius = radius
        self.models = []
        self.vert_index = dict()

    def add_model(self, model):
        self.models.append(model)

    def get_indexed_vertex(self, idx):
        return self.vert_index[idx]
    
    def get_vertex_count(self):
        count = 0
        for model in self.models:
            for polygon in model.polygons:
                count += len(polygon.vertices)      
        return count

    def get_vertex_index_count(self):
        return len(self.vert_index)

    def pack(self):
        data = struct.pack('<I', self.super_index_format)
        data += struct.pack('<I', self.global_flag)
        data += struct.pack('<f', self.center_point[0])
        data += struct.pack('<f', self.center_point[1])
        data += struct.pack('<f', self.center_point[2])
        data += struct.pack('<f', self.radius)

        for model in self.models:
            data += model.pack()

        data += struct.pack('<I', 0)
        data += struct.pack('<I', self.get_vertex_count())

        return data

    def save_to_file(self, file_path):
        packed_data = self.pack()
        with open(file_path, 'wb') as file:
            file.write(packed_data)

class Polygon:
    def __init__(self, envmap=0, not_gp=1, gouraud=1, s_index=1, strip=1, triangle=0, sprite=0, culling=2, strip_num=4):

        #gflag
        self.envmap = envmap
        self.s_index = s_index
        self.not_gp = not_gp
        self.gouraud = gouraud
        self.culling = culling
        self.strip = strip
        self.triangle = triangle
        self.sprite = sprite
        self.strip_num = strip_num  # strip count (4 vertices per strip -2)
        
        # if NL_PF_NOT_GP is set, the polygon vertex data 
        # has an additional two values for cache control
        # 0x5fffff40,0xffffff48, /* (DMA:48,RAM:44) << Reuse number 2. This vertex is the last here.>> cache ON */

        self.vertices = [
            # (x, y, z, nx, ny, nz, u, v) or (index, offset)
        ]

    def set_vertices(self, vertices):
        self.vertices = vertices

    def pack(self):
        header = (self.envmap << 8) | (self.not_gp << 7) | (self.gouraud << 6) | (self.s_index << 5) | \
                 (self.strip << 4) | (self.triangle << 3) | (self.sprite << 2) | (self.culling)
        data = struct.pack('<I', header)
        data += struct.pack('<I', self.strip_num)

        # if self.data[self.index + 2:self.index + 4] == b'\xff\x5f' and self.data[self.index + 6:self.index + 8] == b'\xff\xff':
        #     vertex = self.allvertices[-self.get_ref_vertex_id()]
        # else:
        #     vertex = self.read_vertex()

        for vertex in self.vertices:
            if len(vertex) == 8:
                data += struct.pack('<8f', *vertex)
            else:
                data += struct.pack('<I', vertex[0][0])
                data += struct.pack('<I', vertex[0][1])

        return data

class Model:
    def __init__(self, parameter_control=0x80000000 | (0 << 24) | (0 << 23) | (2 << 21) | (1 << 20) | (1 << 19) | (0 << 18) | (0 << 17),
            isp_tsp_instruction=(4 << 29) | (0 << 27) | (0 << 26) | (1 << 25) | (1 << 24) | (0 << 23) | (0 << 22) | (0 << 21) | (0 << 20),
            tsp_instruction=(1 << 31) | (0 << 30) | (0 << 29) | (0 << 28) | (0 << 27) | (0 << 26) | (0 << 25) | (1 << 24) | (0 << 23) | (0 << 22) | (0 << 21) | (0 << 20) | (4 << 19) | (1 << 18) | (0 << 17) | (4 << 16),
            texture_control=(0 << 31) | (0 << 30) | (1 << 29) | (0 << 28) | (0 << 27) | (0 << 26),
            mesh_center_point=(0xbe4500fe, 0x00000000, 0xb2800000),
            mesh_radius=0x3f093f5d,
            tex_pvf_index=0,
            tex_shading=0,
            tex_ambient=0x3f400000,
            face_color=(0x3f800000, 0x3f800000, 0x3f800000, 0x3f800000),
            face_offset_color=(0x00000000, 0x3f800000, 0x3f800000, 0x3f800000),
            skip_byte_gflag=0):
        self.polygons = []
        self.all_verts = []

        self.parameter_control = parameter_control
        self.isp_tsp_instruction = isp_tsp_instruction
        self.tsp_instruction = tsp_instruction
        self.texture_control = texture_control
        self.mesh_center_point = mesh_center_point
        self.mesh_radius = mesh_radius
        self.tex_pvf_index = tex_pvf_index
        self.tex_shading = tex_shading
        self.tex_ambient = tex_ambient
        self.face_color = face_color
        self.face_offset_color = face_offset_color
        self.skip_byte_gflag = skip_byte_gflag

    def add_polygon(self, polygon):
        self.polygons.append(polygon)

    def pack(self):
        data = struct.pack('<I', self.parameter_control)
        data += struct.pack('<I', self.isp_tsp_instruction)
        data += struct.pack('<I', self.tsp_instruction)
        data += struct.pack('<I', self.texture_control)
        data += struct.pack('<f', self.mesh_center_point[0])
        data += struct.pack('<f', self.mesh_center_point[1])
        data += struct.pack('<f', self.mesh_center_point[2])
        data += struct.pack('<f', self.mesh_radius)
        data += struct.pack('<I', self.tex_pvf_index)
        data += struct.pack('<I', self.tex_shading)
        data += struct.pack('<f', self.tex_ambient)
        data += struct.pack('<f', self.face_color[0])
        data += struct.pack('<f', self.face_color[1])
        data += struct.pack('<f', self.face_color[2])
        data += struct.pack('<f', self.face_color[3])
        data += struct.pack('<f', self.face_offset_color[0])
        data += struct.pack('<f', self.face_offset_color[1])
        data += struct.pack('<f', self.face_offset_color[2])
        data += struct.pack('<f', self.face_offset_color[3])
        data += struct.pack('<I', self.skip_byte_gflag)
        
        for polygon in self.polygons:
            data += polygon.pack()

        return data


if __name__ == '__main__':
    from NLPolyFormatReader import NLReader

    file_path = 'model_BAS00_005.bin'
    nl_reader = NLReader(file_path)
    nl_polyformat = nl_reader.read()

    print(nl_polyformat.models[0].polygons[0].vertices)

    print(nl_polyformat.get_vertex_count())

    # Save to file
    nl_polyformat.save_to_file('test.bin')