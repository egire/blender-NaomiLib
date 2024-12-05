import bpy
from . pvr2image import decode as pvrdecode
from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add
import struct
import os
from io import BytesIO
from math import radians
from mathutils import Vector

xVal = 0
yVal = 1
zVal = 2

# static magic numbers and headers , updated as per official naming

magic_naomilib = [
    b'\x01\x00\x00\x00\x01\x00\x00\x00',  # Super index , always true
    b'\x00\x00\x00\x00\x01\x00\x00\x00',  # Pure beta , always true
    b'\x01\x00\x00\x00\x02\x00\x00\x00',  # Super index , skip 1st light source
    b'\x00\x00\x00\x00\x02\x00\x00\x00',  # Pure beta , skip 1st light source
    b'\x01\x00\x00\x00\x03\x00\x00\x00',  # Super index , always true , skip 1st light source
    b'\x00\x00\x00\x00\x03\x00\x00\x00',  # Pure beta , always true , skip 1st light source
    b'\x01\x00\x00\x00\x05\x00\x00\x00',  # Super index , always true , Environment mapping
    b'\x00\x00\x00\x00\x05\x00\x00\x00',  # Pure Beta , always true , Environment mapping
    b'\x01\x00\x00\x00\x07\x00\x00\x00',  # Super index , always true , Environment mapping, skip 1st light source
    b'\x00\x00\x00\x00\x07\x00\x00\x00',  # Pure Beta , always true , Environment mapping, skip 1st light source
    b'\x01\x00\x00\x00\x11\x00\x00\x00',  # Super index , always true , Bump mapping
    b'\x00\x00\x00\x00\x11\x00\x00\x00',  # Pure Beta , always true , Bump mapping
    b'\x01\x00\x00\x00\x19\x00\x00\x00',  # Super index , always true , Bump mapping, palette texture
    b'\x00\x00\x00\x00\x19\x00\x00\x00',  # Pure Beta , always true , Bump mapping, palette texture
    b'\x01\x00\x00\x00\x15\x00\x00\x00',  # Super index , always true , Environment mapping, Bump mapping
    b'\x00\x00\x00\x00\x15\x00\x00\x00',  # Pure Beta , always true , Environment mapping, Bump mapping
]


# Global_Flags1_Table
# Bit 	Parameter
# 8 	Reserved 4
# 7 	Reserved 3
# 6 	Reserved 2
# 5 	Reserved 1
# 4 	Bump map available
# 3 	Palette texture
# 2 	Environment mapping
# 1 	Skip 1st light source op.
# 0 	Always true


def collect_data_from_blender():
    # Collect data from the active object
    obj = bpy.context.active_object
    mesh = obj.data

    vertices = [v.co for v in mesh.vertices]
    faces = [f.vertices for f in mesh.polygons]
    uvs = [uv.uv for uv in mesh.uv_layers.active.data]
    normals = [v.normal for v in mesh.vertices]

    return vertices, faces, uvs, normals


def convert_to_nl_format(vertices, faces, uvs, normals):
    # Convert the collected data to NaomiLib format
    nl_data = BytesIO()

    def write_uint32_buff(value):
        nl_data.write(struct.pack("<I", value))

    def write_sint32_buff(value):
        nl_data.write(struct.pack("<i", value))

    def write_float_buff(value):
        nl_data.write(struct.pack("<f", value))

    def write_point3_buff(point):
        nl_data.write(struct.pack("<fff", *point))

    def write_point2_buff(point):
        nl_data.write(struct.pack("<ff", *point))

    def float_to_sint8(num: float) -> int:
        min, max = 0x7f, 0x80
        if num < 0:
            return int(num * max + 0x100)
        else:
            return int(num * min)

    def float_to_col_hex(num: float) -> int:
        max = 0xFF
        return int(num * max)

    # Write Model Header
    globalflag0 = 1  # Naomi globalflag0, values: 0 = pure beta / 1 = super index / -1 NULL

    # Set globalflag1 based on the provided table
    bump_map_available = 0
    palette_texture = 0
    environment_mapping = 0
    skip_first_light_source = 0
    always_true = 1

    globalflag1 = (bump_map_available << 4) | (palette_texture << 3) | (environment_mapping << 2) | (skip_first_light_source << 1) | always_true

    centroid_x = sum(v.x for v in vertices) / len(vertices)
    centroid_y = sum(v.y for v in vertices) / len(vertices)
    centroid_z = sum(v.z for v in vertices) / len(vertices)
    bounding_radius = max((v - Vector((centroid_x, centroid_y, centroid_z))).length for v in vertices)

    nl_data.write(struct.pack('<I', globalflag0))  # Naomi globalflag0
    nl_data.write(struct.pack('<I', globalflag1))  # Naomi globalflag1
    nl_data.write(struct.pack('<f', centroid_x))   # Centroid X
    nl_data.write(struct.pack('<f', centroid_y))   # Centroid Y
    nl_data.write(struct.pack('<f', centroid_z))   # Centroid Z
    nl_data.write(struct.pack('<f', bounding_radius))  # Bounding radius

    # 0x18 bytes (24 bytes)

    # End Write Model Header

    # Write Mesh Struct
    mesh_param = 0

    bit0_16bituv = 0  # Bit 0: U/V (16-bit) (set to 1 or 0)
    bit1_gouraud = 1  # Bit 1: Gouraud (set to 1 or 0)
    bit2_color_offset = 0  # Bit 2: Color Offset (set to 1 or 0)
    bit3_texture = 1  # Bit 3: Texture (set to 1 or 0)
    bit4_5_color_type = 2  # Bits 4-5: Color Type (values 0-3)
    bit6_use_volume = 0  # Bit 6: Use Volume (set to 1 or 0)
    bit7_use_shadow = 0  # Bit 7: Use Shadow (set to 1 or 0)
    bit24_26_list_type = 0  # Bits 24-26: List Type (values 0-7)
    bit29_31_para_type = 0  # Bits 29-31: Para Type (values 0-7)

    mesh_param |= (bit0_16bituv & 0b1) << 0           # Bit 0: U/V (16-bit)
    mesh_param |= (bit1_gouraud & 0b1) << 1           # Bit 1: Gouraud
    mesh_param |= (bit2_color_offset & 0b1) << 2      # Bit 2: Color Offset
    mesh_param |= (bit3_texture & 0b1) << 3           # Bit 3: Texture
    mesh_param |= (bit4_5_color_type & 0b11) << 4     # Bits 4-5: Color Type (2 bits)
    mesh_param |= (bit6_use_volume & 0b1) << 6        # Bit 6: Use Volume
    mesh_param |= (bit7_use_shadow & 0b1) << 7        # Bit 7: Use Shadow
    mesh_param |= (bit24_26_list_type & 0b111) << 24  # Bits 24-26: List Type (3 bits)
    mesh_param |= (bit29_31_para_type & 0b111) << 29  # Bits 29-31: Para Type (3 bits)

    isp_tsp = 0

    # Initial values for each bit or group of bits
    bit20_dcalc_ctrl = 1            # DcalcCtrl: 1-bit (set to 1 or 0)
    bit21_cache_bypass = 0          # CacheBypass: 1-bit (set to 1 or 0)
    bit22_16bit_uv2 = 0             # 16bit_UV2: 1-bit (set to 1 or 0)
    bit23_gouraud2 = 1              # Gouraud2: 1-bit (set to 1 or 0)
    bit24_offset2 = 0               # Offset2: 1-bit (set to 1 or 0)
    bit25_texture2 = 1              # Texture2: 1-bit (set to 1 or 0)
    bit26_zwrite_disable = 0        # ZWriteDisable: 1-bit (set to 1 or 0)
    bit27_28_culling_mode = 2       # CullingMode: 2-bits (values 0-3)
    bit29_31_depth_compare_mode = 5 # DepthCompareMode: 3-bits (values 0-7)

    # Pack each bit/group of bits into its correct position
    isp_tsp |= (bit20_dcalc_ctrl & 0b1) << 20          # Bit 20: DcalcCtrl
    isp_tsp |= (bit21_cache_bypass & 0b1) << 21        # Bit 21: CacheBypass
    isp_tsp |= (bit22_16bit_uv2 & 0b1) << 22           # Bit 22: 16bit_UV2
    isp_tsp |= (bit23_gouraud2 & 0b1) << 23            # Bit 23: Gouraud2
    isp_tsp |= (bit24_offset2 & 0b1) << 24             # Bit 24: Offset2
    isp_tsp |= (bit25_texture2 & 0b1) << 25            # Bit 25: Texture2
    isp_tsp |= (bit26_zwrite_disable & 0b1) << 26      # Bit 26: ZWriteDisable
    isp_tsp |= (bit27_28_culling_mode & 0b11) << 27    # Bits 27-28: CullingMode (2 bits)
    isp_tsp |= (bit29_31_depth_compare_mode & 0b111) << 29  # Bits 29-31: DepthCompareMode (3 bits)

    tsp = 0

    # Initial values for each bit or group of bits
    bit0_2_texture_v_size = 4         # Texture V Size (Height): 3-bits (values 0-7)
    bit3_5_texture_u_size = 5         # Texture U Size (Width): 3-bits (values 0-7)
    bit6_7_texture_shading = 1        # Texture / Shading: 2-bits (values 0-3)
    bit8_11_mipmap_d_adjust = 6      # Mipmap D Adjust: 4-bits (values 0-15)
    bit12_super_sampling = 1          # Super Sampling: 1-bit (set to 1 or 0)
    bit13_14_filter = 3              # Filter: 2-bits (values 0-3)
    bit15_16_clamp_uv = 2            # Clamp UV: 2-bits (values 0-3)
    bit17_18_flip_uv = 2             # Flip UV: 2-bits (values 0-3)
    bit19_ignore_tex_alpha = 0       # Ignore Tex.Alpha: 1-bit (set to 1 or 0)
    bit20_use_alpha = 1              # Use Alpha: 1-bit (set to 1 or 0)
    bit21_color_clamp = 0            # Color Clamp: 1-bit (set to 1 or 0)
    bit22_23_fog_control = 3         # Fog Control: 2-bits (values 0-3)
    bit24_dst_select = 1             # DST Select: 1-bit (set to 1 or 0)
    bit25_src_select = 1             # SRC Select: 1-bit (set to 1 or 0)
    bit26_28_dst_alpha = 5           # DST Alpha: 3-bits (values 0-7)
    bit29_31_src_alpha = 7           # SRC Alpha: 3-bits (values 0-7)

    tsp = (
        (bit0_2_texture_v_size & 7) |
        ((bit3_5_texture_u_size & 7) << 3) |
        ((bit6_7_texture_shading & 3) << 6) |
        ((bit8_11_mipmap_d_adjust & 15) << 8) |
        ((bit12_super_sampling & 1) << 12) |
        ((bit13_14_filter & 3) << 13) |
        ((bit15_16_clamp_uv & 3) << 15) |
        ((bit17_18_flip_uv & 3) << 17) |
        ((bit19_ignore_tex_alpha & 1) << 19) |
        ((bit20_use_alpha & 1) << 20) |
        ((bit21_color_clamp & 1) << 21) |
        ((bit22_23_fog_control & 3) << 22) |
        ((bit24_dst_select & 1) << 24) |
        ((bit25_src_select & 1) << 25) |
        ((bit26_28_dst_alpha & 7) << 26) |
        ((bit29_31_src_alpha & 7) << 29)
    )

    tex_control = 0 

    bit0_24_texture_address = 0       # Texture Address: 25-bits (values 0-33554431), always 0
    bit25_stride_select = 0           # Stride Select: 1-bit (set to 1 or 0)
    bit26_scan_order = 0              # Scan Order: 1-bit (set to 1 or 0)
    bit27_29_pixel_format = 1         # Pixel Format: 3-bits (values 0-7)
    bit30_vq_compressed = 0           # VQ Compressed: 1-bit (set to 1 or 0)
    bit31_mip_mapped = 0              # Mip Mapped: 1-bit (set to 1 or 0)

    tex_control = (
        (bit0_24_texture_address & 0x1FFFFFF) |               # 25-bits for texture address
        ((bit25_stride_select & 1) << 25) |                   # 1-bit for stride select
        ((bit26_scan_order & 1) << 26) |                      # 1-bit for scan order
        ((bit27_29_pixel_format & 7) << 27) |                 # 3-bits for pixel format
        ((bit30_vq_compressed & 1) << 30) |                   # 1-bit for VQ compressed
        ((bit31_mip_mapped & 1) << 31)                        # 1-bit for mip-mapped
    )

    mesh_centroid_x = centroid_x 
    mesh_centroid_y = centroid_y
    mesh_centroid_z = centroid_z 
    mesh_bounding_radius = bounding_radius

    tex_ID = 11  # texture number (0-1000)
    
    tex_shading = -3 # Vertex Colors Mode = -3, Bump Mode = -2, Constant Mode = -1
    tex_ambient = 1  # Ambient lighting
    
    base_color_A = 1 # surface color is RGBA
    base_color_R = 1 
    base_color_G = 1
    base_color_B = 1
    off_color_A = 1  # surface color is RGBA
    off_color_R = 1
    off_color_G = 1
    off_color_B = 1

    # tex_size_shadow = 0x6C  # Example value, adjust as needed
    # tex_filter = 0x24  # Example value for bilinear filtering
    # uv_flip_clamp = 0x00  # Example value, adjust as needed
    # src_dst_alpha = 0x6C  # Example value, adjust as needed
    # tex_color_format = 0  # Example value, adjust as needed
    # spec_light_value = 1  # Example value, adjust as needed
    # light_value = 1  # Example value, adjust as needed
    # transparency_value = 0.0  # Example value, adjust as needed
    # vertex_color_r = 1.0  # Example value, adjust as needed
    # vertex_color_g = 1.0  # Example value, adjust as needed
    # vertex_color_b = 1.0  # Example value, adjust as needed
    # spec_transparency_value = 0.0  # Example value, adjust as needed
    # spec_light_r = 1.0  # Example value, adjust as needed
    # spec_light_g = 1.0  # Example value, adjust as needed
    # spec_light_b = 1.0  # Example value, adjust as needed
    total_mesh_vertex_length = len(vertices)  * 3 * 4  # Number of faces * 3 vertices per face * 4 bytes per vertex

    nl_data.write(struct.pack('<I', mesh_param))     # Mesh Parameter
    nl_data.write(struct.pack('<I', isp_tsp))  # Image Synth & Shading Proc.
    nl_data.write(struct.pack('<I', tsp))  # Texture & Shading Proc.
    nl_data.write(struct.pack('<I', tex_control))  # Texture Control
    nl_data.write(struct.pack('<f', mesh_centroid_x))  # Centroid of mesh, X Coordinate
    nl_data.write(struct.pack('<f', mesh_centroid_y))  # Centroid of mesh, Y Coordinate
    nl_data.write(struct.pack('<f', mesh_centroid_z))  # Centroid of mesh, Z Coordinate
    nl_data.write(struct.pack('<f', mesh_bounding_radius))  # Bounding radius of mesh
    nl_data.write(struct.pack('<i', tex_ID))  # Texture number
    nl_data.write(struct.pack('<i', tex_shading))  # Texture shading
    nl_data.write(struct.pack('<i', tex_ambient))  # Texture ambient lighting
    nl_data.write(struct.pack('<f', base_color_A))  # Base Color - ALPHA
    nl_data.write(struct.pack('<f', base_color_R))  # Base Color - RED
    nl_data.write(struct.pack('<f', base_color_G))  # Base Color - GREEN
    nl_data.write(struct.pack('<f', base_color_B))  # Base Color - BLUE
    nl_data.write(struct.pack('<f', off_color_A))  # Offset Color - ALPHA
    nl_data.write(struct.pack('<f', off_color_R))  # Offset Color - RED
    nl_data.write(struct.pack('<f', off_color_G))  # Offset Color - GREEN
    nl_data.write(struct.pack('<f', off_color_B))  # Offset Color - BLUE
    nl_data.write(struct.pack('<I', total_mesh_vertex_length))  # Total Mesh Vertex data length

    # nl_data.write(struct.pack('<I', spec_light_value))  # Specular light value
    # nl_data.write(struct.pack('<f', light_value))  # Light value
    # nl_data.write(struct.pack('<f', transparency_value))  # Transparency value
    # nl_data.write(struct.pack('<f', vertex_color_r))  # Vertex Color - RED
    # nl_data.write(struct.pack('<f', vertex_color_g))  # Vertex Color - GREEN
    # nl_data.write(struct.pack('<f', vertex_color_b))  # Vertex Color - BLUE
    # nl_data.write(struct.pack('<f', spec_transparency_value))  # Specular Transparency value
    # nl_data.write(struct.pack('<f', spec_light_r))  # Specular Light - RED
    # nl_data.write(struct.pack('<f', spec_light_g))  # Specular Light - GREEN
    # nl_data.write(struct.pack('<f', spec_light_b))  # Specular Light - BLUE


    # 0x50 (80 bytes)

    # End Write Mesh Struct

    # Write Polygon and Vertex Data
    vertex_map = {}
    vertex_counter = 0

    # Face building formula is based on incremental vertex sequence: (0, 1, 2) (1, 2, 3) (2, 3, 4)...
    # 0x08 (8 bytes) each polygon
    for face in faces:

        # total_verts = len(face) if len(face) != 3 else len(face) // 3
        total_verts = len(face)

        # Write Polygon Header
        polygon_type = 0

        bit0_1_culling = 2           # Culling: 2-bits (values 0-3)
        bit2_sprite_quad = 0         # Sprite (Quad): 1-bit (set to 1 or 0)
        bit3_triangles = 0           # Triangles: 1-bit (set to 1 or 0)
        bit4_strip = 1               # Strip: 1-bit (set to 1 or 0)
        bit5_super_index = 1        # Super Index: 1-bit (set to 1 or 0)
        bit6_gouraud = 1             # Gouraud: 1-bit (set to 1 or 0)
        bit7_not_send_gp = 0         # NOT Send GP: 1-bit (set to 1 or 0)
        bit8_env_mapping = 0         # Env. Mapping: 1-bit (set to 1 or 0)
        # Environmental map To enable requires model MAGIC value at offset 0x00, being 0x04 or 0x05

        polygon_type = (
            ((bit0_1_culling & 3) << 0) |                           # 2-bits for Culling
            ((bit2_sprite_quad & 1) << 2) |                         # 1-bit for Sprite (Quad)
            ((bit3_triangles & 1) << 3) |                           # 1-bit for Triangles
            ((bit4_strip & 1) << 4) |                               # 1-bit for Strip
            ((bit5_super_index & 1) << 5) |                         # 1-bit for Super Index
            ((bit6_gouraud & 1) << 6) |                             # 1-bit for Gouraud
            ((bit7_not_send_gp & 1) << 7) |                         # 1-bit for NOT Send GP
            ((bit8_env_mapping & 1) << 8)                           # 1-bit for Env. Mapping
        )

        nl_data.write(struct.pack('<I', polygon_type))  # Polygon Type
        nl_data.write(struct.pack('<I', total_verts))  # Total verts ( Regular-Type ) or Total verts / 3 ( Triple-Type )

        # 0x20 (32 bytes) each type A Vertex, 0x08 (8 bytes) each type B Vertex
        # for i in range(len(face) - 2):
        #     for j in range(3):
        #         vertex_index = face[i + j]
        #         vertex = vertices[vertex_index]
        #         normal = normals[vertex_index]
        #         uv = uvs[vertex_index]

        #         # if vertex_index in vertex_map:
        #         #     # Write Vertex Struct (Type B)
        #         #     type_b_offset = nl_data.tell()
        #         #     vertex_pointer = vertex_map[vertex_index]
        #         #     vertex_offset = type_b_offset - (0xFFFFFFF8 - vertex_pointer)

        #         #     # Ensure vertex_offset is within the valid range for a 32-bit integer
        #         #     vertex_offset = vertex_offset & 0xFFFFFFFF

        #         #     nl_data.write(struct.pack('<I', 0xFFFFFFFF))  # NaN value to detect Type B / Vertex Index Counter
        #         #     nl_data.write(struct.pack('<I', vertex_offset))  # Vertex Pointer

        #         # else:
        #         # Write Vertex Struct (Type A)
        #         nl_data.write(struct.pack('<fff', vertex.x, vertex.y, vertex.z))  # Vertex coordinates
        #         nl_data.write(struct.pack('<fff', normal.x, normal.y, normal.z))  # Normal coordinates
        #         nl_data.write(struct.pack('<ff', uv.x, uv.y))                     # UV coordinates
        #         vertex_map[vertex_index] = vertex_counter
        #         vertex_counter += 1


        
        # Write faces and vertices
        for face in faces:

            face_type = 0x00000000  # Placeholder for face type

            # bit_ppar0_1 = ["clockwise", "counter-clock", "single-side (clockwise)", "double-sided (counter-clockwise)"]
            # bit_ppar6 = ["No (Flat)", "Yes"]
            # bit_ppar7 = ["Send global params", "Don't send global params"]

            # print("bit0-1   | Culling      :[" + str(p_flag_bit0_1) + "] " + bit_ppar0_1[(p_flag_bit0_1)])
            # print("bit2     | Sprite(Quad) :[" + str(p_flag_bit2) + "] " + bit_ny[(p_flag_bit2)])
            # print("bit3     | Triangles    :[" + str(p_flag_bit3) + "] " + bit_ny[(p_flag_bit3)])
            # print("bit4     | Strip        :[" + str(p_flag_bit4) + "] " + bit_ny[(p_flag_bit4)])
            # print("bit5     | Super Index  :[" + str(p_flag_bit5) + "] " + bit_ny[(p_flag_bit5)])
            # print("bit6     | Gouraud      :[" + str(p_flag_bit6) + "] " + bit_ppar6[(p_flag_bit6)])
            # print("bit7     | NOT Send GP  :[" + str(p_flag_bit7) + "] " + bit_ppar7[(p_flag_bit7)])
            # print("bit8     | Env.Mapping  :[" + str(p_flag_bit8) + "] " + bit_ny[(p_flag_bit8)])


            # Define the flags for the polygon type
            bit0_1_culling = 2           # Culling: 2-bits (values 0-3)
            bit2_sprite_quad = 0         # Sprite (Quad): 1-bit (set to 1 or 0)
            bit3_triangles = 0           # Triangles: 1-bit (set to 1 or 0)
            bit4_strip = 1               # Strip: 1-bit (set to 1 or 0)
            bit5_super_index = 1         # Super Index: 1-bit (set to 1 or 0)
            bit6_gouraud = 1             # Gouraud: 1-bit (set to 1 or 0)
            bit7_not_send_gp = 0         # NOT Send GP: 1-bit (set to 1 or 0)
            bit8_env_mapping = 0         # Env. Mapping: 1-bit (set to 1 or 0)

            # Combine the flags into the face_type value
            face_type = (
                ((bit0_1_culling & 3) << 0) |                           # 2-bits for Culling
                ((bit2_sprite_quad & 1) << 2) |                         # 1-bit for Sprite (Quad)
                ((bit3_triangles & 1) << 3) |                           # 1-bit for Triangles
                ((bit4_strip & 1) << 4) |                               # 1-bit for Strip
                ((bit5_super_index & 1) << 5) |                         # 1-bit for Super Index
                ((bit6_gouraud & 1) << 6) |                             # 1-bit for Gouraud
                ((bit7_not_send_gp & 1) << 7) |                         # 1-bit for NOT Send GP
                ((bit8_env_mapping & 1) << 8)                           # 1-bit for Env. Mapping
            )

            write_uint32_buff(face_type)
            write_uint32_buff(len(face) // 3)  # Number of faces

            for vertex_index in face:
                vertex = vertices[vertex_index]
                normal = normals[vertex_index]
                uv = uvs[vertex_index]

                write_point3_buff(vertex)
                write_point3_buff(normal)
                write_point2_buff(uv)


    # End Write Polygon and Vertex Data

    # Write Model End Struct

    # 0x08 (8 bytes)
    total_vertex_count = len(vertices)
    nl_data.write(struct.pack('<I', 0x00000000))  # 00 00 00 00
    nl_data.write(struct.pack('<I', total_vertex_count))  # Total Vertex of model

    return nl_data.getvalue()



########################
# MAIN functions
########################

def main_function_export_file(self, filepath):
    vertices, faces, uvs, normals = collect_data_from_blender()
    nl_data = convert_to_nl_format(vertices, faces, uvs, normals)

    with open(filepath, 'wb') as f:
        f.write(nl_data)

    return True



# def store_nl(mesh_vertices, mesh_uvs, mesh_faces, meshes, mesh_colors, mesh_offcolors, mesh_vertcol, m_headr_grps, gflag_headers, m_backface, m_env, m_centroid, orientation, NegScale_X: bool, debug=False) -> bytes:
#         nlfile = BytesIO()

#         def write_uint32_buff(value):
#             nlfile.write(struct.pack("<I", value))

#         def write_sint32_buff(value):
#             nlfile.write(struct.pack("<i", value))

#         def write_float_buff(value):
#             nlfile.write(struct.pack("<f", value))

#         def write_point3_buff(point):
#             nlfile.write(struct.pack("<fff", *point))

#         def write_point2_buff(point):
#             nlfile.write(struct.pack("<ff", *point))

#         def float_to_sint8(num: float) -> int:
#             min, max = 0x7f, 0x80
#             if num < 0:
#                 return int(num * max + 0x100)
#             else:
#                 return int(num * min)

#         def float_to_col_hex(num: float) -> int:
#             max = 0xFF
#             return int(num * max)

#         # Write magic number
#         nlfile.write(magic_naomilib[0])

#         # Write Global_Flag0
#         gflag0 = gflag_headers[0]
#         nlfile.write(gflag0.to_bytes(1, 'little'))

#         # Write Global_Flag1
#         gflag1 = (
#             (gflag_headers[1] << 1) |
#             (gflag_headers[2] << 2) |
#             (gflag_headers[3] << 3) |
#             (gflag_headers[4] << 4)
#         )
#         nlfile.write(gflag1.to_bytes(2, 'little'))

#         # Write Object Centroid
#         write_float_buff(m_centroid[0][0])
#         write_float_buff(m_centroid[0][1])
#         write_float_buff(m_centroid[0][2])
#         write_float_buff(m_centroid[0][3])

#         # Write mesh parameters
#         for i, mesh in enumerate(meshes):
#             m_headr_grp = m_headr_grps[i]

#             # Write mesh parameters bit0-31
#             m_pflag = (
#                 (m_headr_grp[0][0] << 29) |
#                 (m_headr_grp[0][1] << 28) |
#                 (m_headr_grp[0][2] << 24) |
#                 (m_headr_grp[0][3] << 23) |
#                 (m_headr_grp[0][4] << 18) |
#                 (m_headr_grp[0][5] << 16) |
#                 (m_headr_grp[0][6] << 7) |
#                 (m_headr_grp[0][7] << 6) |
#                 (m_headr_grp[0][8] << 4) |
#                 (m_headr_grp[0][9] << 3) |
#                 (m_headr_grp[0][10] << 2) |
#                 (m_headr_grp[0][11] << 1) |
#                 (m_headr_grp[0][12] << 0)
#             )
#             write_uint32_buff(m_pflag)

#             # Write mesh parameters bit20-31
#             m_isptspflag = (
#                 (m_headr_grp[1][0] << 29) |
#                 (m_headr_grp[1][1] << 27) |
#                 (m_headr_grp[1][2] << 26) |
#                 (m_headr_grp[1][3] << 25) |
#                 (m_headr_grp[1][4] << 24) |
#                 (m_headr_grp[1][5] << 23) |
#                 (m_headr_grp[1][6] << 22) |
#                 (m_headr_grp[1][7] << 21) |
#                 (m_headr_grp[1][8] << 20)
#             )
#             write_uint32_buff(m_isptspflag)

#             # Write mesh tsp parameters bit0-31
#             m_tspflag = (
#                 (m_headr_grp[2][0] << 29) |
#                 (m_headr_grp[2][1] << 26) |
#                 (m_headr_grp[2][2] << 25) |
#                 (m_headr_grp[2][3] << 24) |
#                 (m_headr_grp[2][4] << 22) |
#                 (m_headr_grp[2][5] << 21) |
#                 (m_headr_grp[2][6] << 20) |
#                 (m_headr_grp[2][7] << 19) |
#                 (m_headr_grp[2][8] << 17) |
#                 (m_headr_grp[2][9] << 15) |
#                 (m_headr_grp[2][10] << 13) |
#                 (m_headr_grp[2][11] << 12) |
#                 (m_headr_grp[2][12] << 8) |
#                 (m_headr_grp[2][13] << 6) |
#                 (m_headr_grp[2][14] << 3) |
#                 (m_headr_grp[2][15] << 0)
#             )
#             write_uint32_buff(m_tspflag)

#             # Write texture control bit0-31
#             m_tctflag = (
#                 (m_headr_grp[3][0] << 31) |
#                 (m_headr_grp[3][1] << 30) |
#                 (m_headr_grp[3][2] << 27) |
#                 (m_headr_grp[3][3] << 26) |
#                 (m_headr_grp[3][4] << 25) |
#                 (m_headr_grp[3][5] << 0)
#             )
#             write_uint32_buff(m_tctflag)

#             # Write mesh centroid x,y,z, bound radius
#             write_float_buff(m_centroid[i][0])
#             write_float_buff(m_centroid[i][1])
#             write_float_buff(m_centroid[i][2])
#             write_float_buff(m_centroid[i][3])

#             # Write texture ID
#             write_sint32_buff(m_headr_grp[4])

#             # Write texture shading
#             write_sint32_buff(m_headr_grp[5])

#             # Write texture ambient lighting
#             write_float_buff(0.0)  # Placeholder for ambient lighting

#             # Write base color ARGB
#             write_float_buff(mesh_colors[i][3])
#             write_float_buff(mesh_colors[i][0])
#             write_float_buff(mesh_colors[i][1])
#             write_float_buff(mesh_colors[i][2])

#             # Write offset color ARGB
#             write_float_buff(mesh_offcolors[i][3])
#             write_float_buff(mesh_offcolors[i][0])
#             write_float_buff(mesh_offcolors[i][1])
#             write_float_buff(mesh_offcolors[i][2])

#             # Write mesh size
#             mesh_size = len(mesh_faces[i]) * 3 * 4  # Number of faces * 3 vertices per face * 4 bytes per vertex
#             write_uint32_buff(mesh_size)

#             # Write faces and vertices
#             for face in mesh_faces[i]:

#                 face_type = 0x00000000  # Placeholder for face type

#                 # Define the flags for the polygon type
#                 bit0_1_culling = 2           # Culling: 2-bits (values 0-3)
#                 bit2_sprite_quad = 0         # Sprite (Quad): 1-bit (set to 1 or 0)
#                 bit3_triangles = 1           # Triangles: 1-bit (set to 1 or 0)
#                 bit4_strip = 0               # Strip: 1-bit (set to 1 or 0)
#                 bit5_super_index = 1         # Super Index: 1-bit (set to 1 or 0)
#                 bit6_gouraud = 1             # Gouraud: 1-bit (set to 1 or 0)
#                 bit7_not_send_gp = 0         # NOT Send GP: 1-bit (set to 1 or 0)
#                 bit8_env_mapping = 0         # Env. Mapping: 1-bit (set to 1 or 0)

#                 # Combine the flags into the face_type value
#                 face_type = (
#                     ((bit0_1_culling & 3) << 0) |                           # 2-bits for Culling
#                     ((bit2_sprite_quad & 1) << 2) |                         # 1-bit for Sprite (Quad)
#                     ((bit3_triangles & 1) << 3) |                           # 1-bit for Triangles
#                     ((bit4_strip & 1) << 4) |                               # 1-bit for Strip
#                     ((bit5_super_index & 1) << 5) |                         # 1-bit for Super Index
#                     ((bit6_gouraud & 1) << 6) |                             # 1-bit for Gouraud
#                     ((bit7_not_send_gp & 1) << 7) |                         # 1-bit for NOT Send GP
#                     ((bit8_env_mapping & 1) << 8)                           # 1-bit for Env. Mapping
#                 )

#                 write_uint32_buff(face_type)
#                 write_uint32_buff(len(face) // 3)  # Number of faces

#                 for vertex_index in face:
#                     vertex = mesh_vertices[i][vertex_index]
#                     normal = mesh_vertcol[i][vertex_index]
#                     uv = mesh_uvs[i][vertex_index]

#                     write_point3_buff(vertex)
#                     write_point3_buff(normal)
#                     write_point2_buff(uv)

#         return nlfile.getvalue()