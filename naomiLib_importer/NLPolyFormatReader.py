import struct
import NLPolyFormat

class NLReader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = self.read_file()
        self.index = 0
        self.vert_index = dict()

    def vert_index_count(self):
        return len(self.vert_index)

    def read_file(self):
        with open(self.file_path, 'rb') as file:
            return file.read()

    def read_int(self):
        value = struct.unpack('<I', self.data[self.index:self.index + 4])[0]
        self.index += 4
        return value

    def read_float(self):
        value = struct.unpack('<f', self.data[self.index:self.index + 4])[0]
        self.index += 4
        return value

    def read_s8_int(self):
        value = struct.unpack('<b', self.data[self.index])[0]
        self.index += 1
        return value

    def read_model(self):
        parameter_control = self.read_int()
        isp_tsp_instruction = self.read_int()
        tsp_instruction = self.read_int()
        texture_control = self.read_int()
        mesh_center_point = (self.read_float(), self.read_float(), self.read_float())
        mesh_radius = self.read_float()
        tex_pvf_index = self.read_int()
        tex_shading = self.read_int() 
        tex_ambient = self.read_float()
        face_color = (self.read_float(), self.read_float(), self.read_float(), self.read_float())
        face_offset_color = (self.read_float(), self.read_float(), self.read_float(), self.read_float())
        skip_byte_gflag = self.read_int()

        model = NLPolyFormat.Model(parameter_control, isp_tsp_instruction, tsp_instruction, texture_control, mesh_center_point, mesh_radius, tex_pvf_index, tex_shading, tex_ambient, face_color, face_offset_color, skip_byte_gflag)

        gflag_index = self.index
        while self.index - gflag_index < skip_byte_gflag:
            test = self.index - gflag_index 
            polygon = self.read_polygon(tex_shading)
            model.add_polygon(polygon)

        return model

    # check the each float and see if it starts with 0x5fff, if it does it's a reference to a vertex (uint, uint) else its a standard
    # (float, float, float), (float, float, float), (float, float)
    # this should stop reading when to encounters a 0x00000000 0x00000000
    def read_polygon(self, tex_shading = 0):
        gflag = self.read_int()

        culling = gflag & 0b11                 # Bits 0-1
        sprite = (gflag >> 2) & 1              # Bit 2
        triangle = (gflag >> 3) & 1            # Bit 3
        strip = (gflag >> 4) & 1               # Bit 4
        s_index = (gflag >> 5) & 1             # Bit 5 (Super Vertex Index)
        gouraud = (gflag >> 6) & 1             # Bit 6
        not_gp = (gflag >> 7) & 1              # Bit 7 (Reuse Global Params: Inverted name)
        envmap = (gflag >> 8) & 1              # Bit 8 (Optional if 8+ bits exist in gflag)

        strip_num = self.read_int()

        vertices = []

        for _ in range(strip_num):
            if triangle and not strip:
                vertices.extend(self.read_vertices(3, 0x20))
            elif tex_shading == -3:
                vertices.append(self.read_and_store_vertex(self.read_color_vertex, 0x20))
            elif tex_shading == -2:
                vertices.append(self.read_and_store_vertex(self.read_bump_vertex, 0x34))
            else:
                vertices.extend(self.read_vertices(1, 0x20))

        polygon = NLPolyFormat.Polygon(envmap, not_gp, gouraud, s_index, strip, triangle, sprite, culling, strip_num)

        polygon.set_vertices(vertices)

        return polygon

    def read_vertices(self, count, index_offset):
            vertices = []
            for _ in range(count):
                if self.is_ref_vertex():
                    ref_vertex = self.read_ref_vertex()
                    vertices.append((ref_vertex, self.index - 0x08))
                else:
                    vertex = self.read_vertex()
                    vertices.append(vertex)
                    self.vert_index[self.index - index_offset] = vertex
            return vertices

    def read_and_store_vertex(self, read_vertex_func, index_offset):
        vertex = read_vertex_func()
        self.vert_index[self.index - index_offset] = vertex
        return vertex

    def is_ref_vertex(self):
        return self.data[self.index + 2:self.index + 4] == b'\xff\x5f' and self.data[self.index + 6:self.index + 8] == b'\xff\xff'

    def read_vertex(self):
        x = self.read_float()
        y = self.read_float()
        z = self.read_float()
        nx = self.read_float()
        ny = self.read_float()
        nz = self.read_float()
        u = self.read_float()
        v = self.read_float()
        # 32 bytes
        return (x, y, z, nx, ny, nz, u, v)

    def read_bump_vertex(self):
        x = self.read_float()
        y = self.read_float()
        z = self.read_float()
        nx = self.read_float()
        ny = self.read_float()
        nz = self.read_float()
        b0nx = self.read_float()
        b0ny = self.read_float()
        b0nz = self.read_float()
        b1nx = self.read_float()
        b1ny = self.read_float()
        b1nz = self.read_float()
        u = self.read_float()
        v = self.read_float()
        # 56 bytes
        return (x, y, z, nx, ny, nz, b0nx, b0ny, b0nz, b1nx, b1ny, b1nz, u, v)

    def read_color_vertex(self):
        x = self.read_float()
        y = self.read_float()
        z = self.read_float()

        nx = self.read_s8_int()
        ny = self.read_s8_int()
        nz = self.read_s8_int()
        _ = self.read_s8_int()

        # BGRA8888
        c1_B = self.read_s8_int()
        c1_G = self.read_s8_int()
        c1_R = self.read_s8_int()
        c1_A = self.read_s8_int()

        c2_B = self.read_s8_int()
        c2_G = self.read_s8_int()
        c2_R = self.read_s8_int()
        c2_A = self.read_s8_int()

        u = self.read_float()
        v = self.read_float()
        # 32 bytes
        return (x, y, z, nx, ny, nz, c1_B, c1_G, c1_R, c1_A, c2_B, c2_G, c2_R, c2_A, u, v)

    def read_ref_vertex(self):
        flag = self.read_int() # idx/flag
        offset = self.read_int() # pointer
        return (flag, offset)

    def seek_ref_vertex(self):
        idx = int.from_bytes(self.data[self.index:self.index + 4], byteorder='little')
        offset = int.from_bytes(self.data[self.index + 4:self.index + 8], byteorder='little')

        return (idx, offset)

    def physical_offset(self, ref_vert_offset, vertex_pointer):
        return ref_vert_offset - (0xFFFFFFF8 - vertex_pointer)

    def vertex_index(self, ref_vert_flagid):
        vert_id = ref_vert_flagid[self.index:self.index + 3]
        vertex_index = (0x1000000 - vert_id) // 0x20 # Calculate vertex index

        return vertex_index-1 # 1st vert is index 0

    def read(self):
        super_index_format = self.read_int()
        global_flag = self.read_int()
        center_point = (self.read_float(), self.read_float(), self.read_float())
        radius = self.read_float()

        nl_polyformat = NLPolyFormat.NLPolyFormat(super_index_format, global_flag, center_point, radius)

        while self.index < len(self.data)-8:
            model = self.read_model()
            nl_polyformat.add_model(model)

        _ = self.read_int() # unused
        vertex_count = self.read_int()

        found_vertex_count = nl_polyformat.get_vertex_count()

        nl_polyformat.vert_index = self.vert_index

        if vertex_count != found_vertex_count:
            print(f"ERROR: Vertex count mismatch. Expected {vertex_count} but got {found_vertex_count}")
        
        return nl_polyformat

# Usage
# file_path = 'model_BAS00_004.bin'
# nl_reader = NLPolyFormatReader(file_path)
# nl_polyformat = nl_reader.read()

# print(nl_polyformat.models[0].polygons[0].vertices)

# print(nl_polyformat.get_vertex_count())
