import struct

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

class Polygon:
    def __init__(self, envmap=0, not_gp=1, gouraud=1, s_index=1, strip=1, triangle=0, sprite=0, culling=2, strip_num=0):

        
        #  (0<<NL_PF_ENVMAP)+(1<<NL_PF_S_INDEX)+(0<<NL_PF_NOT_GP)+(1<<NL_PF_GOURAUD)+
        #   (2<<NL_PF_CULLING)+(1<<NL_PF_STRIP)+(0<<NL_PF_TRIANGLE)+(0<<NL_PF_SPRITE), /* gflag */
        #  4,	/* strip num (2 polygons) */

        #gflag
        self.envmap = envmap
        self.s_index = s_index
        self.not_gp = not_gp
        self.gouraud = gouraud
        self.culling = culling
        self.strip = strip
        self.triangle = triangle
        self.sprite = sprite
        self.strip_num = strip_num  # strip count (n vertices per strip -2)
        
        # if NL_PF_NOT_GP is set, the polygon vertex data 
        # has an additional two values for cache control
        # 0x5fffff40,0xffffff48, /* (DMA:48,RAM:44) << Reuse number 2. This vertex is the last here.>> cache ON */

        self.vertices = [
            # (x, y, z, nx, ny, nz, u, v) or (index, offset)
        ]

    def set_vertices(self, vertices):
        self.vertices = vertices
        self.strip_num = len(vertices)

    def pack(self):
        header = (self.envmap << 8) | (self.not_gp << 7) | (self.gouraud << 6) | (self.s_index << 5) \
                 | (self.strip << 4) | (self.triangle << 3) | (self.sprite << 2) | (self.culling)
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
    def __init__(self, parameter_control=None, isp_tsp_instruction=None, tsp_instruction=None, texture_control=None,
            mesh_center_point=(0xbe4500fe, 0x00000000, 0xb2800000), mesh_radius=0x3f093f5d, tex_pvf_index=-1,
            tex_shading=0, tex_ambient=0x3f400000, face_color=(0x3f800000, 0x3f800000, 0x3f800000, 0x3f800000),
            face_offset_color=(0x00000000, 0x3f800000, 0x3f800000, 0x3f800000), skip_byte_gflag=None):
        
        # /* parameter_control */
        # (0x80000000)|	/* global parameter && マテリアル継続 */
        #  (0<<NL_PF_ListType)|(0<<NL_PF_Volume)|(2<<NL_PF_Col_Type)|(1<<NL_PF_Texture)|
        #   (1<<NL_PF_Offset)|(0<<NL_PF_Gouraud)|(0<<NL_PF_16bit_UV)
        if parameter_control is None:
            parameter_control = 0x80000000 | (0 << 24) | (0 << 6) | (2 << 4) | (1 << 3) | (1 << 2) | (0 << 1) | (0 << 0)
        
        # /* ISP_TSP_instruction */
        # (4<<NL_PF_DepthCompareMode)|(0<<NL_PF_CullingMode)|(0<<NL_PF_ZWriteDisable)|
        #  (1<<NL_PF_Texture2)|(1<<NL_PF_Offset2)|(0<<NL_PF_Gouraud2)|(0<<NL_PF_16bit_UV2)|
        #   (0<<NL_PF_CacheBypass)|(0<<NL_PF_DcalcCtrl)
        if isp_tsp_instruction is None:
            isp_tsp_instruction = (4 << 29) | (0 << 27) | (0 << 26) | (1 << 25) | (1 << 24) | (0 << 23) | (0 << 22) | (0 << 21) | (0 << 20)
        
        # /* TSP_instruction */
        # (1<<NL_PF_SRC_AlphaInstr)|(0<<NL_PF_DST_AlphaInstr)|(0<<NL_PF_SRC_Select)|
        #  (0<<NL_PF_DST_Select)|(0<<NL_PF_FogControl)|(0<<NL_PF_ColorClamp)|(0<<NL_PF_UseAlpha)|
        #   (1<<NL_PF_IgnoreTexAlpha)|(0<<NL_PF_FlipUV)|(0<<NL_PF_ClampUV)|(1<<NL_PF_FilterMode)|
        #    (0<<NL_PF_SuperSampleTexture)|(4<<NL_PF_MipMapD_adjust)|(1<<NL_PF_TextureShadingInstr)|
        #     (4<<NL_PF_TextureSize_U)|(4<<NL_PF_TextureSize_V)
        if tsp_instruction is None:
            tsp_instruction = (1 << 29) | (0 << 26) | (0 << 25) | (0 << 24) | (0 << 22) | (0 << 21) | (0 << 20) | (1 << 19) | (0 << 17) | (0 << 15) | (0 << 13) | (0 << 12) | (4 << 8) | (1 << 6) | (0 << 3) | (4 << 0)     
        
        # /* texture_control */
        # (0<<NL_PF_MIP_Mapped)|(0<<NL_PF_VQ_Compressed)|(1<<NL_PF_PixelFormat)|
        #  (0<<NL_PF_ScanOrder)|(0<<NL_PF_StrideSelect)|(0<<NL_PF_TextureAddress)    
        if texture_control is None:
            texture_control = (0 << 31) | (0 << 30) | (1 << 27) | (0 << 26) | (0 << 25) | (0 << 0)

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
        self.skip_byte_gflag = self._compute_skipbyte() if skip_byte_gflag else skip_byte_gflag

    def add_polygon(self, polygon):
        self.polygons.append(polygon)

    def _compute_skipbyte(self):
        skip_byte = 0
        for polygon in self.polygons:
            skip_byte += len(polygon.pack())
        return skip_byte

    def pack(self):
        data = struct.pack('<I', self.parameter_control)
        data += struct.pack('<I', self.isp_tsp_instruction)
        data += struct.pack('<I', self.tsp_instruction)
        data += struct.pack('<I', self.texture_control)
        data += struct.pack('<f', self.mesh_center_point[0])
        data += struct.pack('<f', self.mesh_center_point[1])
        data += struct.pack('<f', self.mesh_center_point[2])
        data += struct.pack('<f', self.mesh_radius)
        data += struct.pack('<i', self.tex_pvf_index)
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

        self.skip_byte_gflag = self._compute_skipbyte()

        data += struct.pack('<I', self.skip_byte_gflag)
        
        for polygon in self.polygons:
            data += polygon.pack()

        return data


if __name__ == '__main__':
    from NLPolyFormatReader import NLReader

    file_path = 'sphere.bin'
    nl_reader = NLReader(file_path)
    nl_polyformat = nl_reader.read()

    print(nl_polyformat.models[0].polygons[0].vertices)

    print(nl_polyformat.get_vertex_count())

    # Save to file
    nl_polyformat.save_to_file('sphere.bin')