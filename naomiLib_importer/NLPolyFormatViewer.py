import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import os

import NLPolyFormat
import NLPolyFormatReader

rotation_x, rotation_y = 0, 0
zoom_level = -0.5
wireframe_mode = False
show_normals = False
show_vertices = False
chr_path = 'C:\\Users\\desktop\\source\\repos\\blender-NaomiLib'

current_file = None

rotate_left = False
rotate_right = False
rotate_up = False
rotate_down = False

def physical_offset(ref_vert_offset, vertex_pointer):
    return ref_vert_offset - (0xFFFFFFF8 - vertex_pointer)

def get_indexed_vertex(vertex):
    global current_file
    if len(vertex) == 2:
        ref_offset = physical_offset(vertex[1], vertex[0][1])
        vertex = current_file.get_indexed_vertex(ref_offset)
    return vertex

def load_texture(file_path):
    texture_surface = pygame.image.load(file_path)
    texture_data = pygame.image.tostring(texture_surface, "RGB", 1)
    width, height = texture_surface.get_size()

    glEnable(GL_TEXTURE_2D)
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, texture_data)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    return texture_id

def aim_camera(camera_loc, aim_at_loc):
    glLoadIdentity()
    gluLookAt(camera_loc[0], camera_loc[1], camera_loc[2],  # Camera position
              aim_at_loc[0], aim_at_loc[1], aim_at_loc[2],  # Look at the center point
              0, 1, 0)   

def setup_lighting():
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, (0, 0, 10, 0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (1, 1, 1, 1))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (1, 1, 1, 1))
    glMaterialfv(GL_FRONT, GL_SPECULAR, (1, 1, 1, 1))
    glMaterialfv(GL_FRONT, GL_SHININESS, 50)

def render(nl_polyformat_files):
    global current_file

    pygame.init()
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)

    glClearColor(0.2, 0.3, 0.3, 1.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, (display[0] / display[1]), 0.1, 50.0)

    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)  # Depth test passes if the fragment is closer

    setup_lighting()

    glMatrixMode(GL_MODELVIEW)

    while True:

        handle_events()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glLoadIdentity()
        glTranslatef(0, 0, zoom_level)
        glRotatef(rotation_x, 1, 0, 0)
        glRotatef(rotation_y, 0, 1, 0)

        for file in nl_polyformat_files:
            current_file = file
            for model in file.models:
                glPushMatrix()

                # Set model center point
                center_point = model.mesh_center_point
                glTranslatef(center_point[0], center_point[1], center_point[2])
                if model.tex_pvf_index != 0xFFFFFFFF:
                    texture_file = f'{chr_path}/textures/TexID_{model.tex_pvf_index:03}.bmp'
                    texture_id = load_texture(texture_file)
                    glBindTexture(GL_TEXTURE_2D, texture_id)

                for polygon in model.polygons:
                    polygon.vertices = [get_indexed_vertex(vert) for vert in polygon.vertices]

                draw(model.polygons)
                glPopMatrix()

        pygame.display.flip()
        pygame.time.wait(10)

def handle_events():
    global rotate_left
    global rotate_right
    global rotate_up
    global rotate_down
    global zoom_level
    global wireframe_mode
    global show_normals
    global show_vertices
    global rotation_y
    global rotation_x

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            return
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                wireframe_mode = not wireframe_mode
            elif event.key == pygame.K_2:
                show_vertices = not show_vertices
            elif event.key == pygame.K_3:
                show_normals = not show_normals
            elif event.key == pygame.K_LEFT:
                rotate_left = True
            elif event.key == pygame.K_RIGHT:
                rotate_right = True
            elif event.key == pygame.K_UP:
                rotate_up = True
            elif event.key == pygame.K_DOWN:
                rotate_down = True
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_LEFT:
                rotate_left = False
            elif event.key == pygame.K_RIGHT:
                rotate_right = False
            elif event.key == pygame.K_UP:
                rotate_up = False
            elif event.key == pygame.K_DOWN:
                rotate_down = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # Scroll up
                zoom_level += 0.1
            elif event.button == 5:  # Scroll down
                zoom_level -= 0.1

    if rotate_left:
        rotation_y -= 10
    if rotate_right:
        rotation_y += 10
    if rotate_up:
        rotation_x -= 10
    if rotate_down:
        rotation_x += 10

def draw(polygons):
    if wireframe_mode:
        glDisable(GL_LIGHTING)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
    else:
        glEnable(GL_LIGHTING)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    for polygon in polygons:
        vertices = polygon.vertices

        if polygon.triangle:
            glBegin(GL_TRIANGLES)
            for i in range(len(vertices)):
                vertex = get_indexed_vertex(vertices[i])
                x, y, z = vertex[0], vertex[1], vertex[2]
                nx, ny, nz = vertex[3], vertex[4], vertex[5]
                u, v = vertex[6], vertex[7]

                glNormal3f(nx, ny, nz)
                glTexCoord2f(u, v)
                glVertex3f(x, y, z)
            glEnd()
        elif polygon.sprite:
            glBegin(GL_QUADS)
            for i in range(len(vertices)):
                vertex = get_indexed_vertex(vertices[i])
                x, y, z = vertex[0], vertex[1], vertex[2]
                nx, ny, nz = vertex[3], vertex[4], vertex[5]
                u, v = vertex[6], vertex[7]

                glNormal3f(nx, ny, nz)
                glTexCoord2f(u, v)
                glVertex3f(x, y, z)
            glEnd()
        else:
            glBegin(GL_TRIANGLE_STRIP)
            for i in range(len(vertices) - 2):
                for j in range(3):
                    vertex = get_indexed_vertex(vertices[i + j])
                    x, y, z = vertex[0], vertex[1], vertex[2]
                    nx, ny, nz = vertex[3], vertex[4], vertex[5]
                    u, v = vertex[6], vertex[7]

                    glNormal3f(nx, ny, nz)
                    glTexCoord2f(u, v)
                    glVertex3f(x, y, z)
            glEnd()
        display_options(vertices)

def display_options(vertices):
    glDisable(GL_LIGHTING)
    if show_normals:
        glColor3f(1.0, 0.0, 0.0)  # Set color to red
        glLineWidth(1)
        glBegin(GL_LINES)
        for vertex in vertices:
            vertex = get_indexed_vertex(vertex)
            x, y, z = vertex[0], vertex[1], vertex[2]
            nx, ny, nz = vertex[3], vertex[4], vertex[5]

            glVertex3f(x, y, z)
            glVertex3f(x + nx * 0.1, y + ny * 0.1, z + nz * 0.1)
        glEnd()
        glLineWidth(1)
        glColor3f(1.0, 1.0, 1.0)  # Set color to red

    if show_vertices:
        glColor3f(1.0, 0.0, 0.0)  # Set color to red
        glPointSize(3)
        glBegin(GL_POINTS)
        for vertex in vertices:
            vertex = get_indexed_vertex(vertex)
            x, y, z = vertex[0], vertex[1], vertex[2]
            glVertex3f(x, y, z)
        glEnd()
        glPointSize(1)
        glColor3f(1.0, 1.0, 1.0)  # Set color to red
    glEnable(GL_LIGHTING)

def get_files_from_path(path, extension=".bin"):
    return [os.path.join(path, f) for f in os.listdir(path) if f.endswith(extension)]

file_paths = get_files_from_path(chr_path)

nl_polyformat_files = []

for file_path in file_paths:
    nl_reader = NLPolyFormatReader.NLReader(file_path)
    nl_polyformat_file = nl_reader.read()
    nl_polyformat_files.append(nl_polyformat_file)

    print(f"NL File: {file_path}")
    print(f"Vertex Count: {nl_polyformat_file.get_vertex_count()}")

render(nl_polyformat_files)
